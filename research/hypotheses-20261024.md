# Five ranked geological hypotheses and their pre-registered tests (session 2026-10-24)

**Provenance of the order of events (honesty record).**  `registry/preregistration_halo88.json` (written 2026-10-24T06:39:45Z) fixed the three
tested hypotheses, their parameters and decision rules **before any result file existed**.  This narrative was completed afterwards; the rank
order of the three tested items is unchanged.  One aborted launch (first fold only) exposed a budget confound in my own FBMT arm (its expected
truth mass was inflated 4.2x, so it emitted 2x the dots); it was fixed (common expected truth for every arm, identical self-credit rule) before
any full run and the aborted numbers are not used anywhere.  The distance-fingerprint diagnostics (D2/D3) were computed while E1 was running and
**did not change any E1-E3 decision rule**.

**Instrument and its limits.**  Hide-and-recover, buffered whole components, seeds 20+21 (8 folds, **22,893 withheld positives**, identical to the
H88-ADHR run), pooled DTI (alpha 0.2, beta 0.8, 300 m kernel), evaluator `gems57-pooled-hide-v2`, paired spatial-block bootstrap (157 20-km
clusters, 1,000 draws).  Primary endpoint = *far subset* (withheld positives > 10 px from every visible catalogue pixel; 10,791 positives) because
the real labels are faults *not already captured* by USGS/INGENIOUS.  Leakage canary: 44 features, max symmetric single-feature AUC **0.5948**
(<= 0.90, PASS).  Stored references from the earlier ADHR run on the same folds: ADHR 0.18789 (far 0.11478), CGO-88 0.09042 (far 0.07683).
Every number below is **HOLDOUT-DTI**; none is ORGANIZER-CONFIRMED.

## Ranking at pre-registration time (expected DTI gain, then cost)

| Rank | ID | Expected gain | Cost | Status |
|---:|---|---|---|---|
| 1 | **FBMT** far-basin-matched training (E1) | medium | low | **tested - negative** |
| 2 | **CCR** catalogue-completeness residual (E2) | low-medium | low | **tested - negative** |
| 3 | **RCP** ridge-continuity prior (E3) | low-medium | low | **tested - null** |
| 4 | **NDVI-SL** spring / phreatophyte lineaments | unknown, possibly high for hydrothermal faults | **high** (new data) | not run - needs outbound access |
| 5 | **SDT-gate** stress-resolved strike gating (carried over) | low | medium (new data + stress model) | not run |

---

## H1 / E1 - FBMT: far-basin-matched training

* **Layers (44 label-blind columns, `gems88.physics.ALL_PHYS_FEATURES`):** 26 competition-stack columns derived from `training_features.tif`
  (19 bands: RTP/TMI gradient and tilt stacks, gravity gradients, 60-degree dip-offset back-projection of gravity/magnetic steps using
  `depth_to_base_surf`, `cond_surf` edges, GPS strain, seismicity, detrended elevation slope/curvature) + 18 external columns: DOE GDR #1391
  INGENIOUS 2-m probes / paleo-sinter / wells / vents (CC BY 4.0), USGS GeoDAWN K/Th/up-continued TMI (CC0), USGS 3DEP 1-m LiDAR scarp stack
  (75 % coverage) and 10-m topography/chi-ksn (public domain), pluvial-shoreline penalty.  All free and official; restored SHA-verified by
  `scripts/restore_inputs.py`.
* **Physical signature / transform.**  Mapped faults that stand alone (no other mapped component within a 5-px window; 10.1 k = 16.6 % of the 61.0 k catalogue
  pixels, 489 of 3,199 components) are the best available proxy for faults in *unmapped* terrain.  Train a gradient-boosted classifier on those positives against
  **far-basin background** (pixels > 8 px from every visible catalogue pixel); neighbourhoods of dense fault networks are left unlabeled so that
  strong range-front relief does not define "fault".
* **Why it could catch faults missing from the catalogue.**  Un-captured faults sit in terrain the catalogue does not describe; a model trained on
  dense range-front networks learns the signature of high-relief, well-expressed faults and ranks proximity to them.  Matching the training
  population to the test population is the textbook covariate-shift remedy.
