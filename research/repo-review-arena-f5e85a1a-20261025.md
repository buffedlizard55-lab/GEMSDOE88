# Independent repository review — Arena session `f5e85a1a` (2026-10-25)

## Executive result

**Decision: NEGATIVE / DUPLICATE_STOP. No new TIF was produced, and none is approved for competition submission.** This is deliberate protocol compliance, not a claim that the unique-submission requirement was met. The existing download promoted by the site is prominently marked `DO-NOT-SUBMIT` and is for research only.

A pinned registry raster from `17GEMSDOE` has positive support on **all 5,106,385 allowed pixels** in the competition footprint. Under the prompt's literal forward 3-pixel overlap rule, every nonempty candidate restricted to allowed pixels therefore has **1.0 overlap**, above the `0.70` maximum. The shared preflight recalculated this from the SHA-pinned raster before any feature construction or placement and returned `DUPLICATE_STOP` (expected exit code 2). No feature, fold, leakage canary, candidate score, or new raster was made in this review.

**The user’s unique-TIFF requirement and the literal registry gate are incompatible on these pinned inputs.** I did not evade the stop by excluding the dense raster, renaming an artifact, changing the threshold, or generating a zero raster. A policy change would need to be explicit and shared—not a private exception in this lane.

## Repository state and checks

- Read `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md`, `AGENTS.md`, and the current machine review before work. The complete user prompt is already recorded in README and `USER_PROMPT_20261025.md`.
- Restored SHA-pinned owner-mirror inputs, including the 19-band feature stack; `scripts/prepare_data.py` verified the hashes, grid (`EPSG:32611`, 3,730 × 3,292, 100 m cells; transform `[100, 0, 243350, 0, -100, 4508550]`), and loaded nine shared robust-z feature planes. These bytes are **not** authenticated downloads from the logged-in organizer page.
- Automated tests: **630 passed, 23 skipped** (`pytest -q`; 61 Rasterio pending-deprecation warnings). This establishes software regression status only—not scientific performance or organizer acceptance.
- `scripts/audit_downloads.py --check`: **43/43** current TIFF/ZIP pairs pass the local research-format audit; **0/43** are eligible under the binding uniqueness rule; no exact decoded-duplicate groups were found. Format acceptance is not score evidence.
- `scripts/render_decision.py --check`, `scripts/check_site.py`, and `python -O scripts/check_site.py` passed. The executive guide and the primary site both preserve the `DO NOT SUBMIT` status.
- `scripts/review_repo_20261025.py` returned success; its `--require-submit` mode and `scripts/preflight_mtas88.py --gate-generation` both returned the expected fail-closed exit code 2. `scripts/review_submission_status.py` and `scripts/audit_protocol_integrity.py` returned negative review results.
- No geological experiment, holdout, new candidate, new submission TIFF, portal upload, or weekly slot was used.

### Irregularity found in a historical audit command

`python scripts/audit_session_start.py` is dated for the 2026-10-23 PRUNE review. With the current ledger it printed `STOP_NO_NEW_VARIANTS` but exited 1 because its historical uniqueness assertion (`unique_primary_and_fallback_hashes`) is false against the expanded ledger. It also rewrites an old dated evidence file with current checkout metadata. That command is not in the current CI workflow, and its failure is **not** a fresh scientific-gate failure. The output was restored after inspection; no stale audit report was retained as current evidence. Do not use this old command as the current submission gate.

## H33-2-B2: what the repository can and cannot explain

The **0.2778** figure is a user/owner-reported claim, **not** `ORGANIZER-CONFIRMED` and not a result from the current shared hide-and-recover evaluator. The repository has no DrivenData receipt for it. The project also records a public leaderboard snapshot of **0.4413** on 2026-10-25; that is a separate observed-public value, not an H33 result and not a verified live/current account view for this audit. The prompt also cites **0.3195** as a maximum, inconsistent with those other numbers; none should be merged into one score.

The pinned H33 raster's measured **geometry** supports a cautious explanation for why its reported score could exceed denser siblings:

1. Its build record identifies H33-2-B2 as a subtraction from the 0.2708 H27-4 base: delete dots at or within 2 pixels of the known fault catalogue; the H33 support is a subset, with no new dots. The independent lineage recheck reports that all 6,436 D2.8-to-H33 deleted dots were within 2 pixels of catalogue traces.
2. H33 contains 37,654 dots, has a measured median catalogue distance of about 19.65 pixels, and its minimum nearest-neighbour spacing is about 2.83 pixels. The earlier H19/D2.8 lineage had many more closely packed dots. Under a distance-weighted Tversky score with α = 0.2 and β = 0.8, reducing redundant dots can reduce weighted false-positive mass while preserving spatial coverage; moving support away from already mapped traces is also consistent with the objective of finding missing faults.
3. Those mechanisms are **plausible explanations, not causal proof**. The hidden positive locations are unavailable here, lineage tuning included owner-reported/live-feedback results, the withheld-catalogue proxy is not the organizer test set, and the artifact's proper on-leaderboard score is not evidenced by a receipt. The local holdout record for a fixed raster derived with the full catalogue is not a fair estimate of unseen-fault generalization and is not compared here.

The defensible answer to “can we beat 0.2778?” is **not demonstrated**. No scientifically valid projection from the local evidence can establish a higher leaderboard score; only an organizer result receipt can do that. The separate public top value in the repository's dated snapshot is not a target estimate for this model.

## Candidate hypotheses ranked before implementation

