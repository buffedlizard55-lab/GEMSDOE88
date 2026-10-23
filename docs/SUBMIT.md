# Submission Checklist — Human Uploads ONE File per Slot (DrivenData #306)

> **Human competitor controls all uploads (`buffedlizard55-lab`, 1 entity, `<= 3` slots/week, 1 blind final file by `2026-12-03` — deadline to re-confirm on the portal).** Agent never logs into or fetches `drivendata.org`/`dropbox.com` and never submits. Candidate `.tif`/`.zip` rasters are gitignored locally under `releases/` (regenerate: restore pinned inputs, then `python scripts/build_relief_variants.py` / `build_prune_variants.py` / `build_snap_variants.py`); tracked SHA-256 receipts live in `releases/*.json` + `ledger/submissions.csv`. Upload **only one** of each pair (`<id>.tif` NaN-outside is primary; `<id>-zeros.tif` is the fallback, identical inside the footprint). After uploading, paste verbatim `receipt_score` + `receipt_date` into that row of `ledger/submissions.csv` — until then `R0 0.2778` is `CLAIM` and everything else is `MODEL`/`PROXY`, never a score.

## Recommended Slot 1 — `R1 = PRUNEp3px` (unchanged)

- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.tif` (`SHA-256 6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9`, `354,519` B) · **Fallback:** `…-6f7ae705-zeros.tif` (`SHA-256 dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f`)
- **Submission name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`
- **Form note (103/140):** `h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL`
- **Receipt:** `37,654` dots, `min d_cat 3.1623 px`, `0` on catalogue, SGMC `0.096083 PROXY`, 12 km CV `0.5700`. Tracked: `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.json`.

## Recommended Slot 2 — `SNAPscarp2px` (unchanged; note collar inheritance)

