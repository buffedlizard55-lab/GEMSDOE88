# 2026-10-24 — Why did `h33-h33-2-b2` score 0.2778 (CLAIM), can we beat it, and is the PROVCREST "promote" real?

Evidence labels: **HOLDOUT-DTI** = local hide-and-recover instrument (`gems57-pooled-hide-v2`);
**CLAIM** = user-reported live score with no portal receipt in this repo; **OBSERVED-PUBLIC** = read from the
public leaderboard page; **MODEL** = a prediction, never a score. Nothing below is an ORGANIZER-CONFIRMED score for any
GEMSDOE88 file (there is none; 0 weekly slots were spent).

## 0. Ground truth first (verified this session)

| Fact | Evidence | Link |
|---|---|---|
| Public #1 = 0.4413 (xiaofanhu); #2 0.3916; #3 0.3904; **#50 = 0.2818** | OBSERVED-PUBLIC, one read of the page on 2026-10-24 (`docs/data/leaderboard.json`) | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> |
| The CLAIMED 0.2778 would sit **below rank 50**; 15 teams sit between 0.326 and 0.333 (ranks 9–23) | same page | same |
| The brief quotes 0.4413, 0.3195 and 0.2778 as "highest" — mutually inconsistent | **Irregularity**: 0.4413 is #1 today; 0.3195 would be mid-table | — |
| Submission form fields: *File to submit* (single-band GeoTIFF or a ZIP with one GeoTIFF; must match CRS, shape, geotransform) and *Note (optional)* only — **there is no name field** | the brief's form transcript | <https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/> |
| Metric: DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w), 300 m triangular kernel | `vendor/gems57/metric.py`, transcribed from the problem page | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> |
| Reference solution is a U-Net notebook (author J. Lipor) | repo page | <https://github.com/drivendataorg/gems-prize-reference-solution> |

## 1. Why the h33 lineage scored high (reading, with its limits)

**1a. Metric algebra.** For binary dots, DTI rises when a dot is added iff its marginal kernel credit exceeds
`α·DTI` (`metric.py`, exact two-sided form). At DTI ≈ 0.28 that bar is only ≈ 0.056 of one truth pixel, so the metric rewards
**many well-separated dots that each own a private 300 m kernel**. Two dots closer than 3 px share kernel area: `T` (truth credit)
saturates at 1 per truth pixel while `M` (dot self-credit) does not, so the second dot costs FP weight without adding TP.

**1b. Measured geometry of 13 restored rasters with CLAIMED scores (selected rows shown; full table in the JSON)** (`scripts/analyze_lineage.py`,
`evidence/lineage_live_vs_geometry.json`):

| Raster | CLAIM | dots | median px to catalogue | nearest-dot px | share > 25 px from catalogue |
|---|---:|---:|---:|---:|---:|
| h16-1 / h19-4 / h19-5 | 0.1855 / 0.1894 / 0.1922 | ~121–124k | 14.6–14.9 | 1.00 (≈ 89% have a neighbour < 2 px) | 0.35 |
| d1-5 | 0.2477 | 60,069 | 14.9 | 2.24 | 0.35 |
| d2-8 | 0.2600 | 44,090 | 15.0 | 3.00 | 0.36 |
| h27-4 | 0.2708 | 40,199 | 17.7 | 3.00 | 0.39 |
| **h33 (R0)** | **0.2778** | 37,654 | 19.7 | 3.00 | 0.42 |
| h83-gvcd / h85a / h81-contasb (catalogue-hugging) | 0.0573 / 0.1110 / 0.0041 | ~38–44k | 7.6 / 4.0 / 5.0 | 3.6 / 2.2 / 2.8 | 0.05 / 0.02 / 0.00 |

Two separable effects are visible among the ledger-linked members:
1. **Kernel de-redundancy.** 121k → 44k dots with nearest-neighbour spacing 1.0 → 3.0 px lifts 0.1922 → 0.2600 while the
   distance-to-catalogue profile is unchanged (median 14.6 → 15.0 px). That isolates the redundancy term in 1a.
2. **Moving mass away from mapped faults.** 0.2600 → 0.2778 coincides with the ≤ 3 px share falling 19.5% → 5.8% and the median
   distance rising 15.0 → 19.7 px. The catalogue-hugging rasters score 0.004–0.111.

