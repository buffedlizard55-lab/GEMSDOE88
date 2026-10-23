# SLOT_PLAN — one entity; <=3 scored uploads per rolling week

**2026-10-23 · AXIS=MASS (agent-selected) · 3 variants of R0 + a random-donor control.**
All 15 manifest pins verified; R0 rebuilt byte-exactly (zeros `c55bafc4…`, NaN
`baeae321…`, 37,654 dots; 2,171 at <=3 px, 1,611 strictly
inside 3 px). Ledger: **38** built rows (35 on main + 3 here),
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

**Reconciliation with the concurrent 2026-10-23 session (PR #36, `AXIS=SNAP`).** That session
built no variants: it proved pure R0 `SNAP` is geometrically impossible (30 of R0's 1,611 dots
inside 3 px have no `>=3 px` destination within a `<=2 px` move —
`evidence/session_20261023_snap_clearance.json`, IR-88-47), added three spacing-locked PRUNE
refill arms (`p3norefill`, `p3space35`, `p4space35`), and **corrected
`scripts/validate_variant.py`** so non-PRUNE axes now fail on any positive mass at `<3 px`.
Consequence for this page: all three `MASSr10*` arms inherit R0's 1,611 collar dots and are
**HOLD** under the corrected gate, so the merged slot order below puts the gate-clean PRUNE
arms first. The `MASS` finding itself is unaffected — the mass-response curve is a property of
the parent's dot set, not of the collar — and its submission-eligible form is `MASS-on-R1`.

## Next three slots — merged order after the PR #36 reconciliation

| Order | File / predicted live change (MODEL) | What a receipt would change |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705`, +0.005 vs R0 | Gate-clean on all 37,654 dots and now locally revalidated byte-for-byte by PR #36. A gain ≥0.01 supports the collar+refill package; a loss ≤−0.01 argues against widening. |
| 2 | `PRUNEp3space35-49fff49b`, +0.007 vs R0 (PR #36) | Highest MODEL that is also gate-clean, so it outranks `MASSr10plus` (+0.003). Tests whether spacing-locked refill beats unconstrained refill — the confounder IR-88-37 recorded. Requires a fresh artifact rebuild and validation first. |
| 3 | **Reserve.** `MASSr10plus-24fd987d` (+0.003) only if the human explicitly scopes controlled R0 edits out of the `<3 px` gate **and** slots 1–2 have receipts; otherwise hold the slot. | Spending it as an experiment is only informative if the ≥0.01 threshold is reachable; `+0.003` is below the brief's no-evidence floor. |

## Weeks to the provisional deadline
- Oct 23–29: human supplies TOP_PUBLIC, slot balance, deadline; slots 1–2 above if quota allows.
- Oct 30–Nov 5: evaluate receipts. Build **MASS-on-R1** (`(PRUNEp3px-6f7ae705, MASS, r10plus)`) —
  the gate-clean form of this session's only positive arm — rather than a second dose on R0.
- Nov 6–19: combine two axes only after each has independent ≥0.01 receipt evidence; name the
  actual parent and record spacing/refill confounding.
- Nov 20–Dec 3: confirm the leading file, prepare Phase-2 TRACKB for geologist review, choose one
  blind final and fallback; freshly validate both.

## Better axes — proposed only, not built this session
- **MASS-on-R1:** the same 10% add ranked by exact marginal DTI, but parented on `PRUNEp3px` so no
  dot is inside 3 px. Mechanism: capture the measured `+0.0011` dose effect without the collar
  dispute. Confounder: R1 already refilled 2,171 dots onto H19-5 support, shrinking the `>3 px`
  candidate pool. Falsifier: no ≥0.01 live gain, or a smaller pool that erases the dose effect.
- **SUPPORT:** spaced H16-1/H19-4 ridge support instead of densifying saturated H19-5 (98.2% of this
  session's additions landed within 3 px of an existing dot). Mechanism: recover uncovered strand
  length. Confounder: ancestor tuning. Falsifier: no ≥0.01 gain in a count-matched experiment.
- **RANKFIELD:** replace the refill field while holding collar/count/spacing fixed; the control here
  bounds any ranking change at `±0.0018`, so only a materially better field is worth a slot.
  Confounder: bedrock-map bias in SGMC. Falsifier: no ≥0.01 gain and no gain over random donors.
- **SPACING:** still the one brief-listed axis never built; MASS's saturation diagnostic says
  spacing, not count, binds on H19-5.
