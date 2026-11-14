"""Artefact schemas v1 (see docs/agents/00-shared-contract.md). Additive changes only."""

import pandas as pd

SCHEMA_VERSION = 1
CROPS = {
    "wheat",
    "clover",
    "sugarbeet",
    "beans",
    "flax",
    "rice",
    "maize",
    "cotton",
    "veg",
    "orchard",
    "other",
    "nonag",
}

# column -> (kind, nullable); kind in {"str", "int", "float", "bool"}
SCHEMAS = {
    "blocks": {
        "block_id": ("str", False),
        "site": ("str", False),
        "row": ("int", False),
        "col": ("int", False),
        "lon": ("float", False),
        "lat": ("float", False),
        "geometry_wkt": ("str", False),
        "cropland_frac": ("float", False),
        "governorate": ("str", False),
        "rice_zone": ("bool", False),
        "dist_coast_km": ("float", True),
        "dist_canal_m": ("float", True),
        "dist_drain_m": ("float", True),
        "elev_m": ("float", True),
    },
    "crop_seq": {
        "block_id": ("str", False),
        "season_id": ("str", False),
        "crop": ("str", False),
        "prob": ("float", False),
        "source": ("str", False),
        "purity": ("float", True),
    },
    "block_season": {
        "block_id": ("str", False),
        "season_id": ("str", False),
        "crop": ("str", True),
        "peak_ndvi": ("float", True),
        "peak_gcvi": ("float", True),
        "ndvi_auc": ("float", True),
        "n_clear_obs": ("int", False),
        "et_season_mm": ("float", True),
        "lst_mean_c": ("float", True),
        "esi_mean": ("float", True),
        "et0_mm": ("float", True),
        "heat_days_gt35": ("int", True),
        "smap_sm_mean": ("float", True),
        "imerg_mm": ("float", True),
        "salinity_index": ("float", True),
        "salinity_class": ("str", True),
    },
    "effects": {
        "effect_id": ("str", False),
        "site": ("str", False),
        "precrop_treat": ("str", False),
        "precrop_ctrl": ("str", False),
        "next_crop": ("str", False),
        "outcome": ("str", False),
        "method": ("str", False),
        "estimate": ("float", False),
        "ci_low": ("float", False),
        "ci_high": ("float", False),
        "n_treat": ("int", False),
        "n_ctrl": ("int", False),
        "stratum": ("str", False),
        "schema_version": ("int", False),
    },
}

_KIND_CHECK = {
    "str": lambda s: pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s),
    "int": pd.api.types.is_integer_dtype,
    "float": pd.api.types.is_float_dtype,
    "bool": pd.api.types.is_bool_dtype,
}


def validate(name: str, df: pd.DataFrame) -> list[str]:
    """Return a list of problems (empty = valid)."""
    errs = []
    for col, (kind, nullable) in SCHEMAS[name].items():
        if col not in df.columns:
            errs.append(f"{name}: missing column {col}")
            continue
        s = df[col]
        if not nullable and s.isna().any():
            errs.append(
                f"{name}.{col}: {int(s.isna().sum())} nulls in non-nullable column"
            )
        nn = s.dropna()
        if kind in ("int", "bool") and nullable and s.isna().any():
            continue  # pandas nullable ints/bools are checked loosely
        if len(nn) and not _KIND_CHECK[kind](s):
            errs.append(f"{name}.{col}: expected {kind}, got {s.dtype}")
    if "crop" in df.columns:
        bad = set(df["crop"].dropna().unique()) - CROPS
        if bad:
            errs.append(f"{name}.crop: unknown values {sorted(bad)}")
    for col in ("prob", "purity", "cropland_frac"):
        if col in df.columns:
            v = df[col].dropna()
            if len(v) and ((v < 0) | (v > 1)).any():
                errs.append(f"{name}.{col}: values outside [0, 1]")
    if "peak_ndvi" in df.columns:
        v = df["peak_ndvi"].dropna()
        if len(v) and ((v < -1) | (v > 1)).any():
            errs.append(f"{name}.peak_ndvi: values outside [-1, 1]")
    if name == "effects":
        e = df.dropna(subset=["estimate", "ci_low", "ci_high"])
        if ((e["ci_low"] > e["estimate"]) | (e["ci_high"] < e["estimate"])).any():
            errs.append("effects: estimate outside its CI")
    if (
        "block_id" in df.columns
        and name == "blocks"
        and df["block_id"].duplicated().any()
    ):
        errs.append("blocks: duplicate block_id")
    return errs