Across all 13, Spearman(median distance to catalogue, CLAIMED score) = **0.891** — *descriptive only*: n = 13, seven members are
ledger-linked (`ledger/historical_climb.csv` parents), scores are claims. It describes where the hidden positives sit relative to the mapped catalogue; it is not a causal law.

**1c. What this does not explain.** (i) The lineage was tuned through several live receipts (5 rows in `ledger/historical_climb.csv`), so part of its score
is information about the public labels that no local holdout can reproduce — R0 scores **0.004** on the hide-and-recover holdout *by construction*
(it was built with the full catalogue, IR-88-20). (ii) 49 entries sit above 0.2818, 15 of them in a tight 0.326–0.333 band; whatever that cluster shares is
not recoverable from public information and is not in this repo.

## 2. Can we beat 0.2778? — honest answer

*Not demonstrable locally.* What can be shown: PROVCREST reproduces both measurable properties (spacing ≥ 3.5 px; median distance 22.8 px,
46% beyond 25 px) while sharing no dots with the lineage (worst 3-px overlap 0.4076, worst |ρ| 0.0302), and its crest field carries signal on withheld faults
(Section 3). Risks: its distance profile lies **outside the observed range** (max 19.7 px), so the 0.891 trend cannot be extrapolated, and a
field-independent crest ranking may simply be worse than a field that was tuned on live feedback. The only instrument that can settle it is a
portal receipt — a selector decision this repo does not take. Beating 0.2778 would still leave ≥ 50 entries above it.

## 3. Pass-2 finding: the original "promote" compared against a degenerate control (IR-88-59)

The PROVCREST promotion cited a paired win over R0 (0.0763 vs 0.0040). R0 cannot be recovered by a visible-only protocol, so that win is vacuous. This session added the
controls that *can* fail (same N, same ≥ 3.5 px spacing, same visible-catalogue collar, no crest information):

| HOLDOUT-DTI (22,663 withheld; FAR = 10,277 withheld > 10 px from visible faults) | ALL | FAR |
|---|---|---|
| **PROVCREST (shipped)** | **0.076277** [0.067653, 0.084607] | **0.055756** [0.047242, 0.063384] |
| null: random order | 0.047876 [0.044093, 0.051372] | 0.033458 [0.029404, 0.037206] |
| null: hex lattice | 0.048408 [0.044269, 0.052441] | 0.032734 [0.028649, 0.036822] |
| paired Δ vs random (95% CI) | +0.028401 [0.020200, 0.036505] | +0.022298 [0.014244, 0.029966] |
| paired Δ vs lattice (95% CI) | +0.027869 [0.020254, 0.034890] | +0.023022 [0.015276, 0.030764] |

Verdict: **the promote survives** a real control (≈ +60% relative lift over no-information dots at identical geometry), and the shipped TIFF
reproduces **bit-for-bit** from the SHA-pinned restored inputs (`SCI-03`). The gate (`scripts/submission_gate.py`) now *requires* both.
The nulls score 0.048 — most of any holdout score is geometry/coverage, which is why a no-information control is mandatory.

## 4. Experiments (budget 3, all used; none spent a slot)

| # | Single factor | Result (HOLDOUT-DTI) | Decision |
|---|---|---|---|
| 1 | null controls + reproduction (above) | promote survives | gate hardened |
| 2 | min spacing 3.0 / **3.5** / 4.5 px | 0.073214 / **0.076277** / 0.074367; Δ(3.5−3.0) +0.003064 [0.000821, 0.005191]; Δ(3.5−4.5) +0.001910 [−0.001077, 0.004845] | **negative** — shipped spacing is the local optimum |
| 3 | N = 20k / 28k / **37,654** / 50k / 65k | 0.048439 / 0.064084 / **0.076277** / 0.085330 / 0.090291 | **hold** — monotone, as the marginal rule predicts at low DTI; but the live lineage improved while *thinning* (1b), so the holdout and live regimes disagree; N is a selector variable, not changed |

## 5. Hypotheses not yet tried (ranked by expected DTI gain ÷ cost; all MODEL, none validated)

Lane note: sibling-lane status comes from the brief's score list and `ledger/`; rasters for GEMSDOE42/67/69 are not in the restored registry, so overlap
vs those lanes is **unmeasured** and must be measured (≤ 0.70 forward overlap, |ρ| ≤ 0.90) before any build is promoted.

