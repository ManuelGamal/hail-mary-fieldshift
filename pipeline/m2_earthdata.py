"""Lane 1 / M2: NASA Earthdata (LP DAAC) ingest on Kaggle, needs Secret EARTHDATA_TOKEN attached to the kernel.

1. HLS v2.0 (HLSS30/HLSL30) backfill for seasons Planetary Computer lacks (2016-2020), written in exactly the
   m2_ingest.py format: hls/comp_{site}_{season}.npy, hls/stats_{site}_{season}.npz (+ grid_{site}.json).
2. ECOSTRESS Collection 2 tiled products per site x season on the 90 m block grid:
   eco/eco_{site}_{season}.npz  et_daily_mean (JET ETdaily, mm/day), et_n, lst_mean_c (L2T LSTE), lst_n,
                                esi_mean (L4T ESI), esi_n   (clear = cloud layer 0, finite value)
LP DAAC answers a bearer-token request with a 303 to a signed S3 URL; we resolve that ourselves and read the
signed URL with no auth header (GDAL would otherwise forward the token to S3 and fail).
"""

import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

if os.path.exists("/kaggle"):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "rasterio"], check=False
    )

import numpy as np
import pandas as pd
import rasterio
import requests
from kaggle_secrets import UserSecretsClient
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

TOK = UserSecretsClient().get_secret("EARTHDATA_TOKEN")
AUTH = {"Authorization": f"Bearer {TOK}"}
T0 = time.time()
WORK = "/kaggle/working"
OUT_H, OUT_E = os.path.join(WORK, "hls"), os.path.join(WORK, "eco")
os.makedirs(OUT_H, exist_ok=True)
os.makedirs(OUT_E, exist_ok=True)
CRS, BLOCK = "EPSG:32636", 90
FAO_URL = "https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-CROP-TYPE/"
BANDS = {
    "HLSS30": ["B02", "B03", "B04", "B8A", "B11", "B12"],
    "HLSL30": ["B02", "B03", "B04", "B05", "B06", "B07"],
}
os.environ.update(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    GDAL_HTTP_MAX_RETRY="5",
    GDAL_HTTP_RETRY_DELAY="2",
    GDAL_HTTP_MULTIRANGE="YES",
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
    VSI_CACHE="TRUE",
)
QA = {"hls": {}, "eco": {}, "timings_s": {}, "failed": {}}
SESSION = requests.Session()


def seasons(years):
    out = {}
    for y in years:
        out[f"W{y}"] = (pd.Timestamp(f"{y - 1}-11-01"), 7)
        out[f"S{y}"] = (pd.Timestamp(f"{y}-05-16"), 6)
    return out


ALL = seasons(range(2016, 2026))
HLS_TODO = {
    s: ["W2016", "S2016", "W2017", "S2017", "W2018", "S2018", "W2019", "S2019", "W2020"]
    for s in ("SGZ", "ZAN")
}
_ECO_SEASONS = [f"S{y}" for y in range(2018, 2026)] + [f"W{y}" for y in range(2019, 2026)]  # ECOSTRESS from mid-2018
ECO_TODO = {"SGZ": _ECO_SEASONS, "ZAN": _ECO_SEASONS, "MLL": ["S2023", "W2024", "S2024"]}


def site_grid(site):
    p = os.path.join(WORK, f"{site}.2024.GS1.tif")
    if not os.path.exists(p):
        r = requests.get(
            FAO_URL + f"WAPOR-3.L3-CROP-TYPE.EGY-{site}.2024.GS1.tif", timeout=120
        )
        r.raise_for_status()
        open(p, "wb").write(r.content)
    with rasterio.open(p) as src:
        b = src.bounds
    x0, y0, x1, y1 = transform_bounds("EPSG:4326", CRS, *b)
    x0, y0 = math.floor(x0 / BLOCK) * BLOCK, math.floor(y0 / BLOCK) * BLOCK
    x1, y1 = math.ceil(x1 / BLOCK) * BLOCK, math.ceil(y1 / BLOCK) * BLOCK
    NR, NC = int((y1 - y0) / BLOCK), int((x1 - x0) / BLOCK)
    g = {
        "x0": x0,
        "y1": y1,
        "res": 30,
        "H": NR * 3,
        "W": NC * 3,
        "NR": NR,
        "NC": NC,
        "crs": CRS,
        "bbox4326": list(b),
    }
    json.dump(g, open(os.path.join(OUT_H, f"grid_{site}.json"), "w"))
    return g


def cmr(short, start, end, bbox, cloud=None):
    out, page = [], 1
    while True:
        p = {
            "short_name": short,
            "bounding_box": ",".join(map(str, bbox)),
            "page_size": 2000,
            "page_num": page,
            "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
        }
        if cloud is not None:
            p["cloud_cover"] = f"0,{cloud}"
        r = SESSION.get(
            "https://cmr.earthdata.nasa.gov/search/granules.json", params=p, timeout=120
        )
        r.raise_for_status()
        e = r.json()["feed"]["entry"]
        out += e
        if len(e) < 2000:
            return out
        page += 1