"""Lane 1 / M1: Sidi Ghazi (SGZ) fixtures + pilot precrop effect.

Runs on Kaggle (CPU, internet). Produces artefacts/{blocks,crop_seq,block_season,effects}.parquet,
robustness_pilot.json, qa.json, MANIFEST.json.  Design: docs/design.md, contract: docs/agents/00-shared-contract.md.
"""

import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            "statsmodels",
            "pyarrow",
            "pyproj",
            "geopandas",
            "pyogrio",
        ],
        check=False,
    )

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
import requests
import statsmodels.formula.api as smf
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import reproject, transform_bounds
from scipy.spatial import cKDTree

try:
    from schemas import SCHEMA_VERSION, validate
except ImportError:  # inlined on Kaggle
    pass

T0 = time.time()
SITE = "SGZ"
GOVERNORATE = "Kafr El-Sheikh"
RICE_ZONE = True  # Kafr El-Sheikh is a designated rice governorate under Decree 26/2025 (governorate-level)
WORK = "/kaggle/working" if os.path.exists("/kaggle") else os.path.abspath("work")
OUT = os.path.join(WORK, "artefacts")
os.makedirs(OUT, exist_ok=True)
CRS = "EPSG:32636"
BLOCK = 90
QA = {"site": SITE, "timings_s": {}, "attrition": {}, "notes": []}
FAO_URL = "https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-CROP-TYPE/"
SEASONS = {  # season_id -> (FAO file season, HLS date range)
    "S2023": ("2023.GS2", "2023-05-16/2023-10-31"),
    "W2024": ("2024.GS1", "2023-11-01/2024-05-15"),
    "S2024": ("2024.GS2", "2024-05-16/2024-10-31"),
}
WINTER = {
    1: "wheat",
    2: "sugarbeet",
    3: "flax",
    4: "clover",
    6: "beans",
    7: "veg",
    8: "orchard",
    9: "other",
    12: "nonag",
    13: "nonag",
    14: "nonag",
}
SUMMER = {
    1: "rice",
    2: "maize",
    3: "cotton",
    7: "veg",
    8: "orchard",
    11: "other",
    12: "nonag",
    13: "nonag",
    14: "nonag",
    15: "nonag",
}
FIELD = {
    "wheat",
    "sugarbeet",
    "flax",
    "clover",
    "beans",
    "rice",
    "maize",
    "cotton",
    "veg",
}


def tick(name, t):
    QA["timings_s"][name] = round(time.time() - t, 1)
    print(
        f"[{time.time() - T0:7.1f}s] {name} done in {QA['timings_s'][name]}s",
        flush=True,
    )


# ---------------------------------------------------------------- grid
def fao_path(season):
    p = os.path.join(WORK, f"{SITE}.{season}.tif")
    if not os.path.exists(p):
        r = requests.get(
            FAO_URL + f"WAPOR-3.L3-CROP-TYPE.EGY-{SITE}.{season}.tif", timeout=120
        )
        r.raise_for_status()
        open(p, "wb").write(r.content)
    return p


t = time.time()
with rasterio.open(fao_path("2024.GS1")) as src:
    B4326 = src.bounds
x0, y0, x1, y1 = transform_bounds("EPSG:4326", CRS, *B4326)
x0 = math.floor(x0 / BLOCK) * BLOCK
y0 = math.floor(y0 / BLOCK) * BLOCK
x1 = math.ceil(x1 / BLOCK) * BLOCK
y1 = math.ceil(y1 / BLOCK) * BLOCK
NR, NC = int((y1 - y0) / BLOCK), int((x1 - x0) / BLOCK)


def grid(res):
    f = BLOCK // res
    return from_origin(x0, y1, res, res), NR * f, NC * f


T30, H30, W30 = grid(30)
print("grid", NR, "x", NC, "blocks; 30 m grid", H30, "x", W30, flush=True)


def block_reduce(a, f, how="mean"):
    a = a.reshape(NR, f, NC, f)
    with np.errstate(all="ignore"):
        if how == "mean":
            return np.nanmean(a, axis=(1, 3))
        if how == "max":
            return np.nanmax(a, axis=(1, 3))
        if how == "min":
            return np.nanmin(a, axis=(1, 3))
    raise ValueError(how)