| Rank | Hypothesis | Layers | Physical signature → why it can catch an *uncatalogued* fault | Differs from | Cost |
|---:|---|---|---|---|---|
| 1 | **Crest-junction/termination prior (Favorable-Structural-Setting proxy computed from crests, not from the catalogue)** | crest masks of Bands 19, 3, 18, 15 already built in `build_provcrest_submission.py` | Thin the crest mask; endpoints (horse-tailing terminations), T/X junctions (intersections) and overlapping parallel crests (step-overs) are the settings hosting most Great Basin systems — step-overs ~32% and terminations ~25% of 250 categorised fields ([Faulds & Hinz 2015](https://www.osti.gov/servlets/purl/1724082)). The geometry is computed from geophysics/topography alone, so it applies where no fault was mapped. Mean relay-ramp width in the western Great Basin is 2.5 km ([Giddens 2025](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf)) = 25 px, far larger than the 3 px kernel, so dots must be placed *at* the junction. | catalogue-geometry relay/tip lanes (h33d, h69, h8-tiprelay) use mapped faults; this uses crest geometry | Low (hit-or-miss on a thinned mask) |
| 2 | **Dilation-tendency-weighted crests** | crest orientation (Hessian eigenvector) + strain-tensor bands (README lists bands 4/10/11 and `strain_2nd_inv`) | Slip tendency `Ts = τ/σn` ([Morris et al. 1996](https://doi.org/10.1130/0091-7613(1996)024<0275:STAAFR>2.3.CO;2)) and dilation tendency `Td = (σ1−σn)/(σ1−σ3)` (Ferrill et al. 1999, as quoted in [GRC 2013, OSTI 1110515](http://www.osti.gov/scitech/servlets/purl/1110515)) rank fault orientations by how readily they open; high-`Td` crest segments are more likely to carry fluid. Non-fault mimic: lithologic contacts with the same strike. | orientation-only lane (h67a, CLAIM 0.0356) used orientation without a stress model | Medium (needs a defensible σ1/σ3 azimuth from the strain bands; unverified) |
| 3 | Scale-persistence of crests (σ = 1…4 px) | Bands 19/3/18/15 | Real fault expression persists across smoothing scales; 400 m flight-line leveling seams and noise do not. | partially overlaps `xscale-worm-persistence` (GEMSDOE42, CLAIM 0.0581) — lane risk | Low |
| 4 | Relief-conditioned K/Th alteration (RDC-88, already queued) | Bands 5–8, 12, 19 | K/Th enrichment on piedmont fault zones without modern springs. Mimic: felsic tuff contacts. | unrun in this repo | Medium |

Every candidate must first beat **both** null controls (paired CI > 0, ALL and FAR) and the canary (≤ 0.90) before a slot is considered.
If a candidate needed new external data, the named free official sources are USGS GeoDAWN (CC0,
<https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>),
DOE GDR #1391 (<https://gdr.openei.org/submissions/1391>) and USGS 3DEP (already restored and SHA-pinned in `registry/data_manifest.json`); none is needed for ranks 1–3.

## 6. Limitations / blockers (what we cannot do from here)

* No DrivenData login ⇒ cannot read the organizer `training_features.tif`/labels directly; this repo uses SHA-pinned owner-mirror copies (owner-hosted, not independently organizer-authenticated; IR-88-02).
* No portal receipt exists, so every score in this repo is HOLDOUT-DTI/PROXY/CLAIM. The leaderboard was read once by a hand-initiated fetch; no scraper was run.
* The holdout can rank ideas against each other and against no-information nulls; it cannot rank against the live lineage.
* Hosts reachable from the sandbox for code are GitHub/PyPI/npm; the leaderboard and papers above were read through the page-fetch tool.

## 7. Reproduce

```
python scripts/restore_inputs.py                 # SHA-pinned grid + 19-band features + external data
python scripts/audit_provcrest_nullcontrol.py    # Exp 1 (~100 s)
python scripts/exp_provcrest_spacing.py          # Exp 2 (~60 s)
python scripts/exp_provcrest_spacing.py count    # Exp 3 (~90 s)
python scripts/analyze_lineage.py
python scripts/submission_gate.py --require-submit   # exit 0 = OK to submit this file
python scripts/render_site.py                        # regenerate pages from the gate
```
