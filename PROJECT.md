# Precrop Payoff Atlas

**NASA Space Apps Cairo 2026 · Challenge: *Field Shift: Adapting Farms with NASA Data* · Team: Project: Hail Mary**

> Thousands of Nile Delta farmers have already run the crop-rotation experiment. NASA satellites recorded the results. We measure them, with honest error bars, and show each farmer the blocks most like theirs that already switched. Then we lay out the current rotation plus three alternatives, each with its evidence, water cost, information gaps and risks.

Status legend used below: **[built]** implemented and run on Kaggle · **[planned]** designed, not yet built.
Last updated: 2026-11-13.

---

## 1. The problem

Delta farmers choose a winter crop (wheat, berseem clover, sugar beet, faba bean, flax) and a summer crop (rice, maize, cotton) every year. That choice is made under:
- **Water scarcity.** Irrigation water arrives by canal on rotating turns, and tail-end farms get less.
- **Salinity.** Seawater intrusion and secondary salinization affect much of the northern Delta.
- **Policy.** Rice is restricted to designated governorates (Decree 26/2025: 724,200 feddans).
- **Little local evidence.** Rotation advice is generic ("legumes are good"). Field trials exist (berseem is repeatedly the best precrop for rice and wheat in Egyptian trials), but only at a few research stations.

The challenge brief asks for a decision-support tool that combines NASA Earth observations with local soil, crop and farmer information. For **at least three rotations, including the current one**, it must explain why each is suggested, its evidence, benefits, information gaps and the risks that need local review, and how the tool handles uncertainty.

## 2. What the system does

1. **Rebuilds each 90 m block's crop history** (which winter and summer crop it grew each season) from NASA satellite imagery.
2. **Measures what the preceding crop did** to the next crop's vigor and water use. It compares blocks that grew clover (or sugar beet) before rice with similar blocks that grew wheat, using causal-inference methods with a robustness suite.
3. **Finds analogs**: for any block, the most similar blocks (same site, rice zone, salinity class, similar history) that *already switched* rotation, and what happened to them.
4. **Applies physics and rules**: FAO-56 crop water demand, salinity tolerance thresholds, rice-zone legality, a canal water ceiling.
5. **Generates options**: the status quo plus three archetypes (*water-saver*, *soil-builder*, *balanced income*), each filled with the brief's five fields from computed numbers.
6. **Explains in Egyptian Arabic or English** through an agent that can only state numbers the tools computed.
7. **Shows its working**: a "How we know" page with map accuracy, every robustness check and known limits.

What it deliberately does **not** claim: soil health (not measurable from orbit at this scale), yield gains, per-field precision (30 m pixels are coarser than many plots), or salinity forecasts.

## 3. Architecture

```
                    ┌──────────────────────── Lane 1: Data & models (Kaggle) ────────────────────────┐
 FAO WaPOR-3 crop   │  [A] labels → 90 m blocks (majority, purity, cropland share)                   │
 maps 2023–24 ─────►│  [A'] Prithvi-EO-2.0 crop-season maps 2016–2025  [planned]                     │
 NASA HLS v2 ──────►│  [B] per-block-season outcomes: peak NDVI/GCVI, NDVI-days, clear obs           │
 NASADEM, OSM,      │      covariates: elevation, canal/drain/coast distance, salinity proxy, ET₀    │
 Natural Earth,     │  [D] embeddings + analog kNN  [planned]                                        │
 NASA POWER ───────►│  → blocks / crop_seq / block_season / analogs .parquet + MANIFEST              │
 (ECOSTRESS, SMAP,  └───────────────────────────────┬────────────────────────────────────────────────┘
  IMERG [planned])                                  │ artefacts (versioned release)
                    ┌───────────────────────────────▼──────── Lane 2: Science engine ─────────────────┐
                    │  [C] causal estimates (naive, OLS [built]; DML, causal forest [planned])        │
                    │      robustness: placebo [built]; permutation, overlap, sensitivity,           │
                    │      misclassification propagation, direction check [planned]                  │
                    │  [E] FAO-56 water, salinity / rice-zone / canal constraints  [planned]          │
                    │  [F] option generator → status quo + 3 archetypes  [planned]                    │
                    └───────────────────────────────┬────────────────────────────────────────────────┘
                                                    │ effects / cate / water .parquet, options JSON
                    ┌───────────────────────────────▼──────── Lane 3: Product & story ────────────────┐
                    │  [G] read-only API + tool-only Egyptian-Arabic agent (numeric grounding guard) │
                    │  [H] web app: map, crop timeline, analog lines, farmer cards, "How we know"    │
                    │  deck (7 slides) / 30-s video / submission texts  [all planned]                │
                    └────────────────────────────────────────────────────────────────────────────────┘
```

