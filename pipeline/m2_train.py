"""Lane 1 / M2 steps 7-10: Prithvi-EO-2.0 crop maps 2016-2025, LightGBM cross-check, switcher fixed effects.

Input: outputs of kernel fieldshift-lane1-m2-ingest (comp_/stats_/grid_ files). Kaggle GPU, internet on.
Split (docs/agents/01-lane-data.md): train SGZ W2024+S2024, ZAN W2024 (top 75% rows);
val ZAN S2024 (summer) + ZAN W2024 bottom 25% rows (winter); test SGZ S2023 (held out), MLL (out-of-region).
"""

import glob
import json
import math
import os
import subprocess
import sys
import time

if os.path.exists("/kaggle"):
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "rasterio",
            "einops",
            "lightgbm",
            "linearmodels",
            "pyarrow",
        ],
        check=False,
    )

import lightgbm as lgb
import numpy as np
import pandas as pd
import rasterio
import requests
import torch
import torch.nn.functional as F
from huggingface_hub import hf_hub_download
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject
from torch import nn

T0 = time.time()
WORK = "/kaggle/working" if os.path.exists("/kaggle") else os.path.abspath("work")
OUT = os.path.join(WORK, "m2")
os.makedirs(os.path.join(OUT, "qa"), exist_ok=True)
_g = glob.glob("/kaggle/input/**/grid_SGZ.json", recursive=True) or glob.glob(
    "work/hls/grid_SGZ.json"
)
IN = os.path.dirname(_g[0])
DEV = "cuda" if torch.cuda.is_available() else "cpu"
QA = {"timings_s": {}, "notes": []}
torch.manual_seed(0)
np.random.seed(0)


def tick(name, t):
    QA["timings_s"][name] = round(time.time() - t, 1)
    print(f"[{time.time() - T0:7.0f}s] {name} {QA['timings_s'][name]}s", flush=True)
    json.dump(
        QA, open(os.path.join(OUT, "qa", "m2_qa.json"), "w"), indent=1, default=str
    )


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
W_MAP = {1: 0, 2: 1, 3: 2, 4: 3, 6: 4, 7: 5, 8: 6, 9: 7, 12: 8, 13: 8, 14: 8}
S_MAP = {1: 0, 2: 1, 3: 2, 7: 3, 8: 4, 11: 5, 12: 6, 13: 6, 14: 6, 15: 6}
FRAMES = {
    "W": [1, 3, 4, 6],
    "S": [1, 2, 3, 4],
}  # 28-day steps fed to Prithvi (4 frames)
STEP0 = {"W": (-1, 11, 1), "S": (0, 5, 16)}  # (year offset, month, day) of step 0
MEAN = np.array([1087.0, 1342.0, 1433.0, 2734.0, 1958.0, 1363.0], np.float32)
STD = np.array([2248.0, 2179.0, 2178.0, 1850.0, 1242.0, 1049.0], np.float32)
FAO_URL = "https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-CROP-TYPE/"
FAO_SEASON = {"S2023": "2023.GS2", "W2024": "2024.GS1", "S2024": "2024.GS2"}

GRID = {
    s: json.load(open(os.path.join(IN, f"grid_{s}.json")))
    for s in ("SGZ", "ZAN", "MLL")
}
# HLS composites can come from two kernels (Planetary Computer ingest: ingest_qa.json "seasons";
# LP DAAC backfill: earthdata_qa.json "hls" with files under hls/). Per site-season keep the source whose
# worst 28-day step has the highest valid fraction.
_root = "/kaggle/input" if os.path.exists("/kaggle/input") else "work"
SRC = {}  # "SITE_SID" -> (dir, step_valid_frac, source)


def _register(qa_path, key, d, src):
    for k, v in json.load(open(qa_path)).get(key, {}).items():
        fr = v.get("step_valid_frac") or [0]
        if os.path.exists(os.path.join(d, f"comp_{k}.npy")) and (
            k not in SRC or min(fr) > min(SRC[k][1])
        ):
            SRC[k] = (d, fr, src)


for q in glob.glob(f"{_root}/**/ingest_qa.json", recursive=True):
    _register(q, "seasons", os.path.dirname(q), "planetary_computer")
for q in glob.glob(f"{_root}/**/earthdata_qa.json", recursive=True):
    _register(q, "hls", os.path.join(os.path.dirname(q), "hls"), "lpdaac")