# ---------------------------------------------------------------- labels (FAO, 10 m -> 90 m blocks)
def labels_10m(season):
    tr, h, w = grid(10)
    dst = np.full((h, w), 255, np.uint8)
    with rasterio.open(fao_path(season)) as src:
        reproject(
            rasterio.band(src, 1),
            dst,
            dst_transform=tr,
            dst_crs=CRS,
            resampling=Resampling.nearest,
            dst_nodata=255,
        )
    return dst


def block_labels(season_id):
    fao_season, _ = SEASONS[season_id]
    lut = WINTER if season_id.startswith("W") else SUMMER
    lab = (
        labels_10m(fao_season)
        .reshape(NR, 9, NC, 9)
        .transpose(0, 2, 1, 3)
        .reshape(NR, NC, 81)
    )
    names = sorted(set(lut.values()))
    counts = np.zeros((NR, NC, len(names)), np.int16)
    for code, name in lut.items():
        counts[..., names.index(name)] += (lab == code).sum(-1).astype(np.int16)
    valid = counts.sum(-1)
    maj = counts.argmax(-1)
    purity = np.where(valid > 0, counts.max(-1) / np.maximum(valid, 1), np.nan)
    field = sum(counts[..., names.index(n)] for n in names if n in FIELD)
    cropfrac = field / 81.0
    crop = np.array(names, dtype=object)[maj]
    crop[valid == 0] = None
    return crop, purity, cropfrac, valid


LAB = {}
for sid in SEASONS:
    LAB[sid] = block_labels(sid)
tick("labels", t)

