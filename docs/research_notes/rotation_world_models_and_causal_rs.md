# AI for crop-rotation planning (world models / RL / digital twins) and causal inference from remote sensing: feasibility for "Field Shift" (Nile Delta)

Scope: two candidate concepts for NASA Space Apps 2026 "Field Shift". (1) a "Rotation World Model": an action-conditioned spatiotemporal model trained on HLS/Prithvi-reconstructed crop histories, with MCTS/CEM planning; (2) a "Natural-experiment engine": causal effects of observed rotation sequences on satellite outcomes, estimated with matching, DML and causal forests. Researched 2026-11-13 using about 17 search/fetch calls. Most results are abstracts or search snippets. Where I read only a snippet, I say so.

## Q1. Existing RL / model-based planning for crop rotation, and crop-model emulators

### Takeaway
RL-for-crop-management is a mature benchmark genre: CropGym, gym-DSSAT, CyclesGym, WOFOSTGym and LLM-as-policy variants. Almost all of it trains inside a process-based crop simulator, not a learned model, and targets in-season N/irrigation, not rotations. Only CyclesGym (NeurIPS 2022) does explicit multi-year crop planning. Rotation planning as such has a long operations-research history (MILP and multi-objective models). ML emulators of APSIM-class models are accurate in-distribution but generalize poorly to unseen locations.

