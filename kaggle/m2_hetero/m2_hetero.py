"""Lane 1 / M2 follow-ups on the v2 switcher design (Kaggle CPU kernel).

1. Phenology: per block x summer season, green-up / senescence day-of-year and season length from the
   28-day HLS NDVI composites (50%-of-amplitude crossings, linear interpolation between steps).
   -> is the precrop "+NDVI-days" a later calendar or a longer season?
2. Heterogeneity: switcher FE per subgroup (salinity class, canal-distance tercile, north-south tercile,
   elevation tercile) for clover/sugar beet vs wheat -> rice, outcomes NDVI-days, season ET, season length.
3. Water productivity: NDVI-days per 100 mm ECOSTRESS ET as an outcome; effects also as % of control mean.

Inputs (kernel_sources): fieldshift-lane1-m2-train (v2 m2/), fieldshift-lane1-m2-ingest + fieldshift-earthdata-probe
(HLS composites), fieldshift-lane1-m1-sgz + fieldshift-lane1-m1-sites (blocks.parquet, salinity_class).
Outputs: /kaggle/working/hetero/{pheno_effects,hetero_effects,water_productivity}.json, pheno_block_season.parquet,
block_subgroups.parquet, hetero_qa.json
"""

import glob
import json
import os
import subprocess
import sys
import time

if os.path.exists("/kaggle"):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "linearmodels", "pyarrow"],
        check=False,
    )

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

T0 = time.time()
ROOT = "/kaggle/input" if os.path.exists("/kaggle/input") else "work"
OUT = "/kaggle/working/hetero" if os.path.exists("/kaggle") else "work/hetero"
os.makedirs(OUT, exist_ok=True)
QA = {"timings_s": {}}
SITES = ("SGZ", "ZAN")


def tick(name, t):
    QA["timings_s"][name] = round(time.time() - t, 1)
    print(f"[{time.time() - T0:6.0f}s] {name}", flush=True)
    json.dump(QA, open(os.path.join(OUT, "hetero_qa.json"), "w"), indent=1, default=str)


def find(name):
    return sorted(glob.glob(f"{ROOT}/**/{name}", recursive=True))


# ---------------------------------------------------------------- inputs
M2 = os.path.dirname(find("crop_seq_lgb.parquet")[0])
crop_seq = pd.read_parquet(os.path.join(M2, "crop_seq_lgb.parquet"))
bseason = pd.read_parquet(os.path.join(M2, "block_season_hls.parquet"))
bseason = bseason[bseason.block_id.str[:3].isin(SITES)]
GRID = {s: json.load(open(find(f"grid_{s}.json")[0])) for s in SITES}

SRC = {}  # same source rule as m2_train: best worst-step coverage


def _register(qa_path, key, d):
    for k, v in json.load(open(qa_path)).get(key, {}).items():
        fr = v.get("step_valid_frac") or [0]
        if os.path.exists(os.path.join(d, f"comp_{k}.npy")) and (
            k not in SRC or min(fr) > min(SRC[k][1])
        ):
            SRC[k] = (d, fr)


for q in find("ingest_qa.json"):
    _register(q, "seasons", os.path.dirname(q))
for q in find("earthdata_qa.json"):
    _register(q, "hls", os.path.join(os.path.dirname(q), "hls"))

blocks = pd.concat(
    [pd.read_parquet(p) for p in find("blocks.parquet")], ignore_index=True
).drop_duplicates("block_id")
sal = (
    pd.concat(
        [
            pd.read_parquet(p, columns=["block_id", "salinity_class"])
            for p in find("block_season.parquet")
            if "m2" not in p
        ],
        ignore_index=True,
    )
    .dropna()
    .drop_duplicates("block_id")
)
blocks = blocks[blocks.site.isin(SITES)].merge(sal, on="block_id", how="left")
QA["n_blocks_meta"] = len(blocks)
print("m2:", M2, "blocks:", len(blocks), "sources:", len(SRC), flush=True)

