# SLOT_PLAN — one entity; at most 3 scored files per rolling week; one blind final file

**2026-10-23 status:** all 15 manifest pins and byte-exact R0 were verified (`N=37,654`; zeros `c55bafc4…`; NaN `baeae321…`). The reconciled ledger has **38 BUILT / 0 RECEIPT**. R0 `0.2778` is a **CLAIM**, not a portal score. No agent session accessed a portal or submitted a file.

## Gate correction and current stops

- **Pure R0 SNAP is stopped:** `30` of the `1,611` parent dots at `<3 px` catalogue distance have no `>=3 px` in-footprint destination within a `<=2 px` SNAP, even ignoring collisions. Moving farther or refilling is a different axis. See `evidence/session_20261023_snap_clearance.json` / IR-88-47.
- The independent validator now enforces zero positive mass at catalogue distance `<3 px` for every **non-PRUNE** child. Historic R0 SNAP/CONCENTRATION/RELIEF files with inherited collar mass remain HOLD. PRUNE is the documented exception.
- Existing p1/p3/p4 PRUNE twins were previously reconstructed at their ledger hashes and passed six fresh disk checks (`evidence/session_20261023_prune_revalidation.json`), but every human upload must still re-open the exact current bytes.

## Completed `AXIS = SPACING` session — parent `h33-h33-2-b2`

All three arms remove the same `1,611` `<3 px` R0 collar dots and `3,765` crowded donors, then add the same number of legal un-emitted H19-5 cells. Thus each has `N=37,654`, zero catalogue mass, and `min d_catalogue=3.0 px`; **only replacement ordering varies**. The common collar repair and a `sqrt(5)` rather than canonical-2.8-px guard make this a HOLD diagnostic, not a raw R0 attribution.

| Value / suffix | `MODEL` change | Report-only reading | Slot status |
|---|---:|---|---|
| `lattice` `03d14f38` | −0.007 | SGMC `0.095895`; hide/recover Δ `−0.004006` | HOLD |
| `poisson` `80ede4fa` | −0.003 | SGMC `0.095735`; hide/recover Δ `−0.004006` | HOLD |
| `alongstrike` `5cb97402` | +0.002 | SGMC `0.095838`; hide/recover Δ `−0.004006` | HOLD |

These numbers are `MODEL`/`PROXY`, never scores or gates. The canonical 2.8-px `dot_thin` result of `36,718` is construction-specific, not a proof of a global packing maximum. The preregistration records prior diagnostic exposure during two interrupted local attempts; predictions did not change.

## Human-controlled conditional queue

| Order | Existing arm | Preconditions / receipt interpretation |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705` (`MODEL +0.005`) | Reconstruct/revalidate its actual primary or zeros twin. A gain `>=0.01` supports the collar+refill package; loss `<=−0.01` closes it; otherwise it is inconclusive. |
| 2 | `PRUNEp3space35-49fff49b` (`MODEL +0.007`) | Only after human quota/receipt review, exact reconstruction, and fresh validation. It is the narrower gate-clean refill-spacing comparison; `MODEL` and SGMC are not receipts. |
| 3 | Reserve `PRUNEp4space35-07bd8182` (`MODEL +0.002`) | Only after receipt-backed support for slot 2; otherwise conserve the slot. |

The three new SPACING files do **not** displace this queue unless the human explicitly elects to run a low-priority diagnostic. Primary and `-zeros` fallback are alternatives, never two slots.

## Before any human upload

1. Confirm current `TOP_PUBLIC` **with date**, rolling-week/total availability, deadline, data-use authorization, and actual upload history.
2. Match the complete recorded SHA-256 and run `scripts/validate_variant.py` against the actual selected TIFF/twin; do not infer current validation from a receipt.
3. Upload one file only; retain the verbatim receipt and populate `receipt_score` / `receipt_date`. A live `|Δ| < 0.01` is no evidence.
4. Select the one blind final file independently. `RECEIPT > CLAIM > PROXY > MODEL`; no local diagnostic chooses it.
