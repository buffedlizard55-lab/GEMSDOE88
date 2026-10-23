# Human submission checklist — CONCENTRATION experiment

**AI does not submit.** Human uploads at most one file per slot, then records the authenticated receipt in `ledger/submissions.csv`. Prefer the NaN-outside file; use the zero-outside twin only if the form rejects NaN. Twins are identical inside the footprint.

## Slot 1 — recommended first

- **File:** `releases/h33-h33-2-b2-CONCENTRATION15pct-20261023-4dfb83f6.tif`
- **Fallback:** `releases/h33-h33-2-b2-CONCENTRATION15pct-20261023-4dfb83f6-zeros.tif`
- **Name:** `h33-h33-2-b2-CONCENTRATION15pct-20261023-4dfb83f6`
- **Note (78 chars):** `h33-2-b2; CONC 15% in 1km gradient blocks; count 37654; pred +0.008 MODEL`
- **SHA-256:** `4dfb83f6a97f4265e442a3f1ed156986d3c25eb9ebb5e8d49d3784b5cec1eb43`

## Slot 2 — only if Slot 1 supports/brackets the mechanism

- **File:** `releases/h33-h33-2-b2-CONCENTRATION10pct-20261023-43c15f56.tif`
- **Fallback:** `releases/h33-h33-2-b2-CONCENTRATION10pct-20261023-43c15f56-zeros.tif`
- **Name:** `h33-h33-2-b2-CONCENTRATION10pct-20261023-43c15f56`
- **Note:** `h33-2-b2; CONC 10% in 1km gradient blocks; count 37654; pred +0.004 MODEL`
- **SHA-256:** `43c15f5648fb150c9ba3bf98f64e64069f90bf41dad846f69d4d9a6f5bb2a23c`

## Slot 3 — only if dose bracketing remains warranted

- **File:** `releases/h33-h33-2-b2-CONCENTRATION20pct-20261023-88fd49f0.tif`
- **Fallback:** `releases/h33-h33-2-b2-CONCENTRATION20pct-20261023-88fd49f0-zeros.tif`
- **Name:** `h33-h33-2-b2-CONCENTRATION20pct-20261023-88fd49f0`
- **Note:** `h33-2-b2; CONC 20% in 1km gradient blocks; count 37654; pred +0.003 MODEL`
- **SHA-256:** `88fd49f0f7b5b660538a0a686d0b11af8ac4f08ea88114db75192301e5b171d6`

## Format receipt (all three; independently re-read)

- One band, float32, EPSG:32611, 3730×3292, 100 m; transform exactly matches pinned `sample_submission.tif` SHA `2176d08e…`.
- Inside footprint: finite values in {0,1}; outside: all NaN (primary) or all zero (fallback).
- Exactly 37,654 dots; zero catalogue mass; inherited R0 collar has minimum catalogue distance √5 px (>2 px). Parent diff is exactly the named relocation percentage removed plus the same count added.
- Exact output hashes and zero-twin hashes are in `ledger/submissions.csv`; `python scripts/validate_concentration_releases.py` re-checks disk bytes.

After each upload: copy receipt score/date verbatim, label it **RECEIPT**, and treat |Δ|<0.01 as no evidence. Do not upload all three automatically; follow `SLOT_PLAN.md`.
