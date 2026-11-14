# Submission text (draft)

**Project name:** Precrop Payoff Atlas

**Short description (≤ 300 chars):** Precrop Payoff Atlas advises Nile Delta farmers what to plant next season to save water or earn more, based on what really happened on fields like theirs, measured by NASA satellites over ten years. First example: clover before rice costs about 50 m³ more water per feddan every season.

**Long description:**
Egypt's farms run on Nile water, and every season farmers choose what to grow in winter before their summer crop. We measured what that choice costs in water, field by field, using only NASA data.
- **NASA HLS** (Landsat + Sentinel-2) maps every field's crop each season, 2016–2025, across about 100,000 field blocks in Kafr El-Sheikh and Sharqia. Our AI crop map is right on about 8 in 10 blocks, checked against FAO's official maps on years it never saw. Rice area comes within about 10% of FAO's maps, so rice limits can be tracked from space.
- **NASA ECOSTRESS** measures how much water each field uses.
- **The result:**
  - We compare each field with itself, summers after clover against summers after wheat, so soil, salinity and canal access cancel out.
  - Fields that had clover in winter use about 12 mm more water over the summer season (+2.4%): about 50 m³ per feddan. Measured on 17,371 fields in Sharqia (range 11–13 mm), and the same in Kafr El-Sheikh (+10 mm).
- **The check:** next year's clover cannot change this year's water use, and our method correctly finds no effect there.
- **Impact:** in our Sharqia study area alone, about 6,100 field blocks grow rice after clover each year, so about 0.6 million m³ of water a year (0.5–0.65). Water planners and farmers can see the water cost of each rotation, on fields like their own, without a farm survey.

**Data:** NASA HLS, NASA ECOSTRESS, NASA POWER, NASADEM, FAO WaPOR crop maps, OpenStreetMap.
**Models:** NASA/IBM Prithvi-EO-2.0, LightGBM.
**AI use:** AI assistants helped write code and text. Every number comes from our own pipeline.