ECO_DIR = {
    os.path.basename(p)[4:-4]: p
    for p in glob.glob(f"{_root}/**/eco/eco_*.npz", recursive=True)
}
SKIPPED = {k: v[1] for k, v in SRC.items() if min(v[1]) < 0.9}
SEASONS = {
    s: sorted(
        k[len(s) + 1 :] for k in SRC if k.startswith(s + "_") and k not in SKIPPED
    )
    for s in GRID
}
QA["seasons_skipped_low_coverage"] = SKIPPED
QA["season_source"] = {k: v[2] for k, v in SRC.items() if k not in SKIPPED}
QA["eco_seasons"] = sorted(ECO_DIR)
print({k: v for k, v in SEASONS.items()}, "skipped:", sorted(SKIPPED), flush=True)
print("eco:", sorted(ECO_DIR), flush=True)
LABEL_SRC = os.environ.get(
    "M2_LABEL_SRC", "lgb"
)  # crop_seq/FE label source: lgb | prithvi


# ---------------------------------------------------------------- data
def load_comp(site, sid):
    """[T,6,H,W] float32 reflectance DN with gaps filled from the nearest valid step (NaN if never valid)."""
    c = np.load(os.path.join(SRC[f"{site}_{sid}"][0], f"comp_{site}_{sid}.npy")).astype(
        np.float32
    )
    c[c == -9999] = np.nan
    T = c.shape[0]
    for k in range(T):  # nearest-step fill
        miss = np.isnan(c[k, 3])
        for d in range(1, T):
            if not miss.any():
                break
            for j in (k - d, k + d):
                if 0 <= j < T:
                    take = miss & ~np.isnan(c[j, 3])
                    c[k][:, take] = c[j][:, take]
                    miss &= ~take
    return c


def labels30(site, sid):
    g = GRID[site]
    p = os.path.join(WORK, f"{site}.{FAO_SEASON[sid]}.tif")
    if not os.path.exists(p):
        r = requests.get(
            FAO_URL + f"WAPOR-3.L3-CROP-TYPE.EGY-{site}.{FAO_SEASON[sid]}.tif",
            timeout=120,
        )
        if r.status_code != 200:
            return None
        open(p, "wb").write(r.content)
    dst = np.full((g["H"], g["W"]), 255, np.uint8)
    with rasterio.open(p) as src:
        reproject(
            rasterio.band(src, 1),
            dst,
            dst_transform=from_origin(g["x0"], g["y1"], 30, 30),
            dst_crs=g["crs"],
            resampling=Resampling.mode,
            dst_nodata=255,
        )
    lut = np.full(256, 255, np.uint8)
    for k, v in (W_MAP if sid[0] == "W" else S_MAP).items():
        lut[k] = v
    return lut[dst]


def coords(site, sid):
    g = GRID[site]
    tf = Transformer.from_crs(g["crs"], "EPSG:4326", always_xy=True)
    lon, lat = tf.transform(g["x0"] + g["W"] * 15, g["y1"] - g["H"] * 15)
    yo, m, d = STEP0[sid[0]]
    start = pd.Timestamp(year=int(sid[1:]) + yo, month=m, day=d)
    tc = []
    for k in FRAMES[sid[0]]:
        mid = start + pd.Timedelta(days=28 * k + 14)
        tc.append([mid.year, mid.dayofyear])
    return np.array(tc, np.float32), np.array([lat, lon], np.float32)


def to_input(c, sid):
    """[T,6,H,W] -> normalised [6,4,H,W] for Prithvi (NaN -> 0 = band mean)."""
    x = c[FRAMES[sid[0]]]  # [4,6,H,W]
    x = (x - MEAN[None, :, None, None]) / STD[None, :, None, None]
    x = np.nan_to_num(x, nan=0.0)
    return np.ascontiguousarray(x.transpose(1, 0, 2, 3))


t = time.time()
LAB = {}
for site in GRID:
    for sid in FAO_SEASON:
        if sid in SEASONS[site]:
            lab = labels30(site, sid)
            if lab is not None:
                LAB[(site, sid)] = lab
QA["label_px"] = {f"{k[0]}_{k[1]}": int((v != 255).sum()) for k, v in LAB.items()}
tick("labels", t)

SPLIT = {
    ("SGZ", "W2024"): "train",
    ("SGZ", "S2024"): "train",
    ("ZAN", "W2024"): "train_top",
    ("ZAN", "S2024"): "val",
    ("SGZ", "S2023"): "test",
    ("MLL", "S2023"): "test_oor",
    ("MLL", "W2024"): "test_oor",
    ("MLL", "S2024"): "test_oor",
}


def split_mask(key, H):
    rows = np.arange(H)[:, None]
    sp = SPLIT.get(key)
    if sp == "train_top":
        return {"train": rows < int(H * 0.75), "val": rows >= int(H * 0.75)}
    return {sp: np.ones((H, 1), bool)} if sp else {}


