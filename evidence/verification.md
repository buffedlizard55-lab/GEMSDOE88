# Independent Verification & Byte-Level Audit (`2026-10-24`)

Current canonical artifact: `docs/downloads/gems88-mrr-bpr-blockresid-dinkelbach-20261024-v1-DO-NOT-SUBMIT.tif`.

## Pass 1 — Implement and verify

1. Restored SHA-pinned grid, 21-raster accessible registry, 19-band feature stack, and official H88 baseline inputs with `scripts/restore_inputs.py`.
2. Built four catalogue-blind MRR-BPR features and tested each alone: 4/4 PASS, maximum symmetric AUC `0.532607 <= 0.90`.
3. Recomputed the H88 incumbent and MRR candidate on the same eight buffered whole-component folds.
4. Candidate HOLDOUT-DTI `0.1852558211`, 95% CI `[0.1715190223,0.1999647712]`, `n=22,893`, evaluator `gems57-pooled-hide-v2`.
5. Paired candidate-minus-incumbent delta `-0.0043780347`, 95% CI `[-0.0079022116,-0.0006230905]`: negative.
6. Generated, reopened, and hashed a new 36,033-dot competition-grid TIFF and exact one-member ZIP.

## Pass 2 — Review and fix

1. Added a pre-placement callback to production emission so the continuous surface Spearman audit executes before Dinkelbach dot placement.
2. Fixed the initial run-card extraction of writer validator keys; reran the cached complete pipeline successfully.
3. Replaced stale release validation with a canonical-card/evidence cross-check covering current holdout, paired CI, canaries, TIFF/ZIP bytes, `[0,1]`, exact grid, and literal witness.
4. Reconciled all four canonical run-card copies byte-for-byte and updated GitHub Pages, status, run card, ledger, irregularities, and next steps.
5. Updated the publication invariant test to cover the current MRR negative deliverable rather than the historical UGFV ladder.

## Pass 3 — Full requirement recheck

Commands executed after the review fixes:

1. `.venv/bin/python scripts/validate_release.py` -> exit `0`; `format_ok=true`, `inside_no_nan=true`, `all_finite_entire_raster=true`, `values_0_1=true`, exact grid, one matching TIFF in ZIP, `ok_to_download=true`, `ok_to_submit=false`.
2. `.venv/bin/python scripts/validate_release.py --require-submit` -> expected exit `2`; fail-closed message `AUTOMATIC SUBMISSION GATE: FAIL. No upload permitted.`
3. `.venv/bin/python scripts/check_site.py` -> PASS for local links, explicit negative decision, and `DO-NOT-SUBMIT` research downloads.
4. `.venv/bin/python scripts/readiness.py` -> `BLOCKED`; both the negative paired HOLDOUT-DTI and literal registry witness are listed.
5. `.venv/bin/python -m pytest -q` -> **238 passed, 22 skipped, 0 failed**. Skips are data-conditional legacy tests; all restored-input current release tests ran.

## Pinned output digests

- **MRR-BPR-88 TIFF** (`36,033` binary dots, `133,729` bytes): `b9cb36519c2ee91c08f587d3c9c006623d8e2505ece0416fdf263b50e42deb7e`
- **MRR-BPR-88 one-TIFF ZIP** (`96,913` bytes): `dc1433b8f622de939c61589dbf30ccb243c3f5231e872bb647466773cc58768f`
- **19-band training features:** `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`
- **Reference sample submission:** `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`
- **Public existing-fault catalogue:** `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093`
- **Literal 17GEMSDOE witness:** `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`
- **H33 educational registry raster:** `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`

## Uniqueness decision

- Byte-unique and pixel-unique across all 21 restored registry rasters.
- Pre-placement surface maximum `|Spearman rho| = 0.468709 <= 0.90`.
- Final sparse-dot maximum 3-pixel forward overlap `0.684178 <= 0.70`; H33 overlap `0.402187`.
- Literal all-raster maximum overlap `1.000000 > 0.70` against positive-everywhere 17GEMSDOE.
- Final machine status: **OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT**.

## Concurrent-main reconciliation

Before merge, `main` advanced with PR #55 (PROVCREST) and an interior-PRUNE experiment. Their data, code, and historical evidence were preserved. PROVCREST's representation-class `promote` decision conflicted with the binding literal any-raster rule because its own audit records 17GEMSDOE overlap `1.0`. Its builder, run-card mirrors, site guard, and tests were corrected to `negative` / `ok_to_submit=false`; sparse-only diagnostics remain visible. The post-merge suite passes: **238 passed, 22 skipped, 0 failed**.
