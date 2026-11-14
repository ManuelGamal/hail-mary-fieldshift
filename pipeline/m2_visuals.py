"""Deck/video visuals from real pipeline outputs (Kaggle CPU kernel). Small PNG/GIF/CSV files only.

1. crop_flip/   30 m LightGBM crop map of a 15 km ZAN window, every usable season 2016-2025 (PNG frames + GIF)
2. calendar.csv mean block NDVI per 28-day step, Nov -> Oct, for rice after clover vs rice after wheat (ZAN)
3. analogs_card.png  one query block and its 10 analogs on the 2024 summer crop map (ZAN)
"""

import glob
import json
import os
import traceback

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

ROOT = "/kaggle/input" if os.path.exists("/kaggle/input") else "work"
OUT = "/kaggle/working/visuals" if os.path.exists("/kaggle") else "work/visuals"
os.makedirs(os.path.join(OUT, "crop_flip"), exist_ok=True)
QA = {}


def find(name):
    return sorted(glob.glob(f"{ROOT}/**/{name}", recursive=True))


W_CLS = [
    "wheat",
    "sugarbeet",
    "flax",
    "clover",
    "beans",
    "veg",
    "orchard",
    "other",
    "nonag",
]
S_CLS = ["rice", "maize", "cotton", "veg", "orchard", "other", "nonag"]
COL = {  # one calm palette, shared with the deck
    "wheat": (224, 179, 65),
    "clover": (58, 157, 93),
    "sugarbeet": (142, 108, 192),
    "rice": (46, 143, 163),
    "maize": (224, 123, 57),
    "cotton": (217, 160, 184),
    "flax": (190, 190, 175),
    "beans": (190, 190, 175),
    "veg": (190, 190, 175),
    "orchard": (120, 140, 110),
    "other": (200, 200, 190),
    "nonag": (238, 236, 230),
}
NODATA = (250, 250, 248)
SITE = "ZAN"
M2 = os.path.dirname(find(f"pred_{SITE}_S2024.npz")[0])
GRID = json.load(open(find(f"grid_{SITE}.json")[0]))
preds = sorted(find(f"pred_{SITE}_*.npz"))
print("pred files:", [os.path.basename(p) for p in preds], flush=True)


def lut(names):
    t = np.array([COL[n] for n in names] + [NODATA] * (256 - len(names)), np.uint8)
    t[255] = NODATA
    return t


# ---------------------------------------------------------------- window: 500 x 500 px (15 km) with most rice
WIN = 500
z = np.load(os.path.join(M2, f"pred_{SITE}_S2024.npz"))
rice = (z["lgb_cls30"] == 0).astype(np.float32)
H, W = rice.shape
ii = np.cumsum(np.cumsum(np.pad(rice, ((1, 0), (1, 0))), 0), 1)
s = ii[WIN:, WIN:] - ii[:-WIN, WIN:] - ii[WIN:, :-WIN] + ii[:-WIN, :-WIN]
r0, c0 = np.unravel_index(np.argmax(s[::10, ::10]), s[::10, ::10].shape)
r0, c0 = int(r0 * 10), int(c0 * 10)
QA["window_px"] = [r0, c0, WIN]

# ---------------------------------------------------------------- 1. crop flip frames
try:
    frames = []

    def key(p):
        sid = os.path.basename(p)[len(f"pred_{SITE}_") : -4]
        return (int(sid[1:]), 0 if sid[0] == "W" else 1)

    for p in sorted(preds, key=key):
        sid = os.path.basename(p)[len(f"pred_{SITE}_") : -4]
        c = np.load(p)["lgb_cls30"][r0 : r0 + WIN, c0 : c0 + WIN]
        img = Image.fromarray(lut(W_CLS if sid[0] == "W" else S_CLS)[c]).resize(
            (1000, 1000), Image.NEAREST
        )
        img.save(os.path.join(OUT, "crop_flip", f"{sid}.png"), optimize=True)
        lab = ("Winter " if sid[0] == "W" else "Summer ") + sid[1:]
        f = img.copy()
        d = ImageDraw.Draw(f)
        d.rectangle([0, 0, 1000, 70], fill=(10, 37, 64))
        d.text((24, 18), lab, fill=(255, 255, 255), font_size=36)
        frames.append(
            f.resize((600, 600), Image.NEAREST).convert(
                "P", palette=Image.ADAPTIVE, colors=32
            )
        )
    frames[0].save(
        os.path.join(OUT, "crop_flip.gif"),
        save_all=True,
        append_images=frames[1:],
        duration=900,
        loop=0,
        optimize=True,
    )
    QA["flip_frames"] = len(frames)
except Exception:
    QA["flip_error"] = traceback.format_exc()[-800:]
print("flip done", QA.get("flip_frames"), flush=True)

