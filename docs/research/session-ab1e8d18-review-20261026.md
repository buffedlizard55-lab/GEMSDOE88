# GEMSDOE88 session review — 2026-10-26

**Branch:** `arena/ab1e8d18-gemsdoe88`  
**Decision:** **DUPLICATE_STOP — no new GeoTIFF generated; do not submit an existing research file.**  
**Experiments:** 0/3 · **submission slots used:** 0 · **organizer receipts verified:** 0.

This is a dated forensic review, not a new scientific result or upload authorization. It follows the request's fail-closed parallel-run protocol. The local pinned registry witness was restored and the shared generation guard was run before feature construction. Because the witness covers every allowed pixel, the guard returned exit code 2 (`DUPLICATE_STOP`). Per the protocol, no features were constructed, no model was fitted, no placement was attempted, and no TIFF was written.

## Executive answer

The supplied GEMSDOE32 H33 figure (`0.2778`) is a **USER-REPORTED CLAIM**, not an `ORGANIZER-CONFIRMED` result: there is no portal receipt in this checkout. The archived analysis in [`h33-forensics-and-xgce-phd-analysis.md`](h33-forensics-and-xgce-phd-analysis.md) supports a plausible mechanism, not proof of causation: H33 is a sparse, binary, collar-pruned subset of the D2.8 lineage. Relative to the supplied D2.8 figure (`0.2600`, also a **USER-REPORTED CLAIM**), the H33 claim is consistent with removing near-catalogue flank predictions that may incur false-positive weight while retaining spatially distal predictions. This is a plausible explanation under an asymmetric distance-weighted Tversky objective; it does not establish that sparsity caused a live score increase or that hidden geothermal faults are preferentially distal.

Beating the claimed H33 result, or the prompt's conflicting public-leaderboard figures `0.3195` and `0.4413`, **cannot be estimated defensibly from this checkout**. Those are user-supplied historical figures without receipts/current portal access. A spatial holdout result is not a public leaderboard score and should not be converted into one. For the nine sites, the score column below is therefore explicitly the reported historical claim, not a forecast.

## Nine-site executive summary

Scores in this table are all **USER-REPORTED CLAIMS** from the recorded prompt and prior site audit; none is organizer-confirmed here. “Unique: no” means not cleared as unique under this project's literal all-registry rule (including the dense witness), not that every pair of the nine files is byte-identical. The recorded pixel relationships are called out separately.

| Site | Highest listed historical submission | Reported score | Unique under this protocol? | Audited relationship / decision |
|---|---|---:|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-…-989f59505db1-nan` | **USER-REPORTED CLAIM: 0.2477** | **No — blocked** | D1.5 H19-5 thinning lineage; shares the D1.5 parent set with the GEMSDOE27 gap-closure variant. Research download only. |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-…-e56ea318af89-nan` | **USER-REPORTED CLAIM: 0.2600** | **No — blocked** | D2.8 thinning lineage; exact positive-pixel duplicate of the GEMSDOE30 D28 artifact. Research download only. |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-…-5512495c6bd1-nan` | **USER-REPORTED CLAIM: 0.2449** | **No — blocked** | D1.5 plus 1,259 recorded T-v2 gap links; not an exact copy of its parent, but fails the all-registry uniqueness rule. Research download only. |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-…-b531dae0a36f-nan` | **USER-REPORTED CLAIM: 0.2710** | **No — blocked** | Historical headline is near the H33-2-B2 subset lineage; separate `h27-4-r1-solo-d2-8` is the same positive-pixel set as GEMSDOE31's listed `h27-4-solo-d28`. Research download only. |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-…-91eae1ca` | **USER-REPORTED CLAIM: 0.2600** | **No — blocked** | Exact positive-pixel duplicate of GEMSDOE25 D2.8. Research download only. |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28-…-8acb75e1-nan` | **USER-REPORTED CLAIM: 0.2708** | **No — blocked** | Exact positive-pixel subset also listed on GEMSDOE28. Research download only. |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **USER-REPORTED CLAIM: 0.2778** | **No — blocked** | Highest claim among these nine; H33-2-B2 belongs to the same nested pruning family and is included in GEMSDOE36's listed superset. Research download only. |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-…-cb490425926e` | **USER-REPORTED CLAIM: 0.2632** | **No — blocked** | Recorded high overlap with H19-5; not established as an exact copy of a focus-site champion. Research download only. |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854-…-9b9ea4e6-zeros` | **USER-REPORTED CLAIM: 0.2750** | **No — blocked** | Recorded as H33-2-B2 plus 1,200 PINN dots; a strict superset, not a distinct cleared candidate. Research download only. |

