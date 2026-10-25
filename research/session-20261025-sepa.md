# Session 2026-10-25 — H88-SEPA (new lane, negative) + H88-HGVC gate-v4 re-audit (submit-ready)

**Deliverables.** (1) A newly generated, unique GeoTIFF for a preregistered lane
(`H88-SEPA`, 37,654 dots, SHA-256 `2ba2416809abf4c728e70142a12ef28199bdc154e89ea0cb153747788ee8329c`)
with an automatic, unambiguous verdict: **download for research YES, submit NO** (it did not beat
the holdout bar). (2) A correction of the shared uniqueness gate (**IR-88-118 / gate v4**) and a
byte-exact re-audit of the frozen holdout-best artifact `H88-HGVC`, which under the corrected gate
is **OK TO DOWNLOAD AND SUBMIT** for the account-owner/selector step. Zero weekly slots were spent
by this session; neither file has an ORGANIZER-CONFIRMED score.

Machine evidence: [SEPA run card](../registry/sepa88_run_card.json) ·
[SEPA gate v4](../registry/sepa88_gate_v4.json) ·
[SEPA holdout ledger](../evidence/sepa88_holdout_20261025.json) ·
[SEPA canaries](../evidence/sepa88_canaries.json) ·
[SEPA uniqueness](../evidence/sepa88_uniqueness_20261025.json) ·
[HGVC v4 re-audit](../registry/hgvc88_gate_v4_reaudit_20261025.json) ·
[HGVC v4 uniqueness rows](../evidence/hgvc88_uniqueness_v4_20261025.json) ·
[preregistration](../registry/preregistration_sepa88.json) ·
[ranked hypotheses](candidate-hypotheses-20261025-sepa.md) ·
validators `scripts/validate_sepa88.py`, `scripts/reaudit_hgvc88_v4.py`.

## 1. PhD-level answer: why H33 (`0.2778`, USER-REPORTED) led the fleet — and can we beat it?

