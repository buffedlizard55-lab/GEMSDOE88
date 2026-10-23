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

## AI-Generated Code, Artifacts & Analyses (2026-10-23, continued)

4. **`AXIS = SPACING` builder (`scripts/build_spacing_variants.py`, `SEED = 20261023`):**
   - Verified manifest pins (`sample_submission`, `existing_faults`, parent R0 zeros `c55bafc4…`) before use; rebuilt nothing new on R0 (array-verified earlier: 37,654 dots, `min d_cat = 2.236 px`).
   - Held fixed: parent mask, count `N = 37,654`, exclusions (footprint, `d_cat > 2 px`), seed; kept = top ~75% (28,241 dots) by rebuilt ranking `0.6*clip(d_cat/50,0,1)+0.4*Uniform(seed88)` (parent recipe not stored); moved = bottom ~25% (9,413 target).
   - `SPACINGlattice25` (`beefad84`, 24.94% moved), `SPACINGpoissondisk25` (`e15a5f06`, 24.95%, 12 px Poisson-disk), `SPACINGalongstrike25` (`b0fc5114`, 24.64%, structure-tensor strike, 0 fallbacks); 1 band `float32`, `NaN` outside / `0` outside twins, `.zip` per TIFF, receipt JSON per variant with full gate block + report-only diagnostics (block CV 10 km / 12 km, SGMC proximity).
   - All 6 rasters pass `scripts/validate_variant.py` MUST-pass gates from disk; unique SHA-256 not in ledger; ledger rows (`status BUILT`, `predicted_change MODEL:0.000`, `predicted_range [-0.010,+0.010]`) and 3 mechanism cards appended; `registry/variant_validation.json` written.

## Human Competitor Decisions Required

- **`AXIS = SPACING` confirmed for this session** (human-assigned; PRUNE/MASS/CONCENTRATION rows already in ledger; SPACING is lowest priority per `SLOT_PLAN.md`).
- Supply live `TOP_PUBLIC` + date, available rolling-week slots (`__ / 3`).
- Upload chosen single file manually from authenticated browser, log verbatim `receipt_score` and `receipt_date` in `ledger/submissions.csv`, and choose the **one blind final file** before `2026-12-03`.
