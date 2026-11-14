# Lane 1 — Data & models (owner: Claude, Manuel's agent)

Read `00-shared-contract.md` first. You own everything that touches satellites and GPUs. You run on Kaggle (account `manuelgamal`, token in `~/.kaggle/access_token`, CLI 1.7.4.5; use `KAGGLE_API_TOKEN`). Each notebook ≤ 8 h, internet on, private.

## Inputs (verified in `docs/gates.md`)
- HLS v2 from Microsoft Planetary Computer (`hls2-s30`, `hls2-l30`), anonymous signed access.
- FAO WaPOR-3 crop maps (CC BY 4.0) for SGZ/ZAN/MLL 2023–24, public GCS bucket.
- ECOSTRESS (AppEEARS; needs Earthdata token as Kaggle Secret — ask Manuel to add it; until then ship ET columns as null), NASA POWER (REST, no auth), SMAP L3/L4, GPM IMERG, SRTM, OSM waterways, Decree 26/2025 rice governorates, Fields of The World 2024/25 (optional QA).
- Prithvi-EO-2.0 (Hugging Face `ibm-nasa-geospatial`), TerraTorch.

## Tasks, in order

### M1 — fixtures + pilot (do first; unblocks both other lanes)
1. Build the 90 m block grid for SGZ; compute `blocks.parquet` (covariates: SRTM elevation, distance to coast/canal/drain from OSM, governorate, rice_zone).
2. `crop_seq.parquet` for S2023, W2024, S2024 from FAO maps: majority class per block, `purity` = share of 10 m pixels agreeing; keep blocks with cropland_frac ≥ 0.6 and purity ≥ 0.6.
3. `block_season.parquet` for S2024 (and W2024): HLS peak NDVI/GCVI, NDVI AUC, n_clear_obs (Fmask), POWER ET₀ (Penman–Monteith) and heat days, SMAP/IMERG regional means, salinity_index (document the formula), salinity_class terciles.
4. Pilot effect: naive and covariate-adjusted (OLS with site-local fixed effects) difference in S2024 peak NDVI for clover→rice vs wheat→rice, and sugarbeet→rice vs wheat→rice. Write to `effects.parquet` (`method=naive|ols`) with clustered CIs (cluster = 900 m super-block).
5. Release `artefacts-v1` (fixtures) + MANIFEST; notify the other lanes.

**M1 acceptance**
- [ ] All files validate against schema v1 (`pipeline/validate.py`, run in CI).
- [ ] ≥ 20,000 SGZ blocks with all three seasons labelled; reported share dropped by each filter.
- [ ] Peak-NDVI distribution by crop is plausible (rice/maize summer peaks > cotton early; documented plot) and n_clear_obs ≥ 5 for ≥ 90% of block-seasons.
- [ ] Pilot effect table with CIs and sample sizes, plus one paragraph on what it means and doesn't mean.
- [ ] Notebook reruns end-to-end from a clean Kaggle session in < 2 h.

### M2 — full history + analogs
6. HLS ingest 2016–2025 for SGZ + ZAN (+ MLL W2024/S2024 only): windowed COG reads, 8–16 threads, scenes with < 60% cloud in the clip, composites at fixed phenology steps (6–8 per season). Cache as a Kaggle Dataset (`fieldshift-hls-clips`).
7. Fine-tune Prithvi-EO-2.0-300M-TL (fallback 100M/tiny) for per-season crop segmentation on FAO 2023–24 labels. Split: train SGZ W2024+S2024 and ZAN W2024; validate ZAN S2024; test SGZ S2023 (held out) and MLL (out-of-region). Infer W2016…S2025.
8. Independent cross-check: TESSERA (or AlphaEarth) embeddings + logistic/LightGBM on the same labels; agreement map.
9. Extend `block_season.parquet` to all seasons; add ECOSTRESS ET/LST/ESI where the Earthdata Secret is available.
10. Analogs: frozen Prithvi encoder embedding per block-season + static covariates; cosine kNN within same site × rice_zone × salinity_class; keep analogs whose sequence differs from the query block in the precrop; write `analogs.parquet` (k = 10).
11. Release `artefacts-v2`.

**M2 acceptance**
- [ ] Held-out SGZ S2023 overall accuracy ≥ 0.80 and per-class F1 ≥ 0.70 for wheat, clover, rice, maize, cotton (report sugar beet separately). If missed: merge classes (e.g. maize+cotton) and log it in `decisions.md`.
- [ ] Yearly rice area per site within ±25% of the S2023/S2024 FAO area, and the trend through 2016–2025 is reported against the national rice caps (direction check, not a hard pass).
- [ ] Prithvi vs TESSERA agreement ≥ 0.75 on the test seasons; disagreement map published.
- [ ] Confusion matrices saved as `artefacts/qa/confusion_{site}_{season}.csv` (Lane 2 needs them for misclassification propagation).
- [ ] Every notebook ≤ 8 h on Kaggle; wall-clock logged in MANIFEST.
- [ ] Analog sanity: for 50 random blocks, analogs share site, rice_zone and salinity_class 100%, and mean |Δelevation| < 1 m.

### M3 — hardening
12. Re-run with final settings, freeze `artefacts-v3`, write `docs/data-card.md` (sources, licences, resolutions, which layers are field-scale vs regional, known failure modes).

## Don'ts
- Don't claim per-field accuracy; blocks only.
- Don't use AlphaEarth/TESSERA as the primary map (NASA relevance).
- Don't change schemas without a `decisions.md` entry and a ping to both lanes.
- Don't commit large rasters to git.
