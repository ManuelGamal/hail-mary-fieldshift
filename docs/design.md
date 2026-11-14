# Precrop Payoff Atlas — design (NASA Space Apps Cairo 2026, Field Shift)

Team: Project: Hail Mary · Challenge: *Field Shift: Adapting Farms with NASA Data* · Status: design, not yet approved
Research behind this: `docs/concept-feasibility-report.md` (+ notes in `docs/research_notes/`); official Cairo PDFs in `docs/official/`

---

## 1. Intent

**Pitch.** *Thousands of Nile Delta farmers have already run the rotation experiment. NASA satellites recorded the results. We measure them — with honest error bars — and show each farmer the fields most like theirs, then lay out three better rotations with the evidence, the water cost and the risks.*

**Why this angle.** The 2026 Field Shift field is crowded (40+ repos) with the same pattern: NASA POWER (+SMAP) → weighted score → chatbot. Two Egyptian teams already hold the obvious Egypt angles (BlinkFarms: FAO-56 + salinity + Egyptian-Arabic Gemini; FieldWitness: HLS history + evidence grades). Nobody measures **what rotations actually did** in the Delta. That measurement is our core: it turns Validity from everyone's weak spot into our strength, and it is AI-heavy where AI earns its place (NASA's Prithvi foundation model, causal ML, embedding retrieval, a verifiable agent).

**Success.** Local Winner → one of Cairo's 10 Global Nominees. Judges (5 equal criteria: Impact, Creativity, Validity, Relevance, Presentation) see it only through a 7-slide deck or 30-s video plus links.

## 2. Goals, non-goals, anti-goals

**Goals**
1. Reconstruct 2016–2025 winter/summer crop sequences for 1–2 Delta districts from NASA HLS with Prithvi-EO-2.0.
2. Estimate the causal effect of the preceding crop (berseem vs wheat, etc.) on next-crop vigor and water use, with confidence intervals and heterogeneity (by salinity, heat, location).
3. For any block: show matched "fields like yours that already switched" as visible evidence.
4. Generate **≥3 rotation options plus the current one**, each with the brief's five fields: *why suggested, evidence, benefits, information gaps, risks needing local review*.
5. Physically grounded water accounting (FAO-56) and hard constraints (salinity tolerance, rice-zone decree, canal water).
6. Egyptian-Arabic explanation layer that can only state numbers the tools computed.
7. A deployed, public, login-free web app + a hindcast/validation page.

**Non-goals**
- Multi-year "soil health" or soil-carbon trajectories (not measurable from orbit; Wallonia MDD result).
- Per-field salinity *forecasting* (no NASA product supports it at field scale).
- Pretraining any model; full world-model planning (MCTS over a learned simulator).
- Canal-level multi-agent negotiation (optional future slide only).
- US benchmark fields, RUSLE erosion, slope-driven logic, rainfall what-ifs (irrelevant in the flat, rain-free, irrigated Delta).

**Anti-goals (failure even if it "works")**
- Any number on screen the pipeline did not compute (LLM-invented figures, decorative "42% heat stress" attribution bars).
- Claiming per-field precision from 30 m pixels.
- Claiming yield jumps or soil-health gains.
- Recommending rice outside decree zones.
- A dense GIS control room a farmer can't read.

## 3. Constraints

| Constraint | Detail |
|---|---|
| Compute | Each pipeline ≤ 8 h Kaggle GPU (T4×2 or P100, 16 GB); disk ~73 GB; 12 h sessions |
| Brief requirements | ≥3 rotations incl. existing; why/evidence/benefits/gaps/risks per option; explain uncertainty & where local expertise is needed; supports, doesn't replace, farmers |
| NASA data | Must be central. Brief-named datasets: SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE/FO, SRTM (+GEDI in fusion section) |
| Cairo rules | No live pitch; demo = exactly 7 slides **or** 30-s video, public; all links open without login/request; leader submits; local form **and** global site; no minors' faces/voices; disclose AI use; credit sources; non-NASA materials openly licensed |
| Policy | Decree 26/2025: rice capped at 724,200 feddans in designated Delta governorates, water 15 May–31 Aug (check for a 2026 decree) |
| Scale | Delta holdings ≈ 1.6 feddan; 1 feddan ≈ 4.7 HLS pixels. Report per 30 m block / FTW polygon, never "your exact field" |

