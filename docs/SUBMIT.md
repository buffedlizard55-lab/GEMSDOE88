# Human submission card — no automated submission

## PRUNE3 — the only candidate built in this branch

**Candidate ID / submission name:** `h33-h33-2-b2-prune3-20261023-01d57649`  
**Form note (91/140 characters):** `R0 h33-h33-2-b2; PRUNE<=3px + fixed-count H19 BFS refill (2171 dots); MODEL -0.003 live DTI`

Choose **only one** TIFF for a slot. Do not upload both twins.

| Choice | Local file | SHA-256 | Outside footprint |
|---|---|---|---|
| Primary | `releases/h33-h33-2-b2-prune3-20261023-01d57649.tif` | `01d57649168d52a0bf2f9aced7aa2280a92b6fd7a0224757d5acc5e925785e96` | NaN; nodata=NaN |
| Fallback | `releases/h33-h33-2-b2-prune3-20261023-01d57649-zeros.tif` | `4131e37133a3c5a874c42fb7c975ec4ecb7b4be946b794ff9c9852afa575e225` | 0; nodata=None |

**Format receipt:** `releases/h33-h33-2-b2-prune3-20261023-01d57649-receipt.json` and `releases/h33-h33-2-b2-prune3-20261023-01d57649-validation.json`.

Both files were re-read from disk and passed: one float32 band; EPSG:32611; shape `(3730,3292)`; sample transform `(100,0,243350,0,-100,4508550)`; finite binary values inside the 5,167,373-pixel footprint; 37,654 dots; zero catalogue mass; every dot `d_cat>3 px`; identical scored content. Parent R0 independently rebuilt to `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`.

**Decision status:** BUILT, not submitted, no receipt. Prediction is **MODEL −0.003**, not a score. See `SLOT_PLAN.md` before spending a slot. New PRUNE rasters are intentionally local and Git-ignored because public-repository data-use terms are unchecked; the JSON receipts and reproducible code are tracked.

## Concurrent MASS artifacts — HOLD, not submission-ready

These three files arrived through the concurrent branch merged into this PR. They use the parent's **2 px**, not the currently required **3 px**, non-PRUNE exclusion. Do not upload them under this session's gates. Their historical dot-overlap/rank-correlation checks are not used as uniqueness gates; exact hashes are recorded in the ledger.

| ID / submission name | Primary SHA-256 | Zeros SHA-256 | Form note |
|---|---|---|---|
| `h33-h33-2-b2-MASSm10minus-20261023-7132935e` | `7132935e1210208cfbc5dc02d0d393816b7e6b35a706fce44020a3513b7fa201` | `58d9ebdbdd9234d5bbe8e248c1b385d7b7ffb03461c94f9624c2eb02d13ac412` | `h33-2-b2 MASSm10minus 33889 dots drop10% low-rank; pred -0.008 MODEL; parent 0.2778 CLAIM` |
| `h33-h33-2-b2-MASSm10plus-20261023-82673b57` | `82673b574213e45cce34f26f6c8918f99ba78ef04f1a41ec420f1a8559329474` | `384f2a3c802b12823ee4510215d6fe825140ed3842b57e80278fe940c37bc6df` | `h33-2-b2 MASSm10plus 41419 dots add10% next-rank; pred +0.004 MODEL; parent 0.2778 CLAIM` |
| `h33-h33-2-b2-MASSm20minus-20261023-6c73303c` | `6c73303cd5055a5af1dc0801a78821db66d8dcd28ab9244d34341c73836e2c4d` | `c31659134bf513a768a1566c0527dc111df60e209ad14eecf7291adab67864f2` | `h33-2-b2 MASSm20minus 30123 dots drop20% low-rank; pred -0.018 MODEL; parent 0.2778 CLAIM` |

All receipt fields remain empty. After any authorized human upload, copy the actual submission-page score and date verbatim into `ledger/submissions.csv`; never infer a receipt from a MODEL or PROXY value.
