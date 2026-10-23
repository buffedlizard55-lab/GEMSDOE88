# SLOT_PLAN — One Entity, 3 Slots/Week, One Blind Final by 2026-12-03

**Parent:** exact `R0 = h33-h33-2-b2`, `N=37,654`; zeros SHA `c55bafc4…`, NaN SHA `baeae321…`. Historical live `0.2778` is **CLAIM**, not a receipt. **TOP_PUBLIC:** `0.4413` (`2026-10-22`, human-supplied; not portal-verified). Last reported budget is `3/3` weekly slots and `~21` total for one entity; the human must reconfirm counts and deadline. No slot was used.

## Axis and built files

The human asked the agent to choose. I chose **PRUNE**: R0 has 2,171 dots at `2 < d_catalogue <= 3 px`; another axis cannot satisfy the strict `>=3 px` rule without mixing in PRUNE. All arms hold count fixed and use the same exact-marginal expected-DTI refill from original H19-5 support. Values/predictions were registered before diagnostics. Percent is relocated R0 dots / 37,654; symmetric difference is twice that.

| Candidate / threshold | Moved (count; exact %) | Min d_catalogue | `MODEL` Δ / range | SHA-8 |
|---|---:|---:|---:|---|
| `PRUNEp3.2px` / 320 m | 2,702; **7.17586%** | 3.6056 px | +0.002 `[-0.010,+0.012]` | `f272cdae` |
| `PRUNEp3.7px` / 370 m | 3,361; **8.92601%** | 4.0000 px | -0.005 `[-0.020,+0.008]` | `5508b0b9` |
| `PRUNEp4.3px` / 430 m | 4,488; **11.91905%** | 4.4721 px | -0.013 `[-0.030,+0.006]` | `21fa2b26` |

Primary NaN-outside rasters and zero-outside fallbacks are local in `releases/`; all six pass `registry/prune_sweep_validation.json`. Report-only: canary max AUC `0.56925`; hide/recover PROXY `0 [0,0]`, `n=22,663` (degenerate, not a gate); blind SGMC PROXY `0.095801 / 0.094869 / 0.092558` vs R0 `0.096060`. Refill min nearest-neighbour spacing is `1.0 px` vs R0 `2.828 px`; this is a disclosed confounder. PROXY is not a score.

## Next 3 live slots (human submits one file per slot)

1. **`PRUNEp3.2px`:** first increment beyond 300 m. Receipt `>= R0+0.01` supports narrow collar removal; `<= R0-0.01` indicates net truth loss; otherwise no evidence.
2. **`PRUNEp3.7px`:** only after Slot 1. A receipt at least `0.01` below Slot 1 closes wider collars; a positive `>=0.01` increment supports the next dose.
3. **`PRUNEp4.3px`:** upper bracket beyond the built 400 m `p4px`. Gain `>=0.01` over both R0 and p4px supports widening; loss `<=-0.01` ends it. Do not submit all blindly; live `|delta|<0.01` is no evidence.

## Weeks to deadline; axes proposed but not built

- **Weeks 1–2 (through 2026-11-05):** confirm receipts, TOP_PUBLIC and slot budget; non-PRUNE work must rebase on gate-clean `R1=PRUNEp3px`.
- **Weeks 3–4:** only test a receipt-supported axis. **RELIEF:** shift 10–15% across Band 12 terciles; mechanism—range-front/piedmont localization; confounder—fan channels/shoreline breaks; falsifier—live gain `<+0.01` vs R1. **DIP_OFFSET_ASYM:** back-project Bands 18/15 updip (`https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11072.pdf`); confounder—caprock/shorelines; falsifier `<+0.01`. **RELAY_TIP_STRESS:** anisotropic tip/step-over support (`https://doi.org/10.1016/B978-0-12-066266-1.50009-0`); confounder—flight-line corrugation; falsifier `<+0.01` vs isotropic PRUNE.
- **Weeks 5–6 (to 2026-12-03):** confirm the best receipt-backed candidate, prepare Phase-2 `TRACKB`, then lock one blind final and format-checked fallback. Human confirms the deadline.
