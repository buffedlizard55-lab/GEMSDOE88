# Ledger

`submissions.csv` reconciles **44** built candidate records across seven axes: three `MASS`, ten `PRUNE`, four `CONCENTRATION`, nine `SNAP`, nine `RELIEF`, six `SPACING`, and three `TRACKB`. Every exact `(parent, axis, value)` pair and every primary/zeros SHA-256 is unique. All rows are `BUILT`; receipt fields are blank and no slot is recorded as used.

- **Parent/evidence:** R0 has `37,654` dots and was rebuilt byte-exactly against both recorded TIFF hashes. Its `0.2778` is `CLAIM`, not a receipt. Every prediction is `MODEL`; holdout/SGMC values are report-only `PROXY`.
- **Literal gate:** current validation rejects non-PRUNE positive mass at `<3 px` catalogue distance. Historic R0 non-PRUNE descendants inheriting collar mass remain HOLD. PRUNE is the explicit exception.
- **R1 SPACING:** `poisson28`, `lattice4px`, and `strike` are parented by gate-clean `PRUNEp3px`, share a 1,914-dot donor set, and vary only receiver geometry. Generic `spacing_*` preregistration/report/validation paths belong to this family. All are HOLD diagnostics.
- **R0 SPACING:** `lattice`, `poisson`, and `alongstrike` parent R0, use fixed count and legal `>=3 px` support, and share 5,376 relocations. Only replacement ordering varies, but the shared collar repair and `sqrt(5)` guard make all three HOLD. Their paths are deliberately namespaced: `scripts/build_spacing_r0_variants.py`, `registry/spacing_r0_preregistration.json`, `evidence/spacing_r0_axis_report.json`, `evidence/spacing_r0_axis_validation.json`, and `evidence/spacing_r0_first_attempt_failure.json`.
- **TRACKB:** `speckle10minus`, `traceext10`, and `tracespine10` are R1-parented Phase-2 controlled geometry variants tied to `evidence/trackb_traces_geologist.geojson`, `evidence/trackb_geologist_dossier.md`, `registry/trackb_preregistration.json`, and `registry/trackb_variant_validation.json`. They are HOLD and not default weekly slots.
- **PRUNE refill spacing:** `p3norefill`, `p3space35`, and `p4space35` vary refill mode, not only radius. `p3space35` remains conditional; report-only instruments disagree.
- **Rasters/cards:** new competition TIFF/ZIP artifacts remain local and gitignored; JSON receipts preserve hashes. `mechanism_cards.json` has 43 documented cards. Historical `h33-h33-2-b2-prune3-20261023-01d57649` is the known cardless row.

Before any build or upload, check exact pair/hash duplication. Before a human upload, revalidate the actual disk bytes and obtain quota/deadline/provenance/receipt information. Never treat a `MODEL` or `PROXY` value as a receipt score.