Heavy computation (A, B, D, and the C estimates) runs offline on Kaggle and is exported as static artefacts. The live app only reads artefacts and runs E–G, so it loads instantly and anyone can reproduce it.

Work is split across three agents with a shared data contract (`docs/agents/00-shared-contract.md`). Each lane codes against the schemas, not against another lane's code.

## 4. Study area and units

| Item | Value |
|---|---|
| Sites | **SGZ** Sidi Ghazi, Kafr El-Sheikh (northern Delta, rice zone). **ZAN** Zankalon, Sharqia (eastern Delta). **MLL** Mallawi, Minya (Upper Egypt; out-of-region test only). Chosen because FAO ground-truth crop maps exist only there. |
| Block | 90 m × 90 m (3×3 HLS pixels ≈ 0.81 ha ≈ 1.9 feddan), EPSG:32636 (UTM 36N), origin snapped to 90 m |
| `block_id` | `{site}_{row}_{col}` |
| Seasons | `S2023` 2023-05-16 → 10-31 · `W2024` 2023-11-01 → 2024-05-15 · `S2024` 2024-05-16 → 10-31 (target range W2016…S2025) |
| Crop classes | wheat, clover, sugarbeet, beans, flax, rice, maize, cotton, veg, orchard, other, nonag |
| SGZ grid | 411 × 233 = 95,763 blocks; 30 m working grid 1,233 × 699 |

## 5. Data sources

| Layer | Product | Native res. | Use | Access | Status |
|---|---|---|---|---|---|
| Crop labels | FAO WaPOR-3 L3 crop type, EGY-SGZ/ZAN/MLL, GS1 (winter) & GS2 (summer) 2023–24 | 10 m | treatment labels, training labels | public GCS bucket `fao-gismgr-wapor-3-data`, CC BY 4.0 | [built] |
| Optical | NASA HLS v2 L30 + S30 | 30 m, 2–3 day | vigor outcomes, crop mapping, salinity proxy | Microsoft Planetary Computer `hls2-l30`, `hls2-s30` (anonymous signed URLs) | [built] |
| Foundation model | NASA/IBM Prithvi-EO-2.0-300M-TL | — | crop-season segmentation, embeddings | Hugging Face `ibm-nasa-geospatial` | [planned] |
| Elevation | NASADEM (NASA SRTM reprocessing) | 30 m | covariate | Planetary Computer `nasadem` | [built] |
| Waterways | OpenStreetMap via Geofabrik Egypt extract (`gis_osm_waterways_free_1`) | vector | distance to canal (canal/river/stream) and drain | download.geofabrik.de, ODbL | [built] (sparse: 69 canal, 4 drain lines at SGZ) |
| Coastline | Natural Earth 10 m coastline | vector | distance to coast | naciscdn.org, public domain | [built] |
| Weather | NASA POWER daily, community AG (T2M_MAX/MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN) | ~0.5° | FAO-56 Penman–Monteith ET₀, heat days | REST, no auth | [built] |
| Thermal / ET | ECOSTRESS Collection 2 (LST, JET ET, ESI) | 70 m | water-use outcome, stress | AppEEARS, needs Earthdata token | [planned] |
| Soil moisture | SMAP L3/L4 | 9 km | regional context only | NSIDC, Earthdata | [planned] |
| Rainfall | GPM IMERG | 0.1° | regional context (near zero in the Delta) | GES DISC, Earthdata | [planned] |
| Groundwater | GRACE-FO mascons | ~300 km | Delta-wide narrative only | PO.DAAC | [planned] |
| Cross-check | TESSERA (or AlphaEarth) embeddings | 10 m | independent crop-map check | open / Earth Engine | [planned] |
| Policy | Decree 26/2025 rice governorates | governorate | rice legality constraint | official text | [built as constant] |