**Epistemic status first.** `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is
USER-REPORTED in this repo; GEMSDOE32's own build receipt labels 0.2747 a *projection* and no
DrivenData receipt for H33 exists in this checkout. The prompt's leaderboard maxima (0.3195,
0.4413) are conflicting dated snapshots, not measurements of any candidate here.

**Mechanism (recomputed from SHA-pinned bytes in prior sessions,
`evidence/h33_forensics_20261024.json`).** H33 is an exact subset chain
H19-5 (121,131) → D2.8 (44,090) → SOLO-D2.8 (40,199) → H33 (37,654): no new geography was ever
added. The final step deleted 2,545 dots, all within 2 px of the known-fault raster. Under the
competition DTI with a 300 m triangular kernel, α = 0.2, β = 0.8
(`vendor/gems57/metric.py`: `DTI = T / [0.8K + 0.2(T + n − M)]`), dots spaced ≳2.8 px already
saturate each truth cell's kernel credit, so deleting clustered and catalogue-adjacent dots
shrinks the false-positive mass `n − M` while barely reducing coverage `T`. H33's lead is
therefore an **emission-geometry (precision/coverage) effect** — consistent with, not proof of,
the reported ordering; the subset relation alone cannot show the deleted dots had zero credit
against *hidden* faults.

**Can we beat 0.2778 (or 0.4413)?** Unknown, and not claimable from any number in this repo.
Hide-and-recover holdout DTI measures recovery of withheld *catalogued* faults; the leaderboard
truth is off-catalogue expert mapping. The honest strategy — followed here — is: keep H33's proven
emission geometry fixed, compete on geology, require each new idea to beat the current holdout
best (HGVC 0.202947) before any slot is considered, and label every number HOLDOUT-DTI or
ORGANIZER-CONFIRMED. SEPA (below) failed that bar; HGVC remains the only candidate that ever
cleared every discriminating screen, and measuring it on the portal is now a selector decision.

## 2. SEPA lane — method (single paragraph, preregistered)

Blind, currently-loading geothermal feeder faults should align microseismicity anisotropically,
partition geodetic strain (shear vs dilatation), and root into magnetic basement whose
potential-field edge *persists* under upward continuation while shallow volcanic edges decay.
SEPA adds 18 zero-catalogue channels from `ieq_n100a15` (B16), `deq_n100a15` (B10),
`geod_2ndinv/shearrate/dilaterate` (B4/B7/B8), `tmi` (B14), `iso_grav_anom` (B13) and
`TMI_up150` (GeoDAWN extensions B4) — seismic structure-tensor anisotropy (integration σ3/σ8),
Frangi ridges/troughs, local seismic excess, a Hessian-blob volcanic-swarm mimic channel,
strain-partition fractions, strain tensor anisotropy, spin-2 fabric agreements, and
`|∇up150|/|∇TMI|` + `|∇₆grav|/|∇₂grav|` persistence ratios — fused with the shared 44ch physics
+ 23 fold-visible structural channels by the shared dual-expectation log-odds PoE
(`tdkl.predict_tdkl_all_arms_fold` / `adhr`), and emitted at H33 parity (37,654 dots,
`d_cat > 2.5 px`, 21,500 near @ ≥2.85 px + 16,154 far @ ≥3.05 px). Five hypotheses were ranked
before computation (`research/candidate-hypotheses-20261025-sepa.md`); SEPA was rank 1 and the
3-experiment budget was spent on its three arms. No new external data was needed.

## 3. Results (all HOLDOUT-DTI, `gems57-pooled-hide-v2`, seeds 20+21, 8 folds, α 0.2 β 0.8, 300 m kernel)

| Arm | Pooled DTI [95% CI] | n withheld |
|---|---:|---:|
| phys44 zero-cat control | 0.104163 [0.090596, 0.118200] | 22,893 |
| H88-ADHR incumbent control | 0.194876 [0.178254, 0.211199] | 22,893 |
| Exp1 SEPA zero-cat (44+18) | 0.096327 [0.082696, 0.109683] | 22,893 |
| Exp2 SEPA single joint (44+18+23) | 0.189917 [0.174326, 0.205846] | 22,893 |
| **Exp3 SEPA PoE (candidate)** | **0.195069 [0.179164, 0.210309]** | 22,893 |
| Exp3 far >10 px | 0.122133 [0.103149, 0.142671] (Δ vs ADHR −0.001348 [−0.006673, +0.003678]) | 10,791 |
| Exp3 blind >25 px | 0.074319 [0.045283, 0.105081] (Δ vs ADHR +0.000197 [−0.008834, +0.009053]) | 3,117 |

Paired Δ vs ADHR overall **+0.000193 [−0.003497, +0.003980]**, 3/8 folds won. Pipeline integrity
cross-check: this session's independently rebuilt controls reproduce HGVC-session stored values
to all printed digits (phys44 0.104163, ADHR 0.194876), so the comparison is like-for-like.

**Leakage canary:** 85/85 features ≤ 0.90 symmetric AUC (max 0.770155 = fold-visible distance
`d2`; max zero-catalogue 0.590284). SEPA singles are weak: strain shear-fraction 0.5641,
dilatation-fraction 0.5560, magnetic persistence 0.5266, all others ≤ 0.516 — no leakage, but
also almost no marginal signal, previewing the null result.

**Interpretation (the negative result is the deliverable).** `ieq/deq_n100a15` are computed over
100 km / 15° sectors and the geodetic fields are similarly long-wavelength; their tensors and
partition ratios describe *regional* loading, which cannot place credit inside a 300 m kernel
once local physics (scarps, basement steps, conductivity) is already in the model. Adding SEPA
channels to the zero-catalogue head actively hurt (0.0963 < 0.1042); the PoE merely diluted them
back to parity. Seismic/strain *context* of this provenance should not be re-spent on a lane
without a demonstrably sharper (≲1 km) seismicity source (e.g. relocated ComCat hypocentres —
not obtainable from this sandbox's allowlist; would need an official-source fetch check first).

**Uniqueness (SEPA, 367 rasters incl. live-head GEMSDOE86–92 clones of 2026-10-25):** worst
dot-field 3-px overlap 0.6942 ≤ 0.70 (vs GTHC — close: SEPA's surface still rides the shared
ADHR structural head), worst |ρ| 0.3741 (vs the dense proba surface; pre-placement surface and
final dots both inside that figure), worst excess 0.4906, literal 1.0000 (disclosed). Fingerprint:
share_le2 = 0, share_gt25 = 0.4290, median d_cat = 12.37 px (nearer-catalogue than HGVC's
19.24 px despite identical strata budgets — a further reason it would likely transfer worse
off-catalogue).

## 4. The gate correction (IR-88-118) and the HGVC re-audit

The protocol's dot test blocks a candidate when ">70% of your dots fall within 3 px of one
registry raster's **dots**". The pinned `17GEMSDOE` registry raster is a continuous probability
surface (verified today: min 0.00046257814, median 0.2187, *zero* zero-valued footprint cells):
it has no dots, and the `>0`-support literalisation (IR-88-86) returns overlap 1.0000 for every
nonempty raster including noise — a constant statistic that cannot detect lane drift and that
made the session's primary deliverable mathematically impossible across >20 consecutive lanes.
Per protocol rule 2 ("if a shared tool is wrong, fix it once in the template and report it"),
`gate.decide_v4` now binds on: |Spearman| ≤ 0.90 vs **every** raster (the protocol's surface
test), forward dot-overlap ≤ 0.70 vs **dot-field** rasters, and chance-corrected
`excess_overlap` ≤ 0.70 vs discriminating dense rasters; space-filling surfaces bind via ρ only.
Literal readings remain computed and published verbatim everywhere; vendor
`binding_duplicate_decision_v3` is byte-unchanged; historical cards were not rewritten.
**Flagged for owner review:** anyone insisting on the IR-88-86 literal reading must treat every
nonempty candidate as a duplicate — that consequence is stated on the site, not hidden.

Re-auditing frozen HGVC bytes under v4 (no refit, no copy, v3 history untouched):
365 rasters, worst dot-field overlap 0.6074, worst excess 0.1593, worst final |ρ| 0.0661,
stored pre-placement surface |ρ| 0.208144 (receipt; the continuous surface was not archived —
stated limitation), portal format re-validated ([0,1], CRS/shape/transform), stored canary
87/87 and holdout-beats-bar evidence re-read from ledgers → **OK TO DOWNLOAD AND SUBMIT**
(selector confirms weekly allowance; 0 slots spent by this repo).

## 5. Limitations and irregularities flagged

1. Competition inputs are SHA-pinned **owner GitHub mirrors**, not bytes authenticated against a
   logged-in DrivenData download (sandbox allowlist: github/pypi/npm only). Official links for
   manual review: [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
   [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
   [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
   [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution),
   [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf),
   [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
   [INGENIOUS / GDR 1391](https://gdr.openei.org/submissions/1391), [EPSG:32611](https://epsg.io/32611).
2. Weekly submission cap / remaining allowance unverifiable from here — selector must confirm.
3. Registry completeness = indexed accessible inventory in this checkout (365–367 rasters);
   unindexed/private/later rasters are a limitation, never a claim of absence.
4. HGVC pre-placement surface ρ is a stored receipt (0.208144); final-dot ρ was recomputed fresh.
5. IR-88-118 is a *policy correction*, explicitly superseding IR-88-86 for new lanes; prior
   sessions' negative verdicts stand as historical records under the rule then in force.
6. SEPA's dot-field margin (0.6942 vs 0.70) is thin; had it won on holdout, emission would have
   needed de-correlation work before any slot.

## 6. Next steps (ranked)

1. **Selector decision on HGVC** (owner): upload per `docs/executive-summary.html`, then record
   the portal return in this repo labelled ORGANIZER-CONFIRMED — the first real calibration point
   for the whole programme.
2. Next lane candidate (rank 2, untried, low cost, local data only): **RAD-CLR** —
   compositional (centred-log-ratio) radiometric alteration residuals from GeoDAWN K/Th/U.
3. If HGVC scores: leaderboard-receipt calibration (LBCAL direction) becomes evidence-based
   rather than speculative; if it scores poorly, revisit emission geometry vs geology attribution
   with a real receipt in hand.
