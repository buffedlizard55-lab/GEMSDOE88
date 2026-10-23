# AI_USE — Generative-AI Disclosure (NLR Official Rules §3.6)

- **Competing Entity (1 human competitor):** `buffedlizard55-lab` (sole submitter, slot owner, and blind-final selector).
- **AI System Used:** Arena.ai Agent Mode across the recorded Arena branches, including current branch `arena/2918f370-gemsdoe88`. Include this disclosure in the final competition narrative per Official Rules §3.6 (https://www.drivendata.org/competitions/306/competition-doe-gems/).

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

3. **Deterministic Constant-Count `AXIS = SNAP` Builder (`scripts/build_snap_variants.py`, `tests/test_snap_axis.py`, `evidence/snap_axis_report.json`, Branch `arena/8ec8bb04-gemsdoe88`):**
   - Verified all `15` SHA-256 manifest pins (`registry/data_manifest.json`), fixed the multipart `FEATURE_PARTS` filename pattern in `scripts/restore_inputs.py`, and rebuilt parent `R0 = h33-h33-2-b2` (`37,654` dots) byte-for-byte on both `zeros` (`c55bafc4...`) and `nan` (`baeae321...`) profiles.
   - Constructed strictly provided-band edge/scarp response surfaces (`data/training_features.tif` Bands 3 `tmi_hg`, 12 `det_elev` Hessian breakline, 18 `iso_grav_anom_hg`, 19 `det_elev_slope`; zero external LiDAR used per Brief §5) and verified all `8/8` channels pass the leakage canary (`max sym_auc = 0.54949 <= 0.90`).
   - Built 3 controlled `<= 2.0 px` (`200 m`) `SNAP` variants at exact count `N = 37,654` with `d_nn >= 2.8284 px > 2.8 px` spacing lock and exact `R0` exclusions (`0` on catalogue, `0` `<= 2 px`, `2,171` `2–3 px` collar dots untouched, `100%` of moved dots at `d_cat > 3.0 px`): `SNAPridge2px` (`83d2d231`, `18.81%` changed, mean disp `0.2299 px` all / `1.2222 px` moved, `SGMC = 0.096439`, `MODEL +0.003`), `SNAPpot2px` (`fc2548e7`, `82.46%` changed, mean disp `1.3489 px` all / `1.6358 px` moved, `SGMC = 0.095178`, `MODEL -0.004`), and `SNAPscarp2px` (`fae77ff4`, `82.03%` changed, mean disp `1.3089 px` all / `1.5956 px` moved, `SGMC = 0.096806`, `MODEL +0.006`).

## Human Competitor Decisions Required

- Supply live `TOP_PUBLIC` + date, available rolling-week slots (`__ / 3`), and confirmation of `AXIS = SNAP` (`Slot 2 = SNAPscarp2px`) alongside `Slot 1 = PRUNEp3px`.
- Upload chosen single file manually from authenticated browser, log verbatim `receipt_score` and `receipt_date` in `ledger/submissions.csv`, and choose the **one blind final file** before `2026-12-03`.

## Session `2026-10-23b` — AXIS = SNAP (branch `arena/c4f505a4-gemsdoe88`)

- **AI wrote:** `scripts/build_snap_variants.py` (edge fields, deterministic window-argmax snap, gate re-read writer, receipt/ledger/card emission), `tests/test_snap_axis.py`, `registry/snap_analysis.json`, the three SNAP mechanism cards, and the SNAP sections of `SLOT_PLAN.md`, `docs/SUBMIT.md`, `IRREGULARITIES.md` and the README CURRENT STATE block.
- **AI decided (no human input available):** the AXIS (SNAP, last unbuilt in the default order); the three variant definitions (literal 2 px edge argmax, 200 m-scale gain-gated edge, organizer derivative bands); the `d_cat > 3 px` destination rule; dropping the planned 1 px dose arm because every arm already saturated its window (mean displacement `1.82 px` of `2 px`); and correcting the predicted sign from `+0.004` to `-0.002` after the blind SGMC measurement, with both values kept in the cards.
- **Human must decide:** whether any SNAP file is uploaded at all (all are `HOLD`, negative PROXY) and the blind final file.

## Latest session — human-assigned CONCENTRATION (branch `arena/2918f370-gemsdoe88`)

- **Human decided:** AXIS=CONCENTRATION; TOP_PUBLIC `0.4413` dated `2026-10-22`; planning counts `3/3` this rolling week and approximately `21` total. Human remains the sole submitter and receipt/final selector.
- **AI wrote:** `scripts/generate_concentration_variants.py`, `scripts/validate_concentration_releases.py`, DTI algebra coverage, the exact parent-build receipt, mechanism card, ledger row, release twins, and current planning/submission disclosures.
- **Reconciliation:** concurrent main already contained semantically equivalent 10%/20% 1 km arms, so those newly generated outputs were removed before merge. The only retained new dose is 15% (`4dfb83f6`), based on official TMI/gravity gradients. It is `HOLD` because it inherits R0’s 2–3 px collar.
- **Evidence labels:** R0 `0.2778` is CLAIM; candidate `+0.008` is MODEL; no candidate-specific hide-and-recover number was reported because static full-catalogue exclusion makes that proxy misleading. Build/code commit `0d63cb22b651a0c5c96d68a45fe025dce2a81ed3`.
