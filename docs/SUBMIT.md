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

## Other Reconciled Ledger Inventory (`HOLD` / Superseded — `ledger/submissions.csv`)
- **Score-blind `PRUNE=3` (`h33-h33-2-b2-prune3-20261023-01d57649`, `MODEL -0.003`):** Superseded by physics-ranked `PRUNEp3px` (`6f7ae705`, `MODEL +0.005`).
- **`CONCENTRATION` (`CONCb10px-m10` `89ffd4f3` `+0.011`, `CONCb10px-m20` `c42cd475` `+0.020`, `CONCb50px-m20` `fae2a52f` `+0.006`):** `HOLD` under strict non-PRUNE `>=3 px` gate because they inherit `R0`'s `2,171` `(2, 3] px` dots; clean Week-2 follow-up applies concentration directly atop `PRUNEp3px` (`>3 px`).
- **`MASS` (`MASSm10minus` `7132935e`, `MASSm10plus` `82673b57`, `MASSm20minus` `6c73303c`):** `HOLD` per `registry/mass_ranking_audit.json` (`0.6*dist + 0.4*uniform` ranking).

## Format Gate Verification Summary
- All `6` `PRUNE` GeoTIFFs (`EPSG:32611`, `3730×3292`, `Affine(100,0,243350,0,-100,4508550)`, `1` band `float32`, `[0,1]`, `0` NaN inside footprint, `0` on catalogue, unique SHA-256) re-read and verified in `tests/test_prune_axis.py`. After human upload, record verbatim `receipt_score` + `receipt_date` in `ledger/submissions.csv`.

## Session `2026-10-23` — `AXIS = SNAP` on Parent `R1 = PRUNEp3px` (DOI: **do not spend a slot**)

Three gate-clean, count-preserving geometry variants of `R1` (`37,654` dots, `min d_cat = 3.162 px`, `> 3 px` strictly, `0` mass on catalogue). Each moves at most `35%` of dots by at most `1-2 px` onto the strongest edge cell in the dot's own window; nothing else changes (same source ridges, same exclusions, same count). Rebuild with `python3 scripts/build_snap_variants.py` (pinned inputs, no RNG in the allocation).

| Value | Window | Edge field | Moved | Mean displacement | `.tif` SHA-256 (NaN outside) | Note (`chars`) |
| :--- | ---: | :--- | ---: | ---: | :--- | :--- |
| `g2f35` | `<= 2 px` | `tmi_hg 0.55 + iso_grav_anom_hg 0.45` | `34.5%` | `1.92 px` | `4c460fd4f57c8c2198b14c4f563c2ec2a93ce7f363a5631433c7d55975395c7d` | `h33-2-b2 PRUNEp3px; SNAP<=2px to potential-field HG (tmi_hg+grav_hg), 35% moved; pred +0.002 MODEL` (`98`) |
| `d2f35` | `<= 2 px` | `+ det_elev_slope 0.20 + tc 0.10` | `34.3%` | `1.86 px` | `a98ce2b85cd7a6bcf503a7923fc0144acb21df9ecd622b2aa1f511823d167466` | `h33-2-b2 PRUNEp3px; SNAP<=2px to TMI+grav+scarp+curvature edge, 35% moved; pred +0.001 MODEL` (`92`) |
| `d1f35` | `<= 1 px` | as `d2f35` | `34.9%` | `1.00 px` | `33783252d6c8b747e7affb6161d57bca8e06228684d8efeac7e1e60057b6dc60` | `h33-2-b2 PRUNEp3px; SNAP<=1px to composite edge, 35% moved; pred +0.003 MODEL` (`77`) |

Fallback twins (`-zeros.tif`, identical inside, `0.0` outside) and single-TIFF `.zip`s sit beside each `.tif`; tracked receipts are `releases/<id>.json`.

**Why they are not slot candidates.** On the blind off-catalogue USGS `SGMC` fault control (`PROXY`, `n = 62,703 px` outside the 300 m halo) every SNAP variant is *worse* than the parent it came from: `R1 = 0.09608` vs `0.09198` (`g2f35`), `0.09246` (`d2f35`), `0.09505` (`d1f35`). Snapping dots onto geophysical edge maxima moves mass *away* from where blind faults actually are — consistent with the weak per-band localisation measured here (percentile rank at catalogue pixels `0.53-0.56` vs `0.50` background). The `12 km` block CV is unchanged (`0.5705-0.5708` vs `0.5700`), so this is not a dispersion effect.

**Decision:** spend slot 1 on `R1` (`6f7ae705`), not on `SNAP`. Keep the three SNAP files as the geometry control: if a future detector beats `R1`, these bound how much of the gain can be re-positioning rather than new evidence. `IRREGULARITIES.md` IR-88-24 records the reason.

**What the human must still supply:** `TOP_PUBLIC` + the date it was read, the `receipt_score` + `receipt_date` for whatever is actually uploaded, and the rolling-week slot count. None of those numbers exist in this repository, and the agent will not fetch or scrape them.
