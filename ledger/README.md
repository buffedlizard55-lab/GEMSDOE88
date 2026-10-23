# Ledger

`submissions.csv` reconciles **seven** built candidates from three concurrent branches: three MASS variants, the PRUNE3 variant, and three CONCENTRATION variants from PR #18. Every exact `(parent, axis, value)` pair and every primary/zeros SHA-256 is unique. All rows are `BUILT`; no receipt field is filled and no slot is recorded as used.

- **Gate status:** PRUNE3 is the only candidate that satisfies the literal `>= 3 px` non-PRUNE exclusion. The MASS and CONCENTRATION rows are `HOLD` — they retain the parent's 2 px collar. `recommendation` on each row says which and why.
- **Predictions:** `predicted_change` is always labelled `MODEL:` and is never a score. MASS predictions come from PR #17's audit (`registry/mass_ranking_audit.json`); CONCENTRATION predictions from `registry/concentration_projection.json`.
- **Rasters:** new competition rasters stay out of Git (data-use terms unchecked). PRUNE3 and CONCENTRATION keep hashes, gate receipts and rebuild commands in `releases/*-receipt.json`; the older MASS rasters were tracked before that policy and are left in place.
- **Mechanism cards:** `mechanism_cards.json` holds the audited MASS cards and the three CONCENTRATION cards. The PRUNE3 card sits beside its release receipt in `releases/`.

Before any future build, check every exact `(parent, axis, value)` pair and primary/zeros SHA-256. Never treat a MODEL or PROXY value as a receipt score.
