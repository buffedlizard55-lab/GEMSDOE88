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
**Note on the two slot tables below:** the MASS session's merged order and the SPACING/SNAP session's order agree on slots 1 (`PRUNEp3px`) and 2 (`PRUNEp3space35`); they differ only on the reserve (MASS session: `MASSr10plus` if the collar is scoped for controlled R0 edits; SPACING session: `PRUNEp4space35` / `poisson28`). Neither table is an upload instruction.

## Concurrent sessions — SPACING (PR #35) + SNAP clearance audit (PR #36)

**`2026-10-23` · AXIS = SPACING (3 built, all HOLD) + `AXIS = SNAP` audit (`0` new variants, pure-R0 SNAP impossible) + merged PR #34 PRUNE refill-mode.** All `15` manifest pins verified; R0 rebuilt byte-exactly (zeros `c55bafc4…`, NaN `baeae321…`, `37,654` dots). Ledger: **`38`** built rows (`32` audit base + `3` spaced refill + `3` SPACING), **`0`** portal receipts. No `(parent, axis, value)` or SHA-256 collision any way; pre-existing PRUNE `p1/p3/p4` TIFF twins recreated at exact ledger hashes with six fresh disk checks passing (`evidence/session_20261023_prune_revalidation.json`).

**Before any slot:** human supplies current `TOP_PUBLIC`/date, actual weekly/total balance (unknown), R0 receipt (`0.2778` is CLAIM), permission to use/redistribute the public mirrors and old tracked TIFFs, and confirms the provisional `2026-12-03` deadline on the competition page and rules. No automated page access or submissions. Primary/zeros twin = **one** slot; one blind final. Public/private/expert-expanded chunks differ; `|live delta| < 0.01` is no evidence. Without an R0 receipt no paired live delta is established. New `p3space35`/`p4space35` TIFFs are **absent locally**; their receipts require exact reconstruction and fresh validation.

## Session results — refill spacing (PR #34), receiver geometry (SPACING), SNAP clearance (PR #36)
| Arm | Edit | `N` | refill min NN | four-line field `MODEL` vs R0 | blind `SGMC` `PROXY` vs R0 |
|---|---|---:|---:|---:|---:|
| `p3norefill` `fb308615` | `300 m` collar, **no refill** | `35,483` | – | `0.270354` (−0.0157) | `0.093643` (−0.0024) |
| `p3space35` `49fff49b` | `300 m` collar, `3.5 px` spacing lock | `37,654` | `3.4641 px` | `0.273539` (−0.0112) | `0.101042` (+0.0050) |
| `p4space35` `07bd8182` | `400 m` collar, `3.5 px` spacing lock | `37,654` | `3.4641 px` | `0.278731` (−0.0228) | `0.102454` (+0.0064) |
| Arm (on `R1`) | Receiver geometry | moved | receiver min NN | `w`-DTI field `MODEL` vs R1 | blind `SGMC` vs R1 `0.096083` |
| `poisson28` `60f65400` | farthest-point, `R1 = 2.8 px` decluster | `1,914` | `2.2361 px` | `−0.0026` (pred `+0.003`) | `0.096820` (+0.00074) |
| `strike` `bc8e6d1a` | along-strike H19-5 alignment | `1,914` | `1.0000 px` | `−0.0059` (pred `+0.000`) | `0.095396` (−0.00069) |
| `lattice4px` `6c7e0b72` | `4 px` grid, phase frozen | `1,914` | `1.0000 px` | `−0.0059` (pred `−0.004`) | `0.095292` (−0.00079) |

Both sessions' instruments **disagree** (their IR-88-44; SPACING reproduces it: field prefers densified placement, `SGMC` prefers spaced placement), and neither is a live score. Shared substantive finding: **spacing/uniformity is the lever, spaced ancestor support amplifies it** (`p3space35 +0.0050` vs `poisson28 +0.00074`); ancestor support is a confounder, so even a live delta does not isolate spacing alone. `p3norefill` is diagnostic only. Strict spacing locks on `H19-5` at matched count are infeasible (their IR-88-43, agreed); maximal-spacing variants on un-emitted `H19-5` are feasible and built (IR-88-48). Pure-R0 SNAP is geometrically impossible under the literal `3 px` clearance: `30` of `1,611` sub-`3 px` dots have no compliant in-footprint pixel within `<=2 px`, even ignoring collisions — do not substitute a PRUNE refill and call it SNAP (their IR-88-47; `evidence/session_20261023_snap_clearance.json`). Earlier R0 non-PRUNE arms retaining the collar stay HOLD.

## Next three conditional slots (SPACING/SNAP session's ordering)
| Order | Existing arm / live projection (MODEL vs R0) | What a receipt changes |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705` / +0.005 | Gain `>=0.01` supports the `300 m` collar+refill; loss `<=-0.01` closes this family; otherwise inconclusive. This file alone is freshly validated and locally available (primary + fallback). |
| 2 | `PRUNEp3space35-49fff49b` / +0.007 | Only if slot 1 does not materially lose, the human approves another test, and exact bytes validate. Gain `>=0.01` **over `p3px`** favors spaced refill; loss `<=-0.01` disfavors it; smaller differences teach nothing. `poisson28` is also above its parent at one-seventh the gain, so slot 2 tests spacing support by effect size. |
| 3 | Reserve `PRUNEp4space35-07bd8182` / +0.002 | Only if slot 2 materially wins: a `>=0.01` gain vs slot 2 favors widening with spaced refill; `<=-0.01` loss favors `300 m`. Else conserve the slot. |

**HOLD, regardless of old validators:** `SNAPscarp2px-fae77ff4` and all R0 SNAP/CONCENTRATION/RELIEF arms retaining sub-`3 px` mass; all 3 SPACING arms (sub-threshold diagnostics, `|SGMC delta| < 0.001`); `PRUNEp1px` (PRUNE `<3 px` mass allowed by the exception, diagnostic rather than a lead). Human uploads at most one file per slot.

**Weeks:** Oct 23–Nov 5 (wk1–2): receipt/quota/legal checks, conditional PRUNE; Nov 6–19 (wk3–4): combine axes only with independent `>=0.01` receipt evidence on a gate-clean parent; Nov 20–Dec 3 (wk5–6): validate final and fallback from disk, choose one blind final. `TRACKB` is Phase-2 geologist review only.

**Better axes, proposals only:** SUPPORT — new spaced H16-1/H19-4 strands may cover gaps; spaced-support receiver confounder prior is leaderboard-tuned; falsifier: no `>=0.01` live gain at matched count/collar. RANKFIELD — change `p3px` refill ranking at fixed spacing; confounder SGMC map bias; falsifier: no `>=0.01` gain vs randomized ranking. STRIKE_ALIGN — snap on gate-clean `p3px` to coherent edges; confounder lithology / GeoDAWN flight lines; falsifier: no gain over randomized-strike control. Build each separately.
