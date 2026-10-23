# Submission checklist — human uploads ONE file per slot (DrivenData form)

> **No file here is pre-approved for submission.** Every candidate passes 100 % of the competition *format* gates (EPSG:32611, 3730×3292, float32, one band, values in [0,1], finite inside the footprint, NaN outside + a `-zeros` fallback that is bit-equal inside, zero mass on the mapped catalogue, zero dots within 2 px of it, sha256 not already in the ledger) — see `registry/variant_validation.json`. Promotion is a **human** decision; nothing in this repo submits anything.

## Candidates — AXIS = CONCENTRATION, parent `h33-h33-2-b2`, built 2026-10-23

Every candidate: 37,654 dots (mass held fixed), 0 dots ≤ 2 px from the catalogue, 2,171 dots in the 2–3 px collar (inherited from R0, unchanged), no block emptied, no RNG. Predicted changes are **MODEL** values from `registry/concentration_projection.json`, not scores.

### 1. 1 km × 20 % — recommended Slot 1
- **File (NaN outside, per spec):** `releases/h33-h33-2-b2-CONCb10px-m20-20261023-c42cd475.tif` — sha256 `c42cd4756bd28dde29a8b24ab9cfca75f9a8e2564305655ffe2073b792f4e093`
- **Fallback (zeros outside):** `releases/h33-h33-2-b2-CONCb10px-m20-20261023-c42cd475-zeros.tif` — sha256 `bf66292d9d199a174f7ba53aa463c1f0d1ef14d3adf4aa7c28d37b175b4c7948`
- **Zip (one TIFF, byte-identical):** `releases/h33-h33-2-b2-CONCb10px-m20-20261023-c42cd475.zip`
- **Submission name:** `h33-h33-2-b2-CONCb10px-m20-20261023-c42cd475`
- **Submission note (106 / 140):** `h33-2-b2 CONC 1km 20% coldest->hottest blocks; 37654 dots CV .62->1.26; pred +0.020 MODEL; R0 0.2778 CLAIM`
- **Parent diff:** 7,531 dots moved (20.00 %), 30,123 common with R0, receivers 1.04 px from their host on average.
- **Format receipt:** one band float32, `EPSG:32611`, 3730×3292, `Affine(100, 0, 243350, 0, -100, 4508550)`, matches `sample_submission.tif` (`2176d08e…`); 0 non-finite inside, NaN outside, `-zeros` twin 0 outside and identical inside; re-read verified after write.

### 2. 1 km × 10 % — the slope, read with #1
- **File:** `releases/h33-h33-2-b2-CONCb10px-m10-20261023-89ffd4f3.tif` — sha256 `89ffd4f3fbb4de28598c2ac9e994a34280eed39a9652adfee17ecef4a8bbc878`
- **Fallback:** `releases/h33-h33-2-b2-CONCb10px-m10-20261023-89ffd4f3-zeros.tif` — sha256 `c6cdc230f24923b14ec03cf256ab1e034c9322add5dc673e7a6f3ad59648dc0d`
- **Name:** `h33-h33-2-b2-CONCb10px-m10-20261023-89ffd4f3`
- **Note (106 / 140):** `h33-2-b2 CONC 1km 10% coldest->hottest blocks; 37654 dots CV .62->1.02; pred +0.011 MODEL; R0 0.2778 CLAIM`
- **Parent diff:** 3,765 dots moved (10.00 %); 90 % of R0's dots untouched.

### 3. 5 km × 20 % — scale control
- **File:** `releases/h33-h33-2-b2-CONCb50px-m20-20261023-fae2a52f.tif` — sha256 `fae2a52f5117ffd4a0bac016e244f820a0c15b6b81dca14919660fb6ce2da1cc`
- **Fallback:** `releases/h33-h33-2-b2-CONCb50px-m20-20261023-fae2a52f-zeros.tif` — sha256 `586e3a047e249a251cbdf8f0c57062362688718649bcc141b9aea2cea676f5b2`
- **Name:** `h33-h33-2-b2-CONCb50px-m20-20261023-fae2a52f`
- **Note (106 / 140):** `h33-2-b2 CONC 5km 20% coldest->hottest blocks; 37654 dots CV .70->1.36; pred +0.006 MODEL; R0 0.2778 CLAIM`

### Still on the shelf (MASS axis, built 2026-10-23)
`h33-h33-2-b2-MASSm10minus-20261023-7132935e` (33,889 dots, −0.008 MODEL),
`…-MASSm10plus-20261023-82673b57` (41,419, +0.004),
`…-MASSm20minus-20261023-6c73303c` (30,123, −0.018).
Their ranking is a *reconstructed* ordering (`0.6·norm(dist/50) + 0.4·rand(88)`), not the parent's own ranking — see `IRREGULARITIES.md` IR-88-18 before spending a slot on one.

## Validation steps (human, from their own authenticated account)

1. `python scripts/restore_inputs.py --validation` — grid pins verified (`2176d08e…`, `7ba308cc…`); parent `c55bafc4…` restored.
2. `python -m pytest -q` — includes `tests/test_dti_algebra.py` and `tests/test_concentration_variants.py`.
3. `python scripts/validate_variant.py releases/<id>.tif releases/<id>-zeros.tif` — must print PASS for both.
4. Open the chosen `.tif` in QGIS/GDAL: `gdalinfo -stats` should show `Band 1 Type=Float32`, `Size is 3292, 3730`, `NoData=nan` (or the `-zeros` twin with 0 outside).
5. Upload **ONE** file per slot, paste the note, then copy the receipt id/timestamp/score into `ledger/submissions.csv` (`receipt_score`, `receipt_date`) and mark the row `RECEIPT`.

> Irregularities that change a decision: `IRREGULARITIES.md` (IR-88-14 collar, IR-88-17 byte-sha, IR-88-18 reconstructed MASS ranking, IR-88-19 CV band). Generative-AI disclosure: `AI_USE.md`.
