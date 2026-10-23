# AI_USE — Generative-AI disclosure per NLR Rules §3.6

**Human:** `buffedlizard55-lab` (entity owner, submitter, approver). **AI:** Arena.ai Agent Mode (branch `arena/b266c684-gemsdoe88` → this PR). Disclosure must be copied into final technical narrative.

## What AI wrote (session 2026-10-23, branch `arena/b266c684-gemsdoe88`, CONCENTRATION axis)
- `scripts/verify_parent_r0.py` — re-verifies the three input pins, checks R0's 37,654-pixel mask against the footprint/catalogue collar, and re-emits R0 with two writer profiles to test byte- vs array-level reproducibility. Writes `registry/r0_verification.json`. Result: array exact, byte sha not reproducible (IR-88-17).
- `scripts/make_concentration_variants.py` — deterministic builder for the CONCENTRATION axis: 1 km and 5 km blocks, smoothed parent-density prior, coldest→hottest mass relocation with a one-dot-per-block donor floor, receivers welded ≤1.41 px to surviving host dots outside the 3 px collar, count fixed at 37,654. Emits `releases/*.tif` + `-zeros.tif` + one-TIFF `.zip`, re-reads from disk, writes `registry/concentration_report.json` (CV ladder, Gini, top-1 % mass share, displacement, emptied blocks).
- `scripts/project_concentration.py` — metric-algebra MODEL projection with a scenario grid; writes `registry/concentration_projection.json`.
- `scripts/eval_concentration_proxy.py` — REPORT-ONLY catalogue hide-and-recover PROXY on the repo's shared instrument (`vendor/gems57`, split v2, seeds 20/21, 22,893 withheld positives); writes `registry/concentration_proxy.json`.
- `scripts/validate_variant.py` — independent gate check re-read from disk; writes `registry/variant_validation.json`. `scripts/finalize_concentration.py` — ledger rows + mechanism cards.
- `tests/test_dti_algebra.py` (6 tests) and `tests/test_concentration_variants.py` (7 tests).
- Documentation: `SLOT_PLAN.md`, README CURRENT STATE block, `docs/SUBMIT.md`, `IRREGULARITIES.md` IR-88-17…20, this file.

## What the human decided / must still decide
- The brief's AXIS field was blank; AI took the next unbuilt axis from the default plan (CONCENTRATION) and logged it as IR-88-20. **The human can override.**
- Which variants, if any, are promoted to the 3 weekly slots (`SLOT_PLAN.md` proposes CONC 1 km × 20 %, then × 10 %, then MASS −10 %).
- `TOP_PUBLIC`, the receipt scores and the slot counts must be copied by the human from their own authenticated pages; no agent fetch was made (brief §4.1).
- The final single blind file for both rounds (Rules §3.4) — still open.

## Reproducibility
Pinned inputs only: `data/bridge/sample_submission.tif` `2176d08e…`, `data/bridge/existing_faults.tif` `7ba308cc…`, `data/registry/h33_education.tif` `c55bafc4…`, restored by `scripts/restore_inputs.py`. No random numbers are drawn on the CONCENTRATION axis (every ordering ends in row/col), git SHA and timestamp are recorded in `registry/concentration_report.json`. No `dropbox.com` or `drivendata.org` fetch, no credentials stored, nothing submitted.