## 4. System overview

```
 HLS L30/S30 2016–25 ──► [A] Prithvi-EO-2.0 crop-season maps ──┐
 (FAO WaPOR-2, WorldCereal labels)    + TESSERA cross-check     │
                                                                ▼
 HLS, ECOSTRESS, POWER, SMAP, GPM, SRTM, GRACE-FO ──► [B] block-season table
                                                                │
                    ┌───────────────────────────┬───────────────┤
                    ▼                           ▼               ▼
        [C] causal engine            [D] analog retrieval   [D'] 1-season forecaster
   (precrop effect ± CI, CATE)     ("fields like yours")   (only if beats baselines)
                    └──────────────┬────────────┘───────────────┘
                                   ▼
            [E] physics + constraints (FAO-56 water, salinity, rice zone, canal budget)
                                   ▼
            [F] option generator → Pareto set → status quo + 3 archetypes
                                   ▼
            [G] tool-only Egyptian-Arabic agent  ──►  [H] web app (map + farmer cards + validation page)
```

All heavy work (A–D) runs offline on Kaggle and is exported as static artefacts (Parquet + COGs). The live app only reads artefacts and runs E–G, so it loads instantly for judges.

## 5. Components

### A. Crop-history reconstruction (GPU)
- **Area:** the two FAO-labelled Delta sites: **SGZ Sidi Ghazi** (Kafr El-Sheikh, north, salinity gradient, rice zone) and **ZAN Zankalon** (Sharqia, east). **MLL Mallawi** (Upper Egypt) is an out-of-region test. See `gates.md`.
- **Input:** HLS v2 L30+S30, 2016–2025, Fmask cloud masking, composited to ~6–8 time steps per season.
- **Seasons/classes:** winter (Nov–May): wheat / berseem / other; summer (May–Oct): rice / maize / cotton / other. Berseem's repeated-cut NDVI sawtooth is a strong signature.
- **Model:** Prithvi-EO-2.0-300M (temporal) fine-tuned for multitemporal segmentation via the official T4 notebook / TerraTorch; fallback Prithvi-EO-2.0-tiny/100M.
- **Labels:** FAO WaPOR-3 Egypt crop maps 2023–24 (CC BY 4.0, public bucket; see `gates.md`), ESA WorldCereal 2021 masks + reference points, ~300–500 photo-interpreted points from NDVI curves + high-res imagery.
- **Cross-check:** TESSERA (or AlphaEarth) embeddings + light classifier at 10 m; agreement map shown on the validation page. Not used as the primary map (keeps the core NASA-native).
- **Unit of analysis:** 30 m block, aggregated to FTW Global 2024/25 polygons where they look sane; otherwise fixed 90 m blocks.
- **Outputs:** `crop_seq.parquet` (block_id, season, class, probability), accuracy report per season vs held-out labels; sanity check: yearly rice area vs national/decree figures.
- **Targets to beat/compare:** published 0.77–0.80 (summer, 30 m, multi-year) and ~0.93/0.96 (single-season S2).

### B. Outcome & covariate table (CPU)
Per block-season:
- **Outcomes:** peak NDVI and GCVI (HLS) — next-crop vigor proxy; seasonal ET and LST (ECOSTRESS L2/L3/L4, ~70 m) — water use; ESI (ECOSTRESS L4) — stress.
- **Covariates:** NASA POWER daily (T2M_MAX/MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN → heat-stress days, PM ET₀); SRTM elevation; distance to coast, main canal and drain (OSM waterways); salinity proxy (HLS salinity indices + ECOSTRESS LST anomaly); governorate and rice-zone indicator; SMAP L3/L4 soil moisture and GPM IMERG as **regional context only**; GRACE-FO Delta-wide storage trend (narrative layer, never per-block).
- **Output:** `block_season.parquet` (10⁴–10⁵ rows).

