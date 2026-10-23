# SLOT_PLAN — one entity; at most 3 scored files per rolling week

**2026-10-23 · AXIS=MASS (agent-selected) · 3 variants of R0 + a random-donor control.**
All 15 manifest pins verified; R0 rebuilt byte-exactly (zeros `c55bafc4…`, NaN
`baeae321…`, 37,654 dots, 2,171 of them at 2–3 px). Ledger: **35** built rows,
**0** portal receipts. Random arms are diagnostics: no GeoTIFF, no ledger row.

**MASS is now measured, and it is exhausted.** The three MASS rows already in the
ledger were ranked by `0.6*clip(d_cat/50)+0.4*uniform`, which the PR17 audit showed
was ~89% a catalogue-collar extension. These arms are the first ranked by the
parent's own exact-marginal DTI: the dropped dots have mean `w = 0.1445` against a
parent mean of `0.1928` and sit `34.3 px` from the catalogue, so this is mass, not collar.

| Arm | Dots | w-model Δ | Blind SGMC (R0 `0.096060`) | Random-donor control | Dose effect | Ranking effect | Revised MODEL |
|---|---|---|---|---|---|---|---|
| `MASSr10minus` `6d3dd59e` | 33,889 | −0.0084 | 0.087999 (−0.0081) | 0.089830 (−0.0062) | −0.0062 | −0.0018 | **−0.008** [−0.013, −0.003] |
| `MASSr10plus` `24fd987d` | 41,419 | +0.0107 | 0.098918 (**+0.0029**) | 0.097162 (+0.0011) | +0.0011 | +0.0018 | **+0.003** [−0.002, +0.011] |
| `MASSr10swap` `cde5b4a5` | 37,654 | +0.0029 | 0.092054 (−0.0040) | 0.091592 (−0.0045) | −0.0045 | +0.0005 | **−0.001** [−0.006, +0.004] |

**Reading (both instruments agree on the two pure-mass arms):** R0 sits **at** its
mass optimum. Losing 10% of the dots costs 5.6× more than gaining 10% returns
(`−0.0062` vs `+0.0011` on the blind control), the signature of a concave curve
peaking just above 37,654 dots — inside the 37–44 k band every good file occupies.
The field `w` adds only `+0.0018` over random receivers and *loses* `0.0018` versus
random donors, which replicates IR-88-38 (`w` AUC 0.4724 for blind-fault credit).
Catalogue hide-and-recover is degenerate for all arms (`≈0.0040`, `n = 22,663`,
deltas `≤1.7e-4`), so it ranks nothing here — IR-88-35 confirmed at family level.

**Budget/target:** TOP_PUBLIC **unknown** in the current brief (the repository's older
0.4413 is not adopted). Slots left this rolling week / total: **unknown**, never
inferred from blank receipt fields. Deadline **2026-12-03 is human-confirmation
pending**, not verified by this session. Human checks the
[competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
and [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf); no automated access.
One blind final file; primary and zeros twin are alternatives, never two slots.

## Next three slots — conditional, and no MASS arm earns one on its own

| Order | File / predicted live change (MODEL) | What a receipt would change |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705`, +0.005 vs R0 | Standing recommendation from the prior session: gate-clean (`>3 px` on all 37,654 dots). Restore the artifact privately, match its full recorded hash, re-read and validate both twins. A gain ≥0.01 supports the collar+refill package; a loss ≤−0.01 argues against widening. |
| 2 | `MASSr10plus-24fd987d`, +0.003 vs R0 | Only arm in the inventory predicted **positive by two independent instruments**. Spend **only if** the human scopes the `>=3 px` rule as "a controlled single-axis edit may retain the parent's own 2,171 collar dots" — it adds nothing inside 3 px (`min d_cat` of new dots `3.162 px`). A receipt ≥+0.01 would prove R0 is under-massed and re-open count; anything under 0.01 is no evidence and retires MASS. |
| 3 | **Reserve.** Do not spend. | Reserve until slot 1 and (if used) slot 2 have receipts. If the collar is read literally and slot 2 is skipped, the reserve becomes `PRUNEp3.2px-f272cdae` (+0.002) only after a receipt supports widening. |

Every upload awaits human confirmation of quota, exact-file dedupe against actual
submission history, legal data provenance, and a fresh disk validator receipt.
A live difference **under 0.01 is no evidence**; public/private chunks may differ.
`SNAPscarp2px-fae77ff4` stays **HOLD** (min catalogue distance 2.2361 px).
Holdout / SGMC / CV remain report-only PROXY, never promotion gates.

## Weeks to the provisional deadline
- Oct 23–29: human supplies TOP_PUBLIC, slot balance, deadline and the collar-scope
  decision; slots 1–2 above if quota allows.
- Oct 30–Nov 5: evaluate receipts. If `r10plus` is positive, build **MASS on R1**
  (`(PRUNEp3px-6f7ae705, MASS, r10plus)`) — the gate-clean form of this session's
  only positive arm — rather than a second mass dose on R0.
- Nov 6–19: combine two axes only after each has independent ≥0.01 receipt evidence;
  name the actual parent and record spacing/refill confounding.
- Nov 20–Dec 3: confirm the leading file, prepare Phase-2 TRACKB for geologist review,
  choose one blind final and fallback; freshly validate both.

## Better axes — proposed only, not built this session
- **MASS-on-R1:** the same 10% add ranked by exact marginal DTI, but parented on
  `PRUNEp3px` so no dot is inside 3 px. Mechanism: capture the measured `+0.0011`
  dose effect without the collar dispute. Confounder: R1 already refilled 2,171 dots
  onto H19-5 support, shrinking the `>3 px` candidate pool. Falsifier: no ≥0.01 live
  gain, or a smaller candidate pool that erases the dose effect.
- **SUPPORT:** spaced H16-1/H19-4 ridge support instead of densifying saturated H19-5
  (98.2% of this session's additions landed within 3 px of an existing dot).
  Mechanism: recover uncovered strand length. Confounder: ancestor tuning.
  Falsifier: no ≥0.01 gain in a count-matched, spacing-controlled experiment.
- **RANKFIELD:** replace the refill field while holding collar/count/spacing fixed;
  the control here bounds any ranking change at `±0.0018`, so only a materially
  better field is worth a slot. Confounder: bedrock-map bias in SGMC.
  Falsifier: no ≥0.01 live gain and no improvement over random donors.
- **SPACING:** still the one brief-listed axis never built; MASS's saturation
  diagnostic says spacing, not count, binds on H19-5.
