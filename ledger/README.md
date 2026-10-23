# Ledger

`submissions.csv` reconciles **41** built candidate records: three `MASS`, ten `PRUNE`, four `CONCENTRATION`, nine `SNAP`, nine `RELIEF`, and **six `SPACING`** variants. Every exact `(parent, axis, value)` pair and every primary/zeros SHA-256 is unique. All rows are `BUILT`; no portal receipt field is filled and no slot is recorded as used.

- **Parent/evidence:** R0 has `37,654` dots and was rebuilt byte-exactly against both recorded TIFF hashes. Its `0.2778` is `CLAIM`, not a receipt. Every `predicted_change` is `MODEL`; report-only holdout/SGMC values are `PROXY`.
- **Literal gate:** current validation rejects non-PRUNE positive mass at `<3 px` catalogue distance. Historic R0 non-PRUNE descendants that inherit collar mass remain HOLD. PRUNE is the explicit exception.
- **R1 SPACING family:** `poisson28`, `lattice4px`, and `strike` parented by gate-clean `PRUNEp3px` share a 1,914-dot donor set and differ only in receiver geometry. Generic `spacing_*` preregistration/report/validation paths belong to this family. All are HOLD diagnostics.
- **R0 SPACING family:** `lattice`, `poisson`, and `alongstrike` parent R0, use fixed count and legal `>=3 px` support, and share 5,376 relocations. Their only arm-to-arm difference is replacement ordering, but shared collar repair and a `sqrt(5)` guard make all three HOLD. R0 records are deliberately namespaced: `scripts/build_spacing_r0_variants.py`, `registry/spacing_r0_preregistration.json`, `evidence/spacing_r0_axis_report.json`, `evidence/spacing_r0_axis_validation.json`, and `evidence/spacing_r0_first_attempt_failure.json`.
- **PRUNE refill-spacing family:** `p3norefill`, `p3space35`, and `p4space35` are refill-mode treatments, not radius aliases. `p3space35` is conditional only; the two report-only instruments disagree.
- **Rasters/cards:** new TIFF/ZIP artifacts remain local and gitignored; JSON receipts preserve hashes. `mechanism_cards.json` has 40 cards for documented candidates; historical `h33-h33-2-b2-prune3-20261023-01d57649` has no card.

Before any build or upload, check exact pair/hash duplication. Before a human upload, revalidate the actual disk bytes and obtain quota/deadline/provenance/receipt information. Never treat a `MODEL` or `PROXY` value as a receipt score.