# ---------------------------------------------------------------- 2. calendar curves (Nov -> Oct)
try:
    SRC = {}
    for q in find("ingest_qa.json"):
        for k, v in json.load(open(q))["seasons"].items():
            if os.path.exists(os.path.join(os.path.dirname(q), f"comp_{k}.npy")):
                SRC.setdefault(k, []).append(
                    (min(v["step_valid_frac"] or [0]), os.path.dirname(q))
                )
    for q in find("earthdata_qa.json"):
        d = os.path.join(os.path.dirname(q), "hls")
        for k, v in json.load(open(q)).get("hls", {}).items():
            if os.path.exists(os.path.join(d, f"comp_{k}.npy")):
                SRC.setdefault(k, []).append((min(v["step_valid_frac"] or [0]), d))
    SRC = {k: max(v)[1] for k, v in SRC.items() if max(v)[0] >= 0.9}
    cs = pd.read_parquet(os.path.join(M2, "crop_seq_lgb.parquet"))
    cs = cs[cs.block_id.str.startswith(SITE)]
    NR, NC = GRID["NR"], GRID["NC"]

    def block_ndvi(sid, rr, cc):
        c = np.load(
            os.path.join(SRC[f"{SITE}_{sid}"], f"comp_{SITE}_{sid}.npy"), mmap_mode="r"
        )
        out = []
        for k in range(c.shape[0]):
            red = c[k, 2, : NR * 3, : NC * 3].astype(np.float32)
            nir = c[k, 3, : NR * 3, : NC * 3].astype(np.float32)
            nd = np.where(
                (red == -9999) | (nir == -9999),
                np.nan,
                (nir - red) / (nir + red + 1e-6),
            )
            with np.errstate(all="ignore"):
                out.append(np.nanmean(nd.reshape(NR, 3, NC, 3), (1, 3))[rr, cc])
        return np.array(out)  # [T, N]

    rows = []
    for y in range(2016, 2026):
        w, s_ = f"W{y}", f"S{y}"
        if f"{SITE}_{w}" not in SRC or f"{SITE}_{s_}" not in SRC:
            continue
        a = cs[cs.season_id == w][["block_id", "crop"]].rename(columns={"crop": "pre"})
        b = cs[cs.season_id == s_][["block_id", "crop"]]
        m = a.merge(b, on="block_id")
        m = m[(m.crop == "rice") & m.pre.isin(["clover", "wheat"])]
        if m.pre.nunique() < 2:
            continue
        rc = m.block_id.str.split("_", expand=True)
        rr, cc = rc[1].astype(int).values, rc[2].astype(int).values
        nd = np.concatenate([block_ndvi(w, rr, cc), block_ndvi(s_, rr, cc)], 0)
        for pre in ("clover", "wheat"):
            sel = (m.pre == pre).values
            for k, v in enumerate(np.nanmean(nd[:, sel], 1)):
                rows.append(
                    {
                        "year": y,
                        "precrop": pre,
                        "step": k,
                        "ndvi": float(v),
                        "n_blocks": int(sel.sum()),
                    }
                )
        print("calendar", y, m.pre.value_counts().to_dict(), flush=True)
    cal = pd.DataFrame(rows)
    # step k: winter steps 0-6 start Nov 1 (y-1) + 28k; summer steps 7-12 start May 16 (y) + 28(k-7)
    cal.to_csv(os.path.join(OUT, "calendar.csv"), index=False)
    QA["calendar_years"] = sorted(cal.year.unique().tolist())
except Exception:
    QA["calendar_error"] = traceback.format_exc()[-800:]
print("calendar done", flush=True)

# ---------------------------------------------------------------- 3. analogs card
try:
    A = pd.read_parquet(find("analogs.parquet")[0])
    A = A[A.block_id.str.startswith(SITE)]
    rc = A.block_id.str.split("_", expand=True)
    A["r"], A["c"] = rc[1].astype(int), rc[2].astype(int)
    inwin = (
        (A.r * 3 >= r0 + 60)
        & (A.r * 3 < r0 + WIN - 60)
        & (A.c * 3 >= c0 + 60)
        & (A.c * 3 < c0 + WIN - 60)
    )
    q = (
        A[inwin]
        .groupby("block_id")
        .similarity.mean()
        .sort_values(ascending=False)
        .index[0]
    )
    g = A[A.block_id == q].copy()
    rc2 = g.analog_block_id.str.split("_", expand=True)
    g["ar"], g["ac"] = rc2[1].astype(int), rc2[2].astype(int)
    qr, qc = int(g.r.iloc[0]), int(g.c.iloc[0])
    span = max(60, int(max(abs(g.ar - qr).max(), abs(g.ac - qc).max()) * 3 + 30))
    R0, C0 = max(qr * 3 - span, 0), max(qc * 3 - span, 0)
    c = z["lgb_cls30"][R0 : R0 + 2 * span, C0 : C0 + 2 * span]
    sc = 1000 / c.shape[1]
    img = Image.fromarray(lut(S_CLS)[c]).resize(
        (1000, int(c.shape[0] * sc)), Image.NEAREST
    )
    d = ImageDraw.Draw(img)
    for _, a in g.iterrows():
        x, y = (a.ac * 3 - C0 + 1.5) * sc, (a.ar * 3 - R0 + 1.5) * sc
        d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=(255, 255, 255), width=6)
        d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=(10, 37, 64), width=3)
    x, y = (qc * 3 - C0 + 1.5) * sc, (qr * 3 - R0 + 1.5) * sc
    d.ellipse(
        [x - 20, y - 20, x + 20, y + 20],
        fill=(255, 196, 0),
        outline=(10, 37, 64),
        width=4,
    )
    img.save(os.path.join(OUT, "analogs_card.png"), optimize=True)
    g[
        [
            "block_id",
            "rank",
            "analog_block_id",
            "similarity",
            "analog_seq",
            "delta_peak_ndvi",
        ]
    ].to_csv(os.path.join(OUT, "analogs_card.csv"), index=False)
    QA["analogs_card"] = {"query": q, "span_px": span, "km": round(2 * span * 0.03, 1)}
except Exception:
    QA["analogs_error"] = traceback.format_exc()[-800:]
json.dump(QA, open(os.path.join(OUT, "visuals_qa.json"), "w"), indent=1)
print(QA, flush=True)