# ---------------------------------------------------------------- model
sys.path.insert(
    0,
    os.path.dirname(
        hf_hub_download("ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL", "prithvi_mae.py")
    ),
)
from prithvi_mae import PrithviViT

ckpt = hf_hub_download(
    "ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL", "Prithvi_EO_V2_300M_TL.pt"
)
FEAT_LAYERS = [7, 15, 23]
N_FROZEN = 16


class CropNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc = PrithviViT(
            img_size=224,
            patch_size=(1, 16, 16),
            num_frames=4,
            in_chans=6,
            embed_dim=1024,
            depth=24,
            num_heads=16,
            mlp_ratio=4.0,
            coords_encoding=["time", "location"],
            coords_scale_learn=True,
        )
        sd = torch.load(ckpt, map_location="cpu", weights_only=True)
        sd = {
            k[len("encoder.") :]: v
            for k, v in sd.items()
            if k.startswith("encoder.") and "pos_embed" not in k
        }
        missing, unexpected = self.enc.load_state_dict(sd, strict=False)
        QA["prithvi_load"] = {"missing": missing, "unexpected": unexpected}
        self.proj = nn.ModuleList([nn.Conv2d(4 * 1024, 256, 1) for _ in FEAT_LAYERS])

        def up(i, o):
            return nn.Sequential(
                nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
                nn.Conv2d(i, o, 3, padding=1),
                nn.BatchNorm2d(o),
                nn.ReLU(inplace=True),
            )

        self.up = nn.Sequential(up(256, 128), up(128, 64), up(64, 64), up(64, 64))
        self.head = nn.ModuleDict(
            {"W": nn.Conv2d(64, len(W_CLS), 1), "S": nn.Conv2d(64, len(S_CLS), 1)}
        )

    def forward(self, x, tc, lc, season):
        feats = self.enc.forward_features(x, tc, lc)
        f = 0
        for p, li in zip(self.proj, FEAT_LAYERS):
            tok = feats[li][:, 1:, :]  # B, 4*196, 1024
            B = tok.shape[0]
            tok = (
                tok.reshape(B, 4, 14, 14, 1024)
                .permute(0, 1, 4, 2, 3)
                .reshape(B, 4 * 1024, 14, 14)
            )
            f = f + p(tok)
        emb = self.up(f)
        return self.head[season](emb), emb


model = CropNet().to(DEV)
for i, blk in enumerate(model.enc.blocks):
    for p_ in blk.parameters():
        p_.requires_grad = i >= N_FROZEN
for p_ in model.enc.patch_embed.parameters():
    p_.requires_grad = False
print("prithvi load:", {k: len(v) for k, v in QA["prithvi_load"].items()}, flush=True)

# ---------------------------------------------------------------- training data in memory
t = time.time()
TRAIN, VAL = [], []
CACHE = {}
for key, lab in LAB.items():
    site, sid = key
    m = split_mask(key, lab.shape[0])
    if not ({"train", "val"} & set(m)):
        continue
    c = load_comp(site, sid)
    CACHE[key] = c
    x = to_input(c, sid)
    tc, lc = coords(site, sid)
    for sp in ("train", "val"):
        if sp in m:
            y = np.where(np.broadcast_to(m[sp], lab.shape), lab, 255).astype(np.uint8)
            (TRAIN if sp == "train" else VAL).append((key, x, y, tc, lc))
tick("load_train", t)


def class_weights(season):
    n = len(W_CLS) if season == "W" else len(S_CLS)
    cnt = np.zeros(n)
    for key, _, y, _, _ in TRAIN:
        if key[1][0] == season:
            cnt += np.bincount(y[y != 255], minlength=n)[:n]
    w = 1 / np.sqrt(np.maximum(cnt, 1))
    return torch.tensor(w / w.mean(), dtype=torch.float32, device=DEV)


CW = {"W": class_weights("W"), "S": class_weights("S")}


