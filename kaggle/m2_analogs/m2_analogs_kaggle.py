"""Lane 1 / M2 step 10: "fields like yours that already switched" -> analogs.parquet (k = 10).

Usage: python pipeline/m2_analogs.py <m2_dir> <m1_artefact_dir>[,<m1_dir2>...] <out_dir>
  m2_dir   : outputs of fieldshift-lane1-m2-train (pred_{site}_{season}.npz, crop_seq_prithvi.parquet,
             block_season_hls.parquet)
  m1 dirs  : M1 fixtures per site (blocks.parquet, block_season.parquet with salinity_class)

Method
  land signature = mean over all summers 2016-2025 of the block's 64-d Prithvi decoder embedding (PCA -> 24 d),
                   plus z-scored elevation and log canal distance (weight 2 each); L2-normalised, cosine kNN.
  candidates     = same site x rice_zone x salinity_class, |d elevation| <= 1.5 m, and the candidate has a
                   *switch event*: a year y with W{y} precrop != the query's latest precrop and S{y} crop ==
                   the query's latest summer crop.
  analog_seq     = "W{y}:{precrop}>S{y}:{crop}" for the candidate's most recent such event.
  delta_peak_ndvi= candidate's peak NDVI in S{y} minus its own mean peak NDVI in summers of the same crop that
                   followed the query's precrop (within-block before/after; NaN if it never had that precrop).
  delta_et_mm    = NaN until ECOSTRESS ET is ingested.
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

K, POOL, DELEV = 10, 300, 1.5


def main(m2_dir, m1_dirs, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    blocks = pd.concat(
        [pd.read_parquet(os.path.join(d, "blocks.parquet")) for d in m1_dirs],
        ignore_index=True,
    )
    sal = pd.concat(
        [
            pd.read_parquet(
                os.path.join(d, "block_season.parquet"),
                columns=["block_id", "salinity_class"],
            ).drop_duplicates("block_id")
            for d in m1_dirs
        ],
        ignore_index=True,
    )
    blocks = blocks.merge(sal, on="block_id", how="left")
    _cs = os.path.join(m2_dir, "crop_seq_lgb.parquet")
    cs = pd.read_parquet(_cs if os.path.exists(_cs) else os.path.join(m2_dir, "crop_seq_prithvi.parquet"))
    bs = pd.read_parquet(
        os.path.join(m2_dir, "block_season_hls.parquet"),
        columns=["block_id", "season_id", "peak_ndvi"],
    )
    cs["year"] = cs.season_id.str[1:].astype(int)
    W = cs[cs.season_id.str[0] == "W"][["block_id", "year", "crop"]].rename(
        columns={"crop": "precrop"}
    )
    S = cs[cs.season_id.str[0] == "S"][["block_id", "year", "crop"]]
    bs["year"] = bs.season_id.str[1:].astype(int)
    S = S.merge(
        bs[bs.season_id.str[0] == "S"][["block_id", "year", "peak_ndvi"]],
        on=["block_id", "year"],
        how="left",
    )
    ev = S.merge(W, on=["block_id", "year"])  # (block, year, precrop, crop, peak_ndvi)
    latest = ev.sort_values("year").groupby("block_id").tail(1).set_index("block_id")

    # land signature from Prithvi embeddings
    sig = {}
    for site in blocks.site.unique():
        files = sorted(glob.glob(os.path.join(m2_dir, f"pred_{site}_S*.npz")))
        if not files:
            continue
        acc = None
        for f in files:
            e = np.load(f)["block_emb"].astype(np.float32)  # [64, NR, NC]
            acc = e if acc is None else acc + e
        acc /= len(files)
        b = blocks[blocks.site == site]
        sig.update(dict(zip(b.block_id, acc[:, b.row.values, b.col.values].T)))
    blocks = blocks[
        blocks.block_id.isin(sig) & blocks.block_id.isin(latest.index)
    ].reset_index(drop=True)
    E = np.stack([sig[b] for b in blocks.block_id])
    E = PCA(24, random_state=0).fit_transform(E)
    E /= E.std(0, keepdims=True) + 1e-6
    elev = blocks.elev_m.fillna(blocks.elev_m.median()).values
    dcan = np.log1p(blocks.dist_canal_m.fillna(blocks.dist_canal_m.median()).values)
    X = np.c_[
        E,
        2 * (elev - elev.mean()) / (elev.std() + 1e-6),
        2 * (dcan - dcan.mean()) / (dcan.std() + 1e-6),
    ]
    X /= np.linalg.norm(X, axis=1, keepdims=True)

    ev_by_block = {b: g for b, g in ev.groupby("block_id")}
    rows = []
    blocks["salinity_class"] = blocks.salinity_class.fillna("unknown")
    for (site, rz, sc), g in blocks.groupby(["site", "rice_zone", "salinity_class"]):
        idx = g.index.values
        nn = NearestNeighbors(n_neighbors=min(POOL + 1, len(idx)), metric="cosine").fit(
            X[idx]
        )
        dist, nbr = nn.kneighbors(X[idx])
        for qi, (dd, nb) in enumerate(zip(dist, nbr)):
            q = idx[qi]
            qid = blocks.block_id[q]
            qpre, qcrop = latest.loc[qid, "precrop"], latest.loc[qid, "crop"]
            rank = 0
            for d_, j in zip(dd, nb):
                c = idx[j]
                if c == q or abs(elev[c] - elev[q]) > DELEV:
                    continue
                cev = ev_by_block.get(blocks.block_id[c])
                sw = cev[(cev.precrop != qpre) & (cev.crop == qcrop)]
                if sw.empty:
                    continue
                last = sw.sort_values("year").iloc[-1]
                base = cev[(cev.precrop == qpre) & (cev.crop == qcrop)].peak_ndvi
                rank += 1
                rows.append(
                    {
                        "block_id": qid,
                        "rank": rank,
                        "analog_block_id": blocks.block_id[c],
                        "similarity": float(1 - d_),
                        "analog_seq": f"W{last.year}:{last.precrop}>S{last.year}:{last.crop}",
                        "delta_peak_ndvi": float(last.peak_ndvi - base.mean())
                        if len(base)
                        else np.nan,
                        "delta_et_mm": np.nan,
                    }
                )
                if rank == K:
                    break
    A = pd.DataFrame(rows)
    A.to_parquet(os.path.join(out_dir, "analogs.parquet"), index=False)

    # sanity check (lane brief): 50 random blocks -> same site/rice_zone/salinity_class, mean |d elev| < 1 m
    bi = blocks.set_index("block_id")
    rng = np.random.default_rng(0)
    qs = rng.choice(A.block_id.unique(), min(50, A.block_id.nunique()), replace=False)
    s = A[A.block_id.isin(qs)]
    a, b = bi.loc[s.block_id], bi.loc[s.analog_block_id]
    same = float(
        (
            (a.site.values == b.site.values)
            & (a.rice_zone.values == b.rice_zone.values)
            & (a.salinity_class.values == b.salinity_class.values)
        ).mean()
    )
    qa = {
        "rows": len(A),
        "query_blocks": int(A.block_id.nunique()),
        "blocks_considered": len(blocks),
        "coverage": round(A.block_id.nunique() / max(len(blocks), 1), 3),
        "sanity_same_stratum_share": same,
        "sanity_mean_abs_delev_m": round(
            float(np.abs(a.elev_m.values - b.elev_m.values).mean()), 3
        ),
        "median_similarity": round(float(A.similarity.median()), 3),
    }
    json.dump(qa, open(os.path.join(out_dir, "analogs_qa.json"), "w"), indent=1)
    print(json.dumps(qa))


if False:
    main(sys.argv[1], sys.argv[2].split(","), sys.argv[3])


# ---- Kaggle entry: locate inputs from attached kernel outputs
m1_dirs = sorted({os.path.dirname(p) for p in glob.glob("/kaggle/input/**/blocks.parquet", recursive=True)})
m2_dir = os.path.dirname(glob.glob("/kaggle/input/**/crop_seq_*.parquet", recursive=True)[0])
print("m1:", m1_dirs, "m2:", m2_dir, flush=True)
main(m2_dir, m1_dirs, "/kaggle/working/analogs")
