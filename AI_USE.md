# AI_USE — Generative-AI Disclosure (NLR Official Rules §3.6)

- **Competing Entity (1 human competitor):** `buffedlizard55-lab` (sole submitter, slot owner, and blind-final selector).
- **AI System Used:** Arena.ai Agent Mode working on branch `arena/4a61d770-gemsdoe88` from base commit `baee52d65d88245e9765ebd916a82e5712540d8f`. Include this disclosure in the final competition narrative per Official Rules §3.6 (https://www.drivendata.org/competitions/306/competition-doe-gems/).

## AI-Generated Code, Artifacts & Analyses (2026-10-23)

1. **Manifest, Provenance & Scraping Remediation (`registry/data_manifest.json`, `scripts/restore_inputs.py`, `scripts/update_leaderboard.py`, `.github/workflows/pages.yml`):**
   - Pinned and SHA-256/byte-verified all `15` inputs (`sample_submission.tif`, `existing_faults.tif`, `training_features.tif`, `5` lineage ancestors from `H19-5` to `R0`, USGS 3DEP 1 m LiDAR scarps, GeoDAWN radiometrics, DOE GDR 1391 geothermometry CSV, and USGS SGMC fault control).
   - Flagged public sibling mirrors (`FLAGGED_DATA_USE_UNCHECKED`) and disabled automated `drivendata.org` scraping/cron workflows.
2. **Deterministic Single-Axis Builder (`scripts/build_prune_variants.py`, `SEED = 20261023`):**
   - Rebuilt parent `R0 = h33-h33-2-b2` (`37,654` unit dots) pixel-for-pixel across all 5 lineage steps and byte-for-byte on both `zeros` (`c55bafc4...`) and `nan` (`baeae321...`) GeoTIFF profiles.
   - Built a 100% label-free 4-line physical corroboration field (`LiDAR/det_elev scarp`, `gravity/magnetic/basement potential`, `geodetic/seismic kinematics`, `GDR geothermometry + K/Th + MT hydro-alteration`). During initial execution, the built-in leakage canary caught a real `~catalogue` pre-masking leak (`sym_auc = 1.0000 > 0.90`); execution halted, pre-masking was removed from feature construction, and all `15/15` unmasked channels passed (`max sym_auc = 0.56925 <= 0.90`).
   - Implemented exact local-window (`11×11`) incremental marginal-DTI `add` and `drop` solvers under `DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|)` and emitted `PRUNEp1px` (`0542a27c`), `PRUNEp3px` (`6f7ae705`), and `PRUNEp4px` (`be9fd3d5`) at strict fixed mass `N = 37,654` (`NaN`-outside `.tif` + `-zeros.tif` + `.zip` + `.json`), verified by re-opening every file from disk.
   - Computed `REPORT-ONLY` diagnostics (`evidence/prune_axis_report.json`): 20-fold whole-component Holdout-DTI + 20 km cluster bootstrap 95% CI (`seeds 20, 30; boot seed 520810`), blind off-catalogue USGS `SGMC` control, and `10 km` / `12 km` block-density CV.
3. **Automated Tests & Documentation (`tests/test_prune_axis.py`, `SLOT_PLAN.md`, `docs/SUBMIT.md`, `IRREGULARITIES.md`, `README.md` CURRENT STATE block, `ledger/`):**
   - Added unit tests proving DTI algebra parity with `vendor/gems57/metric.py`, isolated `0.2 * DTI` threshold, $\mathbb{Z}^2$ multi-pixel sub-shortcut gain theorem, brute-force parity of incremental `add`/`drop`, live 5-stage `R0` SHA-256 rebuild, and all release gates (`78/78` pytest green).

## Human Competitor Decisions Required

- Confirm live `TOP_PUBLIC` + date, available rolling-week slots (`__ / 3`), and approval of `AXIS = PRUNE` (`Slot 1 = PRUNEp3px`).
- Perform any portal upload manually from authenticated browser, log verbatim `receipt_score` and `receipt_date` in `ledger/submissions.csv`, and choose the **one blind final file** before `2026-12-03`.