* **Named non-fault mimics.**  Pleistocene Lake Lahontan/Bonneville shorelines (constant-elevation benches), E-W GeoDAWN flight-line corrugation,
  circular volcanic plugs/calderas, playa margins (`pluvial_shoreline_pen` and the `cond_surf` terms address these only partially).
* **Difference from the repo.**  ADHR/CGO/MGC train on every visible positive everywhere and (ADHR) use visible-catalogue structure features.
* **Result (8 folds, far subset):** BASE 0.07152 [0.05857, 0.08380]; **FBMT 0.06175 [0.04835, 0.07511]**; paired difference -0.00977
  [-0.02050, +0.00102], 3/8 fold wins.  Overall: BASE 0.10725, FBMT 0.07596, difference **-0.03129 [-0.04535, -0.01554]**.
  **Verdict: negative** (pre-registered keep rule not met).
* **Caveat to carry forward.**  FBMT was trained with an 8-px unlabeled zone around dense networks but allocated over d > 3 px, so it emitted dots in
  a zone it never saw.  A matched-domain variant (allocation d > 8 px) was **not** run: the budget of 3 experiments was spent.  Listed as N1 below.

## H2 / E2 - CCR: catalogue-completeness residual

* **Layers:** the E1 surface + the *visible* catalogue density (no hidden label enters).
* **Transform:** E = 1.5-km Gaussian-smoothed model evidence, C = same-window smoothed visible catalogue density, f(C) = median E per C-quantile
  bin over the allowed pixels (transductive, label-free); z = log[(E+eps)/(f(C)+eps)]; p' = p·exp(0.5·clip(z, +/-2)), renormalised.  gamma = 0.5 was
  fixed in advance (0.25 and 1.0 reported as sensitivity only, not selectable).
* **Why it could catch missing faults.**  Compilation completeness varies regionally; where geophysical evidence is high but mapped density is low
  compared with what such evidence usually accompanies, faults are more likely unmapped.