# ---------------------------------------------------------------- 1. phenology per block x summer season
t = time.time()
ph = []
for site in SITES:
    g = GRID[site]
    NR, NC = g["NR"], g["NC"]
    ids = bseason[bseason.block_id.str.startswith(site)].block_id.unique()
    rc = pd.Series(ids).str.split("_", expand=True)
    rr, cc = rc[1].astype(int).values, rc[2].astype(int).values
    sids = sorted(
        s
        for s in bseason[bseason.block_id.str.startswith(site)].season_id.unique()
        if s[0] == "S" and f"{site}_{s}" in SRC
    )
    for sid in sids:
        d = SRC[f"{site}_{sid}"][0]
        c = np.load(os.path.join(d, f"comp_{site}_{sid}.npy"), mmap_mode="r")
        red = c[:, 2, : NR * 3, : NC * 3].astype(np.float32)
        nir = c[:, 3, : NR * 3, : NC * 3].astype(np.float32)
        bad = (red == -9999) | (nir == -9999)
        nd = np.where(bad, np.nan, (nir - red) / (nir + red + 1e-6))
        T = nd.shape[0]
        with np.errstate(all="ignore"):
            nb = np.nanmean(nd.reshape(T, NR, 3, NC, 3), (2, 4))[:, rr, cc]  # [T, N]
        nb = pd.DataFrame(nb).ffill().bfill().values
        st = np.load(os.path.join(d, f"stats_{site}_{sid}.npz"))
        start = pd.Timestamp(str(st["start"]))
        lo, hi = np.nanmin(nb, 0), np.nanmax(nb, 0)
        thr = lo + 0.5 * (hi - lo)
        above = nb >= thr
        k = above.argmax(0)  # first step at/above threshold
        j = T - 1 - above[::-1].argmax(0)  # last step at/above threshold
        n = np.arange(nb.shape[1])
        km = np.maximum(k - 1, 0)
        gu = np.where(
            k > 0,
            km + (thr - nb[km, n]) / np.maximum(nb[k, n] - nb[km, n], 1e-6),
            0.0,
        )
        jp = np.minimum(j + 1, T - 1)
        se = np.where(
            j < T - 1,
            j + (nb[j, n] - thr) / np.maximum(nb[j, n] - nb[jp, n], 1e-6),
            T - 1.0,
        )
        ok = (hi - lo) >= 0.2
        doy0 = start.dayofyear + 14  # step k centred at start + 28k + 14 days
        ph.append(
            pd.DataFrame(
                {
                    "block_id": ids,
                    "season_id": sid,
                    "greenup_doy": np.where(ok, doy0 + 28 * gu, np.nan),
                    "senesce_doy": np.where(ok, doy0 + 28 * se, np.nan),
                    "season_len_d": np.where(ok, 28 * (se - gu), np.nan),
                    "ndvi_early": nb[:2].mean(0),  # steps 0-1: May 16 - Jul 10 (precrop tail + transplanting)
                    "ndvi_days_late": nb[2:].mean(0) * 28 * (T - 2),  # steps 2+: Jul 11 onward, the rice crop itself
                    "greenup_censored": (k == 0) & ok,
                    "senesce_censored": (j == T - 1) & ok,
                }
            )
        )
        del c, red, nir, nd
    print(site, "phenology", sids, flush=True)
pheno = pd.concat(ph, ignore_index=True)
pheno.to_parquet(os.path.join(OUT, "pheno_block_season.parquet"), index=False)
QA["pheno_rows"] = len(pheno)
QA["pheno_censored_share"] = {
    "greenup": round(float(pheno.greenup_censored.mean()), 3),
    "senesce": round(float(pheno.senesce_censored.mean()), 3),
}
tick("phenology", t)

# ---------------------------------------------------------------- panel (same construction as m2_train v2)
W_ = crop_seq[crop_seq.season_id.str[0] == "W"][
    ["block_id", "season_id", "crop"]
].copy()
W_["year"] = W_.season_id.str[1:].astype(int)
S_ = bseason[bseason.season_id.str[0] == "S"].dropna(subset=["crop"]).copy()
S_ = S_.merge(pheno, on=["block_id", "season_id"], how="left")
S_["year"] = S_.season_id.str[1:].astype(int)
S_["wp_ndvi_days_per_100mm"] = np.where(
    (S_.get("et_n_obs", 0) >= 2) & (S_.get("et_season_mm", np.nan) > 50),
    S_.ndvi_auc / S_.get("et_season_mm", np.nan) * 100,
    np.nan,
)
D = S_.merge(
    W_[["block_id", "year", "crop"]].rename(columns={"crop": "precrop"}),
    on=["block_id", "year"],
)
D = D[D.n_clear_obs >= 5]
LEAD = W_.assign(year=W_.year - 1).rename(columns={"crop": "lead_precrop"})[
    ["block_id", "year", "lead_precrop"]
]