# ---------------------------------------------------------------- HLS outcomes (Planetary Computer)
CAT = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
BANDS = {
    "hls2-s30": {
        "blue": "B02",
        "green": "B03",
        "red": "B04",
        "nir": "B8A",
        "fmask": "Fmask",
    },
    "hls2-l30": {
        "blue": "B02",
        "green": "B03",
        "red": "B04",
        "nir": "B05",
        "fmask": "Fmask",
    },
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


def read_warp(href, resampling=Resampling.nearest, res_tr=(T30, H30, W30), dtype=None):
    tr, h, w = res_tr
    for attempt in range(4):
        try:
            with rasterio.Env(**GDAL_ENV), rasterio.open(pc.sign(href)) as src:
                with WarpedVRT(
                    src,
                    crs=CRS,
                    transform=tr,
                    width=w,
                    height=h,
                    resampling=resampling,
                    nodata=src.nodata,
                ) as vrt:
                    return vrt.read(1), src.nodata
        except Exception as e:  # transient network errors
            if attempt == 3:
                print("read failed", href[:90], repr(e)[:120], flush=True)
                return None, None
            time.sleep(2 * (attempt + 1))


def process_date(items, want_si):
    """Combine all items (tiles/sensors) of one date into clear-sky NDVI/GCVI/SI on the 30 m grid."""
    ndvi = np.full((H30, W30), np.nan, np.float32)
    gcvi = np.full((H30, W30), np.nan, np.float32)
    si = np.full((H30, W30), np.nan, np.float32)
    for it in items:
        b = BANDS[it.collection_id]
        arr = {}
        for k, band in b.items():
            if k == "blue" and not want_si:
                continue
            a, nod = read_warp(it.assets[band].href)
            if a is None:
                arr = None
                break
            arr[k] = (a, nod)
        if arr is None:
            continue
        fm, fnod = arr["fmask"]
        clear = ((fm & 0b00011111) == 0) & (fm != 255)
        refl = {}
        for k in ("green", "red", "nir") + (("blue",) if want_si else ()):
            a, nod = arr[k]
            clear &= a != nod
            refl[k] = a.astype(np.float32) * 1e-4
        clear &= (refl["red"] > 0) & (refl["nir"] > 0) & (refl["green"] > 0)
        with np.errstate(all="ignore"):
            nd = (refl["nir"] - refl["red"]) / (refl["nir"] + refl["red"])
            gc = refl["nir"] / refl["green"] - 1
        nd[~clear] = np.nan
        gc[~clear] = np.nan
        ndvi = np.fmax(ndvi, nd)
        gcvi = np.fmax(gcvi, gc)
        if want_si:
            s = np.sqrt(np.clip(refl["blue"], 0, None) * refl["red"])
            s[~clear | ~(nd < 0.25)] = np.nan
            si = np.fmax(si, s)
    return ndvi, gcvi, si


def season_stats(season_id):
    _, dates = SEASONS[season_id]
    bbox = list(B4326)
    items = list(
        CAT.search(
            collections=list(BANDS),
            bbox=bbox,
            datetime=dates,
            query={"eo:cloud_cover": {"lt": 75}},
        ).items()
    )
    by_date = defaultdict(list)
    for it in items:
        by_date[it.datetime.date()].append(it)
    want_si = (
        season_id == "S2023"
    )  # salinity proxy from the pre-treatment summer's bare-soil looks
    mx_nd = np.full((H30, W30), np.nan, np.float32)
    mx_gc = np.full((H30, W30), np.nan, np.float32)
    sum_nd = np.zeros((H30, W30), np.float32)
    n_cl = np.zeros((H30, W30), np.int16)
    sum_si = np.zeros((H30, W30), np.float32)
    n_si = np.zeros((H30, W30), np.int16)
    with ThreadPoolExecutor(12) as ex:
        futs = [ex.submit(process_date, v, want_si) for v in by_date.values()]
        for i, f in enumerate(as_completed(futs)):
            nd, gc, si = f.result()
            ok = ~np.isnan(nd)
            mx_nd = np.fmax(mx_nd, nd)
            mx_gc = np.fmax(mx_gc, gc)
            sum_nd[ok] += nd[ok]
            n_cl += ok
            oks = ~np.isnan(si)
            sum_si[oks] += si[oks]
            n_si += oks
            if i % 20 == 0:
                print(f"  {season_id}: {i + 1}/{len(futs)} dates", flush=True)
    with np.errstate(all="ignore"):
        mean_nd = np.where(n_cl > 0, sum_nd / n_cl, np.nan)
        mean_si = np.where(n_si > 0, sum_si / n_si, np.nan)
    d0, d1 = (pd.Timestamp(x) for x in dates.split("/"))
    days = (d1 - d0).days
    QA.setdefault("hls", {})[season_id] = {"items": len(items), "dates": len(by_date)}
    return {
        "peak_ndvi": block_reduce(mx_nd, 3),
        "peak_gcvi": block_reduce(mx_gc, 3),
        "ndvi_auc": block_reduce(mean_nd, 3)
        * days,  # mean clear-sky NDVI x season length (NDVI-days)
        "n_clear_obs": np.nan_to_num(block_reduce(n_cl.astype(np.float32), 3))
        .round()
        .astype(np.int32),
        "si": block_reduce(mean_si, 3),
    }


HLS = {}
for sid in SEASONS:
    t = time.time()
    HLS[sid] = season_stats(sid)
    tick(f"hls_{sid}", t)

# ---------------------------------------------------------------- covariates
t = time.time()
rows, cols = np.mgrid[0:NR, 0:NC]
cx = x0 + (cols + 0.5) * BLOCK
cy = y1 - (rows + 0.5) * BLOCK
to_ll = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
to_utm = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
lon, lat = to_ll.transform(cx, cy)

# elevation: NASADEM (NASA SRTM reprocessing) on Planetary Computer
elev = np.full((NR, NC), np.nan, np.float32)
try:
    for it in CAT.search(collections=["nasadem"], bbox=list(B4326)).items():
        a, nod = read_warp(it.assets["elevation"].href, Resampling.average, grid(BLOCK))
        if a is not None:
            a = a.astype(np.float32)
            a[a == nod] = np.nan
            elev = np.where(np.isnan(elev), a, elev)
except Exception as e:
    QA["notes"].append(f"NASADEM failed: {e!r}")


UA = {"User-Agent": "fieldshift-pipeline/0.1"}


def fetch(url, name):
    p = os.path.join(WORK, name)
    if not os.path.exists(p):
        with requests.get(url, headers=UA, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(p, "wb") as f:
                f.writelines(r.iter_content(1 << 20))
    return p


def lines_to_elements(gdf):
    """GeoDataFrame of (Multi)LineStrings in EPSG:4326 -> list of {"geometry": [{"lon","lat"}...]}"""
    out = []
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            continue
        parts = geom.geoms if geom.geom_type.startswith("Multi") else [geom]
        for g in parts:
            out.append({"geometry": [{"lon": x, "lat": y} for x, y in g.coords]})
    return out


def densify_points(elements, step=30.0):
    pts = []
    for el in elements or []:
        g = el.get("geometry")
        if not g:
            continue
        xs, ys = to_utm.transform([p["lon"] for p in g], [p["lat"] for p in g])
        for (xa, ya), (xb, yb) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
            n = max(1, int(math.hypot(xb - xa, yb - ya) // step))
            for k in range(n):
                pts.append((xa + (xb - xa) * k / n, ya + (yb - ya) * k / n))
    return np.array(pts) if pts else None


def nearest(pts):
    if pts is None or len(pts) == 0:
        return np.full((NR, NC), np.nan)
    d, _ = cKDTree(pts).query(np.c_[cx.ravel(), cy.ravel()])
    return d.reshape(NR, NC)


s_, w_, n_, e_ = B4326.bottom, B4326.left, B4326.top, B4326.right
canal_el, drain_el, coast = [], [], []
try:
    import geopandas as gpd

    # OSM waterways from the Geofabrik Egypt extract (ODbL); fclass in {river, stream, canal, drain}
    zp = fetch(
        "https://download.geofabrik.de/africa/egypt-latest-free.shp.zip",
        "egypt-osm.shp.zip",
    )
    ww = gpd.read_file(
        f"zip://{zp}!gis_osm_waterways_free_1.shp",
        bbox=(w_ - 0.05, s_ - 0.05, e_ + 0.05, n_ + 0.05),
    ).to_crs("EPSG:4326")
    canal_el = lines_to_elements(ww[ww.fclass.isin(["canal", "river", "stream"])])
    drain_el = lines_to_elements(ww[ww.fclass == "drain"])
    QA["osm_fclass_counts"] = ww.fclass.value_counts().to_dict()
    # coastline: Natural Earth 10 m (public domain)
    cp = fetch(
        "https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip",
        "ne_coast.zip",
    )
    cl = gpd.read_file(
        f"zip://{cp}", bbox=(w_ - 1.5, s_ - 0.5, e_ + 1.5, n_ + 1.5)
    ).to_crs("EPSG:4326")
    coast = lines_to_elements(cl)
except Exception as e:
    QA["notes"].append(f"waterways/coast failed: {e!r}")
dist_canal = nearest(densify_points(canal_el))
dist_drain = nearest(densify_points(drain_el))
dist_coast = nearest(densify_points(coast, step=200.0)) / 1000.0
QA["osm"] = {
    "canal_lines": len(canal_el),
    "drain_lines": len(drain_el),
    "coast_lines": len(coast),
}

# NASA POWER daily -> FAO-56 Penman-Monteith ET0 and heat days (regional, ~0.5 deg; site-constant)
clat, clon = float(np.mean(lat)), float(np.mean(lon))
power = requests.get(
    "https://power.larc.nasa.gov/api/temporal/daily/point",
    params={
        "parameters": "T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN",
        "community": "AG",
        "longitude": round(clon, 3),
        "latitude": round(clat, 3),
        "start": "20230501",
        "end": "20241031",
        "format": "JSON",
    },
    timeout=120,
).json()
RS_UNITS = power["parameters"]["ALLSKY_SFC_SW_DWN"]["units"]
RS_TO_MJ = 1.0 if "MJ" in RS_UNITS else 3.6
QA["power_rs_units"] = RS_UNITS
power = power["properties"]["parameter"]
P = pd.DataFrame(power).replace(-999.0, np.nan)
P.index = pd.to_datetime(P.index, format="%Y%m%d")
z = float(np.nanmedian(elev)) if np.isfinite(np.nanmedian(elev)) else 2.0


def et0_pm(df, lat_deg, z):
    tmax, tmin, rh, u2 = df.T2M_MAX, df.T2M_MIN, df.RH2M, df.WS2M
    rs = df.ALLSKY_SFC_SW_DWN * RS_TO_MJ  # POWER AG community already reports MJ/m2/day
    tmean = (tmax + tmin) / 2
    e0 = lambda T: 0.6108 * np.exp(17.27 * T / (T + 237.3))
    es = (e0(tmax) + e0(tmin)) / 2
    ea = rh / 100 * es
    delta = 4098 * e0(tmean) / (tmean + 237.3) ** 2
    pres = 101.3 * ((293 - 0.0065 * z) / 293) ** 5.26
    gamma = 0.000665 * pres
    j = df.index.dayofyear.values
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    dec = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(-np.tan(phi) * np.tan(dec))
    ra = (
        24
        * 60
        / np.pi
        * 0.0820
        * dr
        * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    )
    rso = (0.75 + 2e-5 * z) * ra
    rnl = (
        4.903e-9
        * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4)
        / 2
        * (0.34 - 0.14 * np.sqrt(ea))
        * (1.35 * np.clip(rs / rso, 0, 1) - 0.35)
    )
    rn = 0.77 * rs - rnl
    return (0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / (
        delta + gamma * (1 + 0.34 * u2)
    )


P["et0"] = et0_pm(P, clat, z)
CLIM = {}
for sid, (_, dates) in SEASONS.items():
    d0, d1 = dates.split("/")
    sub = P.loc[d0:d1]
    CLIM[sid] = {
        "et0_mm": float(sub.et0.sum()),
        "heat_days_gt35": int((sub.T2M_MAX > 35).sum()),
    }
QA["power"] = {"lat": clat, "lon": clon, **CLIM}
tick("covariates", t)

# ---------------------------------------------------------------- assemble artefacts
t = time.time()
crop_w, pur_w, cf_w, _ = LAB["W2024"]
keep = cf_w >= 0.6
QA["attrition"]["grid_blocks"] = int(NR * NC)
QA["attrition"]["cropland_frac>=0.6 (W2024)"] = int(keep.sum())
ids = np.char.add(
    np.char.add(f"{SITE}_", rows.astype(str)), np.char.add("_", cols.astype(str))
)
half = BLOCK / 2
corners = [
    to_ll.transform(cx + dx, cy + dy)
    for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half))
]


def wkt(i, j):
    pts = [(corners[k][0][i, j], corners[k][1][i, j]) for k in range(4)]
    pts.append(pts[0])
    return "POLYGON((" + ", ".join(f"{a:.6f} {b:.6f}" for a, b in pts) + "))"


ki, kj = np.nonzero(keep)
blocks = pd.DataFrame(
    {
        "block_id": ids[ki, kj],
        "site": SITE,
        "row": ki.astype(np.int64),
        "col": kj.astype(np.int64),
        "lon": lon[ki, kj],
        "lat": lat[ki, kj],
        "geometry_wkt": [wkt(i, j) for i, j in zip(ki, kj)],
        "cropland_frac": cf_w[ki, kj].astype(float),
        "governorate": GOVERNORATE,
        "rice_zone": RICE_ZONE,
        "dist_coast_km": dist_coast[ki, kj].astype(float),
        "dist_canal_m": dist_canal[ki, kj].astype(float),
        "dist_drain_m": dist_drain[ki, kj].astype(float),
        "elev_m": elev[ki, kj].astype(float),
    }
)

si = HLS["S2023"]["si"][ki, kj].astype(float)
si_q = np.nanquantile(si, [1 / 3, 2 / 3]) if np.isfinite(si).any() else [np.nan, np.nan]
si_class = np.where(
    np.isnan(si),
    None,
    np.where(si < si_q[0], "low", np.where(si < si_q[1], "med", "high")),
)

cs_rows, bs_rows = [], []
for sid in SEASONS:
    crop, pur, cf, valid = LAB[sid]
    h = HLS[sid]
    c = crop[ki, kj]
    p = pur[ki, kj]
    ok = (c != None) & (p >= 0.6)
    QA["attrition"][f"{sid} purity>=0.6"] = int(ok.sum())
    cs_rows.append(
        pd.DataFrame(
            {
                "block_id": blocks.block_id[ok].values,
                "season_id": sid,
                "crop": c[ok].astype(str),
                "prob": p[ok].astype(float),
                "source": "fao",
                "purity": p[ok].astype(float),
            }
        )
    )
    bs_rows.append(
        pd.DataFrame(
            {
                "block_id": blocks.block_id.values,
                "season_id": sid,
                "crop": pd.Series(np.where(ok, c, None), dtype="object"),
                "peak_ndvi": h["peak_ndvi"][ki, kj].astype(float),
                "peak_gcvi": h["peak_gcvi"][ki, kj].astype(float),
                "ndvi_auc": h["ndvi_auc"][ki, kj].astype(float),
                "n_clear_obs": h["n_clear_obs"][ki, kj].astype(np.int64),
                "et_season_mm": np.nan,
                "lst_mean_c": np.nan,
                "esi_mean": np.nan,
                "et0_mm": CLIM[sid]["et0_mm"],
                "heat_days_gt35": np.int64(CLIM[sid]["heat_days_gt35"]),
                "smap_sm_mean": np.nan,
                "imerg_mm": np.nan,
                "salinity_index": si,
                "salinity_class": pd.Series(si_class, dtype="object"),
            }
        )
    )
crop_seq = pd.concat(cs_rows, ignore_index=True)
block_season = pd.concat(bs_rows, ignore_index=True)
QA["notes"] += [
    "et_season_mm, lst_mean_c, esi_mean null: ECOSTRESS needs an Earthdata token (Kaggle Secret).",
    "smap_sm_mean, imerg_mm null in v1: NSIDC/GES DISC need Earthdata login; regional context only.",
    "salinity_index = mean sqrt(blue*red) over clear bare-soil looks (NDVI<0.25) in S2023 (pre-treatment); weak proxy.",
    "rice_zone and governorate are governorate-level constants for SGZ.",
    "ndvi_auc = mean clear-sky NDVI x season length in days (NDVI-days).",
]
tick("assemble", t)

# ---------------------------------------------------------------- pilot precrop effects
t = time.time()
num = block_season.pivot(
    index="block_id",
    columns="season_id",
    values=["peak_ndvi", "ndvi_auc", "n_clear_obs"],
).astype(float)
num.columns = [f"{a}_{b}" for a, b in num.columns]
crp = block_season.pivot(index="block_id", columns="season_id", values="crop")
crp.columns = [f"crop_{b}" for b in crp.columns]
wide = num.join(crp)
D = blocks.set_index("block_id").join(wide)
D["superblock"] = (D["row"] // 10).astype(str) + "_" + (D["col"] // 10).astype(str)
D["si"] = si
D["si_missing"] = D["si"].isna().astype(int)
D["si_f"] = D["si"].fillna(np.nanmedian(si))
for c_ in ("dist_canal_m", "dist_drain_m", "dist_coast_km", "elev_m"):
    D[c_ + "_f"] = D[c_].fillna(D[c_].median())
D = D[
    (D["n_clear_obs_S2024"] >= 5)
    & D["crop_S2023"].notna()
    & D["crop_W2024"].notna()
    & D["crop_S2024"].notna()
]
QA["attrition"]["analysis (3 seasons labelled, n_clear S2024>=5)"] = len(D)
_cands = [
    "elev_m_f",
    "dist_canal_m_f",
    "dist_drain_m_f",
    "dist_coast_km_f",
    "si_f",
    "si_missing",
]
_used = [c_ for c_ in _cands if D[c_].notna().all() and D[c_].nunique() > 1]
QA["pilot_covariates_dropped"] = {
    c_: f"nan={int(D[c_].isna().sum())}, unique={int(D[c_].nunique())}"
    for c_ in _cands
    if c_ not in _used
}
COV = " + ".join(_used + ["peak_ndvi_S2023", "C(crop_S2023)"])
print(
    "pilot covariates:", COV, "| dropped:", QA["pilot_covariates_dropped"], flush=True
)
# write data artefacts now so a failure in the pilot can't lose them
for _n, _df in (
    ("blocks", blocks),
    ("crop_seq", crop_seq),
    ("block_season", block_season),
):
    _df.to_parquet(os.path.join(OUT, f"{_n}.parquet"), index=False)
print(
    "QA_PRE",
    json.dumps(
        {k: QA.get(k) for k in ("attrition", "hls", "osm", "power", "notes")},
        default=str,
    ),
    flush=True,
)

effects, robust = [], {}
for next_crop in ("rice", "maize", "cotton"):
    for treat in ("clover", "sugarbeet", "beans"):
        sub = D[
            (D.crop_S2024 == next_crop) & D.crop_W2024.isin([treat, "wheat"])
        ].copy()
        sub["T"] = (sub.crop_W2024 == treat).astype(int)
        nt, nc = int(sub["T"].sum()), int((1 - sub["T"]).sum())
        if nt < 200 or nc < 200:
            continue
        for outcome in ("peak_ndvi", "ndvi_auc"):
            y = f"{outcome}_S2024"
            s2 = sub.dropna(subset=[y, "peak_ndvi_S2023"])
            if s2["T"].sum() < 100 or (1 - s2["T"]).sum() < 100:
                QA["notes"].append(
                    f"skip {treat}>{next_crop}:{outcome}: n after dropna {len(s2)}"
                )
                continue
            if s2.crop_S2023.nunique() < 2:
                cov = COV.replace(" + C(crop_S2023)", "")
            else:
                cov = COV
            for method, formula in (("naive", f"{y} ~ T"), ("ols", f"{y} ~ T + {cov}")):
                m = smf.ols(formula, s2).fit(
                    cov_type="cluster", cov_kwds={"groups": s2["superblock"]}
                )
                lo, hi = m.conf_int().loc["T"]
                eid = f"{SITE}:{treat}-vs-wheat>{next_crop}:{outcome}:{method}"
                effects.append(
                    {
                        "effect_id": eid,
                        "site": SITE,
                        "precrop_treat": treat,
                        "precrop_ctrl": "wheat",
                        "next_crop": next_crop,
                        "outcome": outcome,
                        "method": method,
                        "estimate": float(m.params["T"]),
                        "ci_low": float(lo),
                        "ci_high": float(hi),
                        "n_treat": int(s2["T"].sum()),
                        "n_ctrl": int((1 - s2["T"]).sum()),
                        "stratum": "all",
                        "schema_version": SCHEMA_VERSION,
                    }
                )
            # placebo: W2024 precrop "explaining" the PREVIOUS summer's vigor (should be ~0 if no selection)
            if outcome == "peak_ndvi":
                pcov = cov.replace(" + peak_ndvi_S2023", "")
                pm = smf.ols(f"peak_ndvi_S2023 ~ T + {pcov}", s2).fit(
                    cov_type="cluster", cov_kwds={"groups": s2["superblock"]}
                )
                plo, phi = pm.conf_int().loc["T"]
                robust[f"{SITE}:{treat}-vs-wheat>{next_crop}:peak_ndvi:ols"] = {
                    "placebo_prev_summer_peak_ndvi": {
                        "estimate": float(pm.params["T"]),
                        "ci": [float(plo), float(phi)],
                        "pass": bool(plo <= 0 <= phi),
                    },
                    "pending": [
                        "permutation",
                        "overlap",
                        "sensitivity",
                        "misclass_propagation",
                        "direction_check",
                    ],
                }
effects = pd.DataFrame(effects)
tick("pilot_effects", t)

# ---------------------------------------------------------------- QA, validation, write
QA["peak_ndvi_by_crop"] = {
    sid: block_season[block_season.season_id == sid]
    .groupby("crop")["peak_ndvi"]
    .describe(percentiles=[0.25, 0.5, 0.75])[["count", "25%", "50%", "75%"]]
    .round(3)
    .to_dict("index")
    for sid in SEASONS
}
bsS = block_season[block_season.season_id == "S2024"]
QA["n_clear_obs_S2024_share_ge5"] = float((bsS.n_clear_obs >= 5).mean())
problems = []
for name, df in (
    ("blocks", blocks),
    ("crop_seq", crop_seq),
    ("block_season", block_season),
    ("effects", effects),
):
    problems += validate(name, df)
    df.to_parquet(os.path.join(OUT, f"{name}.parquet"), index=False)
QA["validation_problems"] = problems
json.dump(robust, open(os.path.join(OUT, "robustness_pilot.json"), "w"), indent=1)
QA["total_runtime_s"] = round(time.time() - T0, 1)
json.dump(QA, open(os.path.join(OUT, "qa.json"), "w"), indent=1, default=str)
manifest = []
for fn in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, fn)
    rows_ = len(pd.read_parquet(p)) if fn.endswith(".parquet") else None
    manifest.append(
        {
            "file": fn,
            "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(),
            "rows": rows_,
            "schema_version": SCHEMA_VERSION,
            "produced_by": "lane1/m1_sgz.py",
            "date": time.strftime("%Y-%m-%d"),
        }
    )
json.dump(manifest, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1)
print("VALIDATION", "OK" if not problems else problems)
print("EFFECTS")
print(
    effects[
        ["effect_id", "estimate", "ci_low", "ci_high", "n_treat", "n_ctrl"]
    ].to_string(index=False)
)
print("ROBUST", json.dumps(robust))
print(
    "QA",
    json.dumps(
        {
            k: QA[k]
            for k in (
                "attrition",
                "hls",
                "osm",
                "power",
                "timings_s",
                "n_clear_obs_S2024_share_ge5",
            )
        },
        default=str,
    ),
)
