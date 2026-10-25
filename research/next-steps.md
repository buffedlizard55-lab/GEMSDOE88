## Latest handoff — `H88-HGVC` Hydrothermal Conduit Suite (`2026-10-24`, `IR-88-116..117`)

Read `PROMPT.md`, `README.md`, `registry/hgvc88_run_card.json`, `registry/hgvc88_gate_v3.json`, and `research/candidate-hypotheses-20261024-hgvc88.md` first.
- **Completed this session:** `H88-HGVC` (`20` zero-catalogue hydrothermal geochemical cooling-disequilibrium, tufa-decontaminated opaline sinter, 1m–2m vertical probe gradient, perched smectite clay-cap residual, and cover-decoupled basement conduit channels) achieved the repository's highest 8-fold holdout score (**`HOLDOUT-DTI = 0.202947 [0.185869, 0.219790]`**, `8/8` folds won, Far `0.132800`, Blind `0.078959`, `gems57-pooled-hide-v2`, `n = 22,893`) while clearing `87/87` leakage canaries (`<= 0.770155`), H33 basin fingerprint (`37,654` dots, `share_gt25 = 42.90% >= 35%`, `share_le2 = 0.0%`), local LZW `[0, 1]` sample parity, and **`326`-raster like-for-like uniqueness (`0` blockers, `max 3-px overlap = 0.607426 <= 0.70`, `|rho| = 0.208144 <= 0.90`)**.
- **Automated decision:** **`DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO — DO NOT SUBMIT`** (`ok_to_submit = false`, `0` weekly slots spent, `ORGANIZER-CONFIRMED: none`), held fail-closed solely under the binding literal `17GEMSDOE` space-filling witness (`1.0000 > 0.70`) and the separate human weekly-slot selector step.
- **Concrete next steps & blockers for the next session / human owner:**
  1. **Protocol / Selector Decision on Dense Space-Filling Priors (`IR-88-60` / `IR-88-86` / `IR-88-113`):** Until a human owner/selector explicitly authorizes evaluating continuous probability priors (`17GEMSDOE`, `GEMSDOE87` `bmtd`, `GEMSDOE86` `faulthalo-4210938px`) via top-$N$ effective support rather than `finite > 0` support, `validate_hgvc88.py --require-submit` must continue exiting `2` (`DO NOT SUBMIT`).
  2. **Organizer Byte Authentication & Live Receipt Calibration:** On an unrestricted machine with a competition login, verify SHA-256 identity of `sample_submission.tif`, `existing_faults.tif`, and `training_features.tif` against direct DrivenData downloads (`bash scripts/download_competition_data.sh`), check current remaining weekly submission quota, and log any manual upload receipt verbatim in `ledger/submissions.csv` as `ORGANIZER-CONFIRMED`.
  3. **Next Ranked Scientific Lanes (`research/candidate-hypotheses-20261024-hgvc88.md`):**
     - *In-sandbox viable (`0` external host access needed):* `H88-PSGV` (2D FFT Baranov pseudogravity-to-Bouguer analytic phase dislocation) and `H88-BCSF` (3D elastic half-space Okada Coulomb stress-transfer relay field on fold-visible `trace_segments_utm11.csv`).
     - *Requires unrestricted external host fetch (blocked by sandbox allowlist):* `H88-MT3D` ([NSF SAGE / IRIS SPUD 3D Magnetotelluric Great Basin models](https://ds.iris.edu/spud/emmodel)) and `H88-S2TIR` ([NASA ECOSTRESS `ECO2LSTE`](https://lpdaac.usgs.gov/products/eco2lstev001/) / [USGS Landsat C2 Surface Temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)).
  4. **Sibling HEAD Inventory Refresh (`IR-88-116`):** Re-check `git ls-remote` on `GEMSDOE86..92` before any future placement so newly committed sibling `.tif` files remain inside the uniqueness screen.

## Binding handoff — protocol-integrity review (2026-10-24)

Read `PROMPT.md` and `research/review-43d08c7a-20261024.md` first. Recheck with `python scripts/restore_inputs.py --validation` then `python scripts/audit_protocol_integrity.py`. The `--require-submit` variant must return **2** while the literal dense witness binds. **Do not generate more cosmetic variants:** all nonempty allowed dot sets are duplicates under the current definition. Zero experiments and zero slots in this review.

1. Preserve the binding literal policy unless the project specification is explicitly revised in the shared protocol. Do not silently exempt dense priors or use top-N diagnostics as authorization. The current specification and registry cannot produce a passing nonempty submission.
2. Use one indexed, hash-bound registry audit for both real pre-placement surfaces and saved final dots; historical compatibility reports from curated lists cannot establish completeness. The compatibility decision now reports only selector eligibility, never permission to upload.
3. Before a future scientific experiment, resolve the identity of the current comparable holdout incumbent with a hash and matched folds/seeds/masks. Historical best claims in this long-lived repo differ; do not compare a newly hidden-component model to the fixed H33 raster as if that were a fair control.
4. Consider the ranked **conditional-null contrasts**, not recycled feature names, in the review dossier only after the stop is resolved. No positive DTI improvement has been demonstrated for them. Future outputs must retain single-feature symmetric leakage checks and paired CIs.
5. Current rules, deadline, account allowance and organizer receipts are unverified in this network-restricted session. GitHub Pages is configured, but deployment success must be checked after merge. No credentials belong in chat; no DrivenData upload is attempted. CPU training is supported by the official reference; GPU is optional.

Earlier handoffs below are historical, not overriding authorization.

## Current handoff — H88-MVRD integrated review, 2026-10-24

Read `README.md`, `PROMPT.md`, `registry/mvrd_run_card.json`, `evidence/mvrd88_holdout.json`, and `research/candidate-hypotheses-20261024.md` first. H88-MVRD is the strongest stored overall hide-and-recover result: **HOLDOUT-DTI 0.197314 [0.181121,0.213008]**, `gems57-pooled-hide-v2`, 22,893 withheld positives, paired Δ vs ADHR `+0.009426 [0.001962,0.016994]`. It is still **DOWNLOAD FOR RESEARCH — DO NOT SUBMIT**: literal overlap is 1.0 against the continuous full-footprint 17GEMSDOE witness and the production distance fingerprint has only 2.87% of dots >25 px from the catalogue (35% gate). The far holdout diagnostics also trail ADHR. Zero slots used; no organizer receipt.

**Concurrent QTS-88 result:** preserve `registry/qts88_run_card.json` and its research TIFF. QTS-88 improves over its raw-19 control by paired `+0.006340 [0.001574,0.011511]` but remains below ADHR and fails literal uniqueness. It is not the current release and must not be submitted. Its far-basin/fingerprint behavior is relevant to the separately preregistered next lane, but do not fuse or retune it inside the completed MVRD lane.

**Next separately preregistered scientific frontier:** combine the 62-channel pure-physics MPSC surface with far-basin (`d_cat >25 px`) strand/polyline allocation, without using another experiment from the completed MVRD lane. The objective is to improve far HOLDOUT-DTI while preserving format and sparse-registry uniqueness. The dense-witness interpretation must be clarified by the selector; never silently claim a literal pass. The deferred USGS point-gravity/Bouguer source cannot be fetched under this sandbox's host allowlist.

## Archived handoffs

The sections below predate MVRD integration. Their artifacts and negative findings remain auditable, but none is the current decision.

## PHASE-88 handoff — 2026-10-24

Read `registry/phase88_run_card.json` and `research/phase88-20261024.md`. PHASE-88 is OK to download for research and **DO NOT SUBMIT**: HOLDOUT-DTI 0.053062 [0.046064,0.060233] (`gems57-pooled-hide-v2`, 22,893 withheld positives), below same-split incumbent 0.187888, and overlaps GEMSDOE87 90.90% / dense 17GEMSDOE 100% within 3 px. One preregistered experiment performed; stop in this lane.

## KTH-88 handoff — 2026-10-24

KTH-88 (`gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`) is research-only. HOLDOUT-DTI 0.052656 [0.045911,0.059151], 22,893 positives, `gems57-pooled-hide-v2`; final overlap 0.89882 with GEMSDOE87 and 1.0 with the dense witness. Both holdout and literal uniqueness fail. No slot or organizer receipt.

## LBCAL handoff — 2026-10-24

LBCAL is research-only. Its receipt model is a MODEL-PROJECTION, never a score. The stored HOLDOUT-DTI 0.061566 [0.051910,0.072787] uses a different split from ADHR and cannot be compared as paired evidence. Literal dense-witness overlap remains 1.0.