# subgroups (terciles within site)
B = blocks[
    ["block_id", "site", "lat", "elev_m", "dist_canal_m", "salinity_class"]
].copy()
for col, name in (("lat", "ns"), ("elev_m", "elev"), ("dist_canal_m", "canal")):
    B[name] = (
        B.groupby("site")[col]
        .transform(
            lambda x: (
                pd.qcut(x.rank(method="first"), 3, labels=["low", "mid", "high"])
                if x.notna().sum() > 30
                else pd.Series(index=x.index, dtype=object)
            )
        )
        .astype(object)
    )
B["salinity"] = B.salinity_class.fillna("unknown")
B["ns"] = B["ns"].map({"low": "south", "mid": "middle", "high": "north"})
B["canal"] = B["canal"].map({"low": "near", "mid": "mid", "high": "far"})
B[["block_id", "site", "salinity", "ns", "elev", "canal"]].to_parquet(
    os.path.join(OUT, "block_subgroups.parquet"), index=False
)
D = D.merge(
    B[["block_id", "salinity", "ns", "elev", "canal"]], on="block_id", how="left"
)


def fe(d, outcome, treat, min_n=100):
    """Switcher two-way FE + lead placebo on frame d (has T, cluster). Returns dict or None."""
    dd = d.dropna(subset=[outcome])
    nobs = {"et_season_mm": "et_n_obs", "wp_ndvi_days_per_100mm": "et_n_obs"}.get(
        outcome
    )
    if nobs and nobs in dd:
        dd = dd[dd[nobs] >= 2]
    if dd["T"].sum() < min_n or (1 - dd["T"]).sum() < min_n:
        return None
    ddi = dd.set_index(["block_id", "year"])
    res = PanelOLS(
        ddi[outcome], ddi[["T"]], entity_effects=True, time_effects=True
    ).fit(cov_type="clustered", clusters=pd.Categorical(ddi["cluster"]).codes)
    ci = res.conf_int().loc["T"]
    ctrl_mean = float(dd.loc[dd["T"] == 0, outcome].mean())
    out = {
        "estimate": float(res.params["T"]),
        "ci_low": float(ci.iloc[0]),
        "ci_high": float(ci.iloc[1]),
        "se": float(res.std_errors["T"]),
        "ctrl_mean": ctrl_mean,
        "pct_of_ctrl": float(100 * res.params["T"] / ctrl_mean) if ctrl_mean else None,
        "n_treat": int(dd["T"].sum()),
        "n_ctrl": int((1 - dd["T"]).sum()),
        "n_blocks": int(dd.block_id.nunique()),
        "lead_placebo": None,
    }
    dl = dd.merge(LEAD, on=["block_id", "year"])
    dl = dl[dl.lead_precrop.isin([treat, "wheat"])]
    dl["L"] = (dl.lead_precrop == treat).astype(float)
    if dl["L"].nunique() == 2 and len(dl) > 400:
        dli = dl.set_index(["block_id", "year"])
        try:
            pr = PanelOLS(
                dli[outcome],
                dli[["L", "T"]],
                entity_effects=True,
                time_effects=True,
                drop_absorbed=True,
            ).fit(cov_type="clustered", clusters=pd.Categorical(dli["cluster"]).codes)
            pci = pr.conf_int().loc["L"]
            out["lead_placebo"] = {
                "estimate": float(pr.params["L"]),
                "ci": [float(pci.iloc[0]), float(pci.iloc[1])],
                "pass": bool(pci.iloc[0] <= 0 <= pci.iloc[1]),
            }
        except Exception as e:  # noqa: BLE001
            out["lead_placebo"] = {"error": repr(e)[:200]}
    return out


