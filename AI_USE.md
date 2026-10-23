# AI_USE — Generative-AI Disclosure (NLR Official Rules §3.6)

- **Competing Entity (1 human competitor):** `buffedlizard55-lab` (sole submitter, slot owner, and blind-final selector).
- **AI System Used:** Arena.ai Agent Mode working on branch `arena/4a61d770-gemsdoe88` (reconciled cleanly with concurrent `main` commits `fe8ea6f`, `e079582`, `c3d9485`). Include this disclosure in the final competition narrative per Official Rules §3.6 (https://www.drivendata.org/competitions/306/competition-doe-gems/).

## AI-Generated Code, Artifacts & Analyses (2026-10-23)

1. **Manifest, Provenance & Scraping Remediation (`registry/data_manifest.json`, `scripts/restore_inputs.py`, `scripts/restore_r0_prune_inputs.py`, `scripts/update_leaderboard.py`, `.github/workflows/pages.yml`):**
   - Pinned and SHA-256/byte-verified all `15` inputs (`sample_submission.tif`, `existing_faults.tif`, `training_features.tif`, `5` lineage ancestors from `H19-5` to `R0`, USGS 3DEP 1 m LiDAR scarps, GeoDAWN radiometrics, DOE GDR 1391 geothermometry CSV, and USGS SGMC fault control).
   - Flagged public sibling mirrors (`FLAGGED_DATA_USE_UNCHECKED`), kept candidate `.tif`/`.zip` untracked in `.gitignore` with tracked JSON SHA-256 receipts, and disabled automated `drivendata.org` scraping/cron workflows.
2. **Deterministic Constant-Mass `AXIS = PRUNE` Builder (`scripts/build_prune_variants.py`, `SEED = 20261023`):**
   - Rebuilt parent `R0 = h33-h33-2-b2` (`37,654` unit dots) pixel-for-pixel across all 5 lineage steps AND byte-for-byte on both `zeros` (`c55bafc4...`) and `nan` (`baeae321...`) GeoTIFF profiles (`DEFLATE`, `predictor=3`, `zlevel=9`, `256×256` tiles).
   - Built a 100% label-free 4-line physical corroboration field (`LiDAR/det_elev scarp`, `gravity/magnetic/basement potential`, `geodetic/seismic kinematics`, `GDR geothermometry + K/Th + MT hydro-alteration`). Caught and fixed a live `~catalogue` pre-masking canary trip (`sym_auc = 1.0000 -> max unmasked sym_auc = 0.56925 <= 0.90`).
   - Emitted `PRUNEp1px` (`0542a27c`), `PRUNEp3px` (`6f7ae705`), and `PRUNEp4px` (`be9fd3d5`) at strict fixed mass `N = 37,654` via exact local-window (`11×11`) marginal-DTI `add`/`drop` solvers, re-read all 6 `.tif` + 6 `.zip` from disk, and computed `REPORT-ONLY` Holdout-DTI + 95% CI, blind `SGMC` control, and `10 km` / `12 km` block-density CV (`evidence/prune_axis_report.json`).
   - Reconciled prior concurrent `MASS` audit (`HOLD`), score-blind `PRUNE=3`, and `CONCENTRATION` (`HOLD`) ledger rows, mechanism cards, and test suites (`102+` pytest checks green).

**Branch `arena/55bfd384-gemsdoe88` (PR #19):** an AI coding agent independently built a second CONCENTRATION experiment with an independent physics-gradient prior (bands 13/2/12 Sobel gmag, 2.85 px spacing; MODEL 0.000) but **DROPPED it as redundant** — the CONCENTRATION axis is already built by PR #18 (parent-density, weld-to-host, MODEL +0.011/+0.020/+0.006) and the concurrent test suite expects exactly three variants. The race condition is documented in `IRREGULARITIES.md` item 13; candidate rasters and the generator were removed to keep the ledger and tests consistent.

## Human Competitor Decisions Required

- Supply live `TOP_PUBLIC` + date, available rolling-week slots (`__ / 3`), and confirmation of `AXIS = PRUNE` (`Slot 1 = PRUNEp3px`).
- Upload chosen single file manually from authenticated browser, log verbatim `receipt_score` and `receipt_date` in `ledger/submissions.csv`, and choose the **one blind final file** before `2026-12-03`.

## Session `2026-10-23b` — AXIS = SNAP (branch `arena/c4f505a4-gemsdoe88`)

- **AI wrote:** `scripts/build_snap_variants.py` (edge fields, deterministic window-argmax snap, gate re-read writer, receipt/ledger/card emission), `tests/test_snap_axis.py`, `registry/snap_analysis.json`, the three SNAP mechanism cards, and the SNAP sections of `SLOT_PLAN.md`, `docs/SUBMIT.md`, `IRREGULARITIES.md` and the README CURRENT STATE block.
- **AI decided (no human input available):** the AXIS (SNAP, last unbuilt in the default order); the three variant definitions (literal 2 px edge argmax, 200 m-scale gain-gated edge, organizer derivative bands); the `d_cat > 3 px` destination rule; dropping the planned 1 px dose arm because every arm already saturated its window (mean displacement `1.82 px` of `2 px`); and correcting the predicted sign from `+0.004` to `-0.002` after the blind SGMC measurement, with both values kept in the cards.
- **Human must decide:** whether any SNAP file is uploaded at all (all are `HOLD`, negative PROXY), the `TOP_PUBLIC` value and date, slots used this week, and the blind final file.
