# Submission Checklist — Human Uploads ONE File per Slot (DrivenData #306)

## Current session — 2026-10-23 startup audit (takes precedence over historical cards)

**No new candidate or submission. AXIS=PRUNE:** requested radii already built;
2 px is R0. Ledger stays at 32 rows. Full-lineage R0 startup validation passed
both pinned SHA-256 values after verification of all 15 inputs. Audit receipt:
`evidence/session_20261023_prune_stop.json` (not a submission-page receipt).

**Do not upload yet:** current TOP_PUBLIC/date, actual rolling-week balance and
deadline are unknown. Existing candidate TIFFs below are absent in this checkout;
their old JSON records are **historical build records, not fresh validations**.
Privately restore an existing artifact, match its complete recorded hash, and
independently validate its actual disk bytes, primary/fallback equality, format,
zero catalogue mass, and applicable collar before a human spends a slot.
No rank-correlation or dot-overlap uniqueness threshold is permitted.

| Order | Exact submission name (primary file is `releases/<name>.tif`; fallback `<name>-zeros.tif`) | <=140-char form note | Historical format record |
|---|---|---|---|
| 1 | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` | `h33-2-b2; PRUNE <=3px, fixed 37654 dots; predicted +0.005 MODEL` | `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.json` |
| 2, optional | `h33-h33-2-b2-PRUNEp1px-20261023-0542a27c` | `h33-2-b2; PRUNE <=1px, fixed 37654 dots; predicted -0.006 MODEL` | `releases/h33-h33-2-b2-PRUNEp1px-20261023-0542a27c.json` |
| 3, reserve | `h33-h33-2-b2-PRUNEp3.2px-20261023-f272cdae` | `h33-2-b2; PRUNE <=3.2px, fixed 37654 dots; predicted +0.002 MODEL` | `releases/h33-h33-2-b2-PRUNEp3.2px-20261023-f272cdae.json` |

Human uploads **only one twin per slot**, then pastes the portal receipt into
`receipt_score` / `receipt_date` (with verbatim receipt evidence retained privately).
Check against actual upload history: blank ledger fields do not prove slots remain.
R0 0.2778 is CLAIM; the above predictions are MODEL, never live scores. A change
under 0.01 is no evidence. Slot 3 is reserved unless prior receipts support it.

**Corrections to historical sections below:** `SNAPscarp2px-fae77ff4` is HOLD
(min catalogue distance 2.2361 px; 2,171 dots <=3 px); moving only its additions
outside the collar does not satisfy the non-PRUNE rule. No label-relief probe is
recommended. Historical recommendations to upload SNAP in slot 2 or to spend a
RELIEF slot to probe label composition are withdrawn. Data-use terms for
preexisting public competition-derived rasters remain unchecked (IR-88-43).

---


> **Human competitor controls all uploads (`buffedlizard55-lab`, 1 entity, `<= 3` slots/week, 1 blind final file by `2026-12-03`).** Agent never logs into or fetches `drivendata.org` or `dropbox.com`. Candidate `.tif`/`.zip` rasters live locally in `releases/` (untracked in Git per `.gitignore` data-use policy; reproducible via `python3 scripts/build_snap_variants.py`, `python3 scripts/build_prune_variants.py`, `python3 scripts/build_prune_sweep_variants.py`, `python3 scripts/build_relief_variants.py` (R1 RELIEF family) and `python3 scripts/build_relief_r0_variants.py` (R0 RELIEF family)), with tracked SHA-256 receipts in `releases/*.json` and `ledger/submissions.csv`.

## This Session — R0 Family (`AXIS = RELIEF`, Band 12 `det_elev` Area Terciles, Dose `12%` = `4,518` Dots, Constant `N = 37,654`, Parent `h33-h33-2-b2`, Seed `20261023`; concurrent R1 family below, IR-88-38)

> **Reproduce:** `python scripts/build_relief_r0_variants.py` (rebuilds R0 byte-for-byte first; rasters are gitignored, SHA-256 receipts tracked). **Status: all three are `HOLD` and inherit R0's `2,171` collar dots (same disposition as the R0 `SNAP`/`CONCENTRATION` families). If a RELIEF label-relief probe is ever spent, prefer the gate-clean R1 arm `RELIEFup2t10` (`cffb5570`, below) over `range12`; see `SLOT_PLAN.md`.** Pre-registered predictions: `registry/relief_r0_preregistration.json`.

### `RELIEFrange12` (Least-Negative R0 Arm — Diagnostic Only): 12% of dots (4,518) basin+piedmont -> range tercile
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

## This Session — R1 Family (`AXIS = RELIEF`, parent `R1 = PRUNEp3px`, `N = 37,654`, fixed count; PR #28)

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

## Concurrent RELIEF Bracket Family (`rng2bas12` / `rng2pmt12` / `bas2rng12`, also `HOLD` — IR-88-38)

A second session independently built single-source 12% brackets on the same parent/terciles (`scripts/build_relief_bracket_variants.py`, predictions preregistered in `registry/relief_preregistration.json`). Same conclusion as above: **do not upload**; two builds now agree (basinward SGMC `0.08490`/`0.08502 PROXY`). All three: `37,654` dots, `4,518 (12.00%)` moved, `min d_cat 3.1623 px`, Band 12 terciles `q1=-142.8321 m`, `q2=+38.5885 m`; full receipts in `evidence/relief_axis_report.json`.

- **`rng2bas12` (range→basin):** primary `releases/…-RELIEFrng2bas12-20261023-56093882.tif` (`SHA-256 560938824a6ddae52e45662fe506b7d0f5dea6191746ab517869d5e1205307bb`, `350,762` B) / fallback `…-56093882-zeros.tif` (`a34a51c176fcd53069aa6e7e3d7ea463efca28a833e84b12df9e506c930a6737`, `215,369` B). **Name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFrng2bas12-20261023-56093882`. **Form note (95/140):** `R1(6f7ae705); RELIEF range->basin 12% (4518) B12 terciles, 37654, >3px; pred +0.008 MODEL vs R1`. Shares →`32.42/41.74/25.83%`; `w`-DTI `-0.006988 MODEL`; SGMC `0.085018 PROXY`; CV `0.6048`.
- **`rng2pmt12` (range→piedmont):** `…-RELIEFrng2pmt12-20261023-52717cf5.tif` (`52717cf542642a2f9304d077f462dd0973d1f6b87f811c8d3b4039ff18c82521`, `351,997` B) / `…-52717cf5-zeros.tif` (`a69c94ecbc73ebb465be4cd82bc66898b1e7a58d69fb1f48ad4b17647711502d`, `215,849` B). **Form note (98/140):** `R1(6f7ae705); RELIEF range->piedmont 12% (4518) B12 terciles, 37654, >3px; pred +0.002 MODEL vs R1`. Shares →`20.42/53.74/25.83%`; SGMC `0.085812`; CV `0.5836`.
- **`bas2rng12` (basin→range):** `…-RELIEFbas2rng12-20261023-f4c6dc18.tif` (`f4c6dc18f0cf5b2fa22f0c54374d1d3e7c782ef6246136e71770c188cbf6d663`, `350,381` B) / `…-f4c6dc18-zeros.tif` (`6902c7391b6c50487ef86bbac82f7167522165d1102062f689a7601c831931f4`, `214,118` B). **Form note (95/140):** `R1(6f7ae705); RELIEF basin->range 12% (4518) B12 terciles, 37654, >3px; pred -0.010 MODEL vs R1`. Shares →`8.42/41.74/49.83%`; SGMC `0.093903`; CV `0.6724`.

Ledger after all reconciliations: `32` BUILT rows, `0 RECEIPT`.

## Other Reconciled Ledger Inventory (`HOLD` — `ledger/submissions.csv`)
- **Unspaced `SNAP` (`SNAPw2E1` `01cf9e98` `MODEL -0.002`, `SNAPw2S2` `60ced8c7` `MODEL -0.001`, `SNAPw2E2` `861cd355` `MODEL -0.002`):** `HOLD` due to along-strike bunching (`min_sep = 1 px`, `SGMC` delta `-0.0080` to `-0.0040`); superseded by spacing-locked `SNAPscarp2px` (`fae77ff4`, `d_nn >= 2.8284 px`, `SGMC +0.00075`).
- **`CONCENTRATION` (`CONCb10px-m10` `89ffd4f3` `+0.011`, `CONCb10px-m20` `c42cd475` `+0.020`, `CONCb50px-m20` `fae2a52f` `+0.006`, `CONCENTRATION15pct` `4dfb83f6` `+0.008`):** `HOLD` under literal non-PRUNE `>=3 px` gate (`R0`'s `2,171` `2–3 px` dots inherited); re-base atop `PRUNEp3px` in Week 2.
- **`MASS` (`MASSm10minus` `7132935e`, `MASSm10plus` `82673b57`, `MASSm20minus` `6c73303c`):** `HOLD` per `registry/mass_ranking_audit.json`.

## Format Gate Verification Summary
- All `SNAP`, `PRUNE` and all three `RELIEF` families' GeoTIFFs (`EPSG:32611`, `3730×3292`, `Affine(100,0,243350,0,-100,4508550)`, `1` band `float32`, `[0,1]`, `0` NaN inside footprint, `0` on catalogue, unique SHA-256) re-read and verified in `tests/test_snap_axis.py`, `tests/test_prune_axis.py`, `tests/test_relief_axis.py`, `tests/test_relief_bracket_axis.py`, `tests/test_relief_r0_axis.py`, `tests/test_prune_sweep_variants.py`, and independent `scripts/validate_variant.py` (PASS on every twin checked).

## Current R0 PRUNE Collar Dose Sweep — Human Upload Only

**No upload was made by the agent.** These are three reproducible PRUNE experiments from exact parent `R0 = h33-h33-2-b2`; choose at most one per live slot. The `.tif` primary has NaN outside the footprint. The matching `-zeros.tif` is a fallback with zero outside; never upload both for one slot. Raster files and ZIPs are local-only/ignored by Git because data-use terms are unchecked.

- **Entity/budget:** one human competitor; the last repository-reported count is `3/3` weekly slots remaining and about `21` total, to be re-confirmed by the human.
- **TOP_PUBLIC:** `0.4413`, dated `2026-10-22`, human-supplied and not portal-verified here.
- **R0 score:** `0.2778` is **CLAIM** (no receipt logged). Candidate changes below are **MODEL**, never scores.

### Candidate files, names, and form notes

### 1. `PRUNEp3.2px` — 320 m collar
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3.2px-20261023-f272cdae.tif`
- **Fallback:** `releases/h33-h33-2-b2-PRUNEp3.2px-20261023-f272cdae-zeros.tif`
- **Submission name:** `h33-h33-2-b2-PRUNEp3.2px-20261023-f272cdae`
- **Form note (91/140 chars):** `R0 h33-h33-2-b2; PRUNE <= 3.2px (320m), fixed N=37,654, exact DTI refill; pred +0.002 MODEL`
- **Identity:** primary SHA-256 `f272cdaeb638b9051848e61492c009695643d3d6e53b3d62ce1ad234ff748be5`; fallback SHA-256 `d53a2fadee165452282fb4d8b2be6facf0e7e5eb00c1cf94d6a606ff3d5dbbae`.
- **Parent difference:** 2,702 removed + 2,702 added; **7.17586% moved**; min catalogue distance `3.6056 px`.

### 2. `PRUNEp3.7px` — 370 m collar
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3.7px-20261023-5508b0b9.tif`
- **Fallback:** `releases/h33-h33-2-b2-PRUNEp3.7px-20261023-5508b0b9-zeros.tif`
- **Submission name:** `h33-h33-2-b2-PRUNEp3.7px-20261023-5508b0b9`
- **Form note (91/140 chars):** `R0 h33-h33-2-b2; PRUNE <= 3.7px (370m), fixed N=37,654, exact DTI refill; pred -0.005 MODEL`
- **Identity:** primary SHA-256 `5508b0b9ed9279001297162f357cb11eccb339018941d5e5306626335a8f8a88`; fallback SHA-256 `4a2c0b94bca1d533d4b4203855e2f650de03de3903c45899e1df5a5f32c47c3f`.
- **Parent difference:** 3,361 removed + 3,361 added; **8.92601% moved**; min catalogue distance `4.0000 px`.

### 3. `PRUNEp4.3px` — 430 m collar
- **Primary:** `releases/h33-h33-2-b2-PRUNEp4.3px-20261023-21fa2b26.tif`
- **Fallback:** `releases/h33-h33-2-b2-PRUNEp4.3px-20261023-21fa2b26-zeros.tif`
- **Submission name:** `h33-h33-2-b2-PRUNEp4.3px-20261023-21fa2b26`
- **Form note (91/140 chars):** `R0 h33-h33-2-b2; PRUNE <= 4.3px (430m), fixed N=37,654, exact DTI refill; pred -0.013 MODEL`
- **Identity:** primary SHA-256 `21fa2b2653cf40e48d2436722dc67fe5492b8f07c7d6c8ace81ee50de0a03694`; fallback SHA-256 `ee20c1b843f776e01a41992406b17fbe8d03e3aa46ee381a6bbc13b4d0379fa3`.
- **Parent difference:** 4,488 removed + 4,488 added; **11.91905% moved**; min catalogue distance `4.4721 px`.

## Format receipt and remaining human action

All three primaries and zero-outside fallbacks passed the independent on-disk `validate_variant.py` checks in [`registry/prune_sweep_validation.json`](../registry/prune_sweep_validation.json): GeoTIFF, one `float32` band, `EPSG:32611`, sample shape/transform, values `[0,1]`, no NaN inside, NaN outside on primary, zero outside on fallback, zero catalogue mass, unique SHA-256, fixed count, and disk re-read. Each fallback also passed the strict all-finite format audit (`releases/*-format-audit.json`). This is **format validation only**, not approval to spend a slot. The report-only hide/recover PROXY is degenerate at zero for the `>3 px` collar and is not a gate; blind SGMC values are also PROXY, not competition scores.

**Human:** reconfirm TOP_PUBLIC, deadline, rolling-week/total slot counts, and any live receipt. Select one file manually if desired; after a submission, fill `receipt_score` and `receipt_date` verbatim in `ledger/submissions.csv`. The agent never logs in or submits.