def sample(pool, season, B=4, P=224):
    cand = [r for r in pool if r[0][1][0] == season]
    xs, ys, tcs, lcs = [], [], [], []
    while len(xs) < B:
        key, x, y, tc, lc = cand[np.random.randint(len(cand))]
        H, W = y.shape
        i, j = np.random.randint(0, H - P + 1), np.random.randint(0, W - P + 1)
        yy = y[i : i + P, j : j + P]
        if (yy != 255).mean() < 0.3:
            continue
        xx = x[:, :, i : i + P, j : j + P]
        if np.random.rand() < 0.5:
            xx, yy = xx[..., ::-1], yy[:, ::-1]
        if np.random.rand() < 0.5:
            xx, yy = xx[..., ::-1, :], yy[::-1, :]
        xs.append(np.ascontiguousarray(xx))
        ys.append(np.ascontiguousarray(yy))
        tcs.append(tc)
        lcs.append(lc)
    f = lambda a, dt: torch.tensor(np.stack(a), dtype=dt, device=DEV)
    return (
        f(xs, torch.float32),
        f(ys, torch.long),
        f(tcs, torch.float32),
        f(lcs, torch.float32),
    )


STEPS = int(os.environ.get("M2_STEPS", 1800))
params = [
    {
        "params": [
            p_
            for n_, p_ in model.named_parameters()
            if p_.requires_grad and n_.startswith("enc.")
        ],
        "lr": 3e-5,
    },
    {
        "params": [
            p_ for n_, p_ in model.named_parameters() if not n_.startswith("enc.")
        ],
        "lr": 3e-4,
    },
]
opt = torch.optim.AdamW(params, weight_decay=0.01)
sched = torch.optim.lr_scheduler.OneCycleLR(
    opt, max_lr=[3e-5, 3e-4], total_steps=STEPS, pct_start=0.1
)
scaler = torch.cuda.amp.GradScaler()
t = time.time()
best, hist = 1e9, []
for step in range(STEPS):
    season = "W" if step % 2 == 0 else "S"
    model.train()
    x, y, tc, lc = sample(TRAIN, season)
    with torch.autocast("cuda", dtype=torch.float16):
        logits, _ = model(x, tc, lc, season)
        loss = F.cross_entropy(logits.float(), y, weight=CW[season], ignore_index=255)
    opt.zero_grad(set_to_none=True)
    scaler.scale(loss).backward()
    scaler.step(opt)
    scaler.update()
    sched.step()
    if (step + 1) % 150 == 0:
        model.eval()
        vl = []
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            for s_ in ("W", "S"):
                for _ in range(6):
                    x, y, tc, lc = sample(VAL, s_)
                    lg, _ = model(x, tc, lc, s_)
                    vl.append(F.cross_entropy(lg.float(), y, ignore_index=255).item())
        v = float(np.mean(vl))
        hist.append(
            {
                "step": step + 1,
                "train_loss": round(loss.item(), 4),
                "val_loss": round(v, 4),
            }
        )
        print(hist[-1], f"{time.time() - t:.0f}s", flush=True)
        if v < best:
            best = v
            torch.save(model.state_dict(), os.path.join(WORK, "best.pt"))
QA["train_history"] = hist
model.load_state_dict(torch.load(os.path.join(WORK, "best.pt"), map_location=DEV))
model.eval()
tick("train_prithvi", t)


# ---------------------------------------------------------------- inference (sliding window)
@torch.no_grad()
def predict(x, tc, lc, season, P=224, S=176):
    C, T, H, W = x.shape
    n = len(W_CLS) if season == "W" else len(S_CLS)
    Hp, Wp = max(H, P), max(W, P)
    xp = np.zeros((C, T, Hp, Wp), np.float32)
    xp[..., :H, :W] = x
    prob = torch.zeros((n, Hp, Wp), device=DEV)
    emb = torch.zeros((64, Hp, Wp), device=DEV)
    cnt = torch.zeros((1, Hp, Wp), device=DEV)
    ii = sorted(set(list(range(0, Hp - P + 1, S)) + [Hp - P]))
    jj = sorted(set(list(range(0, Wp - P + 1, S)) + [Wp - P]))
    tct = torch.tensor(tc[None], device=DEV)
    lct = torch.tensor(lc[None], device=DEV)
    for i in ii:
        batch = [xp[:, :, i : i + P, j : j + P] for j in jj]
        for b0 in range(0, len(batch), 8):
            xb = torch.tensor(np.stack(batch[b0 : b0 + 8]), device=DEV)
            k = xb.shape[0]
            with torch.autocast("cuda", dtype=torch.float16):
                lg, e = model(xb, tct.expand(k, -1, -1), lct.expand(k, -1), season)
            pr = lg.float().softmax(1)
            for q, j in enumerate(jj[b0 : b0 + k]):
                prob[:, i : i + P, j : j + P] += pr[q]
                emb[:, i : i + P, j : j + P] += e[q].float()
                cnt[:, i : i + P, j : j + P] += 1
    prob = (prob / cnt)[:, :H, :W].cpu().numpy()
    emb = (emb / cnt)[:, :H, :W].cpu().numpy()
    return prob, emb


