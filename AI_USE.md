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

## AI-Generated Code, Artifacts & Analyses (`2026-10-23`, branch `arena/6eba43d3-gemsdoe88`)

1. **Fixed input restoration (`scripts/restore_inputs.py`):** corrected the pinned feature-stack part names (`gems-geodawn-numerical-features.tif.part-00N`) after the GitHub contents API showed the old `training_features.tif.part0N` paths never existed, and added the two manifest ancestors (`anc_h19_4`, `anc_h16_1`) the script had never restored. All `15/15` pinned inputs now hash-verify.
2. **Parent verification:** `scripts/verify_parent_r0.py` re-ran clean — `R0` is byte-identical to its pin (`c55bafc4…` zeros, `baeae321…` NaN), `37,654` dots, `0` on catalogue, nothing at `<= 2 px`. `scripts/build_snap_variants.py` then rebuilt `R1 = PRUNEp3px` from the lineage and asserted both published hashes (`6f7ae705…` / `dc6f090d…`) before editing it.
3. **`AXIS = SNAP` builder (`scripts/build_snap_variants.py`, `tests/test_snap_axis.py`):** deterministic, count-preserving displacement of up to `35%` of `R1` dots by `<= 1-2 px` onto the strongest percentile-ranked edge cell in each dot's own window, with a strict `> 3 px` catalogue collar on every target and every emitted raster re-read from disk. Three variants (`g2f35`, `d2f35`, `d1f35`) plus receipts, ledger rows and mechanism cards. `9` new tests; full suite `115` passed, `1` skipped.
4. **Report-only instruments:** blind USGS `SGMC` off-catalogue control, catalogue hide-and-recover holdout (degenerate `0.0` for any `> 3 px` raster; IR-88-20) and `10 km` / `12 km` block-density CV. Result recorded in IR-88-24: SNAP is below its parent on the blind control, so the three files are labelled diagnostic, not slot candidates.

**What the human decided, and what the agent decided:** the human answered none of the three session questions (axis, parent, leaderboard facts). The agent chose `SNAP` and the `R1` parent under the standing decision rule ("maximize P(win)") and Brief §4.4, and recorded both choices in `IRREGULARITIES.md` IR-88-22. The human still owns every upload, every `receipt_score`, the `TOP_PUBLIC` number, the rolling-week slot count and the single blind final file.

## Human Competitor Decisions Required

- Supply live `TOP_PUBLIC` + date, available rolling-week slots (`__ / 3`), and confirmation of `AXIS = PRUNE` (`Slot 1 = PRUNEp3px`).
- Upload chosen single file manually from authenticated browser, log verbatim `receipt_score` and `receipt_date` in `ledger/submissions.csv`, and choose the **one blind final file** before `2026-12-03`.