def tifs(entry):
    return {
        l_["href"].rsplit("/", 1)[-1]: l_["href"]
        for l_ in entry.get("links", [])
        if l_["href"].startswith("https") and l_["href"].endswith(".tif")
    }


def signed(href):
    for attempt in range(4):
        try:
            r = SESSION.get(href, headers=AUTH, allow_redirects=False, timeout=60)
            if r.status_code in (302, 303, 307):
                return r.headers["Location"]
            raise RuntimeError(f"status {r.status_code}")
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def read(href, tr, h, w, resampling=Resampling.nearest):
    for attempt in range(4):
        try:
            with rasterio.open("/vsicurl/" + signed(href)) as src:
                with WarpedVRT(
                    src,
                    crs=CRS,
                    transform=tr,
                    width=w,
                    height=h,
                    resampling=resampling,
                    nodata=src.nodata,
                ) as vrt:
                    return vrt.read(1, masked=False), src.nodata
        except Exception as e:
            if attempt == 3:
                print("read failed", href[-70:], repr(e)[:120], flush=True)
                return None, None
            time.sleep(2 * (attempt + 1))


# ---------------------------------------------------------------- 1. HLS backfill
def hls_date(entries, g):
    tr = from_origin(g["x0"], g["y1"], 30, 30)
    out = np.full((6, g["H"], g["W"]), np.nan, np.float32)
    for e in entries:
        short = "HLSS30" if ".S30." in (e.get("producer_granule_id") or e.get("title", "")) else "HLSL30"
        t = tifs(e)
        get = lambda band: next(
            (v for k, v in t.items() if k.endswith(f".{band}.tif")), None
        )
        fm_h = get("Fmask")
        if not fm_h:
            continue
        fm, _ = read(fm_h, tr, g["H"], g["W"])
        if fm is None:
            continue
        clear = ((fm & 0b00011111) == 0) & (fm != 255)
        if clear.mean() < 0.01:
            continue
        stack = []
        for band in BANDS[short]:
            h_ = get(band)
            a, nod = read(h_, tr, g["H"], g["W"]) if h_ else (None, None)
            if a is None:
                stack = None
                break
            clear &= a != nod
            stack.append(a.astype(np.float32) * 1e-4)
        if stack is None:
            continue
        s = np.stack(stack)
        clear &= (s[2] > 0) & (s[3] > 0) & (s[1] > 0)
        s[:, ~clear] = np.nan
        fill = np.isnan(out[3]) & clear
        out[:, fill] = s[:, fill]
    return out


def hls_season(site, sid, g):
    t = time.time()
    start, steps = ALL[sid]
    end = start + pd.Timedelta(days=28 * steps - 1)
    ents = []
    for short in BANDS:
        ents += cmr(short, start.date(), end.date(), g["bbox4326"], cloud=80)
    by_date = defaultdict(list)
    for e in ents:
        by_date[pd.Timestamp(e["time_start"]).date()].append(e)
    dates = sorted(by_date)
    H, W = g["H"], g["W"]
    comp = np.full((steps, 6, H, W), -9999, np.int16)
    peak_nd = np.full((H, W), np.nan, np.float32)
    peak_gc = np.full((H, W), np.nan, np.float32)
    sum_nd = np.zeros((H, W), np.float32)
    n_cl = np.zeros((H, W), np.int16)
    with ThreadPoolExecutor(24) as ex:
        for k in range(steps):
            s0 = start + pd.Timedelta(days=28 * k)
            s1 = s0 + pd.Timedelta(days=28)
            ds = [d for d in dates if s0.date() <= d < s1.date()]
            arrs = list(ex.map(lambda d: hls_date(by_date[d], g), ds))
            if not arrs:
                continue
            st = np.stack(arrs)
            with np.errstate(all="ignore"):
                nd = (st[:, 3] - st[:, 2]) / (st[:, 3] + st[:, 2])
                gc = st[:, 3] / st[:, 1] - 1
                med = np.nanmedian(st, axis=0)
                peak_nd = np.fmax(peak_nd, np.nanmax(nd, axis=0))
                peak_gc = np.fmax(peak_gc, np.nanmax(gc, axis=0))
            ok = ~np.isnan(nd)
            sum_nd += np.where(ok, nd, 0).sum(0)
            n_cl += ok.sum(0).astype(np.int16)
            comp[k] = np.where(
                np.isnan(med), -9999, np.clip(med * 1e4, -9998, 32767)
            ).astype(np.int16)
            del st, arrs
    with np.errstate(all="ignore"):
        mean_nd = np.where(n_cl > 0, sum_nd / n_cl, np.nan).astype(np.float32)
    np.save(os.path.join(OUT_H, f"comp_{site}_{sid}.npy"), comp)
    np.savez_compressed(
        os.path.join(OUT_H, f"stats_{site}_{sid}.npz"),
        peak_ndvi=peak_nd,
        peak_gcvi=peak_gc,
        mean_ndvi=mean_nd,
        n_clear=n_cl,
        start=str(start.date()),
        end=str(end.date()),
    )
    valid = (comp[:, 3] != -9999).mean(axis=(1, 2))
    QA["hls"][f"{site}_{sid}"] = {
        "items": len(ents),
        "dates": len(dates),
        "step_valid_frac": [round(float(v), 3) for v in valid],
        "median_n_clear": float(np.median(n_cl)),
        "source": "LP DAAC",
    }
    QA["timings_s"][f"hls_{site}_{sid}"] = round(time.time() - t, 1)
    print(
        f"[{time.time() - T0:6.0f}s] HLS {site} {sid}: {len(dates)} dates, valid {QA['hls'][f'{site}_{sid}']['step_valid_frac']}, "
        f"{time.time() - t:.0f}s",
        flush=True,
    )


