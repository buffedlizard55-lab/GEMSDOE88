# Submission Checklist — Human Uploads ONE File per Slot (DrivenData #306)

> **Human competitor controls all uploads (`buffedlizard55-lab`, 1 entity, `<= 3` slots/week, 1 blind final file by `2026-12-03`).** Agent never logs into or fetches `drivendata.org` or `dropbox.com`. Candidate `.tif`/`.zip` rasters live locally in `releases/` (untracked in Git per `.gitignore` data-use policy; reproducible via `python3 scripts/build_prune_variants.py`), with tracked SHA-256 receipts in `releases/*.json` and `ledger/submissions.csv`. Confirm selector stance on the 4 space-covering calibration witnesses (`README.md`) before spending a slot.

## Recommended Session Candidates (`AXIS = PRUNE`, Constant `N = 37,654`, Parent `h33-h33-2-b2`, Seed `20261023`)

### Slot 1 (Recommended Primary): `p3px` — Exact `300 m` Kernel-Radius Collar + Physics Marginal-DTI Refill
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.tif` (`SHA-256`: `6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9`, `354,519` B; `.zip` `7e9929cb6b6d81ef5fe5ce77985d41e3b60c2a0125bf2d9146265a899a9664c3`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-zeros.tif` (`SHA-256`: `dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f`, `218,257` B; `.zip` `feba12d64278dbedf8a2dcd874f9c02246a1cc320ca59a928cb9a58352a32638`)
- **Submission Name:** `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`
- **Form Note (`103 / 140` chars):** `h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL`
- **Stats & Receipt:** `37,654` dots (`-2,171` in `2 < d_cat <= 3 px`, `+2,171` on `H19-5` ridges at `d_cat > 3 px`; **`5.77%` moved**, `min d_cat = 3.1623 px`, `0` on catalogue). Blind USGS `SGMC` `0.096083` `PROXY` (highest of sweep); `12 km` CV `0.5700`. Tracked receipt: `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.json`.

### Slot 2 (Lower Collar Bracket): `p1px` — `100 m` Flank Restoration at Fixed `N = 37,654`
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp1px-20261023-0542a27c.tif` (`SHA-256`: `0542a27cd3518f3f5cd6d7b48ff8e2de50e81b233cbc6ffb343b254b241314ac`, `355,283` B; `.zip` `4a939dc1b8f7fb65b38d6f4c92ab11a29adfb10734d6b3f788db00f0fc260770`)
- **Fallback GeoTIFF (`0.0` outside):** `releases/h33-h33-2-b2-PRUNEp1px-20261023-0542a27c-zeros.tif` (`SHA-256`: `d4a16a38ccc276e897458a258d882f3905c3bf7494162ac9967d22b4131818d3`, `219,051` B; `.zip` `782e265464c4495868b7d87f6d6b9a9f9ab92f674868dc4ba7a75604cc3017c3`)
- **Submission Name:** `h33-h33-2-b2-PRUNEp1px-20261023-0542a27c`
- **Form Note (`99 / 140` chars):** `h33-2-b2; PRUNE <=1px held at 37654 (+2545 1-2px flank, -2545 low marginal gain); pred -0.006 MODEL`
- **Stats & Receipt:** `37,654` dots (`+2,545` `SOLO-D2.8` flank dots in `1 < d_cat <= 2 px`, `-2,545` lowest marginal-gain off-collar dots; **`6.76%` moved**, `min d_cat = 1.4142 px`). Holdout-DTI `0.030145` `[0.026907, 0.033396]` (`n=22,663`) `PROXY`; `SGMC` `0.090926` `PROXY`; `12 km` CV `0.5647`. Tracked receipt: `releases/h33-h33-2-b2-PRUNEp1px-20261023-0542a27c.json`.

### Slot 3 (Upper Collar Bracket): `p4px` — `400 m` Halo Collar at Fixed `N = 37,654`
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp4px-20261023-be9fd3d5.tif` (`SHA-256`: `be9fd3d5e8b8cc74a41701a50e88dbed3d6600f02c149262064f57004b188698`, `353,307` B; `.zip` `fabb94143da21536d6ebfdc1fbcb44fb9c860ebb62858dacf0b1de17f96d8f5d`)
- **Fallback GeoTIFF (`0.0` outside):** `releases/h33-h33-2-b2-PRUNEp4px-20261023-be9fd3d5-zeros.tif` (`SHA-256`: `6dd6e0af7e6936f7a8f06625895d29137769c20243865d5c31ea61947a54f4f9`, `217,306` B; `.zip` `6db7a6425da608fd03a54083c31d426cd268a6a185e97ad054652461851529e5`)
- **Submission Name:** `h33-h33-2-b2-PRUNEp4px-20261023-be9fd3d5`
- **Form Note (`103 / 140` chars):** `h33-2-b2; PRUNE <=4px held at 37654 (-3825 in 2-4px, +3825 exact marginal gain >4px); pred -0.009 MODEL`
- **Stats & Receipt:** `37,654` dots (`-3,825` in `2 < d_cat <= 4 px`, `+3,825` at `d_cat > 4 px`; **`10.16%` moved**, `min d_cat = 4.1231 px`). `SGMC` `0.094465` `PROXY`; `12 km` CV `0.5937`. Tracked receipt: `releases/h33-h33-2-b2-PRUNEp4px-20261023-be9fd3d5.json`.


