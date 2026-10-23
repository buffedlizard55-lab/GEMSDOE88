# Submission Checklist — Human Uploads ONE File per Slot (DrivenData #306)

## Concurrent sessions — 2026-10-23 SPACING + SNAP audit (both supersede every historical upload card below)

### SPACING (3 built, all HOLD; slots unchanged; report only)

**No upload recommended. Human uploads at most one twin per slot and pastes each
portal receipt into `receipt_score` / `receipt_date`.** Parent `R1 =
h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` rebuilt with both hashes asserted
(`6f7ae705…` / `dc6f090d…`); all three arms share 1,914 greedy-decluster donors
(**5.08%** changed, `10.16%` symmetric difference) and differ only in receiver
geometry on un-emitted H19-5 at `d_cat > 3 px` (`min d_cat = 3.1623 px`, `0` on
catalogue, `37,654` dots). Reproduce: `python scripts/build_spacing_variants.py`
(predictions frozen in `registry/spacing_preregistration.json`). Rasters are
local-only (gitignored); tracked SHA-256 receipts in `releases/*.json`,
independent twin validation in `registry/spacing_variant_validation.json`
(6/6 PASS), mechanism cards in `ledger/mechanism_cards.json`. All three arms are
sub-threshold diagnostics (`|MODEL| <= 0.004`, `|SGMC delta| < 0.001` vs R1
`0.096083` PROXY); the conditional slot order (`p3px` → `p3space35`, PR #34) is
unchanged by SPACING. Reconciled with the concurrent refill-mode arms (IR-88-48);
ledger now holds 38 rows.
Hide-and-recover is degenerate `0.000000` (`n = 22,663`) for every `> 3 px` file.

### `SPACINGpoisson28-60f65400` (MODEL +0.003; declustered-parent candidate, HOLD)
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SPACINGpoisson28-20261023-60f65400.tif` (`SHA-256 60f654005114eb6542cbc31135d15314adb8892c6e3d5abe72f9f4de743aa7f6`, `354,671` B; `.zip  fec70e909de1…`)
- **Fallback:** `…-SPACINGpoisson28-20261023-60f65400-zeros.tif` (`SHA-256 6816852c233ca9a1dc82d9bd06e10fa784fed02eea5d1089d58b01b4d4586442`, `218,130` B; `.zip 5c59492ff572…`)
- **Form note (98/140):** `R1(6f7ae705); SPACING poisson farthest-point 5.08% (1914) on H19-5, 37654, >3px; pred +0.003 MODEL`
- **Stats:** greedy farthest-point receivers (median `2.236 px` from survivors, `0%` within `1.5 px`, min NN `2.2361 px`); SGMC `0.096820` PROXY (`+0.000737` vs R1); `12 km` CV `0.5808`.

### `SPACINGstrike-bc8e6d1a` (MODEL +0.000; line-continuity probe, HOLD)
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SPACINGstrike-20261023-bc8e6d1a.tif` (`SHA-256 bc8e6d1ae803109fb99f3fbfe95636980f40f39884564a24970a78671065aee1`, `354,072` B; `.zip b8c44402e896…`)
- **Fallback:** `…-SPACINGstrike-20261023-bc8e6d1a-zeros.tif` (`SHA-256 4a3d3dbfbaaa45cda1f69099df688de43463182de38f5729442de2c5cd2a0df1`, `218,017` B; `.zip d89515f32745…`)
- **Form note (98/140):** `R1(6f7ae705); SPACING along-strike receivers 5.08% (1914) on H19-5, 37654, >3px; pred +0.000 MODEL`
- **Stats:** along-strike receivers (median `|cos| 1.000`, median `1.0 px` from survivors, min NN `1.0 px`); SGMC `0.095396` PROXY (`-0.000687` vs R1); `12 km` CV `0.5741`.

### `SPACINGlattice4px-6c7e0b72` (MODEL -0.004; negative control, HOLD)
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SPACINGlattice4px-20261023-6c7e0b72.tif` (`SHA-256 6c7e0b72fb089eb057af5ce2e89a5511cd26d4d4690aa3c88a54fdfc202e15c7`, `353,950` B; `.zip 777b9ced5b67…`)
- **Fallback:** `…-SPACINGlattice4px-20261023-6c7e0b72-zeros.tif` (`SHA-256 2690408c607e67e8d4cc541fd7209ce2cf09f2a7989c3744b48652f53d57f664`, `217,591` B; `.zip a3dfb921e19e…`)
- **Form note (97/140):** `R1(6f7ae705); SPACING 4px-lattice receivers 5.08% (1914) on H19-5, 37654, >3px; pred -0.004 MODEL`
- **Stats:** 4 px lattice receivers (`100%` on-node, median `1.0 px` from survivors, min NN `1.0 px`); SGMC `0.095292` PROXY (`-0.000791` vs R1); `12 km` CV `0.5833`. Lattice period (400 m) equals the GeoDAWN line spacing; phase `(0,0)` frozen, never tuned.

---

### SNAP audit (concurrent; AXIS = SNAP, 0 new variants, HOLD retained)

**No new variant, no upload.** R0 matched both pinned SHA-256s after
all 15 manifest hashes/byte sizes passed. Its 1,611 dots inside the 3 px collar
include **30 with no compliant pixel <=2 px away**: no pure R0 SNAP can pass the
non-PRUNE clearance rule (`evidence/session_20261023_snap_clearance.json`).
Do not substitute a PRUNE refill and call it SNAP. No row was added by this
session; the concurrent PRUNE refill-mode merge brought the ledger to **35 BUILT,
zero portal RECEIPTs**. The audit ran against 32 earlier rows.

**Existing, not new: PRUNE p1/p3/p4 were recreated byte-exactly** from pinned
inputs. All six TIFFs (primary NaN-outside and zeros-outside fallback) were
re-read from disk and passed CRS/3730×3292 shape/transform/float32/band count,
finite [0,1] inside, outside encoding, zero catalogue mass, exact ledger SHA,
parent-diff, and twin/one-file ZIP checks. Audit:
`evidence/session_20261023_prune_revalidation.json`. These reproduced PRUNE
rasters are gitignored (older unrelated TIFFs were tracked, see IR-88-43);
scripts `rebuild_prune_artifacts.py` and `validate_variant.py` reproduce
and check local files. Do not treat this local validation as a portal receipt.

**Potential slot 1 (conditional only):**
- **Name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`
- **Primary file:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.tif`
  (NaN outside; SHA-256 `6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9`).
- **Fallback, never an extra submission:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-zeros.tif`
  (zeros outside; SHA-256 `dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f`).
- **Form note (103/140 chars, copied from existing receipt):**
  `h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL`
- **Mechanism:** remove 2,171 R0 collar dots and exact-marginal refill at fixed
  37,654 count (5.7657% changed, min catalogue distance 3.1623 px). Predicted
  live delta **MODEL +0.005**, *not* a score; an actual |delta|<0.01 is no evidence.

**Do not upload until the human confirms** TOP_PUBLIC/date, rolling-week/total
slots, 2026-12-03 deadline on the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/),
R0's actual portal receipt (0.2778 remains CLAIM), and permissions for public
input mirrors / previously tracked competition rasters. The agent has not fetched
the portal or rules. Human independently checks the exact bytes and uploads **one**
file per slot from their own account, then records verbatim `receipt_score` and
`receipt_date` on the existing ledger row with private receipt evidence (no
credentials). If p3 materially **loses**, close the collar family rather than
spend slot 2 reflexively. If it wins or is inconclusive, the human may consider
already-BUILT `PRUNEp3space35-49fff49b` (MODEL +0.007) as a separate,
spacing/refill-support test. Its TIFFs are **not present in this checkout**;
rebuild them at the exact ledger hashes and re-run the independent validator
before any upload. Only after a material improvement over p3space35 should the
human reserve slot 3 for `PRUNEp4space35-07bd8182` (MODEL +0.002, also absent
locally). Their full filenames, hashes, and form notes appear in the historical
PRUNE refill-mode section below; neither its SGMC PROXY nor its field MODEL is
a live result (`SLOT_PLAN.md`). Revalidate the chosen exact file immediately
before upload.

