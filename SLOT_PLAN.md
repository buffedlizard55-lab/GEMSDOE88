# SLOT_PLAN — one entity; <=3 scored uploads per rolling week

**`2026-10-24` · session `AXIS=PRUNE` (spacing-lock dose ladder + ordering control), PR after this file.**
All `15` manifest pins verified; `R0 = h33-h33-2-b2` rebuilt byte-exactly (`zeros c55bafc4…`, `nan baeae321…`, `37,654` dots). Ledger now **`59`** built rows across all 7 brief axes, **`0`** portal receipts, zero `(parent, axis, value)` and zero SHA-256 collisions. Nothing here is a score: `R0 0.2778` is a **CLAIM**; every variant number is `PROXY`/`MODEL`.

**Human must supply before any upload:** current `TOP_PUBLIC` + date (blank in both briefs; repo's `0.4413` of `2026-10-22` is stale and `UNVERIFIED`, IR-88-49), actual rolling-week/total slot balance, permission to use/redistribute the owner's public mirrors, and a confirmation of the `2026-12-03` deadline. No automated page access, no submission, no credentials.

## This session: `PRUNE` spacing-lock dose ladder on `R0` — built, gate-clean, and closed as a slot axis
Why `PRUNE`: it is the only axis an `R0` child can edit without inheriting R0's sub-`3 px` collar (IR-88-47); `MASS`, `CONCENTRATION`, `SNAP`, `RELIEF`, `SPACING`, `TRACKB` are all closed on this lineage. Within `PRUNE` the one live lever is the spacing-locked refill (`p3space35 +0.0050`, `p4space35 +0.0064` vs `p3norefill -0.0024` and densifying `R1 ±0.0000` on the blind control). Predictions frozen in `registry/prune_spacing_dose_preregistration.json` before any proxy. Matched triplet: same parent, same `3 px` collar, same `2,171` donors, same `N = 37,654`, same H19-5/H19-4/H16-1 pool, same seed.

| Arm | Change | blind SGMC `PROXY` vs `R0 0.096060` | field `w` (MODEL) |
|---|---|---:|---:|
| `p3space28 91d221ad` | lock `2.8 px` (dose down) | `0.099446` (**+0.00339**) | `-0.00937` |
| `p3space35 49fff49b` | lock `3.5 px`, ledgered reference | `0.101042` (+0.00498) | `-0.01117` |
| `p3space35rand 8b3d0a40` | lock `3.5 px`, **random refill order** (control) | `0.101146` (**+0.00509**) | `-0.01345` |
| `p3space45 7a281bde` | lock `4.5 px` (dose up) | `0.101629` (**+0.00557**) | `-0.01261` |

**Findings (all PROXY/MODEL, all below the `0.01` no-evidence floor).** (1) **The order control kills the field story:** at identical geometry a seeded random refill order scores `0.000104` from the ranked arm, so the label-free four-line field contributes essentially nothing to refill placement (cf. the MASS random-donor control, `±0.0018`). Build future refills without `w`. (2) **The dose is saturating and nearly flat:** `2.8 → 3.5 → 4.5 px` gives `+0.0034 → +0.0050 → +0.0056`; the second half of the ladder buys `0.00059`, a tenth of the floor. Do not push the lock further for the final file. (3) **The mechanism is not mutual refill spacing but distance from the surviving dot field:** refill-pair nearest neighbours average `17.4-18.7 px` (the mutual lock almost never binds), while distance to the nearest surviving R0 dot rises `5.89 → 7.22 → 8.69 px` and the share of additions still on the saturated H19-5 support falls `20.9% → 6.5% → 8.6%` (`evidence/prune_spacing_dose_geometry.json`). The lock therefore acts as a **novelty radius**, which is the quantity a next-generation arm should set directly. (4) The two instruments still disagree in sign: `w` prefers the tightest lock, blind `SGMC` the widest, and their whole spread here is `0.003` — inside noise for this instrument (IR-88-51).

**Queue unblocked:** the two ledgered spaced arms were absent from the checkout, so slot 2 could not be executed. `scripts/rebuild_prune_spaced_artifacts.py` reproduces both **byte-exactly** (`p3space35 49fff49b…`/zeros `e0b9d59b…`, `p4space35 07bd8182…`/zeros `fb7ee110…`), hardened validator PASS on disk, `evidence/prune_spaced_artifact_rebuild.json`. Both files now exist in `releases/` and are upload-ready.

## Next three slots (order unchanged; slot 2 is now executable)
| Order | File | What the receipt changes |
|---|---|---|
| 1 | `PRUNEp3px 6f7ae705` (`R1` anchor) | Parents 27 ledgered children. `>= +0.01` supports the collar+refill lineage; `<= -0.01` closes it and demotes every `R1` child; `|Δ| < 0.01` is inconclusive and slot 2 disambiguates by pair. |
| 2 | `PRUNEp3space35 49fff49b` (rebuilt + re-validated this session) | `>= +0.01` over `p3px` means the spacing-locked refill pays → the final file should be a spaced-refill arm; `<= -0.01` closes the whole spaced-refill family including this session's triplet. |
| 3 | conditional: `PRUNEp4space35 07bd8182` (also rebuilt this session) after a `p3space35` win; else conserve and re-plan from receipts | Arbitrates the `300` vs `400 m` collar. Its `w`-MODEL is the worst in the inventory (`-0.0228`), so a live win would say the field instrument is inverted for collar edits. |

## Weeks to the deadline (`2026-12-03`, ~6 weeks)
`wk1 (now)`: run slots 1–2 and get the first receipts ever — the ledger is entirely unpriced, which is the largest single risk. `wk2–3`: slot 3 by receipt; if `p3space35` wins, build ONE combined arm (`p4`-collar or novelty-radius, not both) in a separate session, naming the true parent. `wk4–5`: combine the two best axes only after each has an independent `>= 0.01` receipt on a gate-clean parent. `wk6`: confirm the leader twice, choose ONE blind final + a fallback twin, re-validate both from disk with the hardened validator. `TRACKB` stays Phase-2 geologist review only.

## Better axes — proposals only, one per session, none built here
**NOVELTY_RADIUS** (the successor to this session): set the *distance from every surviving dot* directly (`6/8/10 px`) instead of a mutual lock, holding collar/donors/count/pool and using a random or maximin order since ranking is worthless. Confounder: displacement itself, not novelty of ground, may drive the blind instrument (IR-88-51). Falsifier: no `>= 0.01` live gain over `p3space35` and no monotone ordering across the three radii. **RE-MAP GAP** — refill into the largest *empty* 1 km blocks rather than by ridge support (post-`CONCENTRATION` mirror result). Confounder: uniformising density regresses to background. Falsifier: no gain over a random-receiver control at matched CV. **INSTRUMENT_AUDIT** (still the cheapest unknown): one seeded `1 px` random-jitter twin of a gate-clean parent beside a receipted crest arm — until a receipt exists, no proxy here can be ordered at all.

**Evidence discipline:** RECEIPT > CLAIM > PROXY > MODEL; `|live delta| < 0.01` is no evidence; dedupe on exact hash and `(parent, axis, value)` only; the human uploads at most one file per slot.