def block_majority(cls, prob, ncls, valid):
    """30 m class/prob -> 90 m blocks: majority class, purity (share of 9 px), mean prob of the majority class."""
    H, W = cls.shape
    NR, NC = H // 3, W // 3
    c = (
        np.where(valid, cls, 255)[: NR * 3, : NC * 3]
        .reshape(NR, 3, NC, 3)
        .transpose(0, 2, 1, 3)
        .reshape(NR, NC, 9)
    )
    cnt = np.stack([(c == k).sum(-1) for k in range(ncls)], -1)
    maj = cnt.argmax(-1)
    pur = cnt.max(-1) / 9.0
    pm = np.take_along_axis(
        prob[:, : NR * 3, : NC * 3]
        .reshape(ncls, NR, 3, NC, 3)
        .mean((2, 4))
        .transpose(1, 2, 0),
        maj[..., None],
        -1,
    )[..., 0]
    maj = np.where(cnt.sum(-1) == 0, 255, maj)
    return maj.astype(np.uint8), pur.astype(np.float32), pm.astype(np.float32)


t = time.time()
PRED = {}
for site in GRID:
    for sid in SEASONS[site]:
        key = (site, sid)
        c = CACHE.pop(key, None)
        if c is None:
            c = load_comp(site, sid)
        valid = ~np.isnan(c[:, 3]).all(0)
        x = to_input(c, sid)
        tc, lc = coords(site, sid)
        prob, emb = predict(x, tc, lc, sid[0])
        cls = prob.argmax(0).astype(np.uint8)
        cls[~valid] = 255
        ncls = prob.shape[0]
        maj, pur, pm = block_majority(cls, prob, ncls, valid)
        NR, NC = maj.shape
        bemb = (
            emb[:, : NR * 3, : NC * 3]
            .reshape(64, NR, 3, NC, 3)
            .mean((2, 4))
            .astype(np.float16)
        )
        PRED[key] = {"cls": cls, "conf": prob.max(0).astype(np.float16)}
        np.savez_compressed(
            os.path.join(OUT, f"pred_{site}_{sid}.npz"),
            cls30=cls,
            block_cls=maj,
            block_purity=pur,
            block_prob=pm,
            block_emb=bemb,
        )
        # LightGBM features need the composite; keep the compact feature cube
        T = c.shape[0]
        nd = (c[:, 3] - c[:, 2]) / (c[:, 3] + c[:, 2] + 1e-6)
        PRED[key]["feat"] = np.concatenate(
            [
                np.nan_to_num(c, nan=-1).reshape(T * 6, *c.shape[2:]) / 1e4,
                np.nan_to_num(nd, nan=-1),
            ],
            0,
        ).astype(np.float16)
        del c, x, prob, emb
    print(site, "inferred", flush=True)
tick("infer_prithvi", t)

# ---------------------------------------------------------------- LightGBM cross-check
t = time.time()
LGB = {}
for season, ncls in (("W", len(W_CLS)), ("S", len(S_CLS))):
    Xs, ys = [], []
    for key, lab in LAB.items():
        m = split_mask(key, lab.shape[0]).get("train")
        if m is None or key[1][0] != season:
            continue
        ok = (lab != 255) & np.broadcast_to(m, lab.shape)
        idx = np.flatnonzero(ok)
        idx = np.random.choice(idx, min(len(idx), 150_000), replace=False)
        f = PRED[key]["feat"].reshape(PRED[key]["feat"].shape[0], -1)
        Xs.append(f[:, idx].T.astype(np.float32))
        ys.append(lab.ravel()[idx])
    X, y = np.concatenate(Xs), np.concatenate(ys)
    clf = lgb.LGBMClassifier(
        n_estimators=int(os.environ.get("M2_LGB_TREES", 250)),
        learning_rate=0.08,
        num_leaves=63,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        class_weight="balanced",
        verbose=-1,
    )
    clf.fit(X, y)
    LGB[season] = clf