**HOLD:** all R0 SNAP/CONCENTRATION/RELIEF arms retaining sub-3-px dots,
including `SNAPscarp2px-fae77ff4`; no label-relief probe. Any contrary upload
suggestion in the archived sections below is withdrawn. PRUNEp1's <3 px mass
is allowed by the PRUNE exception, but it is a diagnostic rather than a lead.

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

## Session `2026-10-23f` — `AXIS = PRUNE` with a spacing-locked refill (`arena/0c47b598-gemsdoe88`)

Built three arms of `R0 = h33-h33-2-b2` that separate the **collar purge** from the **refill** for the first time. Files (gitignored locally, SHA-256 receipts tracked):

### `h33-h33-2-b2-PRUNEp3norefill-20261023-fb308615`
- **File:** `releases/h33-h33-2-b2-PRUNEp3norefill-20261023-fb308615.tif` (primary, NaN outside the footprint) · fallback `releases/h33-h33-2-b2-PRUNEp3norefill-20261023-fb308615-zeros.tif`
- **Submission name:** `h33-h33-2-b2-PRUNEp3norefill-20261023-fb308615`
- **Form note (68 / 140):** `R0 h33-2-b2; PRUNE<=300m no refill -2171, N 35483; pred +0.003 MODEL`
- **SHA-256:** `fb308615161ad8f62b063d90972a4c36e7c66e7c58beb3316c81497cfe65261e` (primary) · `a438e92b79dfb7f9f1763c40ffb2d42dd60e45697dfc06fc49efae067d3c1a22` (zeros fallback)
- **Change:** collar `<= 3 px`, remove `2171`, add `0` (no refill); `N = 35,483`; `5.77000%` moved, `5.77000%` symmetric difference.
- **Format receipt (re-read from disk):** CRS `EPSG:32611`, `3730 x 3292`, transform matches `sample_submission.tif`, `float32`, 1 band, values in `[0,1]`, finite inside / NaN outside, **0 mass on the catalogue**, `min d_cat = 3.1623 px`, SHA-256 absent from the ledger before write, independent `scripts/validate_variant.py` `PASS`.
- **Report-only:** four-line field `MODEL 0.270354` (`-0.015708` vs R0); blind off-catalogue `SGMC` `PROXY 0.093643`; hide-and-recover `PROXY 0.000000` (degenerate, `n=22,663`, no weight).
- **Prediction (MODEL, registered before instruments):** `+0.003` vs R0, range `[-0.008, 0.012]`. Not a score.

