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

## SNAP Candidates (Built 2026-10-23 — Conditional: Submit ONLY After a PRUNEp3px Receipt)

Parent for all three: `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` (N=37,654, all dots >3 px from catalogue; regenerate locally with `python3 scripts/build_snap_variants.py`, rasters stay gitignored per data-use policy). Edge: provided TMI/gravity horizontal-gradient bands (3 `tmi_hg`, 18 `iso_grav_anom_hg`).

### Conditional Slot A (preferred SNAP): `r2g` — Gain-Gated ≤2 px Snap
- **Primary (`NaN` outside):** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPr2g-20261023-06b3ac6a.tif` (`06b3ac6a74c04e8b09c0c94db72dbd9cdeeece838d3d59a323ccb418dc1e26b9`, 354,539 B) · **Fallback (`0.0` outside):** `…-SNAPr2g-20261023-06b3ac6a-zeros.tif` (`e4980110ff7149eab12011db8fcfb0177a97f09793421d5769c8932ee8bed5db`)
- **Form note (97/140):** `PRUNEp3px; SNAP r2g <=2px gain>=.05 to max TMI/grav HG, N=37654 held, all >3px; pred +0.003 MODEL` · 42.54% moved, mean disp 0.811 px (1.906 px over moved), MODEL +0.003 vs p3; SGMC PROXY 0.09077 (report only).

### Conditional Slot B: `r1` — ≤1 px Snap
- **Primary:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPr1-20261023-a0133e96.tif` (`a0133e96568e8126d02ae8fa3e911a792a565ec08d9eafb00549e347d2aa1a43`) · **Fallback:** `…-SNAPr1-20261023-a0133e96-zeros.tif` (`fc0f210883fdba4258060b3bf6ee4cbc85d7ab1e86d91a03edccf862db8222fd`)
- **Form note (86/140):** `PRUNEp3px; SNAP r1 <=1px to max TMI/grav HG, N=37654 held, all >3px; pred +0.002 MODEL` · 96.39% moved 1.00 px, MODEL +0.002; SGMC PROXY 0.09318.

### Deprioritised: `r2` — Ungated ≤2 px Snap (98.06% moved; SGMC PROXY 0.08747, worst)
- **Primary:** `releases/…-SNAPr2-20261023-93187627.tif` (`93187627037c34d2b16ad4137d42e96282d8fb71084c2ca6e60985a7cd407268`) · **Fallback:** `…-SNAPr2-20261023-93187627-zeros.tif` (`60de781a7df9c26dd3206b65d6f76782b0dc2c726743d68f2d67ad4941327b6e`) · **Form note (86/140):** `PRUNEp3px; SNAP r2 <=2px to max TMI/grav HG, N=37654 held, all >3px; pred +0.004 MODEL`
- Format receipt for all SNAP files: `registry/snap_variant_validation.json` (independent `validate_variant.py` PASS ×3, re-read from disk) + per-file `releases/*.json`.

## Other Reconciled Ledger Inventory (`HOLD` / Superseded — `ledger/submissions.csv`)
- **Score-blind `PRUNE=3` (`h33-h33-2-b2-prune3-20261023-01d57649`, `MODEL -0.003`):** Superseded by physics-ranked `PRUNEp3px` (`6f7ae705`, `MODEL +0.005`).
- **`CONCENTRATION` (`CONCb10px-m10` `89ffd4f3` `+0.011`, `CONCb10px-m20` `c42cd475` `+0.020`, `CONCb50px-m20` `fae2a52f` `+0.006`):** `HOLD` under strict non-PRUNE `>=3 px` gate because they inherit `R0`'s `2,171` `(2, 3] px` dots; clean Week-2 follow-up applies concentration directly atop `PRUNEp3px` (`>3 px`).
- **`MASS` (`MASSm10minus` `7132935e`, `MASSm10plus` `82673b57`, `MASSm20minus` `6c73303c`):** `HOLD` per `registry/mass_ranking_audit.json` (`0.6*dist + 0.4*uniform` ranking).

## Format Gate Verification Summary
- All `6` `PRUNE` GeoTIFFs (`EPSG:32611`, `3730×3292`, `Affine(100,0,243350,0,-100,4508550)`, `1` band `float32`, `[0,1]`, `0` NaN inside footprint, `0` on catalogue, unique SHA-256) re-read and verified in `tests/test_prune_axis.py`. After human upload, record verbatim `receipt_score` + `receipt_date` in `ledger/submissions.csv`.