### Cited Findings
- CropGym: a Gym environment wrapping a process-based crop model (winter wheat, N-limited soil). The action space is the N amount at each time step. Single-crop, single-season. — [CropGym arXiv 2104.04326](https://arxiv.org/pdf/2104.04326)
- gym-DSSAT: a Gym environment on the DSSAT simulator for fertilization and irrigation problems. — [HAL gym-DSSAT](https://hal-cea.archives-ouvertes.fr/MDLS/hal-03976393v1)
- CyclesGym (Turchetta, Corinzia, Sussex, Burton, Herrera, Athanasiadis, Buhmann, Krause; NeurIPS 2022 Datasets & Benchmarks) is built on the multi-year, multi-crop Cycles model. It argues that earlier RL work used single-year, single-crop simulators. It has modular state/reward constructors and weather generators, and its case studies are N fertilization and crop planning. The crop-rotation experiments were run with only 5 repeats (min/mean/max reported). I could not retrieve its rotation numbers. — [NeurIPS 2022 poster](https://neurips.cc/virtual/2022/poster/55732); [Supplement](https://papers.neurips.cc/paper_files/paper/2022/file/4a22ceafe2dd6e0d32df1f7c0a69ab68-Supplemental-Datasets_and_Benchmarks.pdf)
- WOFOSTGym (2025) trains RL agents on agromanagement for 23 annual crops and 2 perennial crops on the WOFOST/PCSE base. — [arXiv 2502.19308](https://arxiv.org/html/2502.19308v2)
- A 2024 comparative study of deep RL for crop production management, and an RL-based digital-twin review (2024), survey these environments. One review notes a DQN agent that recommends crops from soil conditions, which is the closest thing found to an "RL rotation recommender". — [arXiv 2411.04106](https://arxiv.org/html/2411.04106v1); [arXiv 2406.08854](https://arxiv.org/pdf/2406.08854)
- An RL application to nitrogen management with crop growth models (Cambridge Environmental Data Science). — [Cambridge](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/358749FAFAA4990B1448DAB7F48D641C/S2634460223000286a.pdf/nitrogen-management-with-reinforcement-learning-and-crop-growth-models.pdf)
- RL under partial observability and climate variability for agricultural management. — [arXiv 2401.01273](https://arxiv.org/pdf/2401.01273)
- LLM-based planners: "The New Agronomists" (Wu et al., CVPRW 2024) replaces the RL policy MLP with a pretrained LM, uses DSSAT simulations and five reward functions trading off yield, resources and nitrate leaching. CROPS (arXiv 2411.06034) uses an LM RL agent that also infers masked states. No LLM rotation planner was found. — [arXiv 2403.19839](https://arxiv.org/html/2403.19839v1); [arXiv 2411.06034](https://arxiv.org/html/2411.06034v1)
- "Mechanism-guided crop large model" (CLM, HIT): autoregressive generative pretraining for action-conditioned crop-dynamics forecasting. In simulated fertilization and irrigation it reports more than 27% higher net income, and the authors say real-field validation is future work. This is the closest "learned action-conditioned crop world model", but it is simulation-trained and not satellite-based. (From a search snippet.) — [HIT Scholar](https://scholar.hit.edu.cn/en/publications/empowering-agricultural-decision-making-with-clm-mechanism-guided/)
- Classical rotation planning: Dury et al. review more than 120 models of cropping-plan and rotation decisions in agronomic, economic and land-use studies. Older work, pre-2013. MILP formulations go back at least to Alfandari et al. 2011 (Annals of OR), with multi-period demand and incompatibility constraints. — [HAL hal-00930508](https://hal.archives-ouvertes.fr/hal-00930508); [Multi-objective models for crop rotation planning](https://www.bohrium.com/paper-details/multi-objective-models-for-crop-rotation-planning-problems/1039281237635629068-1360)
- Emulators: a 2026 probabilistic neural emulator of APSIM maize reports R²≈0.93 across 13 outputs, trained on 2 million APSIM runs, with each APSIM run taking about 2 minutes. — [arXiv 2605.22848](https://arxiv.org/html/2605.22848)
- Emulators generalize poorly: Johnston et al. (2023) found that NN, MARS and RF emulators of APSIM-NextGen chickpea all had R²>0.95 at training locations but did not perform well at unseen test locations. — [BL catalog record](https://eld.bl.uk/catalog/100180515115_0x000001)
- Xiao et al. (ERL 2022) found that ML emulators reproduce APSIM yield and soil-carbon dynamics across the Huang-Huai-Hai plain. Sanderson et al. (MODSIM 2021) used deep-NN emulation of archived APSIM runs. — [DOAJ ERL 2022](https://doaj.org/article/964d1814b45c497586a4a1ffbeca5804); [MODSIM 2021](https://www.mssanz.org.au/modsim2021/papers/L1/sanderson.pdf)

### Inferences
- For concept (1), "MCTS/CEM over rotations" is not new as a planning formulation: CyclesGym, MILP and DQN recommenders already exist. Any novelty would have to come from the dynamics model being learned from satellite observations rather than a crop simulator.
- A practical hybrid baseline: plan with an existing process model (WOFOSTGym/PCSE or CyclesGym) and use the satellite world model only for state estimation. Judges will expect the learned model to be compared against such a simulator baseline.
- Emulator out-of-distribution failure (Johnston 2023) carries over directly. A world model trained on few Delta fields will be extrapolating whenever the planner proposes crop sequences that were rare in the data.

### Gaps
- CyclesGym's quantitative rotation results, and whether RL beat fixed rotations, were not retrieved.
- No DSSAT-specific emulator paper was retrieved. No RL/planning work was found for Egypt or for irrigated double-cropping systems (e.g., berseem/wheat to maize/rice).

## Q2. Learned Earth/field world models: action-conditionable? Is planning inside a learned satellite world model done in agriculture?

### Takeaway
State-of-the-art satellite "world models" (EarthNet2021, GreenEarthNet/Contextformer, VegeDiff, EO-WM, probabilistic NDVI transformers) are conditioned on weather only. None conditions on management or crop choice, and none plans. I found no published work that plans inside a learned, satellite-trained, action-conditioned model for crop management. That makes concept (1) novel in framing, but also unvalidated.

### Cited Findings
- GreenEarthNet / Contextformer (Benson et al., CVPR 2024; arXiv 2303.16198) predicts 20 m Sentinel-2 greenness conditioned on coarse meteorology. It uses a delta-prediction scheme from a gap-filled observation, which puts a strong persistence prior on the forecast. Code and weights are at vitusbenson/greenearthnet. The dataset is 24,861 cubes over Europe, 2017–2022. — [arXiv 2303.16198](https://arxiv.org/html/2303.16198v2); [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html)
- VegeDiff (arXiv 2407.12592, reportedly IEEE TGRS 2025) is a latent diffusion model for probabilistic geospatial vegetation forecasting, motivated by deterministic models' poor handling of uncertainty. (From a snippet.) — [VegeDiff](https://fugumt.com/fugumt/paper_check/2407.12592v1_enmode)
- EO-WM (Luo et al., arXiv 2606.27277, June 2026) is a video diffusion transformer, "physically informed world model". Weather is split into climatological baseline, anomaly and cumulative stress. It reports a 5.63% lower error in NDVI-decline amplitude and a 7.80% better directional hit rate versus baselines. The abstract describes no action or management conditioning and no planning. — [arXiv 2606.27277](https://arxiv.org/abs/2606.27277)
- A probabilistic NDVI forecast from sparse satellite series plus historical and future weather covariates (transformer quantile model, Feb 2026). — [arXiv 2602.17683](https://arxiv.org/html/2602.17683v1)
- EcoMapper (ICML 2025) fine-tunes Stable Diffusion 3 on 2.9M Sentinel-2 images linked to climate records to simulate landscapes under weather scenarios. — [ICML 2025](https://icml.cc/virtual/2025/poster/44910)
- A review of "agricultural world models" separates them from yield predictors and digital twins by whether management actions enter as manipulable variables. It warns of a "schedule memory trap": predictors memorize management calendars instead of learning action effects. Its focus is mainly controlled-environment agriculture. — [Zenodo 21699171](https://zenodo.org/records/21699171)
- LeCropFollow (arXiv 2606.31941) plans in a learned latent world model with MPPI, but for robot navigation in crop rows, not management. — [arXiv 2606.31941](https://arxiv.org/pdf/2606.31941)

### Inferences
- The "schedule memory trap" is the central scientific threat to concept (1). In observational satellite data, crop choice is chosen by the farmer (confounded) and nearly deterministic given location and season (low positivity). An action-conditioned model then learns "what fields that chose X looked like", not "what X does". Planning with MCTS/CEM exploits exactly these spurious regions. This is model-exploitation and distribution-shift failure, well known from offline model-based RL. This is my inference; I did not search for an offline-RL citation.
- Weather-conditioned vegetation forecasters lean heavily on persistence (Contextformer's delta scheme). A next-season forecast across a crop switch (e.g., berseem to rice) breaks persistence. The model then mostly has to learn crop-specific phenology templates, which are already well known agronomically.
- So concept (1) is novel as a framing, but a scientist would see it as a crop-type-conditional phenology emulator with confounded actions. Its value hinges on concept (2)-style adjustment or a hybrid with a process model.

### Gaps
- Not verified whether any 2026 paper adds land-cover/crop-type conditioning to GreenEarthNet-style models. Searches did not surface one.

## Q3. Causal inference with remote sensing in agriculture (rotation, cover crops, tillage, DML); confounding/positivity; valid outcome proxies

### Takeaway
Concept (2) has strong, recent precedent from the Lobell group, which applied causal forests to satellite yield proxies for rotation effects across the US, Canada, France and NE China (Kluger, Di Tommaso & Lobell, ERL 2025). It also has Deines et al.'s cover-crop and tillage studies. So the method is established, not novel. A Nile Delta application would be a novel geography. The literature's own caveats include unmeasured fertilizer and management, map misclassification, one-year precrop effects only, spatially correlated errors, and proxy outcomes. Those caveats are the critique judges should expect.

### Cited Findings
- Kluger, Di Tommaso & Lobell, "Precrop Payoffs: Causal machine learning reveals large but variable yield benefits of crop rotation in major breadbaskets," ERL 20 (2025) 114037 (arXiv 2506.02384). Details:
  - Data: NE China 2017–2019 (You et al. 10 m maps), Canada 2011–2020 (AAFC ACI 30 m), France 2015–2021 (parcel data), US 2008–2021 (CDL).
  - Outcome: normalized peak GCVI from harmonic regression (Sentinel-2 or Landsat), calibrated linearly to county/subnational yields.
  - Estimator: causal forests (R `grf`) for the overlap-weighted effect of A→B vs B→B, plus heterogeneity via best linear projection on weather.
  - Findings: rotation generally benefits yield; spring wheat benefits most and corn least; soybean→winter wheat is strongly negative in the US; benefits are larger in rainier seasons; legume-precrop benefits shrink when warm; diversifying beyond a 2-crop rotation adds little (the 2-crop benefit is about 3.7x the added diversification benefit).
  - Robustness: log outcome, geographic FE, NIRv alternative index, soil covariates, outlier removal, calibration transfer, grid-cell difference-in-means.
  - Stated limitations: no control for soil quality, tillage, cover crops, residue, fertilizer or pesticides; management treated as mediators (net effects); attenuation from map and proxy error; CIs ignore confounding bias and spatial correlation; only one-year precrop effects; propensity trimmed to 0.05–0.95; results are on a proxy scale.
  - [arXiv 2506.02384 v2](https://arxiv.org/html/2506.02384v2)
- Kluger, Owen & Lobell (ERL 2022, arXiv 2112.13700) combined randomized field trials with observational satellite data for corn–soy rotation benefits. The average benefit was 1.02 t/ha for corn and 0.20 t/ha for soy, with lower corn benefits in hot conditions. They explicitly say satellite-only estimates are not reliable causal effects: fertilizer is unmeasured (so the corn effect is underestimated), and both rotation labels and yields carry error. — [arXiv 2112.13700](https://arxiv.org/pdf/2112.13700)
- Deines et al. (Global Change Biology 2022), satellite-derived data plus causal forests on more than 90,000 fields (2019–2020): fields cover-cropped for 3 or more years had 5.5% lower maize yield and 3.5% lower soybean yield. Losses were larger on better soils, in cooler mid-season and with lower spring rain. — [PNNL record](https://data.pnnl.gov/group/nodes/publication/33662); [OSTI](https://www.osti.gov/pages/servlets/purl/2441230)
- Deines et al. (ERL 2019), Landsat tillage maps plus causal forest, US Corn Belt 2005–2017: long-term conservation tillage gave +3.3% maize and +0.74% soybean yield. — [IOP ERL 2019](https://iopscience.iop.org/article/10.1088/1748-9326/ab503b/meta); [PDF](https://thesustainabilityalliance.us/wp-content/uploads/2019/12/Positive-yield-effect-from-conservation-tillage.pdf)
- Smallholder context: Jain's group uses 10 m imagery to evaluate programs in smallholder systems, and has used remote sensing to compare groundwater vs canal irrigation effects on winter cropping in India (descriptive, not DML). No smallholder satellite DML study of rotation effects was found. — [Live Science interview](https://www.livescience.com/planet-earth/climate-change/seeing-how-important-agriculture-was-for-daily-livelihoods-and-how-uncertain-and-precarious-agriculture-had-become-in-these-times-it-just-made-me-feel-very-passionate-about-working-on-this-issue); [UC ANR PDF](https://ucanr.edu/sites/HarterGroundwater1/files/252435.pdf)
- Practice detection in smallholder irrigated rice: Sentinel-1 ML mapping of direct-seeded rice and AWD adoption in Punjab (2025). This is mapping, not causal estimation. — [arXiv 2507.08605](https://arxiv.org/html/2507.08605v2)
- The outcome proxy for "soil health" is weak. Optical SOC mapping needs bare soil. Composites help for mapping (NE China geometric-median composite R² 0.64) but bias the predicted range (Brög et al. 2025). A 2026 Wallonia study of 34,418 parcels found the model's minimum detectable difference exceeded the SOC change expected within 10 years of carbon-farming practices. It concluded composites are "not suitable for SOC content monitoring at parcel-level". — [EGU26-17841](https://meetingorganizer.copernicus.org/EGU26/EGU26-17841.html); [Brög et al. via AGRIS](https://agris.fao.org/search/en/records/68877db27fd4d06c32a8d7d5); [UCLouvain multitemporal SOC](https://research.dial.uclouvain.be/handle/2078.5/104302)

### Inferences
- Valid outcomes for concept (2) are next-crop vigor and yield proxies: peak GCVI/NIRv/NDVI, calibrated to CAPMAS/governorate yields if available. ET (e.g., WaPOR or SSEBop) can serve as a water-use outcome. "Soil health" should not be claimed. At best the claim is "legacy effect on subsequent crop vigor". The Wallonia minimum-detectable-difference result directly undermines 5–10-year satellite soil-health monitoring at field scale.
- Delta-specific confounders, from my reasoning plus the rice-policy sources:
  - Rice is legally restricted to designated Delta areas by annual ministerial decree, and permitted area fell from about 1.1M acres (2019) to about 750k acres (2021). Rice/maize choice therefore follows canal command, salinity and policy zone, which also drive vigor. — [USDA FAS 2021](https://www.fas.usda.gov/data/egypt-egyptian-parliament-approves-prohibition-rice-cultivation-non-designated-areas); [APEDA report](https://agriexchange.apeda.gov.in/MarketReport/Reports/Egyptian_Parliament_Approves_the_Prohibition_of_Rice_Cultivation_in_Non-Designated_Areas _Cairo_Egypt_05-25-2021.pdf)
  - The policy zone boundary is a potential natural experiment (a regression discontinuity or instrument). It could also wreck positivity, because there is near-zero rice outside the permitted zones.
  - Other confounders: salinity and water-table gradients toward the north Delta, fertilizer use (unobserved), and livestock ownership (which drives berseem choice).
  - Smallholder fields (often well under 1 ha) mix pixels at 30 m HLS. Interference/SUTVA violations come from shared canals and neighbouring fields.
- Positivity: in the Delta the winter choice is mostly wheat vs berseem, and the summer choice is maize vs rice vs cotton. There are few distinct sequences, which is good for overlap, but the crop choice is regionally clustered. Spatial blocking is therefore needed both for CV and for honest overlap checks.

### Gaps
- Exact per-crop effect sizes in Kluger 2025 (Table S9) were not retrieved.
- No satellite-based causal study of rotation effects in Egypt or any North African irrigated system was found.

## Q4. Is there learnable signal? Rotation legacy effects within 5–10 years; Egypt berseem evidence

### Takeaway
One-season precrop effects on next-crop vigor are real and satellite-detectable in large datasets. Lobell's group detects them across four countries, but they are modest: roughly 1 t/ha for corn in US trials and much smaller for soy. Multi-year cumulative "legacy" or soil effects have not been shown from satellites, and Kluger 2025 explicitly studies only one-year effects. Egyptian field trials consistently find berseem is the best preceding crop, for rice in the Delta and for wheat in Upper Egypt. So a berseem→next-crop vigor effect is a plausible, testable target. A multi-year soil-health trajectory is not.

### Cited Findings
- Kluger 2025: one-year precrop effects only. Long-term or whole-sequence effects are explicitly out of scope, and the limited years of high-resolution crop maps hamper them. Diversification effects are small or non-significant. — [arXiv 2506.02384 v2](https://arxiv.org/html/2506.02384v2)
- A Flanders (Belgium) satellite study using similar methods found an insignificant rotation effect. This shows the signal can vanish. (Reported in a search snippet; I did not verify the primary source.) — [OUCI record](https://ouci.dntb.gov.ua/works/4KeOzAJ9)
- Tag El-Ezz station (Dakahlia, Delta), two-season trial: rice after berseem had the highest means for all traits, attributed to soil fertility after clover. — [EKB journal article](https://journals.ekb.eg/article_257186_9c13162afbfa131f3df085f05509a5d2.pdf)
- Assiut (Upper Egypt) 2015/16–2016/17: wheat after clover outperformed other sequences. — [EKB article](https://journals.ekb.eg/article_36384_16cfcbe3193150ca9923afb030a5fb14.pdf)
- Reclaimed lands: the carry-over effect on summer crops ranked berseem > lentil > barley > wheat. — [EKB/ASEJ article](https://asejaiqjsae.journals.ekb.eg/article_3155_2b3150036a4506bc9a03c6040dda7cff.pdf)
- Nile Delta crop mapping is feasible. El-Shirbeny et al. (2025), RF on GEE: 92.79% overall accuracy for winter 2022/23 (κ 0.889) and 95.94% for summer 2023 (κ 0.941). Wheat and clover dominate winter, maize and rice dominate summer, and cotton is minor. FAO WaPOR also provides Sentinel-2 crop-type maps with ground truth for Zankalon, Sidi Ghazi and Mallawi (2023–2024). Amin et al. (2022) mapped multi-season phenology of wheat, clover, maize and rice with Landsat-8 plus S2 green LAI. — [ASU repository](https://research.asu.edu.eg/handle/123456789/217717); [FAO dataset](https://www.fao.org/agroinformatics/training-and-resources/data-sets/data-set-detail/new-crop-type-mapping-data-for-egypt/en); [RUA Amin 2022](https://rua.ua.es/dspace/handle/10045/123115)

### Inferences
- The HLS record is 2013 onward for L30 and 2015 onward for S30, though reliable 10–30 m crop maps exist only for the Delta in recent seasons. That gives roughly 8–10 seasons of history at most, and 2–3 annual cycles of labelled ground truth. That supports one-step precrop effects. It is far too little to learn multi-year dynamics for a 5–10-year rotation planner, because there are too few independent transitions per sequence type, and they are confounded with year.
- Misclassifying berseem vs wheat or other winter crops attenuates the estimated effect (Kluger's attenuation caveat), so 90%-accuracy maps imply about 10% label noise on the treatment.

### Gaps
- No Delta field trial with wheat-after-berseem figures was retrieved, and no Egyptian estimate of the satellite-detectable effect size exists.

## Q5. Validity pitfalls and best-practice validation

### Takeaway
Validation needs:
- held-out years (temporal split);
- spatially blocked CV (by village or canal command);
- placebo/negative-control tests;
- overlap diagnostics;
- comparison against field-trial effect directions (the Kluger 2022 hybrid template);
- for concept (1), checks that the planner's chosen actions stay in-distribution.

### Cited Findings
- Kluger 2025 robustness suite: alternative index (NIRv), log outcomes, geographic fixed effects, soil covariates, outlier removal, calibration transfer, causal-forest fit diagnostics, and grid-cell difference-in-means. Earlier work showed satellite Soy→Corn estimates correlate positively with RCT results. — [arXiv 2506.02384 v2](https://arxiv.org/html/2506.02384v2)
- Kluger 2022 combines RCTs and observational satellite data, because satellite-only estimates suffer confounding and measurement error. — [arXiv 2112.13700](https://arxiv.org/pdf/2112.13700)
- Emulator validation must use unseen locations: in-sample R²>0.95 collapsed out-of-location (Johnston 2023). — [BL record](https://eld.bl.uk/catalog/100180515115_0x000001)
- Agricultural world models must avoid memorizing management schedules. — [Zenodo 21699171](https://zenodo.org/records/21699171)

### Inferences (recommended checks; methodological, not sourced to a single paper)
- Placebo outcome: estimate the "effect" of the next-season crop on the previous season's vigor (should be ~0). Also estimate the effect on pre-sowing bare-soil reflectance or vigor of a crop 2 seasons back.
- Placebo treatment: randomly permute rotation labels within strata (village, season).
- Negative control: effects on non-crop pixels or on fields that stayed fallow.
- Sensitivity: E-values or omitted-variable bounds (e.g., the Chernozhukov et al. DML sensitivity / `sensemakr`-style analysis), because fertilizer is unobserved.
- Directional check against Egyptian trial evidence (berseem > wheat as a precrop) as external validation.
- For concept (1):
  - Compare against a persistence baseline, a climatology-by-crop baseline and GreenEarthNet-style weather-only models.
  - Report counterfactual consistency, i.e., whether "action" effects in the model match the causal-forest estimates.
  - Restrict planning to the data support (penalize model uncertainty with ensembles, as in offline MBRL). This is my inference.

### Gaps
- No standard benchmark exists for causal effects from satellite agriculture data, and none for action-conditioned satellite forecasting.

## Q6. Compute: trainable within 8 h on a Kaggle T4?

### Takeaway
Concept (2) is easily feasible: causal forests and DML on tabular per-field features train in minutes on CPU, and most of the time goes to data prep. Concept (1) is feasible only in a reduced form: per-field or patch time-series models on frozen Prithvi embeddings or simple indices. Pretraining or full fine-tuning a Prithvi-scale spatiotemporal world model is not.

### Cited Findings
- Prithvi-EO-2.0 pretraining took about 21,000 GPU-hours on 80 GPUs (300M) and about 58,000 GPU-hours on 240 GPUs (600M). Tiny (about 5M) and 100M variants exist. The official multi-temporal crop-segmentation fine-tuning example notebook is designed for a Colab T4. — [arXiv 2506.20174](https://arxiv.org/pdf/2506.20174); [HF Prithvi-EO-2.0-300M](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M); [HF 600M](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-600M)
- Kluger 2025 uses R `grf` causal forests. — [arXiv 2506.02384 v2](https://arxiv.org/html/2506.02384v2)

### Inferences
- Concept (1): fine-tuning Prithvi-EO-2.0-tiny or 100M for crop mapping on a T4 is feasible (an official T4 notebook exists). After that, a small GRU or transformer dynamics model over per-field embeddings and indices, with crop and weather inputs, trains in under 1 h. Video-diffusion world models like EO-WM or VegeDiff on a T4 within 8 h are unrealistic (inference, no compute figure retrieved). HLS download and cloud masking over the Delta is likely the real bottleneck.
- Concept (2): `econml`/`grf` causal forest or DML on about 10^4–10^5 fields with tens of covariates runs in minutes on CPU.

### Gaps
- No fine-tuning GPU-hour figures were retrieved for Prithvi crop segmentation, and no compute figures for GreenEarthNet/Contextformer training.

## Overall assessment (inferences, for the report writer)
- **Concept (1) novelty:** high as a framing, since no satellite-trained, action-conditioned world model with a planner was found in agriculture. Scientific risk is also high: confounded and low-positivity actions, the schedule-memory trap, about 10 seasons of data, and the planner exploiting model errors. Defensible version: "crop-conditional next-season vigor/ET forecaster, with causal adjustment, used to rank 1–2 season options", validated against held-out years and causal estimates. Avoid claiming multi-year soil-health optimization.
- **Concept (2) novelty:** method is established (Lobell group, Deines). Geography and system are novel: an irrigated, smallholder Delta with berseem/wheat to rice/maize/cotton, and a policy-zone natural experiment. Scientific risk is moderate and well understood, and it is very feasible in a hackathon.
- **Strongest combination:** use (2) to estimate precrop effects with honest uncertainty, and use those estimates to constrain or validate a lightweight (1). Frame outcomes as next-crop vigor and water use (ET), not soil health.
