# Precrop Payoff Atlas: the water cost of winter crop choices in the Nile Delta

NASA Space Apps Cairo 2026 · Challenge: Field Shift · Team: Project: Hail Mary

**Deck:** [docs/submission/deck.pdf](docs/submission/deck.pdf)

**Headline:** clover before rice costs about **50 m³ more water per feddan each season**: +12 mm (+2.4%) over the summer, measured with NASA ECOSTRESS on 17,371 fields in Sharqia (range 11–13 mm), and +10 mm in Kafr El-Sheikh. In our Sharqia study area that is about **0.6 million m³ a year**.

## How
1. **Crop history** (`pipeline/m2_ingest.py`, `pipeline/m2_earthdata.py`, `pipeline/m2_train.py`):
   - NASA HLS (Landsat + Sentinel-2) composites, 2016–2025, on a 90 m field-block grid.
   - A LightGBM crop classifier trained on FAO WaPOR crop maps: 0.82 overall accuracy on a held-out year.
   - NASA/IBM Prithvi-EO-2.0 embeddings for field similarity.
2. **Water:** NASA ECOSTRESS daily ET per block, summed over each season.
3. **Effect** (`pipeline/m2_train.py`, `pipeline/m2_hetero.py`):
   - Each field is compared with itself: summers after clover vs after wheat, with field and year fixed effects.
   - 95% intervals are clustered on 900 m super-blocks.
   - An impossible-effect (lead placebo) check must pass.
4. **Fields like yours** (`pipeline/m2_analogs.py`): about 10 matched fields per block, within the same salinity class and rice zone and at similar elevation.

Full technical write-up: [PROJECT.md](PROJECT.md). Decisions: [docs/decisions.md](docs/decisions.md). Gates: [docs/gates.md](docs/gates.md).

## Limits
- Results describe 90 m blocks, not individual farms.
- Season water use cannot be split between the clover's late growth and the rice.
- Rice after clover shows no measurable gain in rice greenness.

## Data and credits
NASA HLS, NASA ECOSTRESS, NASA POWER, NASADEM; FAO WaPOR (CC BY 3.0 IGO); OpenStreetMap via Geofabrik (ODbL). Models: NASA/IBM Prithvi-EO-2.0, LightGBM.
AI use: AI assistants helped write code and text; every number comes from our own pipeline.

License: MIT.