### C. Causal engine — the core (CPU)
- **Question:** effect of the winter precrop (berseem vs wheat; extend to other pairs with enough support) on the following summer crop's vigor and ET, and of summer crop on the following wheat.
- **Methods:** causal forests (`grf`) and double ML (`econml` CausalForestDML / LinearDML) with the B covariates; CATE heterogeneity by salinity proxy, heat, distance-to-canal tail.
- **Design choices:** stratify by rice-zone status; propensity trimming to 0.05–0.95; blocked CV by village/canal command; spatially clustered SEs.
- **Robustness suite (all shown):** placebo (next season's crop on last season's vigor ≈ 0); within-stratum label permutation (effect vanishes); omitted-variable sensitivity bounds (fertilizer unobserved); misclassification propagation (resample treatments by Stage A confusion matrix); external direction check vs Egyptian trials (berseem best precrop at Tag El-Ezz, Assiut).
- **Output:** `effects.parquet` (pair, outcome, ATE, CI, CATE per block), `robustness.json`.
- **Null result plan:** if effects aren't detectable above map noise, publish that as a finding and pivot the headline to "the Delta's first open rotation-history and evidence-gap map".

### D. Analog retrieval ("fields like yours that already switched")
- Embeddings: frozen Prithvi encoder features per block-season (+ static covariates), cosine kNN within the same rice-zone stratum and salinity band.
- For a selected block: the k=5–10 nearest blocks whose sequence switched (e.g. wheat→berseem), with before/after vigor & ET, each linked to its own HLS time-series chart.
- **D′ (optional):** small GRU forecaster of next-season vigor/ET given crop choice + weather. Kept **only if** it beats persistence and crop-climatology baselines out-of-location; used for ranking, never as the evidence. Restricted to sequences with data support (penalise out-of-support options).

### E. Physics + constraints layer (CPU, live)
- **Water:** FAO-56 dual Kc (Kcb + Ke) with Kc_mid/Kc_end adjusted by FAO-56 Eq. 62 for local RH_min and u₂ (arid/windy Egypt); ET₀ from POWER via Penman–Monteith; calibrated against ECOSTRESS ET for the block's history. Output m³/feddan per season and per rotation.
- **Salinity:** Maas–Hoffman thresholds (ECe dS/m): rice 3.0, wheat 6.0, sugar beet 7.0, cotton 7.7, barley 8.0; germination/seedbed caveats (barley/wheat ~4–5, sugar beet ~3). Block salinity is a *risk class* (low/med/high), not an ECe value; options above threshold for the risk class are flagged, not silently dropped.
- **Rice legality:** rice options only inside decree zones (2025 decree; update if 2026 published).
- **Canal water:** user-entered or default canal turn schedule → seasonal water ceiling; options exceeding it are flagged.
- **Nitrogen credit:** literature ranges (berseem ~100–250 kg N/ha; faba bean range) shown as ranges with citations, labelled "agronomy literature, not measured here".

### F. Option generator
- Enumerate 2-year sequences (winter × summer × 2) from the crop set {wheat, berseem (full/Fahl), faba bean, sugar beet, barley} × {rice, maize, cotton, sorghum}; filter by E.
- Objectives: water use (E), measured precrop effect on next-crop vigor (C, with CI), N credit (E, literature), income (user-entered or default farm-gate prices; flagged as an assumption).
- Compute the Pareto set; present **status quo + 3 archetypes**: *Water-saver*, *Soil-builder* (legume-heavy, using measured precrop effects), *Balanced income*.
- Each option card carries the five brief fields, auto-filled from tool outputs: why (which objective/constraint), evidence (effect ± CI, n analog blocks, robustness flags), benefits, gaps (low data support, map uncertainty, unobserved fertilizer), risks for local review (salinity flag, rice legality, canal ceiling, market).
- "Smallest change that flips the top option" is computed but displayed as a sensitivity line (FieldWitness already headlines it).

