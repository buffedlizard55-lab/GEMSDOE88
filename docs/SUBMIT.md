# Submission Checklist — Human Uploads ONE File per Slot (DrivenData #306)

> **Human competitor controls all uploads (`buffedlizard55-lab`, 1 entity, `<= 3` slots/week, 1 blind final file by `2026-12-03`).** Agent never logs into or fetches `drivendata.org` or `dropbox.com`. Candidate `.tif`/`.zip` rasters live locally in `releases/` (untracked in Git per `.gitignore` data-use policy; reproducible via `python3 scripts/build_snap_variants.py`, `python3 scripts/build_prune_variants.py` and `python3 scripts/build_relief_variants.py`), with tracked SHA-256 receipts in `releases/*.json` and `ledger/submissions.csv`.

## Session Built Candidates (`AXIS = SNAP`, Spacing-Locked `d_nn >= 2.8284 px`, Constant `N = 37,654`, Parent `h33-h33-2-b2`, Seed `20261023`)

### 1. `SNAPscarp2px` (Primary `SNAP` Candidate — Recommended Slot 2): `<= 2 px` (`200 m`) Co-Registered Scarp + TMI/Gravity Edge Snap
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4.tif` (`SHA-256`: `fae77ff4e120be7541fd04e9b4fc6651282b8100b9c078eae667d03f5aeee293`, `356,181` B; `.zip` `6cfc27584d03728ef81842d50c1a3753407b9cc3adc4e71cc71a5fd781293426`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4-zeros.tif` (`SHA-256`: `a801b23f057b10d9373664b6d8dd1ca958790416864d654ee364b9054d5063ce`, `219,741` B; `.zip` `d86a05420682db7b6280be5c983debd4725d1f2909ce463cc71721fcbf602140`)
- **Submission Name:** `h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4`
- **Form Note (`105 / 140` chars):** `h33-2-b2; SNAP <=2px to provided scarp+TMI/grav co-edge (82.03% chg, mean disp 1.31px); pred +0.006 MODEL`
- **Stats & Format Receipt:** `37,654` dots (`30,889` displaced `<= 2.0 px`, **`82.03%` changed**; **mean displacement `1.3089 px` [`130.9 m`] overall, `1.5956 px` [`159.6 m`] moved**; `min d_nn = 2.8284 px`; `0` on catalogue, `0` `<= 2 px`, `2,171` in `2–3 px` unchanged, `100%` of moved dots at `d_cat > 3.0 px`). Blind USGS `SGMC` **`0.096806` `PROXY`** (highest of `SNAP` & `PRUNE` sweeps); `12 km` CV `0.5608`. Tracked receipt: `releases/h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4.json`.

