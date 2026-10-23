# Ledger

`submissions.csv` reconciles **ten** built candidates: three MASS variants, score-blind PRUNE3, three CONCENTRATION variants (PR #18), the three-slot physics-ranked PRUNE sweep (`p1px`/`p3px`/`p4px`), and three SNAP variants (`w2E1`/`w2S2`/`w2E2`, session `2026-10-23b`). Every exact `(parent, axis, value)` pair and every primary/zeros SHA-256 is unique. All rows are `BUILT`; no receipt field is filled and no slot is recorded as used.

- **Gate status:** only `PRUNEp3px` / `p4px` satisfy the literal `>= 3 px` collar. MASS, CONCENTRATION and SNAP retain `579–2,171` parent-collar dots and are `HOLD` (SNAP additionally has a **negative** blind SGMC PROXY: `-0.0040 … -0.0080`). `recommendation` on each row says which and why.
- **Predictions:** `predicted_change` is always labelled `MODEL:` and is never a score. MASS predictions come from PR #17's audit (`registry/mass_ranking_audit.json`); CONCENTRATION predictions from `registry/concentration_projection.json`.
- **Rasters:** new competition rasters stay out of Git (data-use terms unchecked). PRUNE3 and CONCENTRATION keep hashes, gate receipts and rebuild commands in `releases/*-receipt.json`; the older MASS rasters were tracked before that policy and are left in place.
- **Mechanism cards:** `mechanism_cards.json` holds the audited MASS, CONCENTRATION, PRUNE and SNAP cards; SNAP cards keep both the a-priori (`+0.004`) and the post-measurement (`-0.002`) prediction. The PRUNE3 card sits beside its release receipt in `releases/`.

Before any future build, check every exact `(parent, axis, value)` pair and primary/zeros SHA-256. Never treat a MODEL or PROXY value as a receipt score.
