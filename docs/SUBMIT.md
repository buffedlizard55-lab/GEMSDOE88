# Submission Package — Human Upload Only (GEMS Prize #306)

**No upload was made by the agent.** These are three reproducible PRUNE experiments from exact parent `R0 = h33-h33-2-b2`; choose at most one per live slot. The `.tif` primary has NaN outside the footprint. The matching `-zeros.tif` is a fallback with zero outside; never upload both for one slot. Raster files and ZIPs are local-only/ignored by Git because data-use terms are unchecked.

- **Entity/budget:** one human competitor; the last repository-reported count is `3/3` weekly slots remaining and about `21` total, to be re-confirmed by the human.
- **TOP_PUBLIC:** `0.4413`, dated `2026-10-22`, human-supplied and not portal-verified here.
- **R0 score:** `0.2778` is **CLAIM** (no receipt logged). Candidate changes below are **MODEL**, never scores.

## Candidate files, names, and form notes

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
