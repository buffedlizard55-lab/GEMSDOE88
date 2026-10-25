# Source-reviewed research queue — 2026-10-25, session 693b10af

**Conditional proposals, not experiments or submission permission.** The request again supplies no single-method paragraph. This session is a read-only software/evidence review; no geological lane was run. The conditional first choice below is H88-SPR, but the unchanged shared `DUPLICATE_STOP` takes precedence over every proposed experiment.

## Correct the stale first choice before spending compute

The previous top-of-site recommendation called magnetic-marker restoration untested. That is no longer true in this checkout: `src/gems88/mmrx.py` and its negative run card are present. MTAS and MFS also have implementations and historical negative execution records. They cannot be advertised as fresh mechanisms. Their historical departures from the duplicate-stop protocol are not authority to rerun them. See the code-bound [JSON queue](https://buffedlizard55-lab.github.io/GEMSDOE88/data/hypothesis_queue.json) and `python scripts/audit_research_state.py`.

“Untried” below means the specific contrast was not found implemented in the reviewed model modules/candidate entrypoints, **not** proof of worldwide novelty or uniqueness against every fleet raster. Several are sharpened, still-unrun proposals from earlier reviews; they are not relabeled as newly invented ideas. The source fingerprint detects code drift, not semantic novelty.

## Ranking by expected scientific benefit versus implementation cost

Expected potential is ordinal judgment with substantial uncertainty, **never a numerical DTI projection**. Every required raster is already in the shared SHA-pinned owner-mirror restoration tier, and was restored in this session. No candidate depends on a newly fetched external dataset; primary-source permissions still need authoritative confirmation before public redistribution. 100 m caches are not raw 1 m LiDAR profiles and cannot establish sub-pixel throws.

### 1. H88-SPR — Repeated scarp-profile restoration against a drainage/shoreline null

- **Exact layers:** `data/training_features.tif` bands 12, 19: det_elev; det_elev_slope; `data/external/topo_10m_derived_100m_u8.tif` bands 8, 9: hs_lineament; dem_mean at 100 m, encoded by its pinned manifest; `data/external/lidar_scarp_features_u8.tif` bands 3, 10, 11, 12: step_max; coh100; strike; valid; `data/external/dem10_chi_100m_u8.tif` bands 1, 4: chan_n; valid_n.
- **Physical signature:** On independent along-strike swaths, fit smooth-landform-plus-signed-step versus no-step profiles; score restoration on held-out profile samples and require a repeatable step away from channel corridors. Use the manifest to decode topographic indices and mask invalid/saturated values.
- **Why a missing catalogue fault:** A weak or cover-softened offset repeated across an otherwise smooth piedmont could escape catalogue mapping while retaining a resolvable profile signal. No mapped trace seeds the surface. Sub-pixel scarps are not claimed detectable from this 100 m cache.
- **Named non-fault mimic:** Fluvial terrace risers and constant-elevation pluvial shoreline benches
- **Contrast with implemented work:** LSC/TDKL/VESS/SHORE use scarp responses, polarity, knickpoint or shoreline context; they do not fit a cross-validated landform-restoration likelihood. MMRX restores magnetic texture, not landform profiles.
- **Expected potential:** First relative priority; moderate but highly uncertain; no numerical DTI projection
- **Implementation cost:** Medium; cached inputs only
- **Falsification:** Reject if sign/step evidence disappears across adjacent withheld swaths, depends on drainage pixels, or is equally explained by contour-following shoreline/terrace controls.

### 2. H88-AWA — Terrain-matched radiometric alteration-width asymmetry

- **Exact layers:** `data/external/geodawn_rad_u8.tif` bands 1, 2, 3: K; Th; U quantized indices, not calibrated concentration ratios; `data/training_features.tif` bands 2, 15, 19: rtp; depth_to_base_surf; det_elev_slope.
- **Physical signature:** Fit relative cross-strike decay widths of within-band, terrain-matched K/Th/U residual profiles on two flanks and test repeated width asymmetry alongside a local RTP depression. Quantized code values must not be divided and called physical K/Th concentrations.
- **Why a missing catalogue fault:** A covered permeable structure might alter one wall more broadly than the other despite no discrete scarp. This conditional spatial pattern does not identify an alteration mineral or prove fluid temperature.
- **Named non-fault mimic:** Differential weathering of adjacent rock units and K-rich transported alluvium
- **Contrast with implemented work:** KTH/MVRD compare enrichment/redox levels or edges; this tests relative fitted decay width, not another radiometric high or a magnetic marker shift.
- **Expected potential:** Second priority; low-to-moderate, uncertain; no numerical DTI projection
- **Implementation cost:** Medium; quantization and background fitting need care
- **Falsification:** Reject if a parent-material/terrain-matched null reproduces the width asymmetry or the apparent signal is quantization/saturation dependent.

### 3. H88-GTD — Potential-field source dimensionality versus compact-body null

- **Exact layers:** `data/training_features.tif` bands 2, 13, 15: rtp; iso_grav_anom; depth_to_base_surf.
- **Physical signature:** Construct a regularized harmonic potential-field gradient tensor from gravity and assess its eigenvalue/determinant dimensionality across scales; compare elongated quasi-2D source edges with compact-body synthetic nulls, using magnetics as an independent contextual check. Freeze derivative sign conventions and padding before fitting.
- **Why a missing catalogue fault:** An elongated buried density discontinuity can survive cover without a surface rupture; testing source geometry may reject compact plutons favored by simple edge magnitude.
- **Named non-fault mimic:** Unfaulted two-dimensional dikes and stratigraphic pinch-out contacts
- **Contrast with implemented work:** HGVC/BPWD/VESS use Hessian ridge/vesselness of response images; MMRX tests shifted texture, MFS tests Gaussian gradient decay. This proposal uses invariants of a reconstructed harmonic field tensor, not the ridge Hessian.
- **Expected potential:** Third priority; low-to-moderate, uncertain; no numerical DTI projection
- **Implementation cost:** Low-to-medium, but an ill-conditioned inverse problem
- **Falsification:** Reject if continuation, taper or azimuth changes reverse the classification, or unfaulted dike/contact controls are indistinguishable from the target.

### 4. H88-CBC — Conductive basin-breach connectivity against a paleochannel null

- **Exact layers:** `data/training_features.tif` bands 12, 13, 15, 17: det_elev; iso_grav_anom; depth_to_base_surf; cond_surf; `data/external/dem10_chi_100m_u8.tif` bands 1, 4: chan_n; valid_n.
- **Physical signature:** Compare narrow conductivity connectivity across independently inferred basin-boundary saddles with a smooth basin-fill null; require cross-boundary gravity discontinuity and test a terrain-aligned drainage explanation. Work on relative model fields, not a claim of resolved metre-scale conduits.
- **Why a missing catalogue fault:** A buried cross-basin structural connection may have no mapped surface trace. The target is a candidate fault-related pathway, never a directly detected geothermal vent.
- **Named non-fault mimic:** Unfaulted permeable alluvial paleochannels and saline groundwater plumes
- **Contrast with implemented work:** CTRA/DHTC use conductivity curvature and thermal conjunctions; this tests topology-preserving cross-basin connectivity against an explicit drainage null.
- **Expected potential:** Fourth priority; low, uncertain; no numerical DTI projection
- **Implementation cost:** Medium-high; coarse-field resolution is a major limitation
- **Falsification:** Reject if basin-fill smoothness or drainage connectivity explains the bridge equally well, or no boundary-normal gravity change is present.

## Conditional validation plan for H88-SPR (not executed)

1. First resolve the universal registry-support contradiction in the shared contract explicitly. This session authorizes **no** policy exception; neither a human inspection, a metadata edit, a dense-prior exemption nor a renamed TIFF can bypass it.
2. Freeze one method, parameters, null controls and a maximum of three experiments/two hours before constructing features. Reuse the existing cached stack and `vendor/gems57/holdout.py`, `evaluate_holdout.py`, and `submission_writer.py`; no private fork.
3. Withhold whole fault components with the shared buffer. Derive all catalogue-dependent features only from visible faults, mask those visible pixels exactly, and train background/normalization choices on training blocks only. Do not mask hidden truth using the full catalogue.
4. Test every feature alone on the holdout; symmetric AUC above 0.90 is a stop pending a demonstrated explanation. Include signed-step versus no-step, profile-scramble and drainage/shoreline nulls. A low canary AUC alone is not proof against leakage.
5. Recompute BPWD on identical folds, truth counts, masks, emitter and prediction budget. The historical reference is **HOLDOUT-DTI 0.2059906799, 95% CI [0.1881052342, 0.2233436382]**, evaluator `gems57-pooled-hide-v2`, **22,893 withheld positive pixels**; it is not a new score, a fair baseline without reproduction, or an organizer receipt. Require a positive paired physical-block improvement, including predeclared far/blind stress tests. Many previous lanes reused these folds; preserve an untouched spatial audit partition for portfolio selection.
6. Check rank correlation and literal overlap against the entire in-scope registry on the surface before placement and on final dots. No conditional scientific improvement overrides a failed uniqueness gate.
7. Independently reopen the saved TIFF and one-TIFF ZIP, check all-finite [0,1], one band, exact sample CRS/shape/transform and footprint, then use the **separate automated slot selector**. Current timing/quota and organizer receipts are unavailable here. No competition slot is spent by this plan.

## Source boundary

- [Official DrivenData reference README at the inspected commit](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md): freshly retrieved via GitHub; CPU and GPU options are explicit. It does not certify any proposed geological signature.
- [Competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [official GeoDAWN landing page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [GDR 1391](https://gdr.openei.org/submissions/1391), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program): authoritative review targets **not retrieved in this session**, because their hosts are outside the allowed network. No new primary geological data source is presented as obtainable here.
- Pinned local band descriptions, restoration manifests, model code and historical run cards establish file identity and the implementation comparison, not organizer authentication or geological truth. Quantized radiometric indices are not calibrated K/Th/U concentrations; missing/saturated cells must not become apparent alteration widths.

**Outcome:** zero features newly constructed for these proposals, zero canaries or holdout fits, zero new TIFFs, zero weekly slots. The requested new unique competition artifact and a demonstrated improvement beyond H33 remain unmet.
