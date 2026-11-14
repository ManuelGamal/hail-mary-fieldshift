"""Lane 1 / M2 step 6: HLS ingest 2016-2025 for SGZ + ZAN (+ MLL 2023-24), Kaggle CPU.

For every site x season it writes, on the 30 m UTM grid that M1 uses (same origin, so block ids match):
  comp_{site}_{season}.npy    int16 [T, 6, H, W]  per-step median clear-sky reflectance x1e4 (-9999 = no data)
                              bands = Prithvi order: blue, green, red, nir_narrow, swir1, swir2
                              T = 7 steps of 28 days (winter, from Nov 1) or 6 steps (summer, from May 16)
  stats_{site}_{season}.npz   peak_ndvi, peak_gcvi, mean_ndvi, n_clear (30 m), plus the season's date span
  grid_{site}.json            x0, y1, res, H, W, NR, NC (90 m blocks), crs
  ingest_qa.json              items/dates per season, timings
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
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "pystac-client",
            "planetary-computer",
            "rasterio",
        ],
        check=False,
    )

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

T0 = time.time()
WORK = "/kaggle/working" if os.path.exists("/kaggle") else os.path.abspath("work")
OUT = os.path.join(WORK, "hls")
os.makedirs(OUT, exist_ok=True)
CRS = "EPSG:32636"
BLOCK, RES = 90, 30
FAO_URL = "https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-CROP-TYPE/"
BANDS = {  # Prithvi-EO-2.0 band order
    "hls2-s30": ["B02", "B03", "B04", "B8A", "B11", "B12"],
    "hls2-l30": ["B02", "B03", "B04", "B05", "B06", "B07"],
}
GDAL_ENV = dict(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    GDAL_HTTP_MULTIRANGE="YES",
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
    VSI_CACHE="TRUE",
    GDAL_HTTP_MAX_RETRY="5",
    GDAL_HTTP_RETRY_DELAY="2",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
)


def seasons(years):
    """W{y}: Nov 1 (y-1) .. May 15 y, 7 x 28 d.  S{y}: May 16 y .. Oct 30 y, 6 x 28 d."""
    out = {}
    for y in years:
        out[f"W{y}"] = (pd.Timestamp(f"{y - 1}-11-01"), 7)
        out[f"S{y}"] = (pd.Timestamp(f"{y}-05-16"), 6)
    return out


SITES = {
    "SGZ": seasons(range(2016, 2026)),
    "ZAN": seasons(range(2016, 2026)),
    "MLL": {
        k: v
        for k, v in seasons([2023, 2024]).items()
        if k in ("S2023", "W2024", "S2024")
    },
}
QA = {"seasons": {}, "timings_s": {}}


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
        "res": RES,
        "H": NR * 3,
        "W": NC * 3,
        "NR": NR,
        "NC": NC,
        "crs": CRS,
        "bbox4326": list(b),
    }
    json.dump(g, open(os.path.join(OUT, f"grid_{site}.json"), "w"))
    return g


def read_band(href, g):
    tr = from_origin(g["x0"], g["y1"], RES, RES)
    for attempt in range(4):
        try:
            with rasterio.Env(**GDAL_ENV), rasterio.open(pc.sign(href)) as src:
                with WarpedVRT(
                    src,
                    crs=CRS,
                    transform=tr,
                    width=g["W"],
                    height=g["H"],
                    resampling=Resampling.nearest,
                    nodata=src.nodata,
                ) as vrt:
                    return vrt.read(1), src.nodata
        except Exception as e:
            if attempt == 3:
                print("read failed", href[-60:], repr(e)[:100], flush=True)
                return None, None
            time.sleep(2 * (attempt + 1))


def read_date(items, g):
    """Merge all tiles/sensors of one date -> float32 [6, H, W] reflectance, NaN where not clear."""
    out = np.full((6, g["H"], g["W"]), np.nan, np.float32)
    for it in items:
        fm, _ = read_band(it.assets["Fmask"].href, g)
        if fm is None:
            continue
        clear = ((fm & 0b00011111) == 0) & (fm != 255)
        if clear.mean() < 0.01:
            continue
        stack = []
        for band in BANDS[it.collection_id]:
            a, nod = read_band(it.assets[band].href, g)
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


def ingest(site, sid, start, steps, g, cat):
    t = time.time()
    end = start + pd.Timedelta(days=28 * steps - 1)
    items = list(
        cat.search(
            collections=list(BANDS),
            bbox=g["bbox4326"],
            datetime=f"{start.date()}/{end.date()}",
            query={"eo:cloud_cover": {"lt": 80}},
        ).items()
    )
    by_date = defaultdict(list)
    for it in items:
        by_date[it.datetime.date()].append(it)
    dates = sorted(by_date)
    H, W = g["H"], g["W"]
    comp = np.full((steps, 6, H, W), -9999, np.int16)
    peak_nd = np.full((H, W), np.nan, np.float32)
    peak_gc = np.full((H, W), np.nan, np.float32)
    sum_nd = np.zeros((H, W), np.float32)
    n_cl = np.zeros((H, W), np.int16)
    with ThreadPoolExecutor(16) as ex:
        for k in range(steps):
            s0 = start + pd.Timedelta(days=28 * k)
            s1 = s0 + pd.Timedelta(days=28)
            ds = [d for d in dates if s0.date() <= d < s1.date()]
            arrs = list(ex.map(lambda d: read_date(by_date[d], g), ds))
            if not arrs:
                continue
            st = np.stack(arrs)  # [n, 6, H, W]
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
    np.save(os.path.join(OUT, f"comp_{site}_{sid}.npy"), comp)
    np.savez_compressed(
        os.path.join(OUT, f"stats_{site}_{sid}.npz"),
        peak_ndvi=peak_nd,
        peak_gcvi=peak_gc,
        mean_ndvi=mean_nd,
        n_clear=n_cl,
        start=str(start.date()),
        end=str(end.date()),
    )
    valid = (comp[:, 3] != -9999).mean(axis=(1, 2))
    QA["seasons"][f"{site}_{sid}"] = {
        "items": len(items),
        "dates": len(dates),
        "step_valid_frac": [round(float(v), 3) for v in valid],
        "median_n_clear": float(np.median(n_cl)),
    }
    QA["timings_s"][f"{site}_{sid}"] = round(time.time() - t, 1)
    print(
        f"[{time.time() - T0:7.0f}s] {site} {sid}: {len(dates)} dates, step valid {QA['seasons'][f'{site}_{sid}']['step_valid_frac']}, "
        f"{time.time() - t:.0f}s",
        flush=True,
    )
    json.dump(QA, open(os.path.join(OUT, "ingest_qa.json"), "w"), indent=1)


cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
# do the labelled seasons first so a timeout still leaves the training data
PRIORITY = ["S2023", "W2024", "S2024"]
for site, ss in SITES.items():
    g = site_grid(site)
    print(site, "grid", g["H"], "x", g["W"], flush=True)
    order = [s for s in PRIORITY if s in ss] + [s for s in ss if s not in PRIORITY]
    for sid in order:
        if os.path.exists(os.path.join(OUT, f"stats_{site}_{sid}.npz")):
            continue
        start, steps = ss[sid]
        try:
            ingest(site, sid, start, steps, g, cat)
        except Exception as e:
            QA.setdefault("failed", {})[f"{site}_{sid}"] = repr(e)[:300]
            print("FAILED", site, sid, repr(e)[:200], flush=True)
QA["total_runtime_s"] = round(time.time() - T0, 1)
json.dump(QA, open(os.path.join(OUT, "ingest_qa.json"), "w"), indent=1)
print("DONE", QA["total_runtime_s"], "s; failed:", QA.get("failed"))
