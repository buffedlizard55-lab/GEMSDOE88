# Ledger

`submissions.csv` reconciles **thirteen** built candidates across four single-axis experiments: three `MASS` variants (`m10minus`, `m10plus`, `m20minus`), four `PRUNE` variants (`3`, `p1px`, `p3px`, `p4px`), three `CONCENTRATION` variants (`b10px-m10`, `b10px-m20`, `b50px-m20`), and three `SNAP` variants (`ridge2px`, `pot2px`, `scarp2px`). Every exact `(parent, axis, value)` pair and every primary/zeros SHA-256 is unique. All rows are `BUILT`; no receipt field is filled and no slot is recorded as used.

- **Gate status:** `PRUNEp3px` (`6f7ae705`) and `PRUNEp4px` (`be9fd3d5`) satisfy the literal `> 3 px` collar across all `37,654` dots. The `SNAP` (`ridge2px`, `pot2px`, `scarp2px`) and `CONCENTRATION` rows hold `100%` of moved dots strictly at `d_cat > 3.0 px` while inheriting `R0`'s `2,171` `2–3 px` collar dots unchanged (`Same count, same exclusions`). `recommendation` on each row records its slot role and collar disposition.
- **Predictions:** `predicted_change` is always labelled `MODEL:` and is never a score. `MASS` predictions come from `registry/mass_ranking_audit.json`; `CONCENTRATION` predictions from `registry/concentration_projection.json`; `PRUNE` and `SNAP` predictions from `evidence/prune_axis_report.json` and `evidence/snap_axis_report.json`.
- **Rasters:** new competition rasters stay out of Git (`.gitignore` excludes `releases/*.tif` and `releases/*.zip`; data-use terms unchecked). `PRUNE`, `CONCENTRATION`, and `SNAP` keep hashes, gate receipts, and rebuild scripts in `releases/*.json`; the older `MASS` rasters were tracked before that policy and are left in place.
- **Mechanism cards:** `mechanism_cards.json` holds the structural-geologist mechanism cards for `MASS`, `CONCENTRATION`, `PRUNE`, and `SNAP`.

Before any future build, check every exact `(parent, axis, value)` pair and primary/zeros SHA-256. Never treat a `MODEL` or `PROXY` value as a receipt score.