Machine audit details and later site-head candidates: [9-site JSON](../data/focus_sites_20261026.json), [latest-candidate JSON](../data/focus_latest_20261026b.json), and [CSV](../data/focus_sites_20261026.csv). The audits report 0/9 historical champions cleared and 0/9 latest candidates cleared under this project's binding rule. These local measurements are not organizer scores.

**Download/submission decision:** existing files marked `DO-NOT-SUBMIT` may be downloaded for research according to the local format audit. There is **no new TIF that is OK to download and submit**. Do not submit any archived TIFF based on this review.

## Preregistered hypotheses available if the gate is ever legitimately revised

The following three proposals are the only still-untested proposals in the current local queue. They are ranked qualitatively; **no numerical DTI improvement is projected**. All use already named cached layers, so the queue does not require a new external dataset. However, the local queue says owner-mirror pin provenance is not authenticated against current organizer downloads; this is not a fresh official-source/license verification.

| Rank | Hypothesis / layers | Physical signature and why it could find a missing fault | Named non-fault mimic | Difference from implemented work | Expected potential / cost |
|---:|---|---|---|---|---|
| 1 | **H88-SPR — repeated scarp-profile restoration**. `training_features.tif` bands 12/19 (`det_elev`, slope); pinned 10 m DEM derivatives bands 8/9; LiDAR scarp features bands 3/10/11/12; DEM chi bands 1/4. | Fit smooth-landform-plus-signed-step versus no-step cross-channel profiles in independent swaths; require repeatable offset away from channel corridors. A weak or cover-softened displacement can remain detectable in profiles without a mapped trace. No claim is made for sub-pixel features at 100 m. | Fluvial terrace risers and constant-elevation pluvial shoreline benches. | Existing LSC/TDKL/VESS/SHORE methods use scarp, polarity, knickpoint, or shoreline signals; this would test cross-validated landform-restoration likelihood against matched geomorphic controls. | Relative priority 1; moderate potential, high uncertainty; medium cost. |
| 2 | **H88-AWA — terrain-matched radiometric alteration-width asymmetry**. GeoDAWN radiometric bands 1–3 (quantized K/Th/U indices); training features bands 2/15/19 (`rtp`, depth-to-basement surface, slope). | Fit relative cross-strike decay widths of terrain-matched K/Th/U residuals on both flanks, alongside local RTP depression. A covered structure might produce asymmetric alteration without a discrete scarp. Quantized indices must not be treated as calibrated concentrations or divided into physical K/Th ratios. | Differential weathering across lithologies and K-rich transported alluvium. | KTH/MVRD test enrichment/redox or edges; this proposal tests a fitted decay-width contrast under a terrain-matched null. | Relative priority 2; low-to-moderate potential, high uncertainty; medium cost. |
| 3 | **H88-CBC — conductive basin-breach connectivity**. Training features bands 12/13/15/17 (`det_elev`, isostatic gravity, depth-to-basement, surface conductivity); DEM chi bands 1/4. | Test narrow conductivity connectivity across independently inferred basin-boundary saddles, requiring a boundary-normal gravity change and comparison with a smooth basin-fill model. It targets a buried cross-basin pathway, not a direct vent detection. | Unfaulted permeable alluvial paleochannels and saline groundwater plumes. | CTRA/DHTC use conductivity curvature or thermal conjunction; CBC would test connectivity topology against an explicit drainage null. | Relative priority 3; low potential, high uncertainty; medium-high cost because the fields are coarse. |

The exact current queue is in the published [`hypothesis_queue.json`](../data/hypothesis_queue.json). These are proposals, not results. The task's prompt did not include a distinct, single-method paragraph that resolves which proposal is the active lane. That ambiguity does not change this run's stop: no proposal was built or evaluated after the preflight stop.

## Gate evidence and tests