### `h33-h33-2-b2-PRUNEp3space35-20261023-49fff49b`
- **File:** `releases/h33-h33-2-b2-PRUNEp3space35-20261023-49fff49b.tif` (primary, NaN outside the footprint) · fallback `releases/h33-h33-2-b2-PRUNEp3space35-20261023-49fff49b-zeros.tif`
- **Submission name:** `h33-h33-2-b2-PRUNEp3space35-20261023-49fff49b`
- **Form note (80 / 140):** `R0 h33-2-b2; PRUNE<=300m +2171 refill >=3.5px spaced, N 37654; pred +0.007 MODEL`
- **SHA-256:** `49fff49b03c47d7ac3822df185f1efd55b0b30855133360689754ce85167a61a` (primary) · `e0b9d59b765a198aa5327bb99bddf09fec52e2806410a403b63ccce2d204824e` (zeros fallback)
- **Change:** collar `<= 3 px`, remove `2171`, add `2171` (refill locked at `>= 3.5 px`, observed refill min NN `3.6056 px`); `N = 37,654`; `5.77000%` moved, `11.53000%` symmetric difference.
- **Format receipt (re-read from disk):** CRS `EPSG:32611`, `3730 x 3292`, transform matches `sample_submission.tif`, `float32`, 1 band, values in `[0,1]`, finite inside / NaN outside, **0 mass on the catalogue**, `min d_cat = 3.1623 px`, SHA-256 absent from the ledger before write, independent `scripts/validate_variant.py` `PASS`.
- **Report-only:** four-line field `MODEL 0.274896` (`-0.011165` vs R0); blind off-catalogue `SGMC` `PROXY 0.101042`; hide-and-recover `PROXY 0.000000` (degenerate, `n=22,663`, no weight).
- **Prediction (MODEL, registered before instruments):** `+0.007` vs R0, range `[-0.002, 0.018]`. Not a score.

### `h33-h33-2-b2-PRUNEp4space35-20261023-07bd8182`
- **File:** `releases/h33-h33-2-b2-PRUNEp4space35-20261023-07bd8182.tif` (primary, NaN outside the footprint) · fallback `releases/h33-h33-2-b2-PRUNEp4space35-20261023-07bd8182-zeros.tif`
- **Submission name:** `h33-h33-2-b2-PRUNEp4space35-20261023-07bd8182`
- **Form note (80 / 140):** `R0 h33-2-b2; PRUNE<=400m +3825 refill >=3.5px spaced, N 37654; pred +0.002 MODEL`
- **SHA-256:** `07bd8182ec4d542aa127601febb2eb37b1458885bce1941593bf846b85f4bb2a` (primary) · `fb7ee110c9ac96a32e53f7d9558bade00d6244f4b5622e35eab83264646e3766` (zeros fallback)
- **Change:** collar `<= 4 px`, remove `3825`, add `3825` (refill locked at `>= 3.5 px`, observed refill min NN `3.6056 px`); `N = 37,654`; `10.16000%` moved, `20.32000%` symmetric difference.
- **Format receipt (re-read from disk):** CRS `EPSG:32611`, `3730 x 3292`, transform matches `sample_submission.tif`, `float32`, 1 band, values in `[0,1]`, finite inside / NaN outside, **0 mass on the catalogue**, `min d_cat = 4.1231 px`, SHA-256 absent from the ledger before write, independent `scripts/validate_variant.py` `PASS`.
- **Report-only:** four-line field `MODEL 0.263231` (`-0.022830` vs R0); blind off-catalogue `SGMC` `PROXY 0.102454`; hide-and-recover `PROXY 0.000000` (degenerate, `n=22,663`, no weight).
- **Prediction (MODEL, registered before instruments):** `+0.002` vs R0, range `[-0.01, 0.014]`. Not a score.