# ---------------------------------------------------------------- 2. ECOSTRESS on the 90 m block grid
ECO = {
    "et": ("ECO_L3T_JET", "_ETdaily.tif", "_cloud.tif"),
    "lst": ("ECO_L2T_LSTE", "_LST.tif", "_cloud.tif"),
    "esi": ("ECO_L4T_ESI", "_ESI.tif", "_cloud.tif"),
}


def eco_one(entry, suffix, cloud_suffix, g):
    tr = from_origin(g["x0"], g["y1"], BLOCK, BLOCK)
    t = tifs(entry)
    vh = next((v for k, v in t.items() if k.endswith(suffix)), None)
    ch = next((v for k, v in t.items() if k.endswith(cloud_suffix)), None)
    if not vh:
        return None
    v, nod = read(vh, tr, g["NR"], g["NC"], Resampling.average)
    if v is None:
        return None
    v = v.astype(np.float32)
    if nod is not None and not np.isnan(nod):
        v[v == nod] = np.nan
    if ch:
        c, _ = read(ch, tr, g["NR"], g["NC"], Resampling.max)
        if c is not None:
            v[c > 0] = np.nan
    return v


def eco_season(site, sid, g):
    t = time.time()
    start, steps = ALL[sid]
    end = start + pd.Timedelta(days=28 * steps - 1)
    res = {"start": str(start.date()), "end": str(end.date())}
    with ThreadPoolExecutor(16) as ex:
        for var, (short, suf, csuf) in ECO.items():
            ents = cmr(short, start.date(), end.date(), g["bbox4326"])
            arrs = [
                a
                for a in ex.map(lambda e: eco_one(e, suf, csuf, g), ents)
                if a is not None
            ]
            if arrs:
                st = np.stack(arrs)
                if var == "lst":
                    st = st - 273.15
                    st[(st < -20) | (st > 75)] = np.nan
                if var == "et":
                    st[(st < 0) | (st > 20)] = np.nan
                with np.errstate(all="ignore"):
                    res[f"{var}_mean"] = np.nanmean(st, 0).astype(np.float32)
                res[f"{var}_n"] = (~np.isnan(st)).sum(0).astype(np.int16)
            QA["eco"].setdefault(f"{site}_{sid}", {})[var] = {
                "granules": len(ents),
                "read": len(arrs),
            }
    np.savez_compressed(os.path.join(OUT_E, f"eco_{site}_{sid}.npz"), **res)
    QA["timings_s"][f"eco_{site}_{sid}"] = round(time.time() - t, 1)
    print(
        f"[{time.time() - T0:6.0f}s] ECO {site} {sid}: {QA['eco'][f'{site}_{sid}']}, {time.time() - t:.0f}s",
        flush=True,
    )


GRIDS = {s: site_grid(s) for s in ("SGZ", "ZAN", "MLL")}
jobs = [
    ("eco", s, sid) for s in ECO_TODO for sid in ECO_TODO[s]
]  # ECOSTRESS first: small and needed by Lane 2
jobs += [("hls", s, sid) for s in HLS_TODO for sid in HLS_TODO[s]]
for kind, site, sid in jobs:
    try:
        (eco_season if kind == "eco" else hls_season)(site, sid, GRIDS[site])
    except Exception as e:
        QA["failed"][f"{kind}_{site}_{sid}"] = repr(e)[:300]
        print("FAILED", kind, site, sid, repr(e)[:200], flush=True)
    json.dump(QA, open(os.path.join(WORK, "earthdata_qa.json"), "w"), indent=1)
QA["total_runtime_s"] = round(time.time() - T0, 1)
json.dump(QA, open(os.path.join(WORK, "earthdata_qa.json"), "w"), indent=1)
print("DONE", QA["total_runtime_s"], "failed:", QA["failed"])
