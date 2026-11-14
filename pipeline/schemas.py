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
