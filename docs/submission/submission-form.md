# Submission form: what to paste where

The exact fields aren't saved anywhere in our notes. These follow the usual NASA Space Apps global project page; match them to the real form. Where a field has a character limit, use the short version.

| Field | What to enter |
|---|---|
| **Challenge** | Field Shift |
| **Team name** | Project: Hail Mary |
| **Team members** | Every teammate's Space Apps account (the leader adds them) |
| **Project name** | Precrop Payoff Atlas |
| **Link to final project / demo** (must be public; 7 slides OR a 30-s video) | https://github.com/ManuelGamal/hail-mary-fieldshift/blob/main/docs/submission/deck.pdf |
| **Link to repository / project files** | https://github.com/ManuelGamal/hail-mary-fieldshift |
| **Project image / thumbnail** | `docs/submission/assets/map_S2024.png` (summer crop map), or a screenshot of deck slide 5 |

## High-level summary (short field)
Precrop Payoff Atlas advises Nile Delta farmers what to plant next season to save water or earn more, based on what really happened on fields like theirs, measured by NASA satellites over ten years. First example: clover before rice costs about 50 m³ more water per feddan every season.

## Project details (long field)
**What it does.**
- A farmer picks their field.
- The tool finds about 10 fields like it (same salinity, water access and soil fingerprint) and looks at ten years of what those fields grew and how much water they used.
- It then suggests what to plant next: the option that saves the most water, or, with the farmer's own crop prices, the one that should earn the most.
- Every suggestion shows its evidence and how sure we are.

**What exists today.**
- The full measurement engine: ten years of crop maps, water use per field, a fair field-by-field comparison and the 10-field matching.
- One fully worked example, below.
- The farmer-facing advice screen and the revenue calculator (using farmer-entered prices) are next.

**How it works.**
1. **Ten years of crops.** NASA HLS (Landsat + Sentinel-2) is turned into a crop map of every 90 m field block, every season from 2016 to 2025. That's about 100,000 blocks in Kafr El-Sheikh and Sharqia. A LightGBM classifier trained on FAO WaPOR crop maps is right on about 8 in 10 blocks in a year it never saw. Rice area comes within about 10% of FAO's maps.
2. **Water.** NASA ECOSTRESS gives each block's daily water use, summed over each season.
3. **Fair comparison.** Each field is compared only with itself: summers after clover against summers after wheat, year after year. Soil, salinity and canal access cancel out.
4. **Check.** Next year's clover cannot change this year's water use. Our method correctly finds no effect there.
5. **Fields like yours.** For any field, the pipeline finds about 10 similar fields: same salinity class and rice zone, similar elevation, and similar satellite fingerprints from NASA/IBM's Prithvi-EO-2.0 model.

**Worked example: should a Sharqia farmer plant clover or wheat before rice?**
The tool's first answer, fully measured:
- Clover before rice: +12 mm over the summer (+2.4%), measured on 17,371 Sharqia fields (range 11–13 mm). That's about 50 m³ per feddan.
- Kafr El-Sheikh: +10 mm.
- About 0.6 million m³ a year in our Sharqia study area alone.

**Benefits.**
- Water planners can see the water cost of rotations without surveys.
- Rice-area limits can be tracked from space.
- The method runs on free data and a free Kaggle GPU.

**Tools.** Python, PyTorch, LightGBM, rasterio, linearmodels; Kaggle notebooks (free GPU); NASA Earthdata and Microsoft Planetary Computer for data access.

**Limits.**
- Results describe 90 m blocks, not individual farms.
- Season water use can't be split between the clover's late growth and the rice.
- We found no gain in rice greenness after clover.

## Use of NASA data
- **HLS** (Harmonized Landsat Sentinel-2, v2.0): crop maps and greenness, 2016–2025.
- **ECOSTRESS** (L3T JET evapotranspiration, L2T LSTE, L4T ESI): field water use and stress.
- **POWER:** reference evapotranspiration and temperature.
- **NASADEM:** elevation.
- **Prithvi-EO-2.0** (NASA/IBM geospatial foundation model): field similarity.

## Other space agency / partner data
- ESA Sentinel-2, inside HLS.
- FAO WaPOR Level 3 crop-type maps (CC BY 3.0 IGO), used as training and test labels.
- OpenStreetMap via Geofabrik (ODbL): canals and drains.
- Natural Earth (public domain): coastline.

## References
- NASA LP DAAC: HLSS30/HLSL30 v2.0, ECO_L3T_JET, ECO_L2T_LSTE, ECO_L4T_ESI.
- NASA POWER API; NASADEM.
- Prithvi-EO-2.0-300M-TL (Hugging Face: ibm-nasa-geospatial).
- FAO WaPOR v3 L3 crop type.
- OpenStreetMap / Geofabrik Egypt extract.

## Use of AI (required disclosure)
- AI assistants helped write code, documentation and the deck text.
- All analysis runs in our own pipeline; every number traces to its outputs in the repo.
- No AI-generated images, voices or video.

## Before pressing submit
- [ ] Both links open in a private window, ideally on a second network too.
- [ ] Submitted on the **local Cairo form** and on the **global Space Apps site**.
- [ ] The team leader submits.