Data scale honesty: HLS, ECOSTRESS and NASADEM are block-scale. SMAP, IMERG, POWER and GRACE-FO are regional and are never presented as block values.

## 6. Pipeline in detail

### Stage A — labels to blocks **[built]** (`pipeline/m1_sgz.py`)
1. Download the FAO GeoTIFFs for the site (EPSG:4326, ~10 m).
2. Reproject to a 10 m UTM grid aligned with the 90 m block grid (nearest neighbour).
3. For each block (9×9 = 81 sub-pixels), count pixels per class using the season's legend:
   - GS1 winter: 1 wheat, 2 sugar beet, 3 flax, 4 clover, 6 beans, 7 veg, 8 orchard, 9 other, 12–14 non-ag.
   - GS2 summer: 1 rice, 2 maize, 3 cotton, 7 veg, 8 orchard, 11 other, 12–15 non-ag.
4. Per block it outputs:
   - `crop` = the majority class;
   - `purity` = majority share among the valid sub-pixels;
   - `cropland_frac` = field-crop share of the 81 sub-pixels.
5. Filters:
   - a block is kept if `cropland_frac(W2024) ≥ 0.6`;
   - a block-season label is kept if `purity ≥ 0.6`.

**Planned (A′):** fine-tune Prithvi-EO-2.0 on HLS composites with the FAO 2023–24 labels, then predict W2016…S2025.
- Train on SGZ W2024+S2024 and ZAN W2024; validate on ZAN S2024.
- Test on the held-out SGZ S2023 and on MLL.
- Cross-check against TESSERA embeddings with a light classifier.

### Stage B — outcomes and covariates **[built]**
**HLS ingest.**
1. Query the Planetary Computer STAC for `hls2-s30` and `hls2-l30` over the site bbox and season, keeping scenes with `eo:cloud_cover < 75`.
2. Group items by acquisition date, so overlapping tiles and sensors on the same day merge into one look.
3. Process dates in parallel (12 threads). Each band is warped from its MGRS tile onto the 30 m UTM grid with `WarpedVRT`. Only the needed byte ranges of the cloud-optimized GeoTIFFs are read.
4. Bands: blue B02, green B03, red B04, NIR (B8A for S30, B05 for L30), and Fmask. Reflectance = DN × 1e-4.
5. A pixel is clear when Fmask bits 0–4 (cirrus, cloud, adjacent, shadow, snow) are all 0, Fmask ≠ 255, and all bands are valid and positive.

**Per-pixel season statistics:**
- `peak_ndvi` = maximum clear NDVI;
- `peak_gcvi` = maximum clear GCVI (NIR/green − 1);
- `ndvi_auc` = mean clear NDVI × season length in days ("NDVI-days");
- `n_clear_obs` = number of clear dates.

These are then averaged to 90 m blocks (3×3).

**Salinity proxy (v1):** mean √(blue·red) over clear bare-soil looks (NDVI < 0.25) in S2023, i.e. before the W2024 precrop, so it can't be affected by the treatment. Split into terciles (`low`/`med`/`high`). It's a weak proxy, logged as such.

**Covariates:**
- `elev_m` from NASADEM, averaged to 90 m.
- `dist_canal_m` and `dist_drain_m` from OSM lines, densified every 30 m, with a KD-tree nearest distance from each block centroid.
- `dist_coast_km` from Natural Earth.
- `governorate` and `rice_zone` are constants per site.

**Weather:**
- NASA POWER daily at the site centroid feeds FAO-56 Penman–Monteith ET₀:
  - saturation vapour pressure from Tmax/Tmin;
  - actual vapour pressure from RH;
  - net radiation from POWER shortwave (MJ m⁻² d⁻¹, units read from the API response) with FAO-56 Ra/Rso/Rnl;
  - u₂ = WS2M.
- Season sums give `et0_mm`; `heat_days_gt35` counts days with Tmax > 35 °C. Both are site-constant (regional) values.

**Planned:**
- ECOSTRESS seasonal ET, LST and ESI per block (`et_season_mm`, `lst_mean_c`, `esi_mean`);
- SMAP and IMERG regional means;
- all seasons from 2016.

