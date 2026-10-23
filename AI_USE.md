# AI_USE — Generative-AI disclosure per NLR Rules §3.6

**Human:** `buffedlizard55-lab` (entity owner, submitter, approver). **AI:** Arena.ai Agent Mode. Disclosure must be copied into the final technical narrative.

## Prior revision (2026-10-23, earlier turn) — built the three MASS rasters

`scripts/generate_axis_variants.py` loads pinned `h33_education.tif` (`c55bafc4…`) and the grid (`sample_submission.tif` `2176d08e…`, `existing_faults.tif` `7ba308cc…`), computes a ranking as `0.6·clip(d_catalogue/50)+0.4·uniform(seed88)` for the parent and `seed90` for the candidate pool on the allowed-2px mask, and emits three variants (drop 10% → 33,889; add 10% → 41,419; drop 20% → 30,123) with NaN-outside and `-zeros` twins. That revision disclosed the formula in this file while `SLOT_PLAN.md` and `mechanism_cards.json` called it "the parent ranking" — an internal contradiction, resolved this turn in favour of the measured facts.

## This revision (2026-10-23) — audited the prior revision, built no new rasters

**What AI wrote:**
- `scripts/audit_mass_ranking.py` — reconstructs each shipped MASS array bit-for-bit from the recorded formula (all three: `identical_to_on_disk: true`), measures what the ranking actually selects against the catalogue, tests its stability under a seed swap, compares the dropped set to an independent pinned model score, and computes the exact DTI sensitivity curve from `vendor/gems57/metric.py`. No metric fork: the bar and kernel come from the vendor module.
- `registry/mass_ranking_audit.json` — the generated receipt (Q1 reconstruction, Q2 confound, Q3 stability, Q4 prior alignment, marginal bar, sensitivity by mean credit).
- `tests/test_mass_ranking.py` — 5 tests that lock those findings so a later session cannot restate the ranking as a model ranking.
- Corrected `ledger/mechanism_cards.json`, `ledger/submissions.csv`, `SLOT_PLAN.md`, `README.md` (CURRENT STATE only), `docs/SUBMIT.md`, `IRREGULARITIES.md` (IR-88-17…21).
- Re-verified: all six mirror groups restore with matching SHA-256; R0 rebuilds to 37,654 dots and `c55bafc4…`; 77 tests pass; `check_site.py`, `readiness.py` and `validate_release.py` behave as before.

**What AI decided (and the human may overrule):** kept the three rasters rather than rebuilding them, because (AXIS, value) pairs are built once and rebuilding the same values would burn the dedupe rule for no new information; reclassified m10minus as a collar-extension probe; withdrew m10plus from slot contention; recommended uploading the `-zeros` twin.

**What the human must decide:** whether to spend this week's slots at all (the incumbent is 0.1635 behind #1 while the largest effect ever measured here is +0.007); which of the three to submit, if any; and the ONE final blind file per Rules §3.4. Receipt scores are pasted by the human only — never fetched by AI.

## Reproducibility

Inputs are GitHub owner mirrors pinned in `scripts/restore_inputs.py` and verified by SHA-256 at every run: `sample_submission.tif` `2176d08e…`, `existing_faults.tif` `7ba308cc…`, `h33_education.tif` `c55bafc4…`, dense witness `ab0a0a62…`. Every emitted raster has a fixed seed (88/90) and a logged `git` SHA. No `dropbox.com` contact, no `drivendata.org` fetch, no credentials read, stored or printed, no automated leaderboard access. Model inputs that are *not* organiser numbers (the denominator `D0 = 18,233.29` taken from the prior projected live-mirror build) are labelled as MODEL in `registry/mass_ranking_audit.json`.
