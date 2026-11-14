# Decisions log

| Date | Lane | Change | Reason |
|---|---|---|---|
| 2026-11-13 | 1 | Study sites = SGZ Sidi Ghazi + ZAN Zankalon (MLL Mallawi = out-of-region test), replacing Gharbia | Only places with FAO WaPOR-3 crop labels (CC BY 4.0); see `gates.md` |
| 2026-11-13 | 1 | HLS source = Microsoft Planetary Computer (`hls2-s30`, `hls2-l30`) | Works from Kaggle without Earthdata login; same NASA HLS v2 product |
| 2026-11-13 | 1 | Block = 90 m (3×3 HLS px) on EPSG:32636, origin snapped to 90 m | ≈ 1.9 feddan, close to the median Delta holding; avoids claiming per-field results |
| 2026-11-13 | 1 | Season windows: S2023 2023-05-16→10-31, W2024 2023-11-01→2024-05-15, S2024 2024-05-16→10-31 | Matches FAO GS1/GS2 and Delta calendars; no overlap |
| 2026-11-13 | 1 | Label filter: cropland_frac(W2024) ≥ 0.6 for blocks; purity ≥ 0.6 per season for labels | Removes mixed/urban blocks; mixed blocks would blur treatment |
| 2026-11-13 | 1 | `salinity_index` v1 = mean √(blue·red) over clear bare-soil looks (NDVI < 0.25) in S2023 | Pre-treatment for the W2024 precrop; weak proxy, replace when a better one is validated |
| 2026-11-13 | 1 | ECOSTRESS, SMAP, IMERG columns null in v1 | Need an Earthdata token as a Kaggle Secret; regional layers are context only |
| 2026-11-13 | 1 | Elevation from NASADEM (Planetary Computer) | NASA reprocessing of SRTM, no login |
| 2026-11-13 | 1 | Canal distance uses OSM waterway=canal\|river\|ditch; drain distance uses waterway=drain | OSM tagging in the Delta; ditch is usually a mesqa |
| 2026-11-13 | 1 | rice_zone, governorate are governorate-level constants per site | Decree 26/2025 is governorate-level; no finer public map |
| 2026-11-13 | 1 | Waterways from the Geofabrik OSM Egypt extract + Natural Earth coastline instead of Overpass | Overpass public endpoints returned 406/502 to automated requests |
| 2026-11-13 | 1 | POWER radiation units read from the API response (AG community = MJ/m²/day) | v1–v3 multiplied by 3.6 in error; ET₀ was 3.6× too high |
| 2026-11-13 | 1 | M2 composites: 28-day median steps (winter 7 from Nov 1, summer 6 from May 16), 6 Prithvi bands, scenes < 80% cloud, 30 m grid identical to M1 | Fixed phenology steps make seasons comparable across years; same grid keeps block ids stable |
| 2026-11-13 | 1 | Prithvi-EO-2.0-300M-TL with 4 frames (winter steps 1,3,4,6; summer 1,2,3,4) + time/location coords; blocks 0–15 frozen; UPerNet-lite head, separate winter/summer class heads | Model was pre-trained on 4 frames; freezing fits a T4 and the time budget |
| 2026-11-13 | 1 | Cross-check = LightGBM per-pixel on all composite steps instead of TESSERA | TESSERA needs a separate download pipeline; an independent model family on the same labels answers the same question (map stability) faster |
| 2026-11-13 | 1 | ZAN W2024 split by rows: top 75% train, bottom 25% winter validation | ZAN has no S2023 label; need a winter validation set |
| 2026-11-13 | 1 | G3 primary design = switcher two-way fixed effects (block + year FE) over 2016–2025, with a lead placebo | M1 placebo showed selection on land quality; within-block comparison removes time-invariant land differences |
| 2026-11-13 | 1 | Usable history = S2020–S2025 and W2021–W2025; seasons with any 28-day step < 90% valid are skipped | Planetary Computer `hls2-*` has almost no scenes before 2020 (0–10 dates per season 2016–2019; W2020 lacks Nov–Dec 2019). The full 2013+ archive needs Earthdata (LP DAAC) |
| 2026-11-14 | 1 | Crop label source for crop_seq and effects = LightGBM, not Prithvi (env `M2_LABEL_SRC`) | M2 v1: LightGBM OA 0.82 (SGZ S2023 test) / 0.81 (ZAN W2024 val) vs Prithvi 0.64 / 0.58; Prithvi reached only 0.48 OA on its own training season, so it is undertrained. Prithvi is kept for block embeddings (analogs) |
| 2026-11-14 | 1 | m2_train reads HLS from both the Planetary Computer and LP DAAC kernels; per site-season it keeps the source with the best worst-step coverage | Backfills 2016–2020 without changing the format; one rule picks the source |
| 2026-11-14 | 1 | Rice-area check is on FAO-labelled pixels only | v1 compared whole-grid predictions with FAO's labelled subset, which is not like-for-like |
| 2026-11-14 | 1 | G3 framing = evidence map with honest nulls; the switcher FE shows no positive precrop vigor payoff (all placebos pass) | The M1 positive effect was selection on land quality; within-block estimates are ≈ 0 or slightly negative after clover |
| 2026-11-14 | 1 | Headline effects = v2 switcher FE effects that pass the lead placebo (season length, ECOSTRESS ET); v1 (Prithvi labels, 2020+) superseded | v1 labels were noisy (OA ~0.6), which biases effects toward 0; v2 doubles the history and adds ET |
| 2026-11-14 | 1 | Effect outcomes for options use the late summer window (Jul 11+) rather than whole-window NDVI-days; ECOSTRESS ET is labelled rotation-season water use | The early window carries precrop greenness (+5–15% NDVI), which inflated v2 NDVI-days; the season-mean ET cannot be split |
