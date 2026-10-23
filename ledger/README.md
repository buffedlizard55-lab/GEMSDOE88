# Ledger

`submissions.csv` reconciles **thirteen** built candidates from four sessions: three `MASS` variants, one score-blind `PRUNE3`, three `CONCENTRATION` variants (PR #18), three physics-ranked `PRUNE` variants around the collar radius, and three `SNAP` variants (`2026-10-23`). Every exact `(parent, axis, value)` pair and every primary/zeros SHA-256 is unique.

- **Parents:** `MASS` / `CONCENTRATION` / `PRUNE` are edits of `R0 = h33-h33-2-b2`. `SNAP` is an edit of `R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`, because a non-`PRUNE` axis on `R0` would inherit the `2,171` dots at `2 < d_cat <= 3 px` and break Brief §4.4 (IR-88-22).
- **Gate status:** `PRUNE p1px/p3px/p4px` and all three `SNAP` variants satisfy the `>= 3 px` non-`PRUNE` exclusion. The `MASS` and `CONCENTRATION` rows are `HOLD` — they retain the parent's 2 px collar. `recommendation` on each row says which and why.
- **Predictions:** `predicted_change` is always labelled `MODEL:` and is never a score. `MASS` predictions come from PR #17's audit (`registry/mass_ranking_audit.json`), `CONCENTRATION` from `registry/concentration_projection.json`, `PRUNE` from the exact marginal-DTI sweep, and `SNAP` from the mechanism cards.
- **`SNAP` is diagnostic only (IR-88-24):** every SNAP variant scores below its own parent on the blind off-catalogue USGS `SGMC` control, so none is recommended for a weekly slot. Spend slot 1 on `PRUNEp3px`.
- **Rasters:** competition rasters stay out of Git (data-use terms unchecked). Every family keeps hashes, gate receipts and rebuild commands in `releases/*-receipt.json` (or the enriched `releases/<id>.json`); the older `MASS` rasters were tracked before that policy and are left in place.
- **Mechanism cards:** `mechanism_cards.json` holds the audited `MASS`, `CONCENTRATION`, `PRUNE` and `SNAP` cards.

Before any future build, check every exact `(parent, axis, value)` pair and primary/zeros SHA-256. Never treat a `MODEL` or `PROXY` value as a receipt score.