### Stage C — causal estimates **[pilot built]**
- **Question:** the effect of the winter precrop (clover, sugar beet or beans, each vs wheat) on the following summer crop's (rice, maize, cotton) `peak_ndvi` and `ndvi_auc`.
- **Analysis set:** blocks labelled in all three seasons with `n_clear_obs(S2024) ≥ 5`. Each arm needs at least 200 blocks.
- **Methods:**
  - **naive:** difference in means;
  - **OLS:** adjusted for elevation, canal/drain/coast distance, salinity proxy (plus missing flag), the previous summer's peak NDVI and the previous summer's crop.
  - Covariates that are empty or constant are dropped automatically and the drop is recorded in QA.
- **Inference:** cluster-robust standard errors by 900 m super-block (10×10 blocks), with 95% CIs.
- **Placebo [built]:** regress the *previous* summer's peak NDVI on the W2024 precrop. A non-zero result means farmers choose the precrop on already-better land (selection).
- **Planned:**
  - DML (`econml` LinearDML / CausalForestDML) and causal forests with blocked cross-fitting;
  - effect heterogeneity (CATE) by salinity class and canal-distance tercile;
  - permutation test (200 draws within strata);
  - overlap diagnostics with propensity trimming to [0.05, 0.95];
  - omitted-variable sensitivity (unobserved fertilizer);
  - misclassification propagation using the crop-map confusion matrices;
  - a direction check against Egyptian field trials.

### Stage D — analogs **[planned]**
- Frozen Prithvi encoder embedding per block-season plus static covariates.
- Cosine kNN (k = 10) within the same site × rice zone × salinity class.
- Keep only neighbours whose precrop differs from the query block's, and report their before/after vigor and water-use deltas.
- Optional one-season GRU forecaster, kept only if it beats persistence and crop-climatology baselines out-of-location.

### Stage E — physics and constraints **[planned]**
- **Water:**
  - FAO-56 dual Kc (Kcb + Ke) with Kc_mid/Kc_end adjusted by FAO-56 Eq. 62 for local RH_min and u₂;
  - ETc → m³/feddan per season;
  - calibrated against ECOSTRESS ET where available.
- **Salinity:** Maas–Hoffman ECe thresholds (rice 3.0, wheat 6.0, sugar beet 7.0, cotton 7.7, barley 8.0 dS/m) mapped onto the salinity risk class → `ok/warn/block`.
- **Rice legality** from `rice_zone`.
- **Canal ceiling:** user input with a documented default.
- **Nitrogen credit:** shown only as literature ranges.

### Stage F — options **[planned]**
- Enumerate 2-year sequences: winter {wheat, clover, sugar beet, beans} × summer {rice, maize, cotton}.
- Drop blocked options.
- Score on water use, measured precrop effects (CATE, falling back to the site ATE) and optional user-priced income.
- Compute the Pareto set and return the status quo + `water_saver`, `soil_builder` and `balanced`.
- Each option carries `why`, `evidence` (effect ± CI, n), `benefits`, `gaps`, `risks` and `constraint_flags`, and every number traces to an artefact row.

### Stage G — explainer agent **[planned]**
- Uses tool calling only over the read-only API (history, analogs, effects, water, constraints, options).
- Answers in Egyptian Arabic by default, or English.
- **Numeric grounding guard:** every numeral in the reply (Arabic-Indic or Western digits) must appear in that turn's tool outputs, or the reply is regenerated.
- Every sentence carries a source chip. A "Challenge this" button re-queries an alternative stratum or method.

### Stage H — web app **[planned]**
- MapLibre map of blocks: click a block to see its crop timeline, with analog lines lighting up its "switcher" neighbours.
- Arabic-first farmer cards (RTL).
- "How we know" page: confusion matrices, Prithvi vs TESSERA agreement, effects and robustness, FAO-56 vs ECOSTRESS, a data-scale table and limits.
- Deployed publicly, no login.

## 7. Artefacts (schema v1)
Full definitions: `docs/agents/00-shared-contract.md`; machine-checked by `pipeline/schemas.py` / `pipeline/validate.py`.

