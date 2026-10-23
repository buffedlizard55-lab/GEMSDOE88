# SLOT_PLAN — One Entity, 3 Slots/Week, One Blind Final by 2026-12-03

**Status:** Exact `R0=h33-h33-2-b2`, `N=37,654`; zeros/NaN SHA `c55bafc4…` / `baeae321…`. Existing gate-clean `R1=h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` has `min d_cat=3.1623 px`. `R0=0.2778` is **CLAIM**, not receipt. **TOP_PUBLIC** `0.4413` (`2026-10-22`) is human-supplied, unverified here. Last reported budget `3/3` weekly, `~21` total; human reconfirms counts/deadline. No slot spent.

## Current `AXIS=PRUNE` sweep from R0

R0 has 2,171 dots at `2<d_catalogue<=3 px`; the explicit PRUNE exception is the only single-axis route to the strict `>=3 px` gate. All three candidates hold count fixed and use exact-marginal expected-DTI refill on original H19-5 support. Values/predictions were preregistered before diagnostics. Percent is relocated R0 dots / 37,654; symmetric difference is twice that.

| Candidate / collar | Moved (count; %) | Min d_cat | `MODEL` Δ / range | SHA-8 |
|---|---:|---:|---:|---|
| `PRUNEp3.2px` / 320 m | 2,702; **7.17586%** | 3.6056 px | +0.002 `[-0.010,+0.012]` | `f272cdae` |
| `PRUNEp3.7px` / 370 m | 3,361; **8.92601%** | 4.0000 px | -0.005 `[-0.020,+0.008]` | `5508b0b9` |
| `PRUNEp4.3px` / 430 m | 4,488; **11.91905%** | 4.4721 px | -0.013 `[-0.030,+0.006]` | `21fa2b26` |

All six local primary/fallback files pass `registry/prune_sweep_validation.json`; fallbacks also pass strict format audits. Report-only: canary max AUC `0.56925`; hide/recover PROXY `0 [0,0]`, `n=22,663` (degenerate); SGMC PROXY `0.095801 / 0.094869 / 0.092558` vs R0 `0.096060`. Exact refill lowered min nearest-neighbour spacing `2.828 -> 1.0 px`; disclose as a confounder. Prior `RELIEF` arms on R1 all lost on SGMC (`0.09366 / 0.09252 / 0.08490` vs `0.09608`); they are diagnostics, not slot candidates. No PROXY is a score.

## Next 3 candidate slots (human chooses; not upload recommendations)

1. **p3.2px:** first increment beyond existing 300 m R1. Spend only if the human has a verified live baseline and wants the dose test; `>=+0.01` vs current best supports the next arm, `|delta|<0.01` is no evidence.
2. **p3.7px:** only after a positive, receipt-backed p3.2 result; a `<=-0.01` increment closes wider collars.
3. **p4.3px:** only if p3.7 supports widening; a `<=-0.01` increment ends the sweep. Never upload all three blindly.

**Standing alternatives (from the RELIEF sessions, kept for the human's choice):** `R1 = PRUNEp3px` (`6f7ae705`, `MODEL +0.005`, SGMC `0.09608 PROXY`) is the first gate-clean single-axis test of the `2–3 px` collar itself and the natural baseline the dose sequence above assumes; `SNAPscarp2px` (`fae77ff4`, `MODEL +0.006`, SGMC `0.09681`, best local control) carries R0's `2,171` collar dots unchanged, so it is only spendable if the human accepts the IR-88-36 literal-rule tension (it is a mechanical prune+relocation of R0's own design, not a new non-PRUNE child).

## Weeks to deadline; unbuilt axes

- **Weeks 1–2 (through 2026-11-05):** human reconfirms receipt(s), TOP_PUBLIC, budget and deadline. If continuing non-PRUNE work, rebase on gate-clean R1; do not repeat negative RELIEF.
- **Weeks 3–4:** only receipt-supported, preregistered work. **RELIEF-SPACING:** keep the tercile transfer but force receivers `>=2.8 px` from survivors; mechanism—test whether prior losses were duplicate coverage; confounder—lower-support cells; falsifier—no `+0.01` live gain. **COVER_DEPTH:** allocate by Band 15 basement-depth tercile; mechanism—thin-cover signal; confounder—smooth regional interpolation; falsifier—`|delta|<0.01`. **STRIKE_ALIGN:** move only strike-coherent ridge dots; confounder—flight-line/shoreline lineaments; falsifier—no gain over matched random-angle control. **DIP_OFFSET_ASYM / RELAY_TIP_STRESS:** updip back-projection / anisotropic tip support; confounders—caprock/shorelines / flight-line corrugation; falsifier—live gain `<+0.01` vs matched control.
- **Weeks 5–6 (to 2026-12-03):** confirm only receipt-backed candidate(s), prepare Phase-2 `TRACKB`, then lock one blind final and format-checked fallback. Human confirms deadline; all submissions remain manual.
