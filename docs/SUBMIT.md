# Submission Checklist — Human Uploads ONE File per Slot (DrivenData #306)

> **Human competitor controls all uploads (`buffedlizard55-lab`, 1 entity, `<= 3` slots/week, 1 blind final file by `2026-12-03`).** Agent never logs into or fetches `drivendata.org` or `dropbox.com`. Candidate `.tif`/`.zip` rasters live locally in `releases/` (untracked in Git per `.gitignore` data-use policy; reproducible via `python3 scripts/build_relief_r0_variants.py`, `python3 scripts/build_snap_variants.py` and `python3 scripts/build_prune_variants.py`), with tracked SHA-256 receipts in `releases/*.json` and `ledger/submissions.csv`.

## Session Built Candidates (`AXIS = RELIEF`, Band 12 `det_elev` Area Terciles, Dose `12%` = `4,518` Dots, Constant `N = 37,654`, Parent `h33-h33-2-b2`, Seed `20261023`)

> **Reproduce:** `python scripts/build_relief_r0_variants.py` (rebuilds R0 byte-for-byte first; rasters are gitignored, SHA-256 receipts tracked). **Status: all three are `HOLD`; `range12` is the only one worth a slot, and only as a label-relief probe (see `SLOT_PLAN.md`).** Pre-registered predictions: `registry/relief_r0_preregistration.json`.

### `RELIEFrange12` (Least-Negative Arm — Slot 3 Option as a Probe): 12% of dots (4,518) basin+piedmont -> range tercile
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-RELIEFrange12-20261023-30b15f5e.tif` (`SHA-256`: `30b15f5e601cbc443cdbe250b336836c413b307dfdb23077f7a3a54edd741dde`, `351,646` B; `.zip` `77d31f35e4ed8b49ecde5f2c533ab5896430019fc964a46a72517d855cbc3e0e`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-RELIEFrange12-20261023-30b15f5e-zeros.tif` (`SHA-256`: `5690895c119a66c5511823922ebb560b50a2f4344bda49e63de403c904b797ca`, `215,626` B; `.zip` `4d2347ccf39e07c4a06aeee63947b33c1876be91a28f91aca3b8b2fcc0d462e3`)
- **Submission Name:** `h33-h33-2-b2-RELIEFrange12-20261023-30b15f5e`
- **Form Note (`103 / 140` chars):** `h33-2-b2; RELIEF 12% of dots (4518) basin+piedmont->range det_elev terciles, N fixed; pred -0.003 MODEL`
- **Stats & Format Receipt:** `37,654` dots (`4,518` removed from basin 1,476/piedmont 3,042; `4,518` added on un-emitted H19-5 ridges in the range tercile; **`12.00%` changed**, `24.00%` symmetric difference; tercile shares basin/piedmont/range `0.205/0.418/0.377` -> `0.165/0.337/0.497`; `0` on catalogue, `0` `<= 2 px`, `2,171` in `2–3 px` unchanged; added dots `min d_cat = 3.1623 px`, median spacing to retained dots `2.0 px`). Blind USGS `SGMC` **`0.093143` `PROXY`** (`R0 0.096060`; donor loss `0.107` TP/dot vs add gain `0.068` TP/dot); `12 km` CV `0.6517` (`R0 0.5590`). Format gates (CRS `EPSG:32611`, `3730×3292`, transform, `float32`, 1 band, `[0,1]`, NaN outside / finite inside, zero catalogue mass, unique SHA-256, re-read from disk) `PASS` in `releases/h33-h33-2-b2-RELIEFrange12-20261023-30b15f5e.json` and `registry/relief_r0_variant_validation.json`.

### `RELIEFpied12` (HOLD): 12% of dots (4,518) basin+range -> piedmont tercile
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-RELIEFpied12-20261023-bae3dfc6.tif` (`SHA-256`: `bae3dfc68becc7f4c94319abf8f1e6ab16808d05191a83606cffcf3cb558f748`, `352,801` B; `.zip` `3bc195cb556c762e25077df25df8bd7cc6ed2af775fb775a4ea267c955b5fc00`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-RELIEFpied12-20261023-bae3dfc6-zeros.tif` (`SHA-256`: `8252894345ad9ec08aba80af64c012b9aae6f59caefaadf25a7141ce52a5b0b5`, `216,676` B; `.zip` `83941aaf78e1ea11f342e919808c046ee32b03b15374e1573f37ef36ce2bb567`)
- **Submission Name:** `h33-h33-2-b2-RELIEFpied12-20261023-bae3dfc6`
- **Form Note (`103 / 140` chars):** `h33-2-b2; RELIEF 12% of dots (4518) basin+range->piedmont det_elev terciles, N fixed; pred -0.008 MODEL`
- **Stats & Format Receipt:** `37,654` dots (`4,518` removed from basin 1,575/range 2,943; `4,518` added on un-emitted H19-5 ridges in the piedmont tercile; **`12.00%` changed**, `24.00%` symmetric difference; tercile shares basin/piedmont/range `0.205/0.418/0.377` -> `0.163/0.538/0.299`; `0` on catalogue, `0` `<= 2 px`, `2,171` in `2–3 px` unchanged; added dots `min d_cat = 3.1623 px`, median spacing to retained dots `2.0 px`). Blind USGS `SGMC` **`0.087520` `PROXY`** (`R0 0.096060`; donor loss `0.158` TP/dot vs add gain `0.046` TP/dot); `12 km` CV `0.5818` (`R0 0.5590`). Format gates (CRS `EPSG:32611`, `3730×3292`, transform, `float32`, 1 band, `[0,1]`, NaN outside / finite inside, zero catalogue mass, unique SHA-256, re-read from disk) `PASS` in `releases/h33-h33-2-b2-RELIEFpied12-20261023-bae3dfc6.json` and `registry/relief_r0_variant_validation.json`.