| File | Grain | Key columns |
|---|---|---|
| `blocks.parquet` | block | block_id, site, row, col, lon, lat, geometry_wkt, cropland_frac, governorate, rice_zone, dist_coast_km, dist_canal_m, dist_drain_m, elev_m |
| `crop_seq.parquet` | block × season | crop, prob, source (`fao`/`prithvi`/`tessera`), purity |
| `block_season.parquet` | block × season | crop, peak_ndvi, peak_gcvi, ndvi_auc, n_clear_obs, et_season_mm, lst_mean_c, esi_mean, et0_mm, heat_days_gt35, smap_sm_mean, imerg_mm, salinity_index, salinity_class |
| `effects.parquet` | effect | effect_id, precrop_treat/ctrl, next_crop, outcome, method, estimate, ci_low, ci_high, n_treat, n_ctrl, stratum |
| `robustness_pilot.json` | effect | placebo result; pending checks listed |
| `qa.json` | run | attrition, HLS scene counts, OSM line counts, POWER summary, peak NDVI by crop, timings, notes |
| `MANIFEST.json` | file | sha256, rows, schema_version, producer, date |

## 8. Compute

| Notebook | Work | Hardware | Measured / estimated |
|---|---|---|---|
| `fieldshift-lane1-m1-sgz` | labels + 3 seasons HLS + covariates + pilot | Kaggle CPU | **measured 170 s** (v4: 88–91 dates per season; HLS 20–66 s per season) |
| ingest 2016–2025, 2 sites | HLS composites | CPU | est. < 1–2 h |
| Prithvi fine-tune + inference | segmentation | T4, AMP | est. 1–3 h + minutes |
| causal suite | DML/forests + robustness | CPU | est. < 1 h |
| analogs (+ GRU) | embeddings, kNN | T4 | est. < 1 h |

Every notebook stays within the 8 h Kaggle cap. Data transfer, not GPU time, is the bottleneck.

## 9. Results so far (SGZ pilot, one season pair, run v4, 2026-11-13)
Artefacts are in `artefacts/v1/` and pass schema validation. The full run took 170 s on Kaggle CPU.

**Coverage**
- Grid: 95,763 blocks.
  - 34,682 pass the cropland filter.
  - 9,845 are labelled in all three seasons with ≥ 5 clear looks.
- **Below the M1 target of 20,000.** The W2024 purity ≥ 0.6 filter is the bottleneck: only 15,485 blocks pass it.
- Every S2024 block-season has ≥ 5 clear observations.
- OSM has only 69 canal/river lines and 4 drains here. Small mesqas are largely unmapped, so canal distance is coarse.

**Plausibility.** Median peak NDVI:
- Rice: 0.85–0.86.
- Cotton: 0.82.
- Winter crops: 0.89–0.90.
- Non-ag: 0.66–0.76.

**Seasonal ET₀** (POWER, FAO-56 PM): about 1,180–1,200 mm per summer and 700 mm per winter, which is plausible for the northern Delta.

**Effects (OLS with elevation, canal/drain/coast distance, salinity proxy, previous-summer NDVI and crop; 95% CI clustered on 900 m super-blocks)**

| Comparison | Peak NDVI | NDVI-days (rice mean 93.1) | Placebo: precrop "explains" the previous summer |
|---|---|---|---|
| clover vs wheat → rice (760 vs 4,554 blocks) | −0.002 (−0.005, 0.000) | +1.4 (0.7, 2.2) | **fails**: +0.009 (0.005, 0.013) |
| sugar beet vs wheat → rice (2,771 vs 4,554) | +0.004 (0.001, 0.007) | +1.5 (0.7, 2.4) | **fails**: +0.008 (0.004, 0.012) |
| sugar beet vs wheat → cotton (396 vs 404) | −0.002 (−0.007, 0.004) | −0.0 (−1.0, 0.9) | **fails**: +0.014 (0.006, 0.021) |

**Reading**
- Blocks that get clover or sugar beet were already about 0.01 NDVI greener the summer before. Farmers pick precrops on better land.
- The +1.4 to +1.5 NDVI-day gains (about 1.5%) are the same size as this selection, so they **cannot yet be read as a precrop effect**.
- Peak vigor shows essentially no effect.

