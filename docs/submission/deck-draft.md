# Deck draft: 7 slides (Field Shift, team Project: Hail Mary)

Rules used throughout:
- One idea per slide, and a headline that is a full sentence.
- Name each NASA dataset once, with what it does.
- No jargon on the slides. The words to swap are in the table at the end.
- **Cairo has no live pitch** (`docs/design.md` §Cairo rules): judges read the slides alone, so each slide must make sense without a speaker. The "Notes" are for the 30-s video and for Q&A, not for the slides.

---

## 1. Title
**Headline:** *Does clover really help the next crop? We asked NASA's satellites.*
- Precrop Payoff Atlas: Nile Delta, 2016–2025
- Team Project: Hail Mary · NASA Space Apps Cairo 2026 · Field Shift

**Visual:** full-bleed satellite view of the Delta field mosaic (an HLS true-colour composite of Kafr El-Sheikh), with the title on a dark band.

**Notes:** "Every Egyptian farmer has heard that clover before rice makes the rice better. We wanted to know whether it's true, field by field, using only NASA data."

---

## 2. The problem
**Headline:** *Rotation advice is everywhere. Proof for your own field is nowhere.*
- Farmers in the Delta grow berseem clover, wheat or sugar beet in winter, then rice, maize or cotton in summer.
- Advice says some winter crops help the next one. Trials are few, old, and far from most villages.
- Choosing wrong costs a farmer a whole season.

**Visual:** a simple two-season strip: winter crop → summer crop, with a "?" between them.

---

## 3. What we built
**Headline:** *Ten years of every field's crops, read from space.*
- **NASA HLS** (Landsat + Sentinel-2) shows what grew in each 90 m field block, every season since 2016.
- **NASA ECOSTRESS** measures how much water each block used.
- An AI crop model checked against FAO's official crop maps: **8 in 10 blocks correct** on years it never saw.
- About 100,000 field blocks across two Delta governorates (Kafr El-Sheikh, Sharqia).

**Visual:** the map of one area flipping season by season (wheat / clover / rice colours). This is the strongest picture we have, so make it big.

---

## 4. The twist
**Headline:** *At first, the satellites agreed: clover fields grew better rice.*
- Rice after clover looked 2–4% greener than rice after wheat.
- Then we checked whether it was real.

**Visual:** one bar chart: "rice after wheat" vs "rice after clover", the clover bar a little taller.

**Notes:** "This is where most studies stop. We didn't."

---

## 5. Two illusions
**Headline:** *The "boost" was two illusions, not the clover.*
1. **Farmers give clover their best land.** Those fields were already greener the year before. *Fix:* compare each field only with itself across ten years.
2. **Clover stays green into June.** The satellite counted the clover's own leaves as healthy rice. *Fix:* measure only when the rice is actually in the field.

**Visual:** the field-calendar strip (May–June: clover still green; July on: rice). Shade the trap window red.

**Notes:** "Our proof that the method works: we asked whether *next* year's clover 'improves' *this* year's rice. That's impossible, and our method correctly finds nothing."

---

## 6. The answer
**Headline:** *With both illusions removed, rice after clover does no better than after wheat.*
- The difference is zero to slightly negative. It's at most about +1%, measured on 17,000 fields.
- Clover's real benefit may be **fertilizer farmers save**, which no satellite can see.
- Water use is the same per unit of growth: no water-efficiency gain.

**Visual:** the bar chart from slide 4 again, now with the bars level. Label: "after removing the two illusions".

---

## 7. Why it matters, and what's next
**Headline:** *A tool that tells farmers which advice holds up on land like theirs.*
- For any field, it finds about 10 similar fields (same soil, salinity, water and history) and shows what really happened there.
- Honest by design: every claim passes the "impossible effect" check, or it isn't shown.
- **Next:** add fertilizer-use and yield records from farmer cooperatives, then extend to Upper Egypt.
- Footer, required by the rules:
  - Data: NASA HLS, NASA ECOSTRESS, NASA POWER, NASADEM, FAO WaPOR crop maps, OpenStreetMap.
  - Models: NASA/IBM Prithvi-EO-2.0, LightGBM.
  - AI use: AI assistants helped write the code and the text; every number comes from our own pipeline.

**Visual:** a phone mock-up. A field is selected, with "10 fields like yours" and one plain sentence answer.

---

## Plain words (slides and voice)

| Instead of | Say |
|---|---|
| NDVI, NDVI-days | "how green", "greenness over the season" |
| switcher fixed effects | "compare each field with itself" |
| lead placebo | "the impossible-effect check" |
| precrop | "the winter crop before" |
| 90 m block | "field block" (once: "about the size of a football pitch") |
| confidence interval | "measured on 17,000 fields" |
| evapotranspiration, ET | "water the crop used" |
| HLS, ECOSTRESS | name them once each on slide 3, with what they do, then just "satellites" |

## Visuals to make (and where the data is)
- **Slide 3 map:** `crop_seq_lgb.parquet` (Kaggle `fieldshift-lane1-m2-train` v2) plus the block grid. Render it as a short GIF.
- **Slides 4 and 6 bars:**
  - Slide 4: whole-season numbers, ZAN clover → rice +2.66%.
  - Slide 6: rice-only window, −0.4% (ZAN) and −1.9% (SGZ).
  - Source: `kaggle/m2_hetero/out/hetero/water_productivity.json`.
- **Slide 5 calendar strip:** hand-drawn. The numbers behind it are early-window greenness +12% (ZAN clover), in the same file.