* **Mimic:** ranges with strong lithologic contrasts and no faulting (the model's own false-positive zones look "incomplete" too).
* **Difference from the repo.**  ADHR mixes a physics-only head with a fixed prior (`pi_unmapped = 0.5`); CCR is spatially varying and uses an
  explicit evidence-vs-density residual.
* **Result (far):** FBMT+CCR 0.05373 [0.04013, 0.06826]; difference vs FBMT **-0.00803 [-0.01189, -0.00413]**, 1/8 fold wins.  Sensitivity: gamma 0.25
  0.05863, gamma 1.0 0.04301 (monotone worse with gamma).  **Verdict: negative / falsified.**

## H3 / E3 - RCP: ridge-continuity prior

* **Layers / transform:** top 4 % of the E2 surface, 1-px closing, 8-connected components weighted by clip(bbox diagonal / 12 px, 0.35, 1).
* **Why:** faults are laterally continuous; isolated short ridge fragments are noise (volcanic cones, cultural features).
* **Mimic:** pipelines/roads/flight-line seams are also long and straight - the prior does not separate them from faults.
* **Result (far):** 0.05297 [0.03929, 0.06715]; difference vs CCR -0.00076 [-0.00214, +0.00072] (null); vs FBMT -0.00878 [-0.01276, -0.00482].
  **Verdict: null / dropped.**

## H4 - NDVI-SL: spring and phreatophyte lineaments (not run)

* **Layers:** Sentinel-2 L2A reflectance (10 m; NDVI/NDWI dry-season minimum and its long-wavelength-detrended residual) and NAIP where available.
* **Signature:** fault gouge and offset aquifers pond groundwater, so shallow-rooted phreatophyte stripes and spring lines align with faults even
  when the scarp is buried or eroded; transform = oriented line-integrals (>= 1.5 km) of the detrended dry-season NDVI minimum.
* **Why it could add faults missing from the catalogue:** it is a hydrological, not a topographic or potential-field, signature, and no optical or
  vegetation layer exists anywhere in this repository or in the 215-raster registry's documented inputs.
* **Mimic:** irrigation canals and pivot edges, riparian corridors, roads/pipelines/fences, playa-margin moisture (mask with land-cover and OSM).
* **Free official source and obtainability:** ESA Copernicus Sentinel-2 L2A Cloud-Optimized GeoTIFFs on the AWS Open Data registry (no AWS account:
  `aws s3 ls --no-sign-request s3://sentinel-cogs/`, STAC at <https://earth-search.aws.element84.com/v1>), license "free, full and open"
  <https://registry.opendata.aws/sentinel-2-l2a-cogs/> (**verified to exist this session**).  **Not obtainable from this sandbox** (host allow-list
  excludes `*.amazonaws.com`); needs outbound access to the `sentinel-cogs` bucket and the Earth-Search API.
* **Expected cost:** high (about 100 GB of scenes for a multi-season minimum composite at 10 m, or ~1 GB at 100 m after server-side reduction).

## H5 - SDT-gate: stress-resolved strike gating (carried over from the 10-23 list)

* **Layers:** USGS slip- and dilation-tendency release for Great Basin Quaternary faults (Siler 2022, doi:10.5066/P9YL58W6, ScienceBase item
  6296974dd34ec53d276bb33d, **verified to exist**: 34 MB shapefile zip, public) + the E1 ridge strike field.
* **Caveat discovered while verifying the source:** that release is computed **for faults already in the Quaternary database** - i.e. the
  catalogue itself - so it carries stress and geometry information about *known* faults.  Using it on *new* faults requires fitting a regional
  S_Hmax field from the attributes first; the gain is then limited to re-weighting strikes.  Ranked last for that reason.
* **Obtainability:** public download; ScienceBase host is not on this sandbox's allow-list.

---

## Result against the pre-registered rules

| Rule | Outcome |
|---|---|
| E1 keep: far DTI(FBMT) > far DTI(BASE) with paired CI excluding 0 | **No** (-0.00977, CI includes 0; overall significantly worse) |
| E2 keep: far DTI(CCR) > far DTI(FBMT) with CI excluding 0 | **No** (-0.00803, CI excludes 0 in the wrong direction) |
| E3 keep: far DTI(RCP) > predecessor with CI excluding 0 | **No** (-0.00076, CI includes 0) |
| Beat stored H88-ADHR (overall 0.18789 or far 0.11478) | **No** (best arm BASE: 0.10725 / 0.07152) |
| Beat stored CGO-88 (overall 0.09042 / far 0.07683) | overall yes (+0.0168), far no (-0.0053, within CI) |
| Canary <= 0.90 | **Pass** (0.5948) |

**Falsification statement.**  On the instrument available here, none of "train where you will be tested", "boost where evidence exceeds mapped
density" or "down-weight short ridge fragments" improves recovery of withheld faults, including those > 1 km from the visible catalogue.
The instrument cannot see the H33-class advantage (section 4 of `research/h33-forensics-20261024.md`), so these negatives are evidence about
*this* instrument's transfer to catalogue faults, not proof about the hidden labels.

## Carry-forward list (ranked; none was run, the 3-experiment budget is spent)

1. **N1 - matched-domain FBMT:** allocate only where the model was trained (d > 8 px).  Cheapest fix of the one design flaw found.
2. **N2 - out-of-fold surfaces everywhere.**  Production attempt 1 (fit on the full catalogue, predict the same pixels) put only 6.4 % of dots more
   than 25 px from the catalogue versus 41 % out-of-fold - an *in-sample memorisation* artefact (IR-88-61).  Any raster built that way, **including
   the earlier ADHR production file (4.2 %)**, does not have the profile its holdout number describes.
3. **N3 - ADHR-class surface + far-basin objective:** the only surface family that scored above the control on the holdout, re-emitted out-of-fold.
4. **N4 - NDVI-SL** (H4), the one genuinely new information source; needs data access.
5. **N5 - SDT-gate** (H5).
