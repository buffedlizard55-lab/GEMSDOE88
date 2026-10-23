# SLOT_PLAN — one entity; at most 3 scored files per rolling week; one blind final file

**Status at 2026-10-23:** all 15 manifest pins and byte-exact R0 were verified (`N=37,654`; zeros `c55bafc4…`; NaN `baeae321…`). The reconciled ledger has **38 built rows and no portal receipts**. Historical R0 `0.2778` is a **CLAIM**, not a fresh score. The agent has not accessed a portal or submitted anything.

## Session result — `AXIS = SPACING` on parent `h33-h33-2-b2`

All three arms use the same edit: remove the `1,611` R0 dots at `<3 px` catalogue distance and `3,765` common crowded donors, then add `5,376` cells from legal, un-emitted H19-5 support. Thus `N=37,654`, zero catalogue mass, and `min d_catalogue=3.0 px` for every arm; the **only arm-to-arm treatment is replacement ordering**. The shared collar repair makes this a SPACING/collar-normalization confound, not a clean R0 attribution.

| Value / local file suffix | Registered `MODEL` change | Report-only reading | Status |
|---|---:|---|---|
| `lattice` `03d14f38` | −0.007 | SGMC `0.095895` vs R0 `0.096060`; hide/recover Δ `−0.004006` | HOLD |
| `poisson` `80ede4fa` | −0.003 | SGMC `0.095735`; hide/recover Δ `−0.004006` | HOLD |
| `alongstrike` `5cb97402` | +0.002 | SGMC `0.095838`; hide/recover Δ `−0.004006` | HOLD |

These are **not scores or promotion gates**. The fixed `sqrt(5)` (`2.236 px`) separation guard is weaker than the canonical 2.8-px thinning diagnostic, and a first build exposed local diagnostics before the preregistration was written; both limitations are recorded in the evidence and make all three HOLD. The source-support `MODEL`, SGMC, hide/recover, and leakage canary remain report-only.

## Human-controlled conditional queue

1. **First only if the human chooses it after fresh private validation:** existing gate-clean `PRUNEp3px-6f7ae705`. Its receipt decides whether the collar/refill family deserves further attention.
2. **Conditional spacing comparison, not this session’s SPACING arms:** existing `PRUNEp3space35-49fff49b` only if the human wants the more focused gate-clean refill-spacing test and receipt/quota conditions support it. It is already the conditional candidate in the upstream plan; its `MODEL +0.007` and SGMC `PROXY +0.004982` do **not** constitute a score.
3. **Reserve:** `PRUNEp4space35-07bd8182` only after a positive, human-reviewed `p3space35` receipt; otherwise preserve the slot.

`SPACINGlattice`, `SPACINGpoisson`, and `SPACINGalongstrike` do **not** displace this queue and are not recommended for a weekly slot without an explicit human decision to run a low-priority diagnostic. A primary and its `-zeros` fallback are alternatives—never two uploads.

## Before any human upload

- Confirm current `TOP_PUBLIC` **with date**, rolling-week and total slot availability, competition deadline, data-use authorization, and the exact chosen file against actual upload history.
- Re-open the actual primary and fallback TIFFs, match the complete recorded SHA-256, and rerun `scripts/validate_variant.py`; do not infer validation from a JSON receipt alone.
- Upload at most one file, then record the verbatim portal receipt in `receipt_score` and `receipt_date`. A live `|Δ| < 0.01` is no evidence.
- Choose the one blind final file independently; no local MODEL/PROXY reading selects it.

**Evidence hierarchy:** `RECEIPT` > `CLAIM` > `PROXY` > `MODEL`. No deadline, quota, TOP_PUBLIC value, or score has been portal-verified by this repository.