def arm(site, treat, nxt):
    d = D[
        (D.block_id.str.startswith(site))
        & (D.crop == nxt)
        & D.precrop.isin([treat, "wheat"])
    ].copy()
    d["T"] = (d.precrop == treat).astype(float)
    sw = d.groupby("block_id")["T"].agg(["min", "max"])
    d = d[d.block_id.isin(sw[(sw["min"] == 0) & (sw["max"] == 1)].index)].copy()
    rc = d.block_id.str.split("_", expand=True)
    d["cluster"] = (
        (rc[1].astype(int) // 10).astype(str)
        + "_"
        + (rc[2].astype(int) // 10).astype(str)
    )
    for c in ("greenup_censored", "senesce_censored"):
        d[c] = d[c].fillna(False).astype(bool)
    return d


ARMS = [(s, tr, "rice") for s in SITES for tr in ("clover", "sugarbeet")] + [
    ("ZAN", "clover", "cotton")
]

# ---------------------------------------------------------------- 1b. phenology + 3. water productivity effects
t = time.time()
PH, WP = [], []
for site, treat, nxt in ARMS:
    d = arm(site, treat, nxt)
    keep = {
        "greenup_doy": ~d.greenup_censored,
        "senesce_doy": ~d.senesce_censored,
        "season_len_d": ~(d.greenup_censored | d.senesce_censored),
    }
    for oc, m in keep.items():
        r = fe(d[m], oc, treat)
        if r:
            PH.append({"site": site, "treat": treat, "next_crop": nxt, "outcome": oc, **r})
    for oc in ("ndvi_auc", "ndvi_early", "ndvi_days_late", "et_season_mm", "wp_ndvi_days_per_100mm", "peak_ndvi"):
        if oc in d:
            r = fe(d, oc, treat)
            if r:
                WP.append(
                    {"site": site, "treat": treat, "next_crop": nxt, "outcome": oc, **r}
                )
json.dump(PH, open(os.path.join(OUT, "pheno_effects.json"), "w"), indent=1)
json.dump(WP, open(os.path.join(OUT, "water_productivity.json"), "w"), indent=1)
for r in PH + WP:
    print(
        r["site"],
        r["treat"],
        r["next_crop"],
        r["outcome"],
        round(r["estimate"], 3),
        (round(r["ci_low"], 3), round(r["ci_high"], 3)),
        "pct",
        r["pct_of_ctrl"] and round(r["pct_of_ctrl"], 2),
        "plac",
        (r["lead_placebo"] or {}).get("pass"),
        flush=True,
    )
tick("pheno_wp_effects", t)

# ---------------------------------------------------------------- 2. heterogeneity
t = time.time()
HE = []
for site, treat, nxt in ARMS:
    d = arm(site, treat, nxt)
    for dim in ("salinity", "ns", "canal", "elev"):
        for lev, g in d.groupby(dim):
            for oc in ("ndvi_auc", "ndvi_days_late", "et_season_mm", "season_len_d", "peak_ndvi"):
                r = fe(g, oc, treat, min_n=60)
                if r:
                    HE.append(
                        {
                            "site": site,
                            "treat": treat,
                            "next_crop": nxt,
                            "dim": dim,
                            "level": str(lev),
                            "outcome": oc,
                            **r,
                        }
                    )
HE = pd.DataFrame(HE)
# difference between extreme levels (independent-subgroup z test)
diffs = []
for (site, treat, nxt, dim, oc), g in HE.groupby(
    ["site", "treat", "next_crop", "dim", "outcome"]
):
    if len(g) < 2:
        continue
    a, b = g.loc[g.estimate.idxmax()], g.loc[g.estimate.idxmin()]
    z = (a.estimate - b.estimate) / np.sqrt(a.se**2 + b.se**2)
    diffs.append(
        {
            "site": site,
            "treat": treat,
            "next_crop": nxt,
            "dim": dim,
            "outcome": oc,
            "max_level": a.level,
            "min_level": b.level,
            "diff": float(a.estimate - b.estimate),
            "z": float(z),
            "significant_5pct": bool(abs(z) > 1.96),
        }
    )
HE.to_json(os.path.join(OUT, "hetero_effects.json"), orient="records", indent=1)
json.dump(diffs, open(os.path.join(OUT, "hetero_diffs.json"), "w"), indent=1)
print(
    HE[
        [
            "site",
            "treat",
            "next_crop",
            "dim",
            "level",
            "outcome",
            "estimate",
            "ci_low",
            "ci_high",
            "n_blocks",
        ]
    ]
    .round(3)
    .to_string(index=False),
    flush=True,
)
print(pd.DataFrame(diffs).round(3).to_string(index=False), flush=True)
tick("heterogeneity", t)
QA["total_runtime_s"] = round(time.time() - T0, 1)
tick("done", T0)
print("DONE", QA["total_runtime_s"])
