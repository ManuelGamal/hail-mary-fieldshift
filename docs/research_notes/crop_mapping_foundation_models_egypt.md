# Geospatial foundation models for crop-type mapping and multi-year crop-sequence reconstruction: feasibility for Nile Delta smallholder fields

Research date: 2026-11-13. I made about 16 tool calls, so coverage is broad rather than exhaustive. Some sources (MDPI) returned 403. Items not verified in this session are marked as such.

## Q1. SOTA comparison for crop mapping (Prithvi-EO-2.0, Galileo, Presto, AnySat, TESSERA, AlphaEarth, Clay, SatMAE) and benchmarks

### Takeaway
No single benchmark compares all the candidate models on crop mapping. The evidence that does exist points one way for low-label, low-compute work. Precomputed pixel-time-series embeddings (AlphaEarth 64-d, TESSERA 128-d, Presto 128-d), each fed to a light classifier, are the cheapest option and are competitive or best with few labels. Image-patch ViTs (Prithvi-EO-2.0) only slightly beat strong supervised baselines (U-TAE/UNet) when they have full labels, and they cost far more to fine-tune. All these GFMs degrade sharply under regional distribution shift.

### Cited Findings
- **Prithvi-EO-2.0 (NASA/IBM).** On US multi-temporal crop segmentation it reports mIoU 50.7 (600M) and 48.6 (300M), against 42.6 for U-Net. On PASTIS, the 600M model gets 53.4 mIoU with full data and 37.4 with 10% of labels, against 52.9 and 36.9 for the U-TAE baseline. That is a margin of about 0.5 points over a specialist supervised model. — [Prithvi-EO-2.0 paper, arXiv 2412.02732](https://arxiv.org/pdf/2412.02732)
- Prithvi-EO-2.0 takes 6 HLS reflectance bands as chronologically ordered GeoTIFF timestamps. Its model cards link a multitemporal crop-segmentation Colab meant for a T4 runtime, and a "tiny" variant exists for constrained hardware. No T4 timing figures were found. — [HF model card 300M](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M); [600M-TL](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-600M-TL/raw/main/README.md); [tiny-TL](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-tiny-TL)
- **PANGAEA benchmark.** With full labels, supervised baselines (especially UNet) beat most GFMs. With 10% of labels, CROMA and DOFA are the most competitive. On the crop-type task the supervised baseline falls well behind the GFMs when labels are limited, and SpectralGPT does well with linear probing. The benchmark includes a "Crop Type Mapping-SS" dataset. — [PANGAEA, arXiv 2412.04204](https://arxiv.org/html/2412.04204v2). A 2026 agriculture-benchmark paper describes PANGAEA's coverage differently (unresolved conflict). — [arXiv 2606.29664](https://arxiv.org/pdf/2606.29664)
- **2026 agriculture GFM benchmark** (Prithvi, SpectralGPT, SatMAE; crop segmentation across Iowa, NC, CA and MN with region-disjoint splits). All three models degrade sharply under regional shift, collapse toward majority crops, and miss rare ones. — [arXiv 2606.29664](https://arxiv.org/abs/2606.29664)
- **Galileo (ICML 2025, NASA Harvest).** One generalist model is reported to beat specialist SOTA on 11 benchmarks spanning images and pixel time series, ranking above Presto. A secondary blog gives CropHarvest-Kenya 84.2% and says the Nano and Tiny variants come near the top. That number was not verified against the paper. — [PMLR Tseng et al. 2025](https://proceedings.mlr.press/v267/tseng25a.html); [arXiv 2502.09356](https://arxiv.org/abs/2502.09356)
- **TESSERA (Cambridge).** It produces 128-d per-pixel embeddings at 10 m from S1+S2 time series. The authors report it matches or beats AlphaEarth on several downstream tasks and beats baselines on Austrian crop types (17 classes). Unlike AlphaEarth, it is open and reproducible. — [TESSERA arXiv 2506.20380](https://arxiv.org/html/2506.20380)
- **Senegal groundnut-basin crop types (2026).** The TESSERA-based approach did best among the methods tested, including AlphaEarth, and was about 28% more accurate than the next best in a temporal-transfer example. — [arXiv 2601.16900](https://arxiv.org/abs/2601.16900v1)
- **Presto vs AlphaEarth, cropland in Togo (CropHarvest test set).** Presto F1 0.808 vs AlphaEarth 0.745, and OA 0.897 vs 0.859 (as the snippet reports it). AlphaEarth over-predicts cropland in shrub or scattered-tree areas. This is one region and a binary cropland task, not crop type. — [arXiv 2511.02923](https://arxiv.org/html/2511.02923v1)
- **AlphaEarth Foundations.** The abstract claims it beats "a suite of well-known featurization approaches" across diverse mapping evaluations without retraining, in the sparse-label setting. The abstract names no baselines or numbers. — [arXiv 2507.22291](https://arxiv.org/abs/2507.22291)
- **EuroSAT-Embed (2026)** compares pooling over AlphaEarth, OlmoEarth and TESSERA embeddings. It notes TESSERA encodes per-pixel time series with no spatial context. — [arXiv 2603.02080](https://arxiv.org/pdf/2603.02080)

### Inferences
- **Least labeled data:** precomputed embeddings (AlphaEarth/TESSERA) with logistic regression, a random forest or a small MLP. Presto and Galileo-Nano/Tiny are the best open alternatives if embeddings must be computed from HLS yourself (they are pixel-time-series models and cheap to run).
- **Cheapest at inference:** AlphaEarth and TESSERA, because inference has already been done. The cost is a download plus a classifier, which runs on a CPU in minutes. Presto (about 0.4M parameters, from training knowledge; not verified this session) is next. Prithvi-EO-2.0 300M/600M is the most expensive, and the PASTIS evidence suggests the gain over U-TAE is marginal.
- **Fit to the task:** annual embeddings (AlphaEarth, TESSERA) summarise a whole calendar year. A year in the Delta usually holds one winter crop plus one summer crop, so a natural target is a yearly *sequence class* (for example wheat→rice, berseem→maize). Read per year from 2017 to 2024/25, those classes give a rotation history directly. They do **not** give separate per-season maps unless the class set encodes the season pair. The calendar-year boundary also cuts through the winter season (Oct–May), so one year's embedding mixes the tail of one winter crop with the start of the next.
- Clay, SatMAE and AnySat were not well covered in this session. SatMAE appears only in the 2026 agriculture benchmark, where it has the same regional-shift weakness.

### Gaps
- No head-to-head crop-type benchmark of AlphaEarth vs TESSERA vs Galileo vs Prithvi in Egypt or North Africa was found.
- AnySat and Clay crop results were not retrieved.
- Exact Galileo CropHarvest tables and the PANGAEA per-dataset crop numbers were not verified.

## Q2. AlphaEarth Satellite Embedding dataset: Egypt coverage, years, access, licence

### Takeaway
The dataset is global over land, which includes Egypt (inferred from "terrestrial land surfaces"). It is annual, 10 m, 64 bands, and licensed CC-BY 4.0. The EE catalog lists 2017–2024, while the GCS readme mentions 2017–2025, so check before relying on 2025. It can be used entirely within Earth Engine (sample, export small rasters or tables), so no GPU is needed.

### Cited Findings
- `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL`: annual layers 2017–2024, 10 m, 64 bands A00–A63 (unit-length vectors, values -1 to 1), produced by AlphaEarth v2.1 from optical, radar, LiDAR and other sources. The licence is CC-BY 4.0 with the attribution "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind." Coverage is terrestrial land and shallow waters, with limited polar coverage. The 2017 layer was regenerated as v1.1 (2025-11-17) with more Sentinel-1 acquisitions. Minor swath artifacts remain. Continuity depends on USGS and ESA inputs. The GCS bucket became **"provider pays"** in July 2026. — [EE catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL)
- The GCS readme states the bucket holds 2017–2025 annual embeddings as COGs with a manifest and index. This conflicts with the catalog's 2017–2024. — [AEF GCS readme](https://developers.google.com/earth-engine/guides/aef_on_gcs_readme)
- A secondary press report says Apache-2.0, which conflicts with the official CC-BY 4.0. Trust the official docs. — [The Decoder](https://the-decoder.com/google-deepmind-unveils-an-ai-model-that-acts-as-a-virtual-satellite-for-mapping-the-entire-planet/)

### Inferences
- Since the bucket is now provider-pays, bulk GCS download would cost egress money. The free path is Earth Engine (noncommercial/research access): sample embeddings at labelled points, train `ee.Classifier.smileRandomForest` or export a district-scale stack to Drive.
- Rough download size for a 30×30 km district: 9M pixels × 64 bands. That is about 0.6 GB per year at int8 or about 2.3 GB at float32, so 8 years is about 5–18 GB. It fits Kaggle disk. (These are my own estimates; the export data type was not verified.)
- 2017–2024 gives 8 years, which meets the 5–10-year target. 2025 would make 9 if the GCS claim is correct.

### Gaps
- Explicit Egypt-specific quality and artifact information was not found.
- Whether EE export yields int8 or float was not confirmed.

## Q3. ESA WorldCereal and other Egypt crop labels

### Takeaway
WorldCereal's only confirmed global product year is 2021 (temporary crops, maize, winter/spring cereals, irrigation, 10 m, CC-BY 4.0, on GEE). Validation is global with no Egypt-specific accuracy, and 2024/2025 maps are "TBC". The best Egypt label sources are the FAO WaPOR-2 Delta crop maps (2023–2024), published Nile Delta Sentinel/Landsat classification studies, and the WorldCereal reference-data repository. All of them are sparse in time.

### Cited Findings
- WorldCereal 2021 global accuracy: temporary crops OA 97.8% (cropland UA 88.5%, PA 92.1%), maize UA 85.8% / PA 75.5%, cereals UA 93.6% / PA 77.7%. Irrigation is harder and less accurate, and accuracy depends on location. Temporal coverage is listed as "2021, 2024, 2025 (TBC)". "Cereals" means wheat, barley and rye. — [CEOS GST agriculture](https://ceos.org/gst/agriculture.html)
- 2021 products are on GEE as `ESA/WorldCereal/2021/MODELS/v100` under CC-BY-4.0. — [EE catalog](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCereal_2021_MODELS_v100); Africa access is via [Digital Earth Africa docs](https://docs.digitalearthafrica.org/en/latest/data_specs/ESA_World_Cereal_specs.html)
- The WorldCereal harmonized reference data was extended and updated in 2025 (more than 75M observations, by one source's count). — [WUR record](https://research.wur.nl/en/datasets/worldcereal-harmonized-reference-datasets-extended-and-updated/)
- **FAO "New crop type mapping data for Egypt"** (dated 2026-08-04): crop-type maps for Zankalon and Side Ghazi irrigation areas and Mallawi, summer 2023, summer 2024 and winter 2023–24, from Sentinel-2 plus ground truth. Produced under WaPOR Phase 2 with MWRI and MALR. The page gives no crops, accuracy, licence or direct download, only the FAO data app. — [FAO](https://www.fao.org/agroinformatics/training-and-resources/data-sets/data-set-detail/new-crop-type-mapping-data-for-egypt/en)
- **El-Shirbeny et al. (2025), GEE RF on Sentinel-2:** OA about 92.8% (winter 2022/23, κ 0.889) and about 95.9% (summer 2023, κ 0.941). Winter is dominated by wheat and clover, summer by maize and rice, and cotton is minor. — [ASU repository](https://research.asu.edu.eg/handle/123456789/217717) (via search snippet)
- **Saleh, Ayyad & Ribbe (2025), *Earth*:** rice, maize, wheat and clover at **30 m, 2015–2020** (multi-year). OA 0.77–0.80 in summer and 0.87–0.95 in winter, and areas agree with national statistics. — [MDPI Earth 6(3):80](https://www.mdpi.com/2673-4834/6/3/80) (page returned 403; figures from search snippet)
- A Chapman/Nile Basin study of rice, wheat and clover from S2 indices reports test accuracy 0.73–0.82. — [Chapman](https://digitalcommons.chapman.edu/scs_articles/1127) (snippet)
- **USDA/NASA GLAM GDA CropID Egypt 2020 Rice:** 250 m distributed, classified at 30 m. — [GLAM](https://glam1.gsfc.nasa.gov/api/doc/cropmask/v1/GDA-CropID-Egypt_2020_Rice)
- Tolba et al. (2020) used Landsat thermal signatures for Delta rice and compared results with 2016 statistics. Bratley & Woodcock (2024) used LandTrendr for Egypt agricultural gain and loss, 1987–2019. — via [search results](https://doaj.org/article/24fc98c39b0849e28ee5b6f8cb79f834) (not opened)

### Inferences
- A trustworthy 8-year per-season label history does not exist publicly. The realistic plan is to train on the few labelled seasons (FAO WaPOR 2023–24, WorldCereal reference points, possibly crowdsourced or photo-interpreted points) and apply the model to other years. This is temporal transfer, which TESSERA did well in Senegal. National and governorate statistics (rice and wheat area per year) serve as an area-level sanity check rather than as labels.
- WorldCereal 2021 helps for the winter-cereal (wheat) and maize masks in a single year. It does not separate berseem, rice or cotton.

### Gaps
- CAPMAS/MALR governorate crop-area statistics were not retrieved in this session.
- CGIAR/IWMI Egypt datasets and Radiant MLHub/Source Cooperative Egypt crop labels were not found.
- No Egypt-specific WorldCereal validation was found.
- The licence and downloadability of the FAO WaPOR Egypt crop maps are unknown.

## Q4. The field-size problem: holdings vs 30 m HLS vs 10 m S2, and boundary datasets

### Takeaway
Delta holdings average about 1.6–2.2 feddan (about 0.7–0.9 ha), and individual plots are often smaller, around 1 feddan (4,200 m²). That equals about 4.7 HLS pixels (900 m²) or about 42 S2 pixels (100 m²). Per-field reconstruction at 30 m is therefore unreliable because of mixed pixels. At 10 m (AlphaEarth/TESSERA) it is feasible for many plots, though not all. FTW Global offers 2024–2025 boundaries at 10 m worldwide, but its accuracy in smallholder settings like the Delta is unvalidated. Per-pixel 10 m outputs aggregated to small blocks, or to FTW polygons where their confidence is high, look like the realistic unit.

### Cited Findings
- The average holding in Egypt's old lands fell from 1.93 feddan (2000) to 1.61 feddan (2010). The national average fell from 6.13 (1929) to about 2.19 feddan (2010). — [ASU, AUJAS study](https://research.asu.edu.eg/handle/123456789/221372). Other sources conflict: FAO gives an average farm size of 2.5 feddan with no year ([FAO family farming](https://www.fao.org/family-farming/countries/egy/es/)), and an uncited site claims 0.8 feddan.
- NASA Harvest / Univ. of Valencia describe Delta fields as "often less than two hectares" and fragmented. Fusing S2 and Landsat (Sen2Like) detected 91% of crop cycles across 42 fields over 6 years in El Gharbia, better than S2 alone. Short gaps between back-to-back crops such as clover are hard to resolve. — [NASA Harvest](https://www.nasaharvest.org/news/bringing-clarity-to-crop-cycles-how-data-fusion-is-advancing-smallholder-agriculture-in-egypt) (year not stated on page)
- **FTW Global:** 10 m field polygons for 2024 (1.62B) and 2025 (1.55B), claiming 241 countries. Mean pixel recall is 0.85 across the 24 benchmark countries. Confidence is conservative outside the training distribution, "such as smallholder systems". Polygons are remote-sensing units, not cadastral parcels. Licence CC-BY-4.0; GeoParquet and COG files with anonymous read at `data.source.coop/ftw/global-data/`. — [Source Cooperative FTW Global](https://source.coop/ftw/global-data/llms.txt)
- The FTW benchmark covers 24 countries on 4 continents, and Egypt was not confirmed as a training country. — [FTW arXiv 2409.16252](https://arxiv.org/pdf/2409.16252)

### Inferences
- At 30 m HLS, a 1-feddan plot of roughly 40×100 m holds at most 1–3 pure pixels, and most plots will be mixed. "Per-field" from HLS alone should be presented as per-pixel or per-block (for example a 30 m cell or a ~1 ha hex) with a dominant-sequence label.
- 10 m embeddings (AlphaEarth/TESSERA) are the better choice for anything field-like. Using HLS only for a phenology narrative (NDVI curves) also matches the "NASA data" framing of the challenge.
- FTW 2024/25 boundaries can be applied backwards in time on the assumption that Delta parcel geometry is fairly stable. Expect merged neighbouring plots wherever adjacent plots carry the same crop.
- AI4Boundaries coverage of Egypt was not checked (it is Europe-focused, from training knowledge; not verified).

### Gaps
- No recent census figure for Delta-specific plot or parcel size, as distinct from holding size, was found.
- No FTW accuracy assessment over Egypt was found.

## Q5. Phenology-based crop discrimination in the Delta: reported accuracies

### Takeaway
Winter separation (wheat vs berseem) reaches OA 0.87–0.95, and summer separation (rice vs maize, with cotton minor) 0.77–0.96 in single-season S2 studies. Accuracy drops at 30 m and for multi-year work (summer about 0.77–0.80). Even with HLS, detecting the correct number of seasons per year is only 63–74%. Berseem's multiple cuts and short gaps between crops are the main confusers.

### Cited Findings
- Amin et al. (2022) studied 326 ha near Tanta (162 parcels, 55 double-cropped) with **HLS v1.4 at 30 m (tile 36RUV), 2016–2019**, using green-LAI phenology. Correct season detection was 74% for L8+S2 with GPR gap-filling, 72% with Savitzky–Golay, 69% for S2 alone and 63% for L8 alone. Summer crops ran about 90 days and winter crops about 190 days. Detected start of season fell 2–4 weeks after planting. Cloud-free coverage was adequate. Ground truth came from Univ. of Tanta planting records. — [PMC7613390](https://pmc.ncbi.nlm.nih.gov/articles/PMC7613390/)
- S2 RF results: winter OA about 92.8% and summer about 95.9% (El-Shirbeny 2025). At 30 m over 2015–2020, summer OA was 0.77–0.80 and winter 0.87–0.95 (Saleh et al. 2025). — sources as in Q3.
- Clover's short inter-crop gaps cause missed cycles. — [NASA Harvest](https://www.nasaharvest.org/news/bringing-clarity-to-crop-cycles-how-data-fusion-is-advancing-smallholder-agriculture-in-egypt)

### Inferences
- For per-season classification, winter wheat vs berseem and summer rice vs maize are separable at about 85–95% at 10 m with good labels. Cotton is rare and will be poorly mapped, as with the "rare crop" failure noted in the GFM benchmark.
- Rice is the easiest summer class: it is flooded early, which shows up in Sentinel-1 and the thermal band and is captured in AlphaEarth/TESSERA through S1. Its acreage is also tracked in official statistics, which makes it a good anchor for multi-year validation.

### Gaps
- Per-class producer and user accuracies for berseem and cotton in recent studies were not retrieved (the MDPI full text was blocked).

## Q6. Realistic compute on Kaggle (T4×2 / P100, 8 h; disk about 73 GB; 12 h sessions)

### Takeaway
An embedding-plus-classifier pipeline easily fits the budget: GPU barely needed, with downloads of about 5–20 GB for a district over 8 years. Fine-tuning Prithvi-EO-2.0 on raw HLS for 8 years of a district is feasible but tight, and the gains are marginal. Raw HLS for 8 years over a full MGRS tile would approach or exceed Kaggle disk unless clipped to the district and cloud-filtered.

### Cited Findings
- Prithvi-EO-2.0 ships a T4 Colab for multitemporal crop segmentation and a tiny variant for constrained hardware. No throughput numbers were published in the sources found. — [HF model cards](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M)
- GeoTessera: global 0.1° tiles of shape (H, W, 128). Years are "2017–2025 depending on availability". CLI download is by bbox, region or country and year. Data is on AWS Open Data `s3://tessera-embeddings` and a Hugging Face mirror. As of June 2026, a full global v1.1 for 2017–2025 was "expected within a few months", so coverage is not yet uniform; check with `geotessera coverage`. — [GeoTessera docs](https://geotessera.readthedocs.io/en/stable/); [PyPI](https://pypi.org/project/geotessera/); [June 2026 release note](https://rogue-scholar.org/records/h0wq3-hpy81)
- AlphaEarth GCS is provider-pays from July 2026, while EE access is free for research. — [EE catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL)

### Inferences (my estimates, not sourced benchmarks)
- **Embedding route:** a 30×30 km district is 9M pixels at 10 m. TESSERA (128-d) is about 1.2 GB per year at int8 or about 4.6 GB per year at float32. AlphaEarth (64-d) is about half that. Eight years comes to roughly 5–37 GB depending on dtype. Training a classifier (RF or LightGBM on GPU) on tens of thousands of labelled pixels takes minutes, and predicting 72M pixel-years takes under 1 hour on CPU/GPU.
- **Raw HLS route:** a Delta HLS tile (110×110 km, 3660² px) is roughly 50–100 MB compressed per scene for 6 bands plus Fmask. HLS L30 plus S30 gives about 100–150 usable scenes per year. Clipping to a district (about 8% of a tile) gives roughly 0.5–1 GB per year and about 5–8 GB for 8 years. That fits, but downloads through NASA Earthdata/LP DAAC (needs an Earthdata login) will dominate wall-clock time. Note that HLS S30 starts in late 2015, and L30 goes back to 2013.
- **Prithvi-300M inference:** taking 224×224 px chips with 4–6 timesteps, a district at 30 m is about 1M px, or about 20 chips per season composite. That makes inference trivial (minutes) even on a T4. Fine-tuning on a few thousand labelled chips takes roughly 1–3 h on a T4 with mixed precision. The bottleneck is labels, not GPU. 600M may need gradient checkpointing within 16 GB.
- **Recommendation:** use AlphaEarth (via EE, 2017–2024) and/or TESSERA (open, 128-d, S1+S2, best result in the Senegal smallholder study) as the primary per-year features. Classify yearly winter→summer sequence classes, and use HLS NDVI/LAI time series for interpretability and the NASA-data requirement. Prithvi-EO-2.0 fine-tuned on HLS is a secondary or "NASA-model" showcase rather than the accuracy driver.

### Gaps
- No published T4 or P100 timing benchmarks for Prithvi, Galileo or Presto were found.
- Kaggle's current disk and session limits were taken from the task brief and not re-verified.
- Whether TESSERA tiles exist for the Delta for every year 2017–2025 was not confirmed (use the coverage map).