### G. Verifiable Egyptian-Arabic agent
- Tool-only: `get_block_history`, `get_effects`, `get_analogs`, `get_water_budget`, `get_constraints`, `get_options`. No free-form numbers: a post-generation check rejects any numeral not present in the tool outputs of that turn.
- Every sentence ends with a source chip (dataset / estimate ID); a "challenge this" button reruns the estimate with a different stratum or drops a covariate and shows the change.
- Languages: Egyptian Arabic + English. Voice (Whisper-class ASR, ~18–38% WER on Egyptian dialect) is a **stretch** with a confirm-back step.
- LLM provider: builder's call; must support tool calling and Arabic well.

### H. Web app
- Map (MapLibre) of the study districts: crop-history timeline per block, analog lines lighting up from the selected block.
- Farmer card view (zero jargon, Arabic first) with the 4 options and their five fields.
- "How we know" page: Stage A accuracy, robustness suite results, hindcast of D′, data-scale table (which layer is field-scale vs regional), limits.
- Static artefacts + small FastAPI (or serverless) backend; deployed publicly, no login.
- Stack details are the builder's call.

## 6. Data inventory (verify IDs in AppEEARS/CMR before coding)

| Layer | Product | Res. | Role | Access |
|---|---|---|---|---|
| Optical | HLS v2 L30/S30 (HLSL30/HLSS30 .002) | 30 m | crop maps, vigor | LP DAAC / Earthdata Cloud / AppEEARS |
| Model | Prithvi-EO-2.0-300M(-TL) | — | crop segmentation, embeddings | Hugging Face `ibm-nasa-geospatial` |
| Thermal/ET | ECOSTRESS Collection 2 LST, ET, ESI (tiled names e.g. `ECO_L2T_LSTE`, `ECO_L3T_JET`, `ECO_L4T_ESI`) | 70 m | water use, stress | AppEEARS |
| Climate | NASA POWER daily, community=AG | ~0.5° | ET₀, heat days | REST, no auth |
| Soil moisture | SMAP L3 9 km / L4 | 9 km | regional context | NSIDC / AppEEARS |
| Rain | GPM IMERG | 0.1° | regional context (near-zero in Delta) | GES DISC |
| Elevation | SRTM GL1 | 30 m | elevation, distance to coast | AppEEARS |
| Groundwater | GRACE-FO mascons | ~300 km | Delta-wide trend narrative | PO.DAAC |
| Labels | FAO WaPOR-2 Egypt crop maps 2023–24; ESA WorldCereal 2021 | 10–30 m | training/validation | FAO / Earth Engine (licence TBC) |
| Boundaries | Fields of The World Global 2024/25 | 10 m | block aggregation | Source Cooperative, CC-BY |
| Cross-check | TESSERA embeddings (or AlphaEarth) | 10 m | independent map check | open / Earth Engine |
| Waterways | OpenStreetMap waterways | vector | canal/drain distance | Overpass/Geofabrik |
| Policy | Decree 26/2025 rice zones | admin | constraint | press/official text |

## 7. Validation (one slide, one page)
1. Crop maps: held-out labels per season; confusion matrix; rice-area sanity check; TESSERA agreement.
2. Effects: held-out years; blocked spatial CV; placebo; permutation; overlap diagnostics; sensitivity bounds; misclassification propagation; direction check vs Egyptian trials.
3. Water: FAO-56 vs ECOSTRESS ET on historical seasons (bias, RMSE).
4. Forecaster D′: must beat persistence and crop-climatology out-of-location, else removed.
5. Agent: 30–50 expert-checkable Q&A pairs; numeric-grounding check passes 100%.