for key in PRED:
    f = PRED[key]["feat"]
    clf = LGB[key[1][0]]
    ff = f.reshape(f.shape[0], -1)
    valid = PRED[key]["cls"].ravel() != 255
    ncls = len(W_CLS) if key[1][0] == "W" else len(S_CLS)
    prob = np.zeros((ncls, ff.shape[1]), np.float32)
    vi = np.flatnonzero(valid)
    for a in range(0, len(vi), 400_000):  # chunked predict_proba on valid pixels only
        ii = vi[a : a + 400_000]
        pp = clf.predict_proba(ff[:, ii].T.astype(np.float32))
        prob[clf.classes_[:, None], ii[None, :]] = pp.T
    prob = prob.reshape(ncls, *f.shape[1:])
    lc = prob.argmax(0).astype(np.uint8)
    lc[PRED[key]["cls"] == 255] = 255
    PRED[key]["lgb"] = lc
    maj, pur, pm = block_majority(lc, prob, ncls, lc != 255)
    pth = os.path.join(OUT, f"pred_{key[0]}_{key[1]}.npz")
    z = dict(np.load(pth))
    z.update(lgb_cls30=lc, lgb_block_cls=maj, lgb_block_purity=pur, lgb_block_prob=pm)
    np.savez_compressed(pth, **z)
    del prob, PRED[key]["feat"]
    print("lgb", key, f"{time.time() - t:.0f}s", flush=True)
tick("lightgbm", t)


# ---------------------------------------------------------------- evaluation
def metrics(pred, lab, names):
    ok = (lab != 255) & (pred != 255)
    p, l_ = pred[ok].astype(int), lab[ok].astype(int)
    n = len(names)
    cm = np.zeros((n, n), np.int64)
    np.add.at(cm, (l_, p), 1)
    oa = float(np.trace(cm) / max(cm.sum(), 1))
    f1 = {}
    for k, nm in enumerate(names):
        tp, fp, fn = cm[k, k], cm[:, k].sum() - cm[k, k], cm[k, :].sum() - cm[k, k]
        if cm[k, :].sum() > 0:
            f1[nm] = round(float(2 * tp / max(2 * tp + fp + fn, 1)), 3)
    return oa, f1, cm


t = time.time()
EVAL = {}
for key, lab in LAB.items():
    names = W_CLS if key[1][0] == "W" else S_CLS
    for sp, m in split_mask(key, lab.shape[0]).items():
        lab_s = np.where(np.broadcast_to(m, lab.shape), lab, 255)
        for src in ("prithvi", "lgb"):
            pred = PRED[key]["cls"] if src == "prithvi" else PRED[key]["lgb"]
            oa, f1, cm = metrics(pred, lab_s, names)
            EVAL[f"{key[0]}_{key[1]}_{sp}_{src}"] = {"oa": round(oa, 3), "f1": f1}
            if True:
                pd.DataFrame(
                    cm,
                    index=[f"true_{n}" for n in names],
                    columns=[f"pred_{n}" for n in names],
                ).to_csv(
                    os.path.join(OUT, "qa", f"confusion_{key[0]}_{key[1]}_{sp}_{src}.csv")
                )
        both = (PRED[key]["cls"] != 255) & np.broadcast_to(m, lab.shape)
        EVAL[f"{key[0]}_{key[1]}_{sp}_agreement"] = round(
            float((PRED[key]["cls"][both] == PRED[key]["lgb"][both]).mean()), 3
        )
QA["eval"] = EVAL
for k, v in EVAL.items():
    if "test" in k or "val" in k:
        print(k, v, flush=True)

# rice area per site-year (ha, 30 m px = 0.09 ha) for Prithvi and LightGBM, vs FAO where available
area = []
for (site, sid), d in PRED.items():
    if sid[0] != "S":
        continue
    row = {
        "site": site,
        "season_id": sid,
        "prithvi_rice_ha": float((d["cls"] == 0).sum() * 0.09),
        "lgb_rice_ha": float((d["lgb"] == 0).sum() * 0.09),
    }
    if (site, sid) in LAB:  # like-for-like: only pixels FAO labels
        lm = LAB[(site, sid)] != 255
        row["fao_rice_ha"] = float((LAB[(site, sid)] == 0).sum() * 0.09)
        row["prithvi_rice_ha_fao_mask"] = float(((d["cls"] == 0) & lm).sum() * 0.09)
        row["lgb_rice_ha_fao_mask"] = float(((d["lgb"] == 0) & lm).sum() * 0.09)
    area.append(row)
area = pd.DataFrame(area).sort_values(["site", "season_id"])
area.to_csv(os.path.join(OUT, "qa", "rice_area.csv"), index=False)
print(area.to_string(index=False), flush=True)
tick("eval", t)

