# Gate checks — run 2026-11-13 on Kaggle (private notebooks under manuelgamal)

## G1 — HLS download from Kaggle: PASS (via Microsoft Planetary Computer)
Notebook: `kaggle/gate1/` → kaggle.com/code/manuelgamal/fieldshift-gate1-hls-access
- Planetary Computer STAC has HLS v2 as `hls2-s30` and `hls2-l30`; anonymous signed access, no Earthdata login.
- Gharbia test box (30.85–31.10E, 30.70–30.95N), 2016–2025: 3,528 S30 items (from 2016-01-13) and 1,455 L30 items (from 2017-08-21). Item counts include overlapping tiles.
- Full-COG download from Kaggle: 3.16 MB/s (124.6 MB in ~40 s).
- Clipped windowed reads (~16×16 km, Sidi Ghazi box, `kaggle/gate2/`): 1.28 s per band per scene. Estimate for 10 years × ~2,500 scenes × 7 bands ≈ 6 h single-threaded → <1 h with 8–16 threads and a cloud-cover filter.
- NASA Earthdata (LP DAAC) is reachable from Kaggle (CMR 200), but data URLs 302 to the Earthdata login. Not needed; only add an Earthdata token as a Kaggle Secret if PC fails.

## G2 — FAO Egypt crop maps: PASS
Notebook: `kaggle/gate2/` → kaggle.com/code/manuelgamal/fieldshift-gate2-fao-labels
- FAO WaPOR-3 "Crop type mapping" datasets for Egypt, licence **CC BY 4.0** (FAO data catalog), public GCS bucket, no login:
  `https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-CROP-TYPE/WAPOR-3.L3-CROP-TYPE.EGY-{SITE}.{YEAR}.{GS}.tif`
- Sites: **SGZ** = Sidi Ghazi (Kafr El-Sheikh, northern Delta), **ZAN** = Zankalon (Sharqia, eastern Delta), **MLL** = Mallawi (Minya, Upper Egypt — not Delta).
- Seasons available: SGZ 2023.GS2, 2024.GS1, 2024.GS2; ZAN 2024.GS1, 2024.GS2 (2023.GS2 is 404); MLL all three. GS1 = winter (Oct–May), GS2 = summer (May–Oct).
- 10 m, EPSG:4326, GeoTIFF ~1–1.7 MB each. Downloads work inside Kaggle.
- Legend (from FAO SLD): GS1 winter: 1 wheat, 2 sugarbeet, 3 flax, 4 clover, 6 beans, 7 vegetables, 8 orchards, 9 medicinal, 12 bare, 13 water, 14 built-up. GS2 summer: 1 rice, 2 maize, 3 cotton, 7 veg, 8 orchards, 12 bare, 13 water, 14 built, 15 roads. 255 = nodata.
- **MLL uses extra codes** (winter 5, 15; summer 4, 5, 6, 9, 10) not in the shared SLD — read MLL's own SLD before use. MLL has no rice (expected for Upper Egypt).
- WorldCereal 2021: Zenodo 10.5281/zenodo.7875105, CC BY 4.0, global AEZ ZIPs (15–18 GB each). Optional extra labels; Egypt AEZ not yet identified.

## G3 — Is a berseem precrop effect detectable? SUPPORT PASS; PILOT EFFECT CONFOUNDED (2026-11-13)
Treatment support in the FAO maps is large (10 m pixels; 1 feddan ≈ 42 px):

| Site | winter 2023-24 → summer 2024 | rice | maize | cotton |
|---|---|---|---|---|
| SGZ | wheat | 1,042,097 | 66,313 | 209,756 |
| SGZ | clover | 377,406 | 36,351 | 88,251 |
| SGZ | sugar beet | 558,059 | 13,584 | 159,501 |
| ZAN | wheat | 2,250,664 | 696,543 | 64,867 |
| ZAN | clover | 950,159 | 454,015 | 16,187 |

- Clover→rice in SGZ alone ≈ 9,000 feddan-equivalents; clover→maize in ZAN ≈ 10,800. Sample size is not the risk; confounding and map error are.
- Effect itself not yet measured: needs summer-2024 HLS peak NDVI per block, compared clover→X vs wheat→X with covariates. This is Lane 1's milestone M1 (pilot).

## Consequences for the design
- Study sites change from Gharbia + Kafr El-Sheikh to **SGZ (Sidi Ghazi) + ZAN (Zankalon)**, where labels exist. MLL becomes an out-of-region test (Upper Egypt, maize system).
- Labels exist only for 2023–24, so Prithvi is trained on 2023–24 and predicts 2016–2023; hold out one site-season for accuracy.
- Sugar beet→X is a third precrop arm with big support in salt-affected SGZ.

### G3 pilot result (Lane 1 M1, run v4, SGZ, W2024 → S2024)
- 9,845 blocks are labelled in all three seasons; 760 clover→rice vs 4,554 wheat→rice.
- OLS effects on next-crop NDVI-days are +1.4 (clover) and +1.5 (sugar beet), ≈ 1.5% of the rice mean. Peak NDVI shows ≈ 0.
- **The placebo fails for every arm.** Precrop blocks were already +0.008 to +0.014 NDVI greener in the previous summer, so the selection is as large as the effect.
- Verdict: the effect is not identified from one season pair. M2 needs a multi-year history with block fixed effects (switchers) before any precrop claim; otherwise take the evidence-map pivot.

### G3 M2 result (switcher FE, 2020–2025, run v1, 2026-11-14)
- All lead placebos pass, so the within-block design removes the selection.
- Clover vs wheat → rice: peak NDVI −0.003 in SGZ (2,658 blocks) and ZAN (19,079 blocks), CIs exclude 0. NDVI-days ≈ 0, CIs span 0. The rest are ≈ 0.
- **No positive precrop vigor payoff is detectable at 90 m.** Lead with the evidence map: show honest nulls with tight CIs, plus a small clover→late-summer penalty as a hypothesis. v2 (LightGBM labels, 2016+ history, ECOSTRESS ET) is the confirmatory run.

### G3 M2 v2 result (LightGBM labels, 2016–2025, ECOSTRESS; 2026-11-14) — SUPERSEDES v1
- Placebo-passing within-block effects:
  - Clover → rice: NDVI-days +2.5 in ZAN (17,371 blocks); season ET +11.9 mm (ZAN) and +10.1 mm (SGZ).
  - Sugar beet → rice: NDVI-days +1.2 (SGZ, 9,236 blocks) and +3.6 (ZAN).
- Peak vigor stays ≈ 0 or slightly negative. Maize vigor outcomes fail the placebo.
- **G3 PASS (narrow):** a measurable precrop payoff in season length and water use, not in peak vigor. Placebo-failing effects are flagged unreliable in the evidence map.

### G3 follow-up (timing split, 2026-11-14) — SUPERSEDES the v2 "narrow pass"
- The v2 NDVI-days gains sit entirely in May 16 – Jul 10 (precrop greenness carry-over). Late-window (rice) effects are ≈ 0 or negative: ZAN clover −0.4%, SGZ clover −1.9%, SGZ sugar beet −1.2%.
- **G3: no detectable rice-season precrop payoff at 90 m.** Take the evidence-map pivot. Headline = two traps caught (selection, timing spill-over) with placebo-checked estimates.