## 8. Compute budget (Kaggle, estimates)

| Notebook | Work | GPU | Est. time |
|---|---|---|---|
| NB1 ingest | HLS district clips 2016–25 (~5–8 GB), cloud mask, composites → Kaggle dataset | none | download-bound, 1–3 h |
| NB2 Prithvi | fine-tune + infer all seasons | T4, AMP | 1–3 h + minutes |
| NB3 features | ECOSTRESS, POWER, SMAP, SRTM, OSM → block_season | none | 1–3 h I/O |
| NB4 causal | grf/econml + robustness suite | none | < 1 h |
| NB5 analogs + D′ | embeddings, kNN index, GRU | T4 | < 1 h |
Every notebook stays well under 8 h; data transfer is the real risk.

## 9. Decision gates (kill/fallback)
| Gate | Check | If it fails |
|---|---|---|
| G1 | Kaggle can authenticate to Earthdata and pull HLS at usable speed | Pre-stage via AppEEARS or Planetary Computer locally, upload as Kaggle dataset |
| G2 | WaPOR/WorldCereal labels downloadable + licence OK | Photo-interpreted points + phenology rules as weak labels |
| G3 | Stage A summer accuracy ≥ ~0.75 | Coarser classes (rice vs non-rice; berseem vs cereal), larger blocks |
| G4 | Precrop effect detectable above misclassification noise | Headline becomes the open rotation-history + evidence-gap map |
| G5 | D′ beats baselines | Drop D′; rank on C + E only |

## 10. Submission mapping
- **Demo:** 7 slides (default) — 1 Hook (the analog-map image) · 2 Problem (Delta water, salinity, rotation choices under rice caps) · 3 Idea: the Delta's natural experiments · 4 How: NASA data + Prithvi + causal engine (one diagram, scale honesty table) · 5 Results: berseem precrop effect ± CI, map accuracy, robustness · 6 The farmer card (status quo + 3 options, Arabic) · 7 Validity, limits, roadmap, AI-use disclosure. Optional 30-s video cut from the app.
- **Proposal link, project link (deployed app), GitHub repo, global team page, subjects** (Agriculture, Earth Observation, Machine Learning, Causal Inference, Water).
- **Licences/credits:** MIT/Apache code; cite every dataset; AI-use disclosure per the official wording.

## 11. Prepared answers to judges
- *Confounded choices?* Zone stratification, overlap trimming, placebo, sensitivity bounds; rice-zone boundary as a natural experiment.
- *30 m vs tiny plots?* Block-level reporting, FTW aggregation, TESSERA 10 m cross-check.
- *NASA or Google?* HLS + Prithvi carry the core; ECOSTRESS, SMAP, GPM, POWER, SRTM, GRACE-FO used for their proper scales.
- *Soil health?* Not claimed; next-crop vigor and water use only.
- *LLM hallucination?* It cannot emit a number it didn't compute.
- *Impact?* Better-evidenced decisions, not promised yield jumps; the evidence base is open for extension services and WUAs.

## 12. Calls I made (check these)
- Study sites: SGZ + ZAN (FAO-labelled); MLL as out-of-region test.
- Unit: 30 m block / FTW polygon, not "field".
- Prithvi is the primary crop map; TESSERA only a cross-check (trades a little accuracy for NASA relevance).
- Dropped RUSLE, slope, rainfall what-ifs, US benchmark, EMIT soil carbon, canal multi-agent.
- Forecaster D′ is optional and gated.
- 7-slide deck over video as the primary demo.
- Income uses user-entered/default prices, flagged as an assumption.

## 13. Left to the builder
Stack and hosting, LLM provider, exact HLS compositing, embedding dimensionality/k, Pareto solver choice, UI styling, whether to attempt voice.