## AXIS = SNAP Variants (`scripts/build_snap_variants.py`, seed `20261023`, parent `h33-h33-2-b2`) — ALL `HOLD`

Three controlled edits of `R0`; each moves dots `<=2 px` onto a potential-field edge maximum, holds the count at `37,654`, and forbids destinations on the catalogue or within `3 px` of it. Rationale and the negative result are in `SLOT_PLAN.md`; hashes below are from the tracked receipts.

### `w2E1` — `SNAP`, window `<=2 px`, count held at `37,654` (`HOLD`, negative PROXY)
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-SNAPw2E1-20261023-01cf9e98.tif` (`SHA-256`: `01cf9e9851dc47b282f15fa7edd35c9afc9e8841fc255c116066f70fd8eb2669`, `354,938` B; `.zip` `c2d5d81b092e71ed315ddde720fc1a8016f8f161dc3ea88ac34c826fe99dd539`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-SNAPw2E1-20261023-01cf9e98-zeros.tif` (`SHA-256`: `135b42b8909d04a4b4bde81d1187eaea65679823b511962c5dafa3f98858ffec`, `219,097` B; `.zip` `7e6a8f793f52aa9990d2c32803cee9de0447a9797b105daa5245dc9d44b0d40f`)
- **Submission Name:** `h33-h33-2-b2-SNAPw2E1-20261023-01cf9e98`
- **Form Note (`74 / 140` chars):** `h33-2-b2; SNAP<=2px to max |grad rtp+igrav|; 37654 held; pred -0.002 MODEL`
- **Format receipt:** `scripts/validate_variant.py` **PASS** on both files (CRS/shape/transform/dtype/band, `[0,1]`, `0` NaN inside footprint, NaN-or-0 outside, `0` on catalogue, `0` within `2 px`, unique SHA-256). Parent diff: `-35,771` / `+35,771` dots (`95.0%` moved), `min d_cat 2.2361 px`, `644` dots left in the `2–3 px` collar. Blind SGMC `PROXY` `0.088098` (Δ `-0.00796` vs `R0`), `12 km` CV `0.5582`.
- **Why it is `HOLD`:** blind off-catalogue SGMC DTI **fell** vs `R0`; predicted live change is `MODEL -0.002 … -0.001`, below the `0.01` evidence bar, and it inherits `R0`'s `2–3 px` collar. Upload only if the human wants the axis retired with a live receipt; it is not a slot-1 candidate.

### `w2S2` — `SNAP`, window `<=2 px`, count held at `37,654` (`HOLD`, negative PROXY)
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-SNAPw2S2-20261023-60ced8c7.tif` (`SHA-256`: `60ced8c7129f90730ccd6e867d7d837fae2b58b695052ff9ce73119cf00f05c1`, `355,660` B; `.zip` `c887f62a2e00397f5576e1360bf5802f2b39d1fed006a628dadb06975f19183d`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-SNAPw2S2-20261023-60ced8c7-zeros.tif` (`SHA-256`: `68e5f41b1b077966695fbe5faeb4f30d81fbd29bc26867abb9ec548e0999e1eb`, `219,400` B; `.zip` `61c5febb0b89f37830bd5fea073fc3c5f9c951000eb3bd058c05d6f8fb850835`)
- **Submission Name:** `h33-h33-2-b2-SNAPw2S2-20261023-60ced8c7`
- **Form Note (`75 / 140` chars):** `h33-2-b2; SNAP<=2px to 200m-scale edge, gain>=0.25z only; pred -0.001 MODEL`
- **Format receipt:** `scripts/validate_variant.py` **PASS** on both files (CRS/shape/transform/dtype/band, `[0,1]`, `0` NaN inside footprint, NaN-or-0 outside, `0` on catalogue, `0` within `2 px`, unique SHA-256). Parent diff: `-19,617` / `+19,617` dots (`52.1%` moved), `min d_cat 2.2361 px`, `1565` dots left in the `2–3 px` collar. Blind SGMC `PROXY` `0.092105` (Δ `-0.00396` vs `R0`), `12 km` CV `0.5578`.
- **Why it is `HOLD`:** blind off-catalogue SGMC DTI **fell** vs `R0`; predicted live change is `MODEL -0.002 … -0.001`, below the `0.01` evidence bar, and it inherits `R0`'s `2–3 px` collar. Upload only if the human wants the axis retired with a live receipt; it is not a slot-1 candidate.

