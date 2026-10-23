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

## CONCENTRATION candidates — HOLD under the literal 3 px gate, otherwise the highest MODEL gain

Built 2026-10-23 on parent R0 (count fixed at 37,654; no mass added inside the 3 px collar; the 2,171 inherited collar dots are untouched). They are **not** eligible while the literal `>=3 px` non-PRUNE gate stands, because they necessarily carry R0's collar. Their rasters are kept local (data-use flag) and tracked receipts hold the hashes: `releases/<id>-receipt.json`; gate evidence: `registry/variant_validation.json`; full statistics: `registry/concentration_report.json`.

| id (submission name) | Moved | MODEL Δ | Primary SHA-256 | Form note |
|---|---|---|---|---|
| `h33-h33-2-b2-CONCb10px-m20-20261023-c42cd475` | 7,531 (20 %) | +0.020 `[-0.006,+0.056]` | `c42cd4756bd28dde29a8b24ab9cfca75f9a8e2564305655ffe2073b792f4e093` | `h33-2-b2 CONC 1km 20% coldest->hottest blocks; 37654 dots CV .62->1.26; pred +0.020 MODEL; R0 0.2778 CLAIM` (106/140) |
| `h33-h33-2-b2-CONCb10px-m10-20261023-89ffd4f3` | 3,765 (10 %) | +0.011 `[-0.002,+0.030]` | `89ffd4f3fbb4de28598c2ac9e994a34280eed39a9652adfee17ecef4a8bbc878` | `h33-2-b2 CONC 1km 10% coldest->hottest blocks; 37654 dots CV .62->1.02; pred +0.011 MODEL; R0 0.2778 CLAIM` (106/140) |
| `h33-h33-2-b2-CONCb50px-m20-20261023-fae2a52f` | 7,531 (20 %) | +0.006 `[-0.012,+0.028]` | `fae2a52f5117ffd4a0bac016e244f820a0c15b6b81dca14919660fb6ce2da1cc` | `h33-2-b2 CONC 5km 20% coldest->hottest blocks; 37654 dots CV .70->1.36; pred +0.006 MODEL; R0 0.2778 CLAIM` (106/140) |

**Local file pair per row:** `releases/<id>.tif` (NaN outside, nodata=NaN) and `releases/<id>-zeros.tif` (0 outside, nodata=None); scored content is identical, upload **one**. Each has a single-TIFF `.zip` beside it. Both twins were re-read from disk and passed: one band float32; `EPSG:32611`; `3730×3292`; transform `(100,0,243350,0,-100,4508550)`; finite binary values inside the 5,167,373-pixel footprint; 37,654 dots; zero catalogue mass; zero dots ≤2 px; the 2–3 px collar reported (2,171) and unchanged; sha256 absent from the ledger except as its own row.

**Decision status:** BUILT, not submitted, no receipt. `MODEL` and `PROXY` numbers are never scores. See `SLOT_PLAN.md` for the conditional slot order and `IRREGULARITIES.md` item 12 for why this axis is HOLD.

## Concurrent MASS artifacts — HOLD, not submission-ready

PR #17's audit reproduced all three arrays and corrected their interpretations/predictions (`registry/mass_ranking_audit.json`). They do not use a parent model ranking. They also retain the parent's **2 px**, not the currently required **3 px**, non-PRUNE exclusion, so **do not upload them under this session's gates**. Historical dot-overlap/rank-correlation checks are not uniqueness gates.

| ID / submission name | Audited MODEL prediction | Primary / zeros SHA-256 | Updated form note |
|---|---|---|---|
| `h33-h33-2-b2-MASSm10minus-20261023-7132935e` | `+0.004` `[-0.006,+0.014]`; collar extension, not pure MASS | `7132935e1210208cfbc5dc02d0d393816b7e6b35a706fce44020a3513b7fa201` / `58d9ebdbdd9234d5bbe8e248c1b385d7b7ffb03461c94f9624c2eb02d13ac412` | `h33-2-b2 33889 dots, collar cut 2->10px vs catalogue; pred +0.004 MODEL; parent 0.2778 CLAIM` |
| `h33-h33-2-b2-MASSm10plus-20261023-82673b57` | `-0.010` `[-0.014,+0.002]`; isolated low-prior additions | `82673b574213e45cce34f26f6c8918f99ba78ef04f1a41ec420f1a8559329474` / `384f2a3c802b12823ee4510215d6fe825140ed3842b57e80278fe940c37bc6df` | `h33-2-b2 MASSm10plus 41419 isolated low-prior dots; pred -0.010 MODEL; parent 0.2778 CLAIM` |
| `h33-h33-2-b2-MASSm20minus-20261023-6c73303c` | `+0.001` `[-0.015,+0.017]`; nested deeper cut | `6c73303cd5055a5af1dc0801a78821db66d8dcd28ab9244d34341c73836e2c4d` / `c31659134bf513a768a1566c0527dc111df60e209ad14eecf7291adab67864f2` | `h33-2-b2 MASSm20minus 30123 dots nested collar cut; pred +0.001 MODEL; parent 0.2778 CLAIM` |

All receipt fields remain empty. After any authorized human upload, copy the actual submission-page score and date verbatim into `ledger/submissions.csv`; never infer a receipt from a MODEL or PROXY value.
