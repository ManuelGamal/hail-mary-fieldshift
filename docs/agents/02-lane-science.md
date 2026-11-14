# Lane 2 — Science engine (owner: Friend A's agent)

Read `00-shared-contract.md` first, then `docs/design.md` §5 C, E, F and §7, and `docs/gates.md`. You own every estimate and every recommendation. You never touch satellites directly: you consume Lane 1's Parquet artefacts and ship a Python package `science/` plus `effects.parquet`, `cate.parquet`, `robustness.json`, `water.parquet`.

## Start immediately (before Lane 1's M1)
- Write a synthetic generator `science/synth.py` that produces `blocks`, `crop_seq`, `block_season` matching schema v1 with a **known planted effect** (e.g. clover→rice +0.03 peak NDVI, confounded by salinity and distance to canal). All your methods are developed and tested against it first.
- Then switch to `artefacts-v1` fixtures (SGZ, real FAO labels) as soon as Lane 1 releases them.

## Tasks

### 1. Causal engine (`science/causal.py`)
- Treatment pairs: (clover vs wheat) → rice, maize, cotton; (sugarbeet vs wheat) → rice; reverse direction summer → following wheat when Lane 1 ships more seasons.
- Outcomes: `peak_ndvi`, `ndvi_auc`, `et_season_mm` (when not null).
- Methods: naive, DML (`econml` LinearDML / CausalForestDML) and `grf`-style causal forest (econml `CausalForest` is fine). Covariates: elevation, distances to coast/canal/drain, salinity_index, heat_days, et0, previous-season outcome, site, rice_zone.
- Inference: cluster-robust CIs with 900 m super-blocks; blocked cross-fitting by super-block.
- CATE by salinity_class and by distance-to-canal tercile.

### 2. Robustness suite (`science/robustness.py`)
- Placebo: next season's crop "affecting" the previous season's outcome must be ≈ 0.
- Permutation: shuffle precrop within site × rice_zone × salinity_class strata, 200 draws.
- Overlap: propensity histogram; trim to [0.05, 0.95]; report share trimmed.
- Sensitivity: omitted-variable robustness value (Cinelli–Hazlett style, or econml sensitivity) for unobserved fertilizer.
- Misclassification propagation: resample treatment labels using Lane 1's confusion matrices, 200 draws; report the attenuated CI.
- Direction check against Egyptian trials (berseem best precrop for rice and wheat; cite the EKB papers listed in `docs/concept-feasibility-report.md`).

### 3. Water & constraints (`science/water.py`, `science/constraints.py`)
- FAO-56 dual Kc with Kc_mid/Kc_end adjusted by FAO-56 Eq. 62 for local RH_min and u₂; ET₀ from Lane 1's POWER column; seasonal ETc → m³/feddan. Cite the Kc table source per crop.
- Calibrate against ECOSTRESS `et_season_mm` where present (report bias/RMSE per crop).
- Salinity: Maas–Hoffman thresholds (rice 3.0, wheat 6.0, sugar beet 7.0, cotton 7.7, barley 8.0 dS/m) mapped to salinity_class → `ok|warn|block`; rice legality from `rice_zone`; canal ceiling = user input with a documented default.
- Nitrogen credit: literature ranges only, labelled as such, never computed per block.

### 4. Option generator (`science/options.py`)
- `for_block(block_id, prefs) -> dict` matching the `options` JSON in the shared contract.
- Enumerate 2-year sequences from winter {wheat, clover, sugarbeet, beans} × summer {rice, maize, cotton}; drop `block` constraint flags; score on water (lower better), measured precrop effects (CATE where available, else site ATE), and an optional income term from user-entered prices (flagged as assumption).
- Return status quo + 3 archetypes: `water_saver`, `soil_builder` (legume-heavy, using measured precrop effects), `balanced`. Fill `why`, `evidence`, `benefits`, `gaps`, `risks` from data, e.g. gaps = low overlap, wide CI, few analogs, null ET.
- Pure and deterministic: same inputs → same output. < 200 ms per block.

## Acceptance criteria
- [ ] On the synthetic generator, DML/forest recover the planted effect within its 95% CI in ≥ 90% of 50 seeds, and the naive estimate is visibly biased (proves confounding handling).
- [ ] On fixtures and on v2: `effects.parquet` has every pair × outcome × method with n_treat, n_ctrl and CIs; `robustness.json` has all six checks for every DML/forest effect.
- [ ] Placebo estimates' CIs include 0; permutation p-values are reported. If a placebo fails, the effect is marked `unreliable` and excluded from options (log in `decisions.md`).
- [ ] FAO-56 vs ECOSTRESS: report per-crop bias and RMSE; no tuning to hide a mismatch.
- [ ] `options.for_block` returns valid JSON for 1,000 random blocks; never offers rice outside rice_zone; every numeric field traces to an artefact row (tested).
- [ ] `pytest` coverage ≥ 80% on `science/`; type-checked; docstrings cite the method source.
- [ ] One-page `docs/science-card.md`: what is estimated, assumptions, what is not claimed, results table, robustness table.
- [ ] Null result handling: if the clover effect is null or unreliable, options still work and the science card says so plainly.

## Don'ts
- No "soil health", "yield", or "per field" language in outputs.
- No hand-tuned weights presented as attributions or percentages.
- Don't read raw rasters or call NASA APIs; ask Lane 1 for a column instead.
