# Submission checklist — human uploads ONE per slot (DrivenData form)

> **No file is marked `ok_to_submit: true`.** All three MASS variants below are `BUILT` and pass **100% of competition format checks** (EPSG:32611, 3730×3292, float32, [0,1], no NaN inside, NaN outside + fallback -zeros with 0 outside, 0 on catalogue, ≥2 px collar) and pass like-for-like uniqueness against **134/134 genuine fault rasters (max 3-px overlap <0.70)**. They are **blocked under the unamended literal rule** by 4 space-covering calibration witnesses (>70% halo). Submit only after selector explicitly scopes the 3-px rule to discriminating rasters.

## Candidates (MASS axis, parent h33-h33-2-b2, 2026-10-23)

### 1. Drop 10% — recommended Slot 1 (mass-elasticity probe)
- **File (NaN outside, per spec):** `releases/h33-h33-2-b2-MASSm10minus-20261023-7132935e.tif` (sha256 `7132935e1210208cfbc5dc02d0d393816b7e6b35a706fce44020a3513b7fa201`)
- **Fallback (zeros outside):** `releases/h33-h33-2-b2-MASSm10minus-20261023-7132935e-zeros.tif` (sha256 `58d9ebdbdd9234d5bbe8e248c1b385d7b7ffb03461c94f9624c2eb02d13ac412`)
- **Zip:** `releases/h33-h33-2-b2-MASSm10minus-20261023-7132935e.zip` (contains single matching .tif, byte-identical)
- **Submission name (≤140):** `h33-h33-2-b2-MASSm10minus-20261023-7132935e`
- **Submission note (109/140):** `h33-2-b2 MASSm10minus 33889 dots drop10% low-rank; pred -0.008 MODEL; parent 0.2778 CLAIM`
- **Format receipt:** `format_report` below — 1 band float32 EPSG:32611 3730×3292 `Affine(100,0,243350,0,-100,4508550)` [0,1], 0 NaN inside, NaN outside, 0 outside zeros fallback, 0 catalogue, transform matches `sample_submission.tif` (`2176d08e...`). Re-read verified.

### 2. Add 10% — Slot 2 (tip-relay test)
- **File:** `releases/h33-h33-2-b2-MASSm10plus-20261023-82673b57.tif` (sha256 `82673b574213e45cce34f26f6c8918f99ba78ef04f1a41ec420f1a8559329474`)
- **Fallback:** `releases/h33-h33-2-b2-MASSm10plus-20261023-82673b57-zeros.tif` (sha256 `384f2a3c802b12823ee4510215d6fe825140ed3842b57e80278fe940c37bc6df`)
- **Name:** `h33-h33-2-b2-MASSm10plus-20261023-82673b57`
- **Note (108/140):** `h33-2-b2 MASSm10plus 41419 dots add10% next-rank; pred +0.004 MODEL; parent 0.2778 CLAIM`
- **Format receipt:** same as above, 41,419 dots, 10.00% changed, re-read verified.

### 3. Drop 20% — Slot 3 alternate (elasticity bound)
- **File:** `releases/h33-h33-2-b2-MASSm20minus-20261023-6c73303c.tif` (sha256 `6c73303cd5055a5af1dc0801a78821db66d8dcd28ab9244d34341c73836e2c4d`)
- **Fallback:** `releases/h33-h33-2-b2-MASSm20minus-20261023-6c73303c-zeros.tif` (sha256 `c31659134bf513a768a1566c0527dc111df60e209ad14eecf7291adab67864f2`)
- **Name:** `h33-h33-2-b2-MASSm20minus-20261023-6c73303c`
- **Note (109/140):** `h33-2-b2 MASSm20minus 30123 dots drop20% low-rank; pred -0.018 MODEL; parent 0.2778 CLAIM`
- **Format receipt:** same as above, 30,123 dots, 20.00% changed.

## Validation steps (human, from own authenticated account)

1. `python scripts/restore_inputs.py --validation` — grid pins `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` / `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` verified; `h33_education.tif` `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` rebuilt.
2. `python -m pytest -q` — existing H88-GHMD tests still green (37654 0 within 200m, gates, canaries).
3. Re-open chosen `.tif` in QGIS/GDAL: check `gdalinfo -stats` shows `Min=0 Max=1 NoData=nan` (or 0 fallback), `Band 1 Type=Float32`, `Size 3292,3730`.
4. Upload **ONE** file per slot (either NaN or -zeros variant; both identical inside) + note, submit, copy receipt timestamp/id/score verbatim into `ledger/submissions.csv` as `receipt_score` / `receipt_date`, mark `RECEIPT`.

> Irregularities: see `IRREGULARITIES.md`. Generative-AI disclosure required per NLR Rules §3.6 in final narrative (`AI_USE.md`).
