# Shared contract — read this before your lane brief

Project: **Precrop Payoff Atlas** for NASA Space Apps Cairo 2026, challenge *Field Shift: Adapting Farms with NASA Data*, team *Project: Hail Mary*.
Full design: `docs/design.md`. Gate results (data access verified): `docs/gates.md`.

**One-line idea.** Nile Delta farmers have already run the rotation experiment; NASA satellites recorded it. We measure what the preceding crop (clover/berseem vs wheat vs sugar beet) did to the next crop's vigor and water use, show farmers "fields like yours that already switched", and present the current rotation + 3 alternatives with evidence, water cost, gaps and risks.

## Lanes
| Lane | Owner | Scope | Brief |
|---|---|---|---|
| 1 Data & models | Claude (Manuel's agent) | HLS ingest, Prithvi crop history, outcome/covariate table, embeddings + analogs, fixtures | `01-lane-data.md` |
| 2 Science engine | Friend A's agent | causal estimates + robustness, FAO-56 water, constraints, option generator | `02-lane-science.md` |
| 3 Product & story | Friend B's agent | agent API, Egyptian-Arabic explainer, web app, validation page, deck/video, submission texts | `03-lane-product.md` |

Lanes 2 and 3 never wait on Lane 1: they start on **fixtures** (real FAO-label data for Sidi Ghazi, delivered at Lane 1 M1) and swap to full artefacts at M2. Everyone codes against the schemas below, not against each other's code.

## Repo layout (one GitHub repo, `main` protected, one branch per lane)
```
pipeline/        Lane 1 (Kaggle notebooks/scripts)
science/         Lane 2 (Python package `science`)
app/             Lane 3 (backend + frontend)
artefacts/       schemas + small fixtures only (big files go to GitHub Releases)
docs/            design, gates, agent briefs, decisions log
```
Big artefacts: GitHub Release tag `artefacts-vN` (Parquet/COG). Each release has a `MANIFEST.json` (file, sha256, rows, schema_version, produced_by, date).

## Identifiers
- `site`: `SGZ` (Sidi Ghazi, Kafr El-Sheikh), `ZAN` (Zankalon, Sharqia), `MLL` (Mallawi, Minya; out-of-region test only).
- `block_id`: `"{site}_{row}_{col}"` on a fixed **90 m grid** (3×3 HLS pixels ≈ 0.81 ha ≈ 1.9 feddan), EPSG:32636, origin = site bbox upper-left. Never say "field" in the UI; say "block".
- `season_id`: `W2024` = winter Nov 2023–May 2024; `S2024` = summer May–Oct 2024. Range W2016…S2025.
- `crop` enum: `wheat, clover, sugarbeet, beans, flax, rice, maize, cotton, veg, orchard, other, nonag`.

## Schemas (schema_version 1; additive changes only, announce in `docs/decisions.md`)
`blocks.parquet` — block_id, site, row, col, lon, lat, geometry_wkt, cropland_frac (0–1), governorate, rice_zone (bool), dist_coast_km, dist_canal_m, dist_drain_m, elev_m

`crop_seq.parquet` — block_id, season_id, crop, prob (0–1), source (`fao`|`prithvi`|`tessera`), purity (share of 10 m labels agreeing; fao only)

`block_season.parquet` — block_id, season_id, crop, peak_ndvi, peak_gcvi, ndvi_auc, n_clear_obs, et_season_mm (ECOSTRESS, nullable), lst_mean_c, esi_mean (nullable), et0_mm (POWER PM), heat_days_gt35, smap_sm_mean (regional), imerg_mm (regional), salinity_index, salinity_class (`low|med|high`)

`effects.parquet` — effect_id, site, precrop_treat, precrop_ctrl, next_crop, outcome (`peak_ndvi|et_season_mm|…`), method (`naive|dml|cforest`), estimate, ci_low, ci_high, n_treat, n_ctrl, stratum, schema_version

`cate.parquet` — block_id, effect_id, cate, ci_low, ci_high

`robustness.json` — per effect_id: placebo, permutation, overlap, sensitivity (RV), misclass_propagation, direction_check

`analogs.parquet` — block_id, rank, analog_block_id, similarity, analog_seq (e.g. `W2023:wheat>W2024:clover`), delta_peak_ndvi, delta_et_mm

`water.parquet` — crop, season, site, etc_mm, etc_m3_per_feddan, kc_ini, kc_mid, kc_end, method_note

`options` (JSON, served by Lane 2's `science.options.for_block(block_id, prefs)`):
```json
{"block_id":"SGZ_120_45","status_quo":{...},"options":[
 {"id":"water_saver","sequence":["W:clover","S:maize","W:wheat","S:cotton"],
  "water_m3_per_feddan":0,"evidence":[{"effect_id":"...","estimate":0,"ci":[0,0],"n":0}],
  "benefits":["..."],"gaps":["..."],"risks":["..."],"why":"...",
  "constraint_flags":{"salinity":"ok|warn|block","rice_zone":"ok|block","canal":"ok|warn"}}]}
```
Every number in an option must be traceable to an artefact row (`effect_id`, `water` row, or `crop_seq` row).

## Team-wide rules
1. No invented numbers anywhere: code, UI, deck, LLM output. Every figure traces to an artefact or a cited source.
2. Claims stop at "next-crop vigor and water use". Never "soil health", "yield gain", "per field".
3. Rice is only offered inside decree zones (Decree 26/2025; update if a 2026 decree appears).
4. Licences: code MIT; cite every dataset; FAO maps CC BY 4.0 (credit FAO WaPOR); disclose AI use.
5. Log any schema or scope change in `docs/decisions.md` (date, lane, change, reason) before merging.
6. PRs must pass CI (lint + tests) and get one review from another lane.

## Integration milestones
| Milestone | What | Gate |
|---|---|---|
| M1 | Lane 1 ships SGZ fixtures (FAO labels + HLS outcomes + covariates) and the pilot effect | Lanes 2 and 3 switch from mocks to fixtures |
| M2 | Lane 1 ships full artefacts (Prithvi history 2016–2025, both sites, analogs); Lane 2 ships effects + options v1; Lane 3 ships app v1 on fixtures | End-to-end demo on one block |
| M3 | Real artefacts everywhere; validation page complete; deck/video frozen | Submission dry-run: every link opens logged-out |