### `w2E2` — `SNAP`, window `<=2 px`, count held at `37,654` (`HOLD`, negative PROXY)
- **Primary GeoTIFF (`NaN` outside):** `releases/h33-h33-2-b2-SNAPw2E2-20261023-861cd355.tif` (`SHA-256`: `861cd35571845bd5392baa91ee621ceb912c3381d6a50e312a5fec37a6f08f5e`, `354,584` B; `.zip` `810701ca1c3af65684dab9a06f11271f487d11784f71cfc6676cbda2028e5209`)
- **Fallback GeoTIFF (`0.0` outside, identical inside):** `releases/h33-h33-2-b2-SNAPw2E2-20261023-861cd355-zeros.tif` (`SHA-256`: `3f999d79ce5b4466ef9b5bb76ecb877ffa35e85c6808baf871a39d440084e5d5`, `218,699` B; `.zip` `c07d4b594a049cb37e619c96d0b70b3e53e5e74e8b9d48d43af42b54bd27780c`)
- **Submission Name:** `h33-h33-2-b2-SNAPw2E2-20261023-861cd355`
- **Form Note (`78 / 140` chars):** `h33-2-b2; SNAP<=2px on organizer tmi/igrav derivative bands; pred -0.002 MODEL`
- **Format receipt:** `scripts/validate_variant.py` **PASS** on both files (CRS/shape/transform/dtype/band, `[0,1]`, `0` NaN inside footprint, NaN-or-0 outside, `0` on catalogue, `0` within `2 px`, unique SHA-256). Parent diff: `-35,725` / `+35,725` dots (`94.88%` moved), `min d_cat 2.2361 px`, `579` dots left in the `2–3 px` collar. Blind SGMC `PROXY` `0.088113` (Δ `-0.00795` vs `R0`), `12 km` CV `0.5575`.
- **Why it is `HOLD`:** blind off-catalogue SGMC DTI **fell** vs `R0`; predicted live change is `MODEL -0.002 … -0.001`, below the `0.01` evidence bar, and it inherits `R0`'s `2–3 px` collar. Upload only if the human wants the axis retired with a live receipt; it is not a slot-1 candidate.

## Latest CONCENTRATION 15% (`HOLD` — inherited collar)

- **File:** `releases/h33-h33-2-b2-CONCENTRATION15pct-20261023-4dfb83f6.tif`
- **Fallback:** `releases/h33-h33-2-b2-CONCENTRATION15pct-20261023-4dfb83f6-zeros.tif`
- **Name:** `h33-h33-2-b2-CONCENTRATION15pct-20261023-4dfb83f6`
- **Note:** `h33-2-b2; CONC 15% in 1km gradient blocks; count 37654; pred +0.008 MODEL`
- **SHA-256:** `4dfb83f6a97f4265e442a3f1ed156986d3c25eb9ebb5e8d49d3784b5cec1eb43`
- **Receipt:** 37,654 dots; 5,648 removed + 5,648 added; float32 EPSG:32611; sample shape/transform; finite [0,1] inside; NaN outside; zero catalogue mass; disk re-read. **Do not upload:** minimum catalogue distance √5 px fails the literal ≥3 px non-PRUNE constraint. Re-base on PRUNEp3 first.

## Other Reconciled Ledger Inventory (`HOLD` / Superseded — `ledger/submissions.csv`)
- **Score-blind `PRUNE=3` (`h33-h33-2-b2-prune3-20261023-01d57649`, `MODEL -0.003`):** Superseded by physics-ranked `PRUNEp3px` (`6f7ae705`, `MODEL +0.005`).
- **`CONCENTRATION` (`CONCb10px-m10` `89ffd4f3` `+0.011`, `CONCb10px-m20` `c42cd475` `+0.020`, `CONCb50px-m20` `fae2a52f` `+0.006`):** `HOLD` under strict non-PRUNE `>=3 px` gate because they inherit `R0`'s `2,171` `(2, 3] px` dots; clean Week-2 follow-up applies concentration directly atop `PRUNEp3px` (`>3 px`).
- **`MASS` (`MASSm10minus` `7132935e`, `MASSm10plus` `82673b57`, `MASSm20minus` `6c73303c`):** `HOLD` per `registry/mass_ranking_audit.json` (`0.6*dist + 0.4*uniform` ranking).

## Format Gate Verification Summary
- All `6` `PRUNE` GeoTIFFs and all `6` `SNAP` GeoTIFFs (`EPSG:32611`, `3730×3292`, `Affine(100,0,243350,0,-100,4508550)`, `1` band `float32`, `[0,1]`, `0` NaN inside footprint, `0` on catalogue, unique SHA-256) re-read and verified in `tests/test_prune_axis.py`. After human upload, record verbatim `receipt_score` + `receipt_date` in `ledger/submissions.csv`.