# ---------------------------------------------------------------- crop_seq + block_season for all seasons
t = time.time()
cs, bs = [], []
for site in ("SGZ", "ZAN", "MLL"):
    g = GRID[site]
    NR, NC = g["NR"], g["NC"]
    if (
        site,
        "W2024",
    ) in LAB:  # cropland mask from FAO W2024 (same rule as M1: field-crop share >= 0.6)
        lw = LAB[(site, "W2024")][: NR * 3, : NC * 3].reshape(NR, 3, NC, 3)
        cf = np.isin(lw, [0, 1, 2, 3, 4, 5]).mean((1, 3))
    else:
        cf = np.ones((NR, NC))
    rr, cc = np.nonzero(cf >= 0.6)
    ids = np.array([f"{site}_{r}_{c}" for r, c in zip(rr, cc)])
    for sid in SEASONS[site]:
        z = np.load(os.path.join(OUT, f"pred_{site}_{sid}.npz"))
        names = np.array((W_CLS if sid[0] == "W" else S_CLS) + [None], dtype=object)
        pre = "lgb_" if LABEL_SRC == "lgb" else ""
        bc = z[pre + "block_cls"][rr, cc]
        crop = names[np.where(bc == 255, len(names) - 1, bc)]
        pur = z[pre + "block_purity"][rr, cc]
        ok = (crop != None) & (pur >= 0.6)
        cs.append(
            pd.DataFrame(
                {
                    "block_id": ids[ok],
                    "season_id": sid,
                    "crop": crop[ok].astype(str),
                    "prob": z[pre + "block_prob"][rr, cc][ok].astype(float),
                    "source": LABEL_SRC,
                    "purity": pur[ok].astype(float),
                }
            )
        )
        st = np.load(os.path.join(SRC[f"{site}_{sid}"][0], f"stats_{site}_{sid}.npz"))
        days = (pd.Timestamp(str(st["end"])) - pd.Timestamp(str(st["start"]))).days + 1

        def b(a):
            with np.errstate(all="ignore"):
                return np.nanmean(
                    a[: NR * 3, : NC * 3].astype(np.float32).reshape(NR, 3, NC, 3),
                    (1, 3),
                )[rr, cc]

        bs.append(
            pd.DataFrame(
                {
                    "block_id": ids,
                    "season_id": sid,
                    "crop": pd.Series(np.where(ok, crop, None), dtype="object"),
                    "peak_ndvi": b(st["peak_ndvi"]),
                    "peak_gcvi": b(st["peak_gcvi"]),
                    "ndvi_auc": b(st["mean_ndvi"]) * days,
                    "n_clear_obs": np.nan_to_num(b(st["n_clear"]))
                    .round()
                    .astype(np.int64),
                }
            )
        )
        ek = f"{site}_{sid}"
        if ek in ECO_DIR:  # ECOSTRESS on the 90 m block grid: season ET = mean daily ET x season days
            e = np.load(ECO_DIR[ek])
            for col, var, f in (
                ("et_season_mm", "et", days),
                ("lst_mean_c", "lst", 1),
                ("esi_mean", "esi", 1),
            ):
                if f"{var}_mean" in e:
                    bs[-1][col] = e[f"{var}_mean"][rr, cc].astype(np.float32) * f
                    bs[-1][f"{var}_n_obs"] = e[f"{var}_n"][rr, cc].astype(np.int16)
crop_seq = pd.concat(cs, ignore_index=True)
block_season = pd.concat(bs, ignore_index=True)
crop_seq.to_parquet(os.path.join(OUT, f"crop_seq_{LABEL_SRC}.parquet"), index=False)
block_season.to_parquet(os.path.join(OUT, "block_season_hls.parquet"), index=False)
QA["crop_seq_rows"] = len(crop_seq)
tick("artefacts", t)

