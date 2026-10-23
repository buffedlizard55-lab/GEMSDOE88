# SLOT_PLAN — one entity; <=3 scored uploads per rolling week

**`2026-10-23` · seven sessions: PRUNE refill-mode (#34) · SPACING on `R1` (#35) · SNAP-clearance audit + hardened gates (#36) · MASS on `R0` (#38/#42) · TRACKB Phase 2 (#40) · SNAP scarp transplant on `R1` (#41) · MASS on gate-clean `R1` (this session, IR-88-51).** All `15` manifest pins verified; `R0` rebuilt byte-exactly (`zeros c55bafc4…`, `nan baeae321…`, `37,654` dots) and gate-clean `R1 = PRUNEp3px-6f7ae705` re-derived and SHA-asserted before editing. Ledger: **`50`** built rows across all 7 brief axes, **`0`** portal receipts, zero `(parent, axis, value)` or SHA-256 collisions.

**Before any slot:** the human supplies current `TOP_PUBLIC`/date (blank in the current brief; the repo's `0.4413` of `2026-10-22` is stale — two same-day briefs disagree on it and on the slot balance, IR-88-49), the actual weekly/total balance, permission to use/redistribute the public mirrors and old tracked TIFFs, and confirms the provisional `2026-12-03` deadline. No automated page access or submissions. Primary/zeros twin = **one** slot; one blind final. `|live delta| < 0.01` is no evidence; without an `R1` receipt no paired live delta exists for any of the 15 gate-clean rows.

## This session — `AXIS=MASS` on the gate-clean parent `R1` (all instruments REPORT-ONLY)
Dose 10% = 3,765 dots; ranking = the parent's own recorded recipe (exact marginal expected-DTI under the label-free field `w`); preregistration `registry/preregistration_mass_r1.json` frozen before any proxy ran.

| Arm | Edit | blind `SGMC` | Δ vs `R1` | ranking premium vs random donors | `w`-field `MODEL` |
|---|---|---:|---:|---:|---:|
| `r10minus` `e56b0e5a` | drop the 3,765 lowest-ranked dots (`N=33,889`) | `0.088680` | `−0.00740` | — | `−0.0080` |
| **`r10plus` `b2d704df`** | add the 3,765 next-ranked un-emitted dots (`N=41,419`) | **`0.098745`** | **`+0.00266`** | `+0.00141` | `+0.0085` |
| `r10swap` `20dc829f` | drop + add, count fixed 37,654 | `0.092489` | `−0.00359` | — | `+0.0013` |
| *random-donor control* (no release) | 3,765 random same-pool cells | `0.097335` | `+0.00125` | — | `+0.0037` |

Convergent findings: (1) **the MASS ordering replicates across parents** — R0 gave `−0.0081 / +0.0029 / −0.0040`, R1 gives `−0.0074 / +0.0027 / −0.0036`; the parent's collar history contributes almost nothing, so MASS is a property of the dot field, not of R0's build. (2) **Half of the add-arm gain is pure count**: a same-pool random add of equal size recovers `+0.00125` of the `+0.00266`, leaving a ranking premium of only `+0.00141`. Under the brief's `0.01` floor, no MASS arm is evidence of a real mechanism. (3) **Added dots saturate the kernel** — median distance to the nearest parent dot `2.0 px`, `99.81%` within `3 px` — so the add arm densifies already-covered strands rather than extending them. (4) The holdout proxy is structurally `0.000000` for every `>3 px` arm (IR-88-20/35).

## Next three *conditional* slots (integrated queue)
| Order | Arm (blind `SGMC`) | What a receipt changes |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705` = `R1` (anchor; parents all 15 gate-clean rows; locally rebuildable, validator-clean) | Gain `>=0.01` supports the collar+refill lineage and pulls every R1 child up with it; loss `<=-0.01` demotes all fifteen; `|Δ|<0.01` is inconclusive but still establishes the anchor every later paired delta needs. |
| 2 | `MASSr10plus-R1 b2d704df` (`+0.00266` vs `R1`; the largest blind margin among locally validated gate-clean arms, direction replicated on both parents) | `>=0.01` over `R1` makes 41,419 dots the final-file count and licenses the 45,185-dot `r20plus` dose. `<0.01` retires MASS on **both** parents and re-queues `SNAPscarp1px`. |
| 3 | conditional: `SNAPscarp1px-R1 1944aaf5` (`+0.00148`) if slot 2 is non-negative · `SNAPscarp2px-R1 c003d7d7` if a scarp receipt exists and the dose question is live · `PRUNEp3space35 49fff49b` (largest blind margin overall, `+0.0050` vs R0) **only after** exact byte reconstruction + fresh validation — else conserve | A scarp gain `>=0.01` promotes crest re-centering over mass; a scarp loss closes SNAP on both parents. After any material loss: conserve and re-plan from receipts. |

**HOLD / off-queue, regardless of old validators:** every R0-parented non-PRUNE arm (`m10*/r10*` MASS, all `CONCENTRATION`, all R0 `RELIEF`/`SNAP`; IR-88-43/47); `r10minus`/`r10swap` on either parent (negative on both instruments and on both parents); the three TRACKB arms (Phase 2, all below `R1`); all three SPACING arms (sub-threshold); capped-gradient SNAP-R1 (`g2f35/d2f35/d1f35`); `p3norefill`, `ridge2px-R1` (diagnostics).

**Weeks:** Oct 23–Nov 5 (wk1–2): receipt/quota/legal checks; spend slot 1 on `R1` and slot 2 on `r10plus` (or `scarp1px` if the human prefers the geometry lane). Nov 6–19 (wk3–4): slot 3 by receipt; only then combine two axes, naming the true parent. Nov 20–Dec 3 (wk5–6): confirm the leading file twice, choose ONE blind final + fallback twin, re-validate both from disk.

**Better axes, proposals only — one axis per session, none built here:** **MASS-DOSE-R1** (`r20plus`, 45,185 dots) — only if `r10plus` returns `>=0.01`; confounder: kernel saturation (median added-dot distance `2.0 px`); falsifier: gain per added dot falls below the random-donor slope. **DECLUSTER-R1** — delete one dot from every `d_nn < 1.5 px` pair (the refill created dense pairs) and re-spend at `>=2.8 px`; confounder: R1's refills were field-ranked; falsifier: no gain over the same-count random control. **SNAP-FIXPOINT** — iterate the `1 px` spacing-locked scarp snap 2–3 passes; confounder: compounding percentile-field noise; falsifier: blind `SGMC` below single-pass `scarp1px`. **RANKFIELD** — replace `w` with a blind-neutral field in every ranking decision (MASS's random-donor control bounds any ranking change at `±0.0014` on this parent); falsifier: no gain over random donors.

**Evidence discipline:** RECEIPT > CLAIM > PROXY > MODEL. Everything above is PROXY/MODEL except the `R0` CLAIM (`0.2778`, unreceipted). Dedupe is exact-hash and `(parent, axis, value)` only. Human uploads at most one file per slot.