### 2. `SNAPridge2px` (Intra-Ribbon `H19-5` `SNAP` Candidate — Slot 3 Option): `<= 2 px` (`200 m`) Snap Inside `H19-5` Parent Ridges
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-SNAPridge2px-20261023-83d2d231.tif` (`SHA-256`: `83d2d231d09c92023993f578e9db4f1838d05e1f3339a5d4cab9b24d31f76c28`, `355,703` B; `.zip` `0225cf929ff5af88546f69de53d4ffff2ec9d32c66e4a835d548f34c1b69a66f`)
- **Fallback GeoTIFF (`0.0` outside):** `releases/h33-h33-2-b2-SNAPridge2px-20261023-83d2d231-zeros.tif` (`SHA-256`: `ef301ff3d4c3994c7f60da37edc1931645903116e0ef731379a87b541d30bb5c`, `219,369` B; `.zip` `cf594c39523b911540e322b65be510fd54f932c3320660d203eee34f6ddb27fe`)
- **Submission Name:** `h33-h33-2-b2-SNAPridge2px-20261023-83d2d231`
- **Form Note (`108 / 140` chars):** `h33-2-b2; SNAP <=2px on H19-5 ridge to scarp+TMI/grav peak (18.81% chg, mean disp 0.23px); pred +0.003 MODEL`
- **Stats & Format Receipt:** `37,654` dots (`7,082` displaced `<= 2.0 px` strictly within `H19-5` ridge ribbons, **`18.81%` changed**; **mean displacement `0.2299 px` [`23.0 m`] overall, `1.2222 px` [`122.2 m`] moved**; `min d_nn = 2.8284 px`). Blind `SGMC` `0.096439` `PROXY`; `12 km` CV `0.5588`. Tracked receipt: `releases/h33-h33-2-b2-SNAPridge2px-20261023-83d2d231.json`.

### 3. `SNAPpot2px` (Subsurface Potential-Field Diagnostic Control — `HOLD`): `<= 2 px` (`200 m`) Snap to TMI + Gravity Horizontal-Gradient Crests
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-SNAPpot2px-20261023-fc2548e7.tif` (`SHA-256`: `fc2548e7c6721ac0797e77637b0544862563891f4dfe76cdd3892dd9f63e85dd`, `356,515` B; `.zip` `fa75f415b42caff6d8fdb028525ea53cfb3520d368a466540990755dabdb7ffa`)
- **Fallback GeoTIFF (`0.0` outside):** `releases/h33-h33-2-b2-SNAPpot2px-20261023-fc2548e7-zeros.tif` (`SHA-256`: `f802bce81bbad9d82da905195024a85cfee4a4e24da40218e15eaa55bfbc2fb3`, `220,087` B; `.zip` `11c0a7cf9944035546d9b1b0a475681a8f3c80c162bce6d8286129f447c0f84d`)
- **Submission Name:** `h33-h33-2-b2-SNAPpot2px-20261023-fc2548e7`
- **Form Note (`104 / 140` chars):** `h33-2-b2; SNAP <=2px to provided TMI+gravity HG crests (82.46% chg, mean disp 1.35px); pred -0.004 MODEL`
- **Stats & Format Receipt:** `37,654` dots (`31,049` displaced `<= 2.0 px` on `Bands 3 & 18`, **`82.46%` changed**; **mean displacement `1.3489 px` [`134.9 m`] overall, `1.6358 px` [`163.6 m`] moved**; `min d_nn = 2.8284 px`). Blind `SGMC` `0.095178` `PROXY` (`-0.00088` vs `R0`: hanging-wall dip offset); `12 km` CV `0.5583`. Tracked receipt: `releases/h33-h33-2-b2-SNAPpot2px-20261023-fc2548e7.json`.