These are the five previously preregistered ideas in `docs/data/repo_review_20261025.json`. Expected benefit is a **qualitative research priority**, not projected DTI. Every candidate remains **UNTESTED**. All use the restored owner-mirror stack; none requires new external data. The duplicate preflight prevents testing any of them now.

| Rank | Candidate; layers | Physical signature and why it could find a missing fault | Named non-fault mimic | Difference from implemented lanes | Benefit / cost |
|---:|---|---|---|---|---|
| 1 | **H88-MTAS** — RTP and gravity gradients at 200 m and 800 m, basement depth, detrended slope, transtension | A scale-dependent gravity-to-magnetic admittance residual: a short-scale gravity edge persists while the magnetic edge is smoothed/demagnetized beneath cover. A buried basement discontinuity need not have a surface scarp or catalogue trace. | Unfaulted intrusive/volcanic density contact; flight-line leveling seam | Existing MRR is magnetic residualization, PHASE tests angular discordance, and GTHC uses upward-continuation/amplitude logic; none is the same paired cross-scale residual. | Highest qualitative potential; low–medium cost |
| 2 | **H88-PRAN** — K/Th, detrended slope, profile curvature, basement depth | Terrain-bin-matched K:Th residual with along-strike coherence, rather than a global radiometric high; targets alteration/soil signatures not dependent on mapped-fault geometry. | K-rich transported alluvium, parent-rock boundaries, soil-moisture effects | MVRD combines radiometry with scarp evidence; this proposes a terrain-matched conditional null. | Medium; low–medium cost |
| 3 | **H88-FARC** — chi-step and normalized steepness jumps, terrain lineaments, LiDAR scarp coherence, slope | Repeated signed drainage offsets across independent channels, normalized by catchment and stream order; replication may reveal a weak blind rupture that no single scarp mapper marked. | Lithologic knickzones, drainage capture, base-level/climate change | QTSK/TDKL rank individual knickwaves or scarp polarity; FARC requires cross-catchment replication and a channel-matched null. | Medium; medium cost |
| 4 | **H88-TCONS** — shallow temperature anomaly, well-temperature anomaly, conductivity edge, basement depth | Residual local temperature after conditioning on conductance and basin depth; a focused thermal/fluid pathway may indicate a blind permeable fault rather than broad conductive fill. | Lake brine, groundwater circulation, unfractured permeable lithology | DHTC combines deep heat/MT and basement structure; TCONS is a conditional residual with head-matched negative controls. | Medium; medium cost |
| 5 | **H88-FLAC** — RTP/gravity gradients, conductivity edge, shear and dilation strain | Cross-sensor edge persistence with an explicit flight-line-direction artifact veto; independent sensors should corroborate a structural edge rather than a processing seam. | Tie-line leveling, gridding artifacts, broad acquisition-aligned lithologic contacts | MGC/XGCE compare cross-field edge geometry but do not apply this preregistered directional null. | Low–medium; low cost |

No top hypothesis was run on holdout because the binding registry stop fires before feature construction. If a shared, explicitly authorized protocol later makes the experiment admissible, it must use the shared cached stack, shared `vendor/gems57` holdout/evaluator/writer, buffered whole-segment hide-and-recover, visible-only catalogue-derived features, pixel-exact visible-catalogue masking, and individual feature leakage canaries. Promotion remains separate from model testing and is not inferred from a local format pass.

## Source review and evidence boundaries

- [Official DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [competition data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/): organizer references. This sandbox did not authenticate to the data tab during this review.
- [Official DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b): immutable official repository reference. Local feature/data mirrors were SHA-checked, but are not proof of organizer provenance.
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR INGENIOUS record](https://gdr.openei.org/submissions/1391), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [EPSG:32611](https://epsg.io/32611), and [NLR competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf): official manual-review links recorded in the source ledger. They were not fetched from those hosts during this review; no current access, terms, leaderboard, weekly quota, deadline, or receipt is claimed here.
- [Immutable GEMSDOE32 owner build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/098f3af9508a135277ef4d1bf2266e2e448be814/registry/submission_build.json): evidence for the H33 build lineage only; it is owner-authored and is not an organizer receipt.

## Three-pass review

1. **Pass 1 — requirements and artifacts:** reread the full recorded prompt and operating contract; restored/verified inputs; inspected the H33 build record, pinned raster lineage and current preflight; ranked five candidates before any implementation.
2. **Pass 2 — bug, leakage and edge-case review:** confirmed the dense witness saturates the complete allowed support; did not treat historic full-catalogue masking as a fair validation; checked download labels, format gates, source status and the dated audit-script irregularity. No private evaluator, writer, threshold exception, slot selection or score projection was introduced.
3. **Pass 3 — end-to-end recheck:** all 630 tests passed (23 skipped); site/download checks passed in normal and optimized Python; preflight and `--require-submit` modes refused clearance as expected. New TIF remains absent; the unique-submission requirement remains unmet and is explicitly reported as such.

## Next useful work (blocked, not performed)

1. Resolve the literal overlap-rule conflict through an explicit, shared policy decision without hiding an in-scope registry raster. Recompute the uniqueness registry under that approved contract before permitting any candidate feature build.
2. Only then preregister one lane, test the selected feature alone for leakage, run matched-fold baseline comparisons and null controls with the shared evaluator, then check surface correlation before placement and all-raster overlap after placement.
3. Authenticate competition data/provenance and check current rules, quota, deadlines and submission receipts in an authorized environment. Do not describe owner mirrors or local validation as organizer confirmation.
4. If the older `audit_session_start.py` is retained as a reusable tool, isolate its dated historical checks and stop it from overwriting a stale-dated evidence file; it is not needed for the current CI gate.