Upload at most one file per slot; paste the portal receipt into `ledger/submissions.csv` (`receipt_score`, `receipt_date`).

---

## Phase 2 `AXIS = TRACKB` Deliverables (`2026-10-23` · Not a Weekly Slot Unless Human Decides)

Per Agent Brief v2 §5, `TRACKB` prepares the `$250k` Phase 2 structural-geologist fault-trace submission and is **not** queued for a weekly Phase 1 public-leaderboard slot unless the human explicitly overrides. All three variants are built from gate-clean `R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` (`min d_cat = 3.1623 px > 3.0 px`) via `.venv/bin/python scripts/build_trackb_variants.py` (`SEED = 20261023`) and pass PR #36's strict `< 3 px` non-PRUNE clearance gate in [`registry/trackb_variant_validation.json`](../registry/trackb_variant_validation.json).

- **Geologist vector deliverable (tracked):** [`evidence/trackb_traces_geologist.geojson`](../evidence/trackb_traces_geologist.geojson) (`SHA-256: 4a1d05415928b2f2ebf885fb6af3342fc60d9a1c88460e790ece43c0a2dbc305`, `1,259` strike-consistent `>= 1.0 km` `LineString` traces totaling `1,753.2 km`, WGS84 + UTM `EPSG:32611` endpoints + 1 geologist evidence paragraph per trace; top-25 dossier in [`evidence/trackb_geologist_dossier.md`](../evidence/trackb_geologist_dossier.md)).

### 1. Preferred Phase 2 Raster — `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtraceext10-20261023-05256d87`
- **Primary (`NaN` outside footprint):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtraceext10-20261023-05256d87.tif` (`SHA-256: 05256d87c0b46211b7c13f348e1dc02f1ede3f73b0169c788c7ccb00e504e859`)
- **Fallback (`0.0` outside if portal rejects `NaN`):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtraceext10-20261023-05256d87-zeros.tif` (`SHA-256: 16003173ddbe068541734cc638ec931ff824d9386d62f3026028fc79fb2dcf49`)
- **Form note (`92 / 140` chars):** `R1(6f7ae705); TRACKB 10% (3765) speckles->spaced >=2.8px >=1km trace tips; pred +0.004 MODEL`
- **Change & diagnostics (report-only, not scores):** `N = 37,654`, `10.00%` moved vs `R1` (`15.61%` vs `R0`), `min d_cat = 3.1623 px`, `added_min_nn = 2.8284 px`; preregistered `MODEL:+0.004` `[-0.008,+0.016]`; blind `SGMC = 0.09462 PROXY` (`-0.00146` vs `R1`, **`+0.00763` above `tracespine10` and `+0.00796` above `speckle10minus`**).

### 2. Pure Speckle-Cut Control — `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBspeckle10minus-20261023-3360100c`
- **Primary (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBspeckle10minus-20261023-3360100c.tif` (`SHA-256: 3360100cde278dd83de9da97664c1b2c0218155ee86a62dcfcd2062ebcc7e20a`)
- **Fallback (`0.0` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBspeckle10minus-20261023-3360100c-zeros.tif` (`SHA-256: aa655ef6082b4ffe18a823a03c81b00cc948789f195196631150d16f0ea7e3eb`)
- **Form note (`92 / 140` chars):** `R1(6f7ae705); TRACKB -10% (3765) isolated <450m speckles off >=1km traces; pred +0.003 MODEL`
- **Change & diagnostics:** `N = 33,889`, `-10.00%` vs `R1` (`0` added), `min d_cat = 3.1623 px`; preregistered `MODEL:+0.003` `[-0.008,+0.012]`; blind `SGMC = 0.08666 PROXY` (`-0.00942` vs `R1`).

### 3. Continuous-Spine Control — `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtracespine10-20261023-a3a183d1`
- **Primary (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtracespine10-20261023-a3a183d1.tif` (`SHA-256: a3a183d163d1dec0b230b559bef46113c35dbb2f7f1e9ec46bc1e57e10c9947d`)
- **Fallback (`0.0` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtracespine10-20261023-a3a183d1-zeros.tif` (`SHA-256: be47ad67baf2f6bb15b91b26ebd9a00ef44e2459867fe2591e74c7ba0436cf66`)
- **Form note (`88 / 140` chars):** `R1(6f7ae705); TRACKB 10% (3765) speckles->100m spines of >=1km traces; pred -0.003 MODEL`
- **Change & diagnostics:** `N = 37,654`, `10.00%` moved vs `R1` onto `100 m` spines, `min d_cat = 3.1623 px`; preregistered `MODEL:-0.003` `[-0.012,+0.006]`; blind `SGMC = 0.08700 PROXY` (`-0.00909` vs `R1` — confirms `100 m` spine saturation tax, IR-88-49).