**What M2 must do**
- Get a ten-year crop history so each block serves as its own control (block fixed effects / DiD on switchers).
- Run the full robustness suite and use planting-date proxies to separate earlier transplanting from real vigor.
- If the effect stays inside the selection band, the product leads with the evidence map and states "no measurable precrop payoff at 90 m" honestly. That is the pivot in `docs/gates.md`.

**Known data issues**
- POWER's 2 m Tmax reads 39–42 °C in early July, which looks hot-biased, so `heat_days_gt35` is regional context only.
- v1–v3 ET₀ was 3.6× too high (a units bug). Fixed in v4.

### 9b. M2 run v1 (2026-11-14, Kaggle T4, 6,135 s; HLS 2020–2025 from Planetary Computer)

**Crop maps** (pixel OA on FAO WaPOR labels; targets OA ≥ 0.80, per-crop F1 ≥ 0.70, agreement ≥ 0.75)

| Split | Prithvi (fine-tuned) | LightGBM |
|---|---|---|
| SGZ S2023 (held-out year) | 0.64 | **0.82** (rice F1 0.89, cotton 0.70, maize 0.39) |
| ZAN W2024 (held-out rows) | 0.58 | **0.81** (wheat 0.87, clover 0.77, sugar beet 0.27) |
| ZAN S2024 (held-out site-season) | 0.58 | 0.75 (rice 0.92, maize 0.61, cotton 0.18) |
| MLL W2024 (out of region) | 0.55 | 0.70 (wheat 0.79, clover 0.80) |
| MLL summers (out of region) | 0.23 | 0.37 |

- Prithvi is undertrained: it reaches only 0.48 OA on its own SGZ W2024 training data (1,800 steps, 4 of 7 winter frames, frozen first 16 blocks). LightGBM on all 28-day steps passes the OA target in the Delta. **LightGBM is therefore the label source from v2 on.** Prithvi stays as the source of the 64-d block embeddings used by the analog search.
- Prithvi/LightGBM agreement is 0.45–0.65, below the 0.75 target, because Prithvi is the weak model.
- Minor classes (veg, orchard, beans, flax) stay below F1 0.70. Rice, wheat, clover and sugar beet (the classes the effects use) are the ones near or above it.
- Rice area on FAO-labelled pixels: Prithvi +21% (SGZ S2023), +28% (ZAN S2024). The v1 `rice_area.csv` compared whole-grid predictions with FAO's labelled subset, so it was not like-for-like. Fixed in v2.
- MLL summers fail out of region: Upper Egypt has no rice and a different maize/sugarcane calendar. The maps are not used there.

**Switcher fixed effects** (block FE + year FE, only blocks that switch between precrop and wheat; 95% CI clustered on 900 m super-blocks; Prithvi labels, so estimates are attenuated toward 0)

| Effect | Peak NDVI | NDVI-days | Lead placebo |
|---|---|---|---|
| SGZ clover vs wheat → rice (2,658 blocks) | −0.003 (−0.006, −0.001) | +0.35 (−0.38, 1.08) | pass |
| ZAN clover vs wheat → rice (19,079 blocks) | −0.003 (−0.004, −0.001) | +0.21 (−0.03, 0.45) | pass |
| SGZ sugar beet vs wheat → rice (6,776) | +0.001 (−0.001, 0.003) | +0.19 (−0.21, 0.59) | pass |
| ZAN clover vs wheat → cotton (1,063) | −0.006 (−0.010, −0.002) | −0.48 (−1.13, 0.16) | pass |
| others (SGZ maize/cotton, ZAN maize) | ≈ 0, CI spans 0 | ≈ 0, CI spans 0 | pass |

**Reading**
- Once each block is compared with itself, the M1 "+1.5 NDVI-days" vanishes. It was land-quality selection, as the M1 placebo warned.
- All lead placebos pass, so the within-block design removes the selection.
- What remains is a small *negative* peak-NDVI signal after clover (about −0.3% of rice peak). This fits a known mechanism: multi-cut berseem delays summer transplanting. It is a hypothesis, not yet shown.
- No positive precrop payoff is measurable at 90 m from vigor proxies. ET (ECOSTRESS) outcomes are added in v2.

### 9c. M2 run v2 (2026-11-14, 6,744 s; LightGBM labels, HLS 2016–2025 from Planetary Computer and LP DAAC, ECOSTRESS)