# ---------------------------------------------------------------- switcher fixed effects (G3, within-block design)
t = time.time()
try:
    from linearmodels.panel import PanelOLS

    W_ = crop_seq[crop_seq.season_id.str[0] == "W"][
        ["block_id", "season_id", "crop"]
    ].copy()
    W_["year"] = W_.season_id.str[1:].astype(int)
    S_ = block_season[block_season.season_id.str[0] == "S"].copy()
    S_["year"] = S_.season_id.str[1:].astype(int)
    S_ = S_.dropna(subset=["crop"])
    prevS = (
        S_[["block_id", "year", "peak_ndvi"]]
        .assign(year=lambda d: d.year + 1)
        .rename(columns={"peak_ndvi": "prev_peak"})
    )
    D = S_.merge(
        W_[["block_id", "year", "crop"]].rename(columns={"crop": "precrop"}),
        on=["block_id", "year"],
    )
    D = D.merge(prevS, on=["block_id", "year"], how="left")
    D = D[D.n_clear_obs >= 5]
    FE = []
    for site in ("SGZ", "ZAN"):
        for treat in ("clover", "sugarbeet", "beans"):
            for nxt in ("rice", "maize", "cotton"):
                d = D[
                    (D.block_id.str.startswith(site))
                    & (D.crop == nxt)
                    & D.precrop.isin([treat, "wheat"])
                ].copy()
                d["T"] = (d.precrop == treat).astype(float)
                sw = d.groupby("block_id")["T"].agg(["min", "max", "size"])
                switchers = sw[(sw["min"] == 0) & (sw["max"] == 1)].index
                d = d[d.block_id.isin(switchers)]
                if d["T"].sum() < 200 or (1 - d["T"]).sum() < 200:
                    continue
                rc = d.block_id.str.split("_", expand=True)
                d["cluster"] = (
                    (rc[1].astype(int) // 10).astype(str)
                    + "_"
                    + (rc[2].astype(int) // 10).astype(str)
                )
                d = d.set_index(["block_id", "year"])
                for outcome in ("peak_ndvi", "ndvi_auc", "et_season_mm", "lst_mean_c"):
                    if outcome not in d.columns:
                        continue
                    dd = d.dropna(subset=[outcome])
                    nobs = {"et_season_mm": "et_n_obs", "lst_mean_c": "lst_n_obs"}.get(outcome)
                    if nobs:
                        dd = dd[dd[nobs] >= 2]
                    if dd["T"].sum() < 100 or (1 - dd["T"]).sum() < 100:
                        continue
                    res = PanelOLS(
                        dd[outcome], dd[["T"]], entity_effects=True, time_effects=True
                    ).fit(
                        cov_type="clustered",
                        clusters=pd.Categorical(dd["cluster"]).codes,
                    )
                    ci = res.conf_int().loc["T"]
                    # lead placebo: next winter's precrop should not "affect" this summer
                    lead = W_.assign(year=W_.year - 1).rename(
                        columns={"crop": "lead_precrop"}
                    )[["block_id", "year", "lead_precrop"]]
                    dl = dd.reset_index().merge(lead, on=["block_id", "year"])
                    dl = dl[dl.lead_precrop.isin([treat, "wheat"])]
                    dl["L"] = (dl.lead_precrop == treat).astype(float)
                    plac = None
                    if dl["L"].nunique() == 2 and len(dl) > 400:
                        dl = dl.set_index(["block_id", "year"])
                        pr = PanelOLS(
                            dl[outcome],
                            dl[["L", "T"]],
                            entity_effects=True,
                            time_effects=True,
                            drop_absorbed=True,
                        ).fit(
                            cov_type="clustered",
                            clusters=pd.Categorical(dl["cluster"]).codes,
                        )
                        pci = pr.conf_int().loc["L"]
                        plac = {
                            "estimate": float(pr.params["L"]),
                            "ci": [float(pci.iloc[0]), float(pci.iloc[1])],
                            "pass": bool(pci.iloc[0] <= 0 <= pci.iloc[1]),
                        }
                    FE.append(
                        {
                            "effect_id": f"{site}:{treat}-vs-wheat>{nxt}:{outcome}:switcher_fe",
                            "site": site,
                            "precrop_treat": treat,
                            "precrop_ctrl": "wheat",
                            "next_crop": nxt,
                            "outcome": outcome,
                            "method": "switcher_fe",
                            "estimate": float(res.params["T"]),
                            "ci_low": float(ci.iloc[0]),
                            "ci_high": float(ci.iloc[1]),
                            "n_treat": int(dd["T"].sum()),
                            "n_ctrl": int((1 - dd["T"]).sum()),
                            "n_blocks": int(dd.index.get_level_values(0).nunique()),
                            "stratum": "all",
                            "schema_version": 1,
                            "lead_placebo": plac,
                        }
                    )
    FE = pd.DataFrame(FE)
    FE.to_json(
        os.path.join(OUT, "effects_switcher_fe.json"), orient="records", indent=1
    )
    print(
        FE[
            [
                "effect_id",
                "estimate",
                "ci_low",
                "ci_high",
                "n_treat",
                "n_ctrl",
                "n_blocks",
            ]
        ].to_string(index=False),
        flush=True,
    )
    for r in FE.itertuples():
        print(r.effect_id, "lead placebo:", r.lead_placebo, flush=True)
except Exception as e:
    import traceback

    traceback.print_exc()
    QA["notes"].append(f"switcher FE failed: {e!r}")
tick("switcher_fe", t)
QA["total_runtime_s"] = round(time.time() - T0, 1)
json.dump(QA, open(os.path.join(OUT, "qa", "m2_qa.json"), "w"), indent=1, default=str)
os.remove(os.path.join(WORK, "best.pt")) if os.path.exists(
    os.path.join(WORK, "best.pt")
) else None
print("DONE", QA["total_runtime_s"])