## Recommended Slot 1 (`AXIS = PRUNE`, Strict `> 3 px` Collar Compliance)
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.tif` (`SHA-256`: `6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9`)
- **Fallback GeoTIFF (`0.0` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-zeros.tif` (`SHA-256`: `dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f`)
- **Submission Name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`
- **Form Note (`103 / 140` chars):** `h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL`
- **Stats & Receipt:** `37,654` dots (`-2,171` in `2 < d_cat <= 3 px`, `+2,171` on `H19-5` ridges at `d_cat > 3 px`; **`5.77%` moved**, `min d_cat = 3.1623 px`, `0` on catalogue). Blind USGS `SGMC` `0.096083` `PROXY`; `12 km` CV `0.5700`. Tracked receipt: `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.json`.
- **Other `PRUNE` brackets:** `PRUNEp1px` (`0542a27c`, `6.76%` moved, `MODEL -0.006`) and `PRUNEp4px` (`be9fd3d5`, `10.16%` moved, `MODEL -0.009`).

## This Session (`AXIS = RELIEF`, parent `R1 = PRUNEp3px`, `N = 37,654`, fixed count)

Built to *measure* the basin/piedmont/range-front mass question, not to win a slot: all three arms are predicted **negative** by three independent report-only instruments. Do **not** upload one ahead of `PRUNEp3px` (Slot 1) or `SNAPscarp2px` (Slot 2). If the human wants the axis closed with a receipt, `up2t15` is the informative one (largest dose, least-negative `SGMC`).

### `RELIEFup2t15` (`15%` basin+piedmont -> range front)
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFup2t15-20261023-77588346.tif` (`SHA-256`: `775883468b1fb9baf4148e54a941db6bd97716b2684c2f78fccd0d967a497006`, `349,438` B)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `...-RELIEFup2t15-20261023-77588346-zeros.tif` (`SHA-256`: `9f12f021b620cb39aeee680a1662f3534ebc9340a2de854235d35eb87c097af0`, `213,532` B)
- **Submission Name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFup2t15-20261023-77588346`
- **Form Note (`90 / 140` chars):** `h33-2-b2 PRUNEp3px; RELIEF 15% basin+piedmont->range-front, count fixed; pred -0.004 MODEL`
- **Stats & Format Receipt:** `37,654` dots, `5,648` removed + `5,648` added (**`15.00%` changed**, `30.00%` symmetric difference); tercile shares `basin 20.4 -> 16.0`, `piedmont 41.7 -> 31.2`, `range front 37.8 -> 52.8`; `min d_cat = 3.1623 px` (`0` dots at `<= 3 px`); `3,579` of `5,648` receivers within `2 px` of a survivor. `SGMC` off-catalogue `0.09252` `PROXY` (`-0.00356` vs `R1`); expected DTI under the label-free field `-0.00686`; `12 km` CV `0.6909`. All `12` format gates re-read from disk: `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFup2t15-20261023-77588346.json`.

### `RELIEFup2t10` (`10%` dose bracket)
- **Primary / fallback:** `...-RELIEFup2t10-20261023-cffb5570.tif` (`SHA-256` `cffb55707adfa4d074d3b3e4ea3dd46935710f512bf5dff93d2cea280c6e2659`, `351,463` B) / `...-cffb5570-zeros.tif` (`46f9f614674552ff0527ada5e39dfb70de48d5f236827c34ac3362ab0e8cd62d`, `215,432` B)
- **Form Note (`90 / 140` chars):** `h33-2-b2 PRUNEp3px; RELIEF 10% basin+piedmont->range-front, count fixed; pred -0.002 MODEL`
- **Stats:** `3,765` moved (`10.00%`); `SGMC` `0.09366` (`-0.00242` vs `R1`); `12 km` CV `0.6467`; `min d_cat = 3.1623 px`.

### `RELIEFdn2t15` (`15%` down-section sign control)
- **Primary / fallback:** `...-RELIEFdn2t15-20261023-ea75b7eb.tif` (`SHA-256` `ea75b7eb6b0551b2572f5bd0d06072461994efb4951bf108e756b3022da957b9`, `347,979` B) / `...-ea75b7eb-zeros.tif` (`2f0f661aef0081165e07ac6fe73f93aa1ec5fd6677e8ec50198eba4421ed3c0c`, `213,003` B)
- **Form Note (`90 / 140` chars):** `h33-2-b2 PRUNEp3px; RELIEF 15% piedmont+range-front->basin, count fixed; pred -0.007 MODEL`
- **Stats:** `5,648` moved (`15.00%`); tercile shares `basin 20.4 -> 35.4`, `range front 37.8 -> 30.3`; `SGMC` `0.08490` (`-0.01118` vs `R1`, worst of the three); `12 km` CV `0.6432`; `min d_cat = 3.1623 px`.

## Other Reconciled Ledger Inventory (`HOLD` — `ledger/submissions.csv`)
- **Unspaced `SNAP` (`SNAPw2E1` `01cf9e98` `MODEL -0.002`, `SNAPw2S2` `60ced8c7` `MODEL -0.001`, `SNAPw2E2` `861cd355` `MODEL -0.002`):** `HOLD` due to along-strike bunching (`min_sep = 1 px`, `SGMC` delta `-0.0080` to `-0.0040`); superseded by spacing-locked `SNAPscarp2px` (`fae77ff4`, `d_nn >= 2.8284 px`, `SGMC +0.00075`).
- **`CONCENTRATION` (`CONCb10px-m10` `89ffd4f3` `+0.011`, `CONCb10px-m20` `c42cd475` `+0.020`, `CONCb50px-m20` `fae2a52f` `+0.006`, `CONCENTRATION15pct` `4dfb83f6` `+0.008`):** `HOLD` under literal non-PRUNE `>=3 px` gate (`R0`'s `2,171` `2–3 px` dots inherited); re-base atop `PRUNEp3px` in Week 2.
- **`MASS` (`MASSm10minus` `7132935e`, `MASSm10plus` `82673b57`, `MASSm20minus` `6c73303c`):** `HOLD` per `registry/mass_ranking_audit.json`.

## Format Gate Verification Summary
- All `SNAP`, `PRUNE` and `RELIEF` GeoTIFFs (`EPSG:32611`, `3730×3292`, `Affine(100,0,243350,0,-100,4508550)`, `1` band `float32`, `[0,1]`, `0` NaN inside footprint, `0` on catalogue, unique SHA-256) re-read and verified in `tests/test_snap_axis.py`, `tests/test_prune_axis.py`, `tests/test_relief_axis.py`, and `scripts/validate_variant.py`.
