# Field Shift (NASA Space Apps 2026): competitive landscape and new idea scouting

Research date: 2026-11-13. Event dates: 14–15 Nov 2026 per a participant's source register citing the indexed official homepage ([senitheknath SOURCES.md](https://github.com/senitheknath/nasa-app-challege/blob/main/preparation/SOURCES.md)). The official Resources tab was reportedly due 13 Nov ([same](https://github.com/senitheknath/nasa-app-challege/blob/main/preparation/SOURCES.md)), so re-check it once the event opens.

## (a) What does the official challenge text say, and which resources are listed?

### Takeaway
The full official text is reproduced verbatim in at least two 2026 participant repos. It names SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE/GRACE-FO, SRTM and GEDI, and asks teams to compare at least 3 rotations including the existing one. For each option it wants the reasoning, the evidence, the benefits, the information gaps and the risks. It frames the tool as supporting the farmer, not replacing them. A local organizer (HackAthlone) lists the Resources, which add VIIRS, NLDAS/GLDAS, OpenET, FAO GAEZ and ESA Sentinel-2/ERA5.

### Cited Findings
- **Copy of the full text:** "copied by the team on 4 Nov 2026" from the official page. Difficulty is Intermediate/Advanced. Subjects are Arts & Multimedia, Earth Science and Software. The page writes "SI" where most readers would expect "AI", and the team kept that wording. — [amr-mousa-eg/fieldwitness docs/official_challenge.md](https://github.com/amr-mousa-eg/fieldwitness/blob/main/docs/official_challenge.md); a second copy matches it: [aroyy007/FieldShiftBD organizer problem-statement](https://github.com/aroyy007/FieldShiftBD/blob/main/docs/plans/references/2026-10-29-organizer/problem-statement.md)
- **Background:** "a crop that improves soil health in one place may consume too much water, introduce disease, conflict with local markets, or fall outside expected growing seasons somewhere else." It also says NASA's long-term datasets "and SI techniques open opportunities to translate that data into practical, farmer-friendly insights." — [fieldwitness official_challenge.md](https://github.com/amr-mousa-eg/fieldwitness/blob/main/docs/official_challenge.md)
- **Objectives, datasets:** "You may explore NASA datasets such as SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE and GRACE‑FO, and SRTM or other NASA elevation products". It lists patterns to analyze: temperature, heat stress, rainfall, soil moisture, evaporation, frost risk, extreme precipitation, vegetation stress and long-term water trends. It lists farmer priorities: "water use, forage value, nitrogen‑fixing potential, erosion reduction, organic matter improvement, or market suitability." — [same](https://github.com/amr-mousa-eg/fieldwitness/blob/main/docs/official_challenge.md)
- **Objectives, outputs:** the tool "may highlight times when fields are typically bare, seasons when current crops appear more vulnerable, or opportunities for rotations that could interrupt pest cycles, reduce water demand, improve infiltration, or add supplemental income. You may compare at least three rotation strategies, including the existing rotation. For each strategy ... explain why it was suggested, what evidence supports it, what benefits it may offer, where information gaps exist, and any risks that would need local review". — [same](https://github.com/amr-mousa-eg/fieldwitness/blob/main/docs/official_challenge.md)
- **Potential considerations, "SI, Modeling, and Data Fusion":** compare SI/statistical approaches; use SI to highlight seasonal transitions, bare-field periods and stress times; "Explain how the model interprets uncertainty and where local expertise would be needed"; harmonize "SMAP soil moisture, ECOSTRESS land‑surface temperature, GPM precipitation, Landsat/MODIS vegetation indices, GEDI biomass, and soil datasets" onto a common grid. The other considerations: explain terms (ET, soil-moisture anomalies, NDVI, frost risk, water balance); satellite vs ground data; interactive maps, field-level vulnerability zones, scenario sliders; farmer-centered design with priority/constraint input. — [same](https://github.com/amr-mousa-eg/fieldwitness/blob/main/docs/official_challenge.md)
- **Resources (organizer reproduction):**
  - NASA: SMAP, GPM/IMERG, MODIS, VIIRS, NASA POWER, SRTM, ECOSTRESS, NLDAS/GLDAS, GEDI.
  - Non-NASA: Landsat (USGS), USDA Ag Data Commons, Web Soil Survey, CDL/CropScape, PRISM, SSURGO, NAIP, NLCD, FAO GAEZ, CoCoRaHS, USGS NWIS, USDA AMS, NASS QuickStats, OpenET, LANDFIRE.
  - ESA partner: Copernicus Sentinel-2, ERA5.

  Source: [HackAthlone challenge page](https://hackathlone.com/challenges/adapting-farms-with-nasa-data). Another participant classes this page as "Local organizer's reproduction, not an independently verified full NASA page" ([SOURCES.md](https://github.com/senitheknath/nasa-app-challege/blob/main/preparation/SOURCES.md)).
- **AI disclosure rule:** the indexed 2026 FAQ reportedly allows AI/SI tools, provided they are disclosed in a mandatory submission question. Non-NASA materials must be open/OSI-licensed, and original content defaults to Apache-2.0. — [SOURCES.md](https://github.com/senitheknath/nasa-app-challege/blob/main/preparation/SOURCES.md) (secondhand; I could not verify the official page because of TLS)
- **Mirror:** nasaspaceapps.ae carries only the summary and links to the official brief. — [nasaspaceapps.ae/challenges](https://nasaspaceapps.ae/challenges)

### Inferences
- The resource list is US-centric (SSURGO, CDL, NASS). A Nile Delta team has to name its own substitutes, such as SoilGrids/HWSD for soils, CAPMAS or FAOSTAT for crops and Egyptian market prices. Doing this clearly is a way to stand out on Validity.
- The brief rewards honesty about evidence and uncertainty ("information gaps", "risks needing local review"). Every one of the five candidate concepts should output a per-option evidence/uncertainty statement.
- GEDI, VIIRS and NLDAS/GLDAS are listed but probably seldom used by teams. GLDAS (global, not NLDAS) is the version relevant to Egypt.

### Gaps
- The official Resources tab itself (I could not reach spaceappschallenge.org because of TLS, and web.archive.org was blocked for the fetch tool). The HackAthlone list may differ from the final official list.
- Official 2026 judging weights and video length limits were not verified.

## (b) What have past winners and the 2026 competition built, and what rotation decision-support tools already exist?

### Takeaway
The 2026 field is crowded: GitHub has more than 40 repos named "field shift" from this cycle. Most are NASA POWER (sometimes with SMAP/MODIS) feeding a rule-based or weighted-score rotation ranker, with bilingual UIs, chat advisors, historical-year replays or evidence grades. At least three appear Egyptian-authored, and one (BlinkFarms) already targets Egyptian farmers with ECOSTRESS, SMAP and an Egyptian-Arabic Gemini advisor. The only past agriculture global winner found is Egypt's 2025 Zumorroda-X, an educational game. I found no deployed rotation DSS for the Delta, only FutureWater's Croptimal WhatsApp crop-resilience app in Sharkia.

### Cited Findings — 2026 competitor entries
- **BlinkFarms:** flash-drought early detection, subsoil hardpan/salinity diagnosis, multi-year rotations, irrigation volume in m³/feddan, and a Gemini advisor "fluent in Egyptian Arabic dialect".
  - Data: ECOSTRESS LST/ESI, SMAP L4, NASA POWER, GPM IMERG.
  - Methods: FAO-56, a surface energy balance, van Genuchten, Feddes, a linear state-space "field memory" model, and TOPSIS ranking.
  - Validation: AmeriFlux US-Ne1, ET R² 0.9966.
  - Claims a 14-day lead over NDVI and up to 36% water savings (self-reported).

  Source: [umar-essayed/BlinkFarms-NASA-SpaceApps](https://github.com/umar-essayed/BlinkFarms-NASA-SpaceApps)
- **FieldWitness (amr-mousa-eg, apparently Egyptian author, but deployed on Kansas HLS tile T14SLH, 200 fields):**
  - HLS field story since 2015 and 3-season alternatives with an A–D evidence grade.
  - Priority sliders and weather what-ifs.
  - "smallest change that would flip the top option", and recommendations turned into predictions next season's satellite data can check.
  - A hindcast scoreboard against baselines, 3D FAO-56 water balance, GRACE/SMAP layers.

  Source: [fieldwitness README](https://github.com/amr-mousa-eg/fieldwitness)
- **FIELDSHIFT AI (a7mdel5taeeb-eng):** bilingual Arabic/English with NASA POWER and optional SMAP. — [repo](https://github.com/a7mdel5taeeb-eng/fieldshift-ai)
- **Other patterns:**
  - FieldShift (samuelakosaonyejekwe): a "Rotation Time Machine" that replays plans through every real year since 1995, plus 2040/2050 suitability projections and MODIS NDVI.
  - CropShift: analog climate-year matching.
  - RotaShift (Bangladesh): measures the shift in the growing window from 22 years of rainfall.
  - Bilingual Urdu/Khmer versions.
  - Kisan Mitra: voice-first, and the repo names itself "Winner", which is unverified.
  - Team Atlas: an ESP32 soil rover.
  - ferrosasfp (Peru): **rotation + parametric insurance demo**.

  Sources: [search results listing](https://github.com/samuelakosaonyejekwe/fieldshift), [RotaShift](https://github.com/XtremeseOISHEE/RotaShift), [ferrosasfp/field-shift](https://github.com/ferrosasfp/field-shift), [Kisan Mitra](https://github.com/Chitransh007-ww/FieldShift-Kisan-Mitra-NASA-Space-Apps-Challenge-Winner), [teamatlaslive/Field-Shift](https://github.com/teamatlaslive/Field-Shift) (descriptions from `gh search repos`)

### Cited Findings — past Space Apps
- **2025 global winners (10 of 11,500+ projects):**
  - Art & Technology went to **Zumorroda-X (Egypt)**, in the "NASA Farm Navigators" agriculture challenge: mini-games about how farmers adapt to heat waves and flooding.
  - Local Impact went to **QUEÑARIS (Peru)**, in BloomWatch: NASA data, drones and AI for queñua reforestation and water security.
  - Best Use of Technology went to Twisters/SkySense (Mexico): NASA EO and AI hyperlocal weather risk.

  Source: [NASA announcement](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/)
- **2024 "Leveraging Earth Observation Data for Informed Agricultural Decision-Making":** I found a team page (AgroEye) but no confirmed global-winner record. — [AgroEye about](https://nasa-hackathon-proj.vercel.app/about.html)
- **Akvelon:** its NASA Earth-data prototype won the local Seattle "Best Use of Data" award. — [Akvelon](https://akvelon.com/engineering-an-end-to-end-geospatial-prototype-with-nasa-earth-data/)
- **NASA ESTO Space-to-Soil Challenge (July 2026; $400k total):**
  - Winners: Hydrosat (onboard thermal alerts using ECOSTRESS/Landsat algorithms) and LandScout (plant-health alerts to farmers' phones).
  - Runner-up DarwinsLabs "SoilSentinel": distils the **NASA-IBM Prithvi** foundation model to predict vegetation and bare-soil indices.

  This shows NASA's own interest in Prithvi plus agriculture. — [ESTO](https://esto.nasa.gov/?p=5934)

### Cited Findings — existing tools
- **FutureWater "Croptimal" (BUCRA project, Qahbunah, Sharkia):** identifies crops and locations resilient to heat, salinity and water scarcity, with recommendations over WhatsApp. Its rotation work sits in demonstration plots, not clearly in the app. — [FutureWater BUCRA](https://www.futurewater.eu/projects/bucra/), [BUCRA inception report 2025](https://nabc.nl/wp-content/uploads/2020/06/BUCRA_Inception-report-and-baseline-study_January-2025.pdf)
- **Nile Delta salt-affected soil mapping** from Sentinel-1/2 time series (2024 paper). — [ASU repository](https://research.asu.edu.eg/handle/123456789/217622)
- **Generic farm-management software with rotation planners:** AGRIVI, Farmbrite, Solara and Agricolus. Soil Health Matrix scores rotation as one of 4 practices. These are not EO-driven decision support. — [Soil Health Matrix](https://soilhealthnexus.org/?p=2097), [Solara](https://solara.ag/features/crop-rotation/)
- **Farmonaut** markets satellite advisories in the Nile Delta (Amza Farms case). Its statistics look like marketing claims. — [Farmonaut](https://farmonaut.com/agriculture/ai-driven-crop-advisories-for-grape-citrus-farms-in-egypts-nile-delta)

### Inferences
- The "default" entry (POWER, a weighted score, a chatbot, a bilingual UI) is saturated. Judges will see many of them. Features already taken include analog-year replay, evidence grades, falsifiable predictions, a 3D water balance, insurance linkage and an Egyptian-Arabic LLM. The candidate concepts need to visibly go beyond these.
- **BlinkFarms overlaps directly** with Egypt targeting, ECOSTRESS/SMAP and salinity/hardpan, which weakens the novelty of candidate (4), salinity-aware rotations. FieldWitness's falsifiable-prediction framing overlaps with the "validity" story of candidate (2).
- Egypt has prior success in agriculture at Space Apps (Zumorroda-X 2025). This helps Relevance and Local Impact framing, but it was an educational-game win, not an analytics win.

### Gaps
- I did not verify what NASA Harvest, Regrow, Cropwise, FarmersEdge, CGIAR or AgroDSS rotation features do; searches returned nothing on them. The Egyptian MoALR "Digital Agriculture" apps were also not verified.
- 2020–2023 agriculture winners were not checked (budget). Neither was the 2024 Galactic Impact winner ([siliconprairienews](https://siliconprairienews.com/2025/02/nebraska-startup-wins-nasas-galactic-impact-award-in-the-2024-space-apps-challenge), topic unverified).
- I could not open full competitor code. Their claims are self-reported.

## (c) Which novel AI-heavy angles not on the candidate list could score higher?

### Takeaway
The strongest new angles are:
1. A **NASA Prithvi-EO-2.0 / HLS crop-sequence foundation model**. Using NASA's own AI scores Relevance and is under-used by competitors.
2. **Analog-field retrieval using geospatial embeddings**: "fields like yours that already switched".
3. **Seasonal-forecast-aware, regret-minimizing rotation choice**. I found no rotation-specific prior work.
4. A **NISAR field-scale soil-moisture early adopter** angle (beta data from Feb 2026).
5. A **verifiable tool-using agent**: an LLM restricted to audited NASA-data tools, with every claim citing a computed number.

Insurance linkage and plain LLM chat are already taken by 2026 teams.

### Cited Findings and assessment per idea

**1. Prithvi-EO-2.0 (NASA-IBM) fine-tuned on HLS to map multi-year Delta crop sequences**
- NASA ESTO recognised a Prithvi-distillation agriculture concept (DarwinsLabs SoilSentinel) in 2026. — [ESTO](https://esto.nasa.gov/?p=5934)
- The FieldWitness competitor uses HLS indices but no foundation model. — [fieldwitness](https://github.com/amr-mousa-eg/fieldwitness)
- NASA data: HLS (Landsat+Sentinel-2, NASA LP DAAC), plus Prithvi itself (a NASA model).
- What it does: maps the existing rotation (rice/maize/cotton in summer, wheat/berseem in winter) for every field. This feeds the "existing rotation" baseline the brief demands.
- **Feasibility (inference):** fine-tuning a ~300M ViT on a few thousand labelled chips fits in under 8 h of Kaggle GPU. Labels are the bottleneck; options are weak labels from phenology rules, or berseem's multiple-cut NDVI signature.
- Risk: no ground truth in the Delta, and cloud cover is low, so this is not a strong argument for a foundation model.
- I did not check whether Prithvi has already been applied to Egyptian crop mapping (gap).

**2. Analog-field retrieval: embedding search for "fields like yours that already rotated"**
- AlphaEarth embeddings have been used for rotation mapping in Henan (ISPRS Annals 2026). A Goyal et al. preprint (Oct 2026) reports that embeddings "capture multi-year crop rotation dynamics", with a trade-off in cross-region transferability. — [ISPRS Annals](https://isprs-annals.copernicus.org/articles/XI-2-2026/865/2026/isprs-annals-XI-2-2026-865-2026.xml), summary via search
- TESSERA beat AlphaEarth for smallholder crop mapping in Senegal. — [arXiv 2601.16900](https://arxiv.org/abs/2601.16900v1), [Cambridge news](https://www.cam.ac.uk/research/news/ai-tool-for-mapping-smallholder-crops-proves-itself-in-senegal)
- I found no work using embeddings for retrieval of analog fields as evidence for rotation advice.
- NASA data: HLS/Prithvi embeddings keep it NASA-native, because AlphaEarth is Google and TESSERA is Cambridge (a Relevance risk). The comparison of outcomes after a switch uses ECOSTRESS ET/LST, SMAP and NDVI.
- **Overlap warning:** this is close to candidate (2), the causal natural-experiment engine. It is best framed as that engine's retrieval layer, or as a lighter, faster alternative to it.
- Risk: matched fields are confounded (selection bias), so it needs honest caveats.

**3. Seasonal-forecast-aware rotation choice (GEOS-S2S / NMME), regret-minimizing**
- A probabilistic AI monsoon-forecast design paper argues calibrated probabilistic forecasts beat deterministic messages. It was used in a 2025 Indian program reaching 38M farmers. — [arXiv 2603.07893](https://arxiv.org/html/2603.07893v1)
- NMME hindcasts show skill for some agricultural decisions (US Pacific Northwest). — [ERL 2024 (DOAJ)](https://doaj.org/article/e004f93fbb0f4018adbca387ca1d241d)
- An NBER experiment found that forecasts change farmers' planting and input decisions. — [NBER w32173](https://img.nber.org/papers/w32173)
- I found no work that applies seasonal ensembles to *rotation* choice.
- Delta use case (inference): terminal heat risk to wheat vs berseem/faba in spring, and summer heat-wave risk for maize vs rice. Rainfall is irrelevant in the irrigated Delta, so the case rests on temperature skill.
- **Risk:** S2S temperature skill over Egypt is not verified (gap). GEOS-S2S is not in the challenge resource list, though it is NASA (GMAO).

**4. NISAR field-scale soil moisture (200 m, Level-3 SME2): be the first rotation tool to use it**
- NASA released over 100,000 NISAR L1–L3 products in February 2026, including NISAR Beta Soil Moisture V1. SME2 is a 200 m field-scale product with 36–72 h latency. Reprocessing is planned, with no date. — [Earthdata alert](https://earthdata.nasa.gov/data/alerts-outages/over-100000-new-data-files-available-from-nisar), [ASF products overview](https://nisar-docs-test.asf.alaska.edu/products-overview)
- ISRO separately produces a 100 m L4 soil moisture product from Feb 2026 acquisitions. — [ISRO](https://new1.isro.gov.in/NisarData_soil_moisture_products.html)
- **Novelty (inference):** none of the competitor repos surveyed mention NISAR, and NISAR is not in the official resource list.
- Use: field-level waterlogging/drainage and salinity proxies, for example in northern Delta rice fields. This can stack on candidate (4).
- **Risk:** the product is beta/pre-calibration; Delta coverage is unverified; L-band soil moisture over flooded rice is ambiguous; and the event is only 48 h, so data access is untested.

**5. A tool-constrained, verifiable rotation agent over NASA APIs**
- In UnivEARTH (ACL Findings 2026), zero-shot LLM agents using Earth Engine reached 40% accuracy, and their code failed to run more than 44% of the time. Free-form EO agents are unreliable. — [ACL Findings 2026](https://preview.aclanthology.org/ingest-acl/2026.findings-acl.124/)
- Agri-SAGE (Jul 2026) grounds multi-agent LLM advice in APSIM simulation; it does not use Earthdata. — [alphaxiv 2607.00454](https://www.alphaxiv.org/abs/2607.00454)
- ESA EVE orchestrates EO tools through MCP. — [StatEO 2026 poster](https://stateo26.esa.int/iframe-agenda/files/ID_324.pdf)
- GeoLLM-Squad pulled MODIS from Earthdata. — [arXiv 2501.16254](https://web3.arxiv.org/pdf/2501.16254)
- I found no LLM agent that combines Earthdata with rotation advice.
- **Differentiator:** an LLM that may only call audited tools (POWER, SMAP, ECOSTRESS, an FAO-56 water balance). Every sentence carries a computed number and provenance, and a "challenge it" mode lets the farmer contest a claim. The pitch is "an agent that cannot hallucinate numbers".
- Risk: BlinkFarms already ships a Gemini advisor in Egyptian Arabic, so this only differentiates if the verification is demonstrated visibly.

**6. Lower-priority angles (taken or unverified)**
- **Parametric insurance/credit linkage:** already done by ferrosasfp (Peru). — [repo](https://github.com/ferrosasfp/field-shift)
- **ECOSTRESS water stress:** already used by BlinkFarms. — [BlinkFarms](https://github.com/umar-essayed/BlinkFarms-NASA-SpaceApps)
- **Pest/disease climate risk** (e.g., wheat rust, fall armyworm degree-days) and **berseem nitrogen credit**: these match the brief's "interrupt pest cycles" and "nitrogen-fixing potential", but I did not run novelty searches on them (gap).

### Inferences
- **Recommended combination (inference):** candidate (1) or (2) as the engine, Prithvi/HLS (idea 1) for the existing-rotation baseline, and the verifiable agent (idea 5) as the interface. NISAR (idea 4) is a "first-mover" slide if the data actually covers the Delta. This mix is AI-heavy, NASA-native (HLS, Prithvi, ECOSTRESS, SMAP, NISAR) and distinct from the saturated POWER-plus-score entries.
- Candidates (3), EMIT soil carbon, and (4), salinity, are weaker on novelty and data access. BlinkFarms already covers salinity and hardpan for Egypt. EMIT soil-carbon retrieval over cropped Delta fields with no ground truth would struggle on Validity.
- Presentation is judged only from the deck or video, so one striking visual matters. Competitors already show 3D farms and "time machine" replays. A contrasting choice would be a map of "fields like yours that switched", or a forecast-fan chart of regret per rotation.

### Gaps
- GEOS-S2S/NMME temperature skill over the Nile Delta.
- NISAR coverage over the Delta and access to the beta product.
- Prior Prithvi crop mapping in Egypt.
- Pest-risk and berseem-N novelty.
- Whether Kaggle can reach Earthdata (network access and auth tokens) within the 8 h cap.
- All feasibility estimates above are my inferences, not sourced benchmarks.
