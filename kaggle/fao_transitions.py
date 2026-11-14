import os
import sys

import numpy as np
import rasterio

W = {
    1: "wheat",
    2: "sugarbeet",
    3: "flax",
    4: "clover",
    6: "beans",
    7: "veg",
    8: "orchard",
    9: "medicinal",
    12: "bare",
    13: "water",
    14: "built",
}
S = {
    1: "rice",
    2: "maize",
    3: "cotton",
    7: "veg",
    8: "orchard",
    12: "bare",
    13: "water",
    14: "built",
    15: "roads",
}
d = sys.argv[1]


def path(site, y):
    return os.path.join(d, f"WAPOR-3.L3-CROP-TYPE.EGY-{site}.{y}.tif")


for site in ["SGZ", "ZAN", "MLL"]:
    with rasterio.open(path(site, "2024.GS1")) as r:
        w = r.read(1)
        res = r.res
        crs = r.crs
    print(f"\n=== {site} res={res} crs={crs} shape={w.shape}")
    vals, c = np.unique(w, return_counts=True)
    print(
        "winter 2023-24 px:", {W.get(int(v), int(v)): int(n) for v, n in zip(vals, c)}
    )
    with rasterio.open(path(site, "2024.GS2")) as r:
        s = r.read(1)
    vals, c = np.unique(s, return_counts=True)
    print("summer 2024 px:", {S.get(int(v), int(v)): int(n) for v, n in zip(vals, c)})
    if s.shape != w.shape:
        print("shape mismatch", s.shape)
        continue
    print("winter 2023-24 -> summer 2024 (px):")
    for wv in [1, 4, 2, 6]:
        m = w == wv
        print(
            f"  {W[wv]:9s} ->", {S[sv]: int(((s == sv) & m).sum()) for sv in [1, 2, 3]}
        )
    if os.path.exists(path(site, "2023.GS2")):
        with rasterio.open(path(site, "2023.GS2")) as r:
            p = r.read(1)
        if p.shape == w.shape:
            print("summer 2023 -> winter 2023-24 (px):")
            for sv in [1, 2, 3]:
                m = p == sv
                print(
                    f"  {S[sv]:7s} ->",
                    {W[wv]: int(((w == wv) & m).sum()) for wv in [1, 4, 2, 6]},
                )