- **Crop maps (LightGBM):**
  - OA: SGZ S2023 0.82, ZAN W2024 0.78, ZAN S2024 0.74, MLL W2024 0.66.
  - Rice area on FAO-labelled pixels: +10% (SGZ S2023), −13% (SGZ S2024), −2% (ZAN S2024). All are within ±25%.
- **Switcher FE** (block + year FE; 95% CI clustered on 900 m super-blocks; ✓ means the lead placebo passes):

| Effect | Peak NDVI | NDVI-days | Season ET (mm, ECOSTRESS) | LST (°C) |
|---|---|---|---|---|
| ZAN clover vs wheat → rice (17,371 blocks) | −0.004 (−0.005, −0.003) ✓ | **+2.5 (2.3, 2.7) ✓** | **+11.9 (10.8, 13.1) ✓** | +0.02 ✓ |
| SGZ clover vs wheat → rice (6,772) | −0.003 placebo ✗ | +0.3 (−0.1, 0.7) placebo ✗ | **+10.1 (5.8, 14.3) ✓** | 0.00 ✓ |
| SGZ sugar beet vs wheat → rice (9,236) | +0.003 (0.002, 0.004) ✓ | **+1.2 (0.9, 1.4) ✓** | +2.7 (−0.6, 6.1) ✓ | −0.03 ✓ |
| ZAN sugar beet vs wheat → rice (868) | +0.009, placebo ✗ | +3.6 (2.7, 4.6) ✓ | +5.0 (−3.6, 13.7) ✓ | −0.06 ✓ |
| ZAN clover vs wheat → cotton (375) | −0.006 ✓ | +2.3 (1.5, 3.2) ✓ | +14.0 (7.5, 20.5) ✓ | −0.07 ✓ |
| clover vs wheat → maize (SGZ 524, ZAN 3,697) | −0.012 / −0.013, placebo ✗ | mixed, placebo ✗ | ≈ 0 / +5.0 ✓ | ≈ 0 ✓ |

- **Reading:**
  - With better labels and 2016+ history, a legume or sugar-beet precrop shows a consistent payoff in season length, not in peak vigor. Rice after clover stays green longer (+2.5 NDVI-days in ZAN, about 2.7%) and transpires 10–12 mm more water over the season in both Delta sites. Both results pass their placebos.
  - The peak-NDVI dip after clover stays small.
  - Effects whose placebo fails are excluded from the options: SGZ clover NDVI outcomes, all maize vigor outcomes, ZAN sugar beet peak.

### 9d. Follow-ups on v2 (2026-11-14, `pipeline/m2_hetero.py`, kernel `fieldshift-lane1-m2-hetero` v2, 118 s CPU)

**Timing test: is the NDVI-days gain the rice, or the precrop?**
- The summer window is split into an early part (steps 0–1, May 16 – Jul 10: precrop tail plus transplanting) and a late part (steps 2+, Jul 11 on: the rice crop itself).

| Precrop vs wheat → rice | Early mean NDVI | Late NDVI-days | Whole-window NDVI-days |
|---|---|---|---|
| ZAN clover (17,371 blocks) | **+0.047 (+12%)** | −0.30 (−0.4%), placebo ✗ | +2.5 ✓ |
| SGZ clover (6,772) | +0.027 (+5%) ✓ | −1.24 (−1.9%), placebo ✗ | +0.3 ✗ |
| SGZ sugar beet (9,236) | +0.033 (+7%) | −0.77 (−1.2%), placebo ✗ | +1.2 ✓ |
| ZAN sugar beet (868) | +0.061 (+15%) ✓ | −0.02 (≈ 0) | +3.6 ✓ |
| ZAN clover → cotton (375) | +0.033 ✓ | −0.06 (≈ 0) ✓ | +2.3 ✓ |

- **The whole-window "payoff" sits entirely in May–early July.** That is leftover precrop greenness (berseem regrowth, late sugar-beet harvest) spilling into the summer window, not better rice. Over the rice season itself, the effect is ≈ 0 or slightly negative.
- The phenology fits this: in ZAN, green-up after clover comes 3.6 days later and the season is 4.5 days shorter (both placebos ✗). Senescence comes 0.9 days earlier (placebo ✓).
- The ECOSTRESS +10–12 mm season ET cannot be split by timing with the stored season means, so it may also be precrop transpiration in May–June. It is reported as "rotation-season water use", not rice water use.