- **REGISTRY-MEASUREMENT:** `scripts/generation_guard.py` returned `DUPLICATE_STOP` (exit code 2) after restoring the pinned validation-tier registry witness `data/registry/dense_17gemdoe.tif` (SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`). It reports 5,106,385 allowed pixels, zero uncovered allowed pixels, coverage 1.0, versus the required maximum 3-pixel overlap of 0.70. Thus every nonempty allowed dot set would have at least 1.0 forward overlap under the recorded support rule. No candidate surface or final dots exist in this session; a candidate correlation was not measured.
- The full R0 startup verifier could not run because the validation-tier restore does not include all R0 `data/bridge` and training inputs. This does not weaken the separate guard's pinned-witness stop. No full training stack was fetched.
- **HOLDOUT-DTI:** not run in this session; evaluator `gems57-pooled-hide-v2` was not invoked; withheld-positive count and 95% CI are not applicable. Historical holdout values are not relabeled as this session's result.
- **Format validator:** not run on a new TIF because none was written. Existing historical artifacts may pass format checks; those checks do not clear duplicate or competition-slot gates.
- Verified locally: `pytest -q` → 932 passed, 23 skipped; `scripts/render_decision.py --check`, normal and optimized site guards, `scripts/audit_research_state.py`, `scripts/audit_downloads.py --check`, and `scripts/validate_current.py` passed. The current artifact validator continues to report a negative, research-only decision.
- **Score evidence:** no organizer receipt. The latest competition leaderboard, submission limit, deadline, and account status were not verified here. The prompt's `0.3195` and `0.4413` are contradictory historical claims; neither is adopted as current fact.

## Sources and verification boundary

- [DrivenData competition overview/rules](https://www.drivendata.org/competitions/306/competition-doe-gems/) and [problem description/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): user-provided official links, but not retrieved in this session (the sandbox has no allowed outbound access to `drivendata.org`; competition data is login-gated per existing project records).
- [Official DrivenData reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution): official reference link supplied in the request; no new competition data or score was obtained from it in this session.
- [USGS GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and): official link supplied by the user; not freshly retrieved here because `usgs.gov` is outside the available outbound-host allowlist.
- [DOE OpenEI GDR submission 1391](https://gdr.openei.org/submissions/1391): existing project provenance link; not re-verified for licensing or current access in this session.

Local source files and prior audit records are cited for reproducibility, but are not substitutes for fresh organizer receipts, current official source retrieval, or confirmed redistribution rights.

## Three-pass review

1. **Pass 1 — inspect and implement:** read the repository's start contract, prompt, README, focus-site machine records, and hypothesis queue; restored only the validation-tier SHA-pinned inputs; reran the shared generation guard. Implemented this report and negative run card only. No builder or writer was called.
2. **Pass 2 — bug/assumption review:** confirmed the guard's pre-placement universal-coverage proof and exit code 2; distinguished exact sibling duplicates from subset/superset or merely high-overlap relations; kept all score figures as claims and did not infer a projected leaderboard score. Reverted audit tools' transient rewrites of historical evidence files after checking their output.
3. **Pass 3 — requirement verification:** rechecked the nine-site summary, current focus audit, no-new-TIF outcome, [0,1]/CRS format requirement, protocol budget, and limitations. All automated checks listed above passed; no new scientific score or submission clearance is claimed.

## Next work, conditional on an authorized policy change

1. Resolve the protocol's universal-dense-witness contradiction through the separate policy/selector governance process; this review does not alter the threshold, exclude the witness, or choose a submission slot.
2. Restore and independently verify every required pinned feature input and licensing/source provenance. Then rerun preflight before any candidate feature construction.
3. Only if the shared guard allows work, preregister one hypothesis and run buffered whole-segment hide-and-recover using the shared `evaluate_holdout.py`, visible-only catalogue features, exact visible-fault masking, pooled DTI (`alpha=0.2`, `beta=0.8`, 300 m triangular kernel), and per-feature leakage canaries. Compare on identical folds against the incumbent. Stop at 3 experiments or 2 hours.
4. Require all-registry surface correlation and final-dot overlap audits, exact sample CRS/shape/transform, finite in-footprint `[0,1]` values, and an independent selector decision before any real slot. Only a portal receipt can establish an organizer score.