- **Primary:** `releases/h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4.tif` (`SHA-256 fae77ff4e120be7541fd04e9b4fc6651282b8100b9c078eae667d03f5aeee293`, `356,181` B) · **Fallback:** `…-fae77ff4-zeros.tif` (`SHA-256 a801b23f057b10d9373664b6d8dd1ca958790416864d654ee364b9054d5063ce`)
- **Submission name:** `h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4`
- **Form note (105/140):** `h33-2-b2; SNAP <=2px to provided scarp+TMI/grav co-edge (82.03% chg, mean disp 1.31px); pred +0.006 MODEL`
- **Receipt:** `37,654` dots on parent **R0 — inherits its `2,171` dots at `2<d_cat<=3 px`** (Brief §4.4 tension is yours to accept; organizers score beside-catalogue pixels normally against new-fault truth per forum #11516, supplied in the brief). SGMC `0.096806 PROXY` (best built), `MODEL +0.006` vs R0. Tracked: `releases/h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4.json`.

## Session Built — `AXIS = RELIEF` on `R1` (all HOLD-conditional; Slot 3 decision in `SLOT_PLAN.md`)

All three: `37,654` dots, exactly `4,518` moved (`12.00%` of R1; `17.3%` cumulative vs R0), `0` on/≤3 px of catalogue (`min 3.1623 px`), Band 12 `det_elev` terciles (`q1=-142.8321 m`, `q2=+38.5885 m`; parent shares basin/piedmont/range `20.42/41.74/37.83%`), predictions preregistered in `registry/relief_preregistration.json` **before** any proxy. Post-build both REPORT-ONLY instruments move down for every arm, explained by kernel saturation (receivers median `1.41 px` from a survivor; IR-88-35) — read `evidence/relief_axis_report.json` before spending a slot on any of them.

### 1. `rng2bas12` — range → basin (conditional Slot 3 information purchase)
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFrng2bas12-20261023-56093882.tif` (`SHA-256 560938824a6ddae52e45662fe506b7d0f5dea6191746ab517869d5e1205307bb`, `350,762` B; `.zip 39de06a325161560c4ed121ccd2e6028dd0d31b2f782641bad638056564eddf3`)
- **Fallback:** `…-56093882-zeros.tif` (`SHA-256 a34a51c176fcd53069aa6e7e3d7ea463efca28a833e84b12df9e506c930a6737`, `215,369` B; `.zip 5ae522f9135ee07ce762c9d9fcb8d024b7e439e14bcb1dc7e03bfef1d92b2bdf`)
- **Submission name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFrng2bas12-20261023-56093882`
- **Form note (95/140):** `R1(6f7ae705); RELIEF range->basin 12% (4518) B12 terciles, 37654, >3px; pred +0.008 MODEL vs R1`
- **Receipt:** shares → `32.42/41.74/25.83%`; prereg `MODEL +0.008 [-0.008,+0.024]` vs R1; `w`-DTI `-0.006988 MODEL`; SGMC `0.085018 PROXY (-0.011065 vs R1)`; 12 km CV `0.6048`; basin coverage `82.55%→82.92%`, range `87.81%→80.26%`.

### 2. `rng2pmt12` — range → piedmont (range-front bracket, HOLD)
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFrng2pmt12-20261023-52717cf5.tif` (`SHA-256 52717cf542642a2f9304d077f462dd0973d1f6b87f811c8d3b4039ff18c82521`, `351,997` B) · **Fallback:** `…-52717cf5-zeros.tif` (`SHA-256 a69c94ecbc73ebb465be4cd82bc66898b1e7a58d69fb1f48ad4b17647711502d`, `215,849` B)
- **Submission name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFrng2pmt12-20261023-52717cf5`
- **Form note (98/140):** `R1(6f7ae705); RELIEF range->piedmont 12% (4518) B12 terciles, 37654, >3px; pred +0.002 MODEL vs R1`
- **Receipt:** shares → `20.42/53.74/25.83%`; prereg `MODEL +0.002`; `w`-DTI `-0.005036`; SGMC `0.085812 PROXY (-0.010271)`; CV `0.5836`.

### 3. `bas2rng12` — basin → range (reverse/SGMC-direction bracket, HOLD)
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFbas2rng12-20261023-f4c6dc18.tif` (`SHA-256 f4c6dc18f0cf5b2fa22f0c54374d1d3e7c782ef6246136e71770c188cbf6d663`, `350,381` B) · **Fallback:** `…-f4c6dc18-zeros.tif` (`SHA-256 6902c7391b6c50487ef86bbac82f7167522165d1102062f689a7601c831931f4`, `214,118` B)
- **Submission name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFbas2rng12-20261023-f4c6dc18`
- **Form note (95/140):** `R1(6f7ae705); RELIEF basin->range 12% (4518) B12 terciles, 37654, >3px; pred -0.010 MODEL vs R1`
- **Receipt:** shares → `8.42/41.74/49.83%`; prereg `MODEL -0.010`; `w`-DTI `-0.011189`; SGMC `0.093903 PROXY (-0.002180)`; CV `0.6724`.

## Format Gate Verification (RELIEF family)

- All six RELIEF twins individually re-read from disk at build (`EPSG:32611`, `3730×3292`, `Affine(100,0,243350,0,-100,4508550)`, 1 band `float32`, values `{0,1}⊂[0,1]`, no NaN inside footprint, NaN outside primary / 0 outside fallback, `0` catalogue mass, `0` dots `<=3 px`, unique SHA-256) and again by the independent `scripts/validate_variant.py` (**PASS ×6, 2026-10-23**). Leakage canaries pass (`max sym AUC 0.56925`; stratifier `B12 raw 0.50432`, tercile class `0.50088`). Full receipts: `evidence/relief_axis_report.json`, `releases/<id>.json`, `tests/test_relief_axis.py`.

## Other Ledger Inventory (all `BUILT`, none submitted — `ledger/submissions.csv`)

`PRUNE` brackets `p1px 0542a27c (-0.006)` / `p4px be9fd3d5 (-0.009)`; `SNAP` on R0 `ridge2px 83d2d231 (+0.003)`, `pot2px fc2548e7 (-0.004)` + unspaced `w2E1/w2S2/w2E2` (HOLD); `SNAP` on R1 `g2f35/d2f35/d1f35` (diagnostic, IR-88-31); `CONCENTRATION` `89ffd4f3/c42cd475/fae2a52f/4dfb83f6` (HOLD, collar inheritance); `MASS` `7132935e/82673b57/6c73303c` (HOLD, IR-88-18); score-blind `prune3 01d57649` (superseded by `6f7ae705`).