### `RELIEFbasin12` (HOLD): 12% of dots (4,518) piedmont+range -> basin tercile
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-RELIEFbasin12-20261023-4cd2af90.tif` (`SHA-256`: `4cd2af90608a644f337ebd436db2bf3f5668babf54bbca60d9db6324931a2619`, `351,331` B; `.zip` `71dd4783b3e3a4a67b6f6b198323c4092ee2b3b10863291ee3c494a74797c03a`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-RELIEFbasin12-20261023-4cd2af90-zeros.tif` (`SHA-256`: `10e7e9a5f332b746fa8865b8fa2436eb6744a4de16bb26ec9da81f9c9b7913ba`, `215,809` B; `.zip` `1196bbaaab4925c5cd997d4c6a35fd6669a2c7700834aa930fe50f54f02e588b`)
- **Submission Name:** `h33-h33-2-b2-RELIEFbasin12-20261023-4cd2af90`
- **Form Note (`103 / 140` chars):** `h33-2-b2; RELIEF 12% of dots (4518) piedmont+range->basin det_elev terciles, N fixed; pred -0.010 MODEL`
- **Stats & Format Receipt:** `37,654` dots (`4,518` removed from piedmont 2,370/range 2,148; `4,518` added on un-emitted H19-5 ridges in the basin tercile; **`12.00%` changed**, `24.00%` symmetric difference; tercile shares basin/piedmont/range `0.205/0.418/0.377` -> `0.325/0.355/0.320`; `0` on catalogue, `0` `<= 2 px`, `2,171` in `2–3 px` unchanged; added dots `min d_cat = 3.1623 px`, median spacing to retained dots `1.4142 px`). Blind USGS `SGMC` **`0.086644` `PROXY`** (`R0 0.096060`; donor loss `0.160` TP/dot vs add gain `0.036` TP/dot); `12 km` CV `0.6101` (`R0 0.5590`). Format gates (CRS `EPSG:32611`, `3730×3292`, transform, `float32`, 1 band, `[0,1]`, NaN outside / finite inside, zero catalogue mass, unique SHA-256, re-read from disk) `PASS` in `releases/h33-h33-2-b2-RELIEFbasin12-20261023-4cd2af90.json` and `registry/relief_r0_variant_validation.json`.

## Previous Session Candidates (`AXIS = SNAP`, Spacing-Locked `d_nn >= 2.8284 px`, Constant `N = 37,654`, Parent `h33-h33-2-b2`, Seed `20261023`)

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

## Other Reconciled Ledger Inventory (`HOLD` — `ledger/submissions.csv`)
- **Unspaced `SNAP` (`SNAPw2E1` `01cf9e98` `MODEL -0.002`, `SNAPw2S2` `60ced8c7` `MODEL -0.001`, `SNAPw2E2` `861cd355` `MODEL -0.002`):** `HOLD` due to along-strike bunching (`min_sep = 1 px`, `SGMC` delta `-0.0080` to `-0.0040`); superseded by spacing-locked `SNAPscarp2px` (`fae77ff4`, `d_nn >= 2.8284 px`, `SGMC +0.00075`).
- **`CONCENTRATION` (`CONCb10px-m10` `89ffd4f3` `+0.011`, `CONCb10px-m20` `c42cd475` `+0.020`, `CONCb50px-m20` `fae2a52f` `+0.006`, `CONCENTRATION15pct` `4dfb83f6` `+0.008`):** `HOLD` under literal non-PRUNE `>=3 px` gate (`R0`'s `2,171` `2–3 px` dots inherited); re-base atop `PRUNEp3px` in Week 2.
- **`MASS` (`MASSm10minus` `7132935e`, `MASSm10plus` `82673b57`, `MASSm20minus` `6c73303c`):** `HOLD` per `registry/mass_ranking_audit.json`.

## Format Gate Verification Summary
- All `SNAP` and `PRUNE` GeoTIFFs (`EPSG:32611`, `3730×3292`, `Affine(100,0,243350,0,-100,4508550)`, `1` band `float32`, `[0,1]`, `0` NaN inside footprint, `0` on catalogue, unique SHA-256) re-read and verified in `tests/test_snap_axis.py`, `tests/test_prune_axis.py`, and `scripts/validate_variant.py`.