**Water productivity** (NDVI-days per 100 mm ET): ZAN clover → rice +0.3% (CI spans 0, ✓). Extra greenness and extra water scale together, with no efficiency gain.

**Heterogeneity:**
- On whole-window NDVI-days, SGZ sugar beet pays 2.6× more on southern and higher blocks (placebos ✓).
- On the late window this vanishes or reverses (south −1.7, high elevation −1.6). It was the timing artefact, not a land-quality interaction.
- ET effects are uniform across subgroups (+11–13 mm everywhere in ZAN).

**Conclusion for G3:** after removing both traps (farmers' land selection, precrop spill-over into the summer window), **no rice-season payoff from a clover or sugar-beet precrop is detectable at 90 m. The upper bound is about +1% and the point estimates are slightly negative.** The product's honest claim is the evidence map, plus a method that catches two traps a naive satellite analysis falls into.

## 10. Validation plan
1. **Crop maps:** held-out labels per season and site, confusion matrices, a rice-area sanity check, Prithvi vs TESSERA agreement (targets: OA ≥ 0.80, per-crop F1 ≥ 0.70, agreement ≥ 0.75).
2. **Effects:** held-out years, spatially blocked cross-validation, placebo, permutation, overlap, sensitivity, misclassification propagation, direction check vs Egyptian trials. An effect that fails its placebo is marked unreliable and excluded from options.
3. **Water:** FAO-56 vs ECOSTRESS bias and RMSE per crop.
4. **Forecaster:** must beat persistence and climatology out-of-location, or it's dropped.
5. **Agent:** 40 scripted questions (20 Arabic, 20 English, 10 adversarial), 100% numeric grounding.

## 11. Limits (stated up front)
- **Blocks are 90 m.** Results describe blocks, not individual farms.
- **Labels exist only for 2023–24 at three sites.** Earlier years depend on the crop model.
- **Fertilizer, planting dates, varieties and irrigation turns are not observed.** The estimates are observational, which is why the robustness suite exists.
- **Salinity is a weak optical proxy, not measured ECe.**
- **Regional layers stay regional.** SMAP, IMERG, POWER and GRACE-FO are never shown as block values.

## 12. Repository layout
```
PROJECT.md                 this file
docs/design.md             full design
docs/concept-feasibility-report.md, docs/research_notes/   research behind the concept
docs/gates.md              data-access checks (HLS, FAO labels, treatment support)
docs/decisions.md          decisions log
docs/agents/               shared contract + three lane briefs
docs/official/             Cairo judging criteria, hackathon guide, guidebook (PDFs)
pipeline/schemas.py        artefact schemas + validator
pipeline/validate.py       CLI: python pipeline/validate.py <artefact dir>
pipeline/m1_sgz.py         Lane 1 M1 pipeline (SGZ)
kaggle/                    Kaggle kernel folders (gate1, gate2, m1) + downloaded outputs
data/fao_probe/            FAO crop maps downloaded during the gate check
```

## 13. How to run (Lane 1 M1)
```bash
cat pipeline/schemas.py pipeline/m1_sgz.py > kaggle/m1/m1_sgz.py     # single-file kernel
KAGGLE_API_TOKEN="$(cat ~/.kaggle/access_token)" kaggle kernels push -p kaggle/m1
kaggle kernels status manuelgamal/fieldshift-lane1-m1-sgz
kaggle kernels output manuelgamal/fieldshift-lane1-m1-sgz -p kaggle/m1/out
python pipeline/validate.py kaggle/m1/out/artefacts
```

## 14. Credits and licences
- **NASA:** HLS, NASADEM, POWER, ECOSTRESS, SMAP, GPM, GRACE-FO, and Prithvi-EO-2.0 (NASA/IBM).
- **Crop maps:** FAO WaPOR-3 Egypt crop type maps (CC BY 4.0).
- **Waterways:** OpenStreetMap contributors (ODbL), via Geofabrik.
- **Coastline:** Natural Earth (public domain).
- **Imagery access:** Microsoft Planetary Computer.
- **Code:** MIT. AI assistance is used in development and will be disclosed in the submission.
