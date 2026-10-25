## Latest handoff — H88-VHGD integrated review & validation (2026-10-25)

Read `README.md`, `PROMPT.md`, `registry/vhgd88_run_card.json`, `registry/vhgd88_gate_verdict.json`, `research/candidate-hypotheses-20261025-vhgd88.md`, and `IRREGULARITIES.md` (`IR-88-116..119`) first. Recheck automatically with `python scripts/restore_inputs.py --validation && PYTHONPATH=src:vendor python scripts/validate_vhgd88.py`.

1. **What `H88-VHGD` accomplished (`PREREG-20261025-VHGD88`, 3 experiments, `0` slots spent):**
   - Repaired `IR-88-116..119` (schema hallucinations in `DHTC`/`UGFV`/`GTHC` and unweighted/self-leaking LightGBM production fits) and extracted previously unopened physical measurements from DOE GDR `#1391` (`T1m`/`T15m` shallow vertical heat-flux gradients $\partial T/\partial z$ across `1,718` probes, `T2m..T2m_7` multi-season persistence across `1,867` probes, and `geothermcat_c` vs `geothermchalc_c` kinetic disequilibrium across `1,040` wells/springs).
   - Achieved **new all-time repository records** on `gems57-pooled-hide-v2` in **Far (`>10 px`) `HOLDOUT-DTI = 0.132383` (`[0.110117, 0.156767]`, `n=10,791`)** and **Blind-Basin (`>25 px`) `HOLDOUT-DTI = 0.092061` (`[0.056908, 0.132098]`, `n=3,117`, `+41.1%` vs `ADHR`)**, with **Overall `HOLDOUT-DTI = 0.198664`** (`paired Δ = +0.009866 [+0.004247, +0.015700]` vs fold-fair `ADHR` `0.188798`).
   - Emitted `docs/downloads/gems88-vhgd88-3strat-27821dots-20261025-zeros-DO-NOT-SUBMIT.tif` (`SHA-256: 752dba748b55b855678f6447628d95bdabc43f785d2c72772004b429f9cb21ab`, `27,821` binary dots, `share_le2 = 0.0%`, `share_gt25 = 36.82% >= 35%`), passing **all 239 registry/sibling/concurrent rasters like-for-like (`0.688545 <= 0.70`, `0` blockers)** while remaining **`OK TO DOWNLOAD: YES · OK TO SUBMIT: NO`** under the binding literal `17GEMSDOE` dense-witness rule (`1.0000 > 0.70`).
2. **Next separately preregistered scientific frontier (`PREREG` required before execution):**
   - Evaluate Rank #2 **`H88-EULER3D`** (sliding $7\times 7$ / $11\times 11$ 3D Euler deconvolution homogeneity clustering for contact structural indices $N \in \{0.0, 0.5, 1.0\}$ where $|z_0 - z_{\text{base}}| \le 500\text{ m}$) or Rank #3 **`H88-FLEXISO`** (2D FFT thin-plate flexural isostatic admittance residual) combined with continuous polyline/graph strand linking across `d_cat > 25 px` blind-basin corridors.
   - Maintain strict literal dense-witness accounting (`ok_to_submit: false` unless a separate portfolio selector revises the dense-witness rule and authorizes a live DrivenData slot with authenticated receipt verification).

---

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
