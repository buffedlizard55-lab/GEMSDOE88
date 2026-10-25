# H33 on-disk forensics: evidence, limits, and what would be needed to beat it

**Review date:** 2026-10-25 UTC
**Artifact reviewed:** `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`data/registry/h33_education.tif`)
**Evidence status:** local raster measurements are reproducible; public score and leaderboard values below are not organizer-confirmed receipts.

## Direct answers

- **Why did H33 score 0.2778?** The repository cannot establish the causal reason. The value is **USER-REPORTED**, not copied from a submission receipt. On-disk geometry shows H33 is a subtractive subset of an earlier prediction lineage, with sparse spacing and removal of catalogue-near pixels. That is *consistent with* lower redundant false-positive mass under the local distance-weighted Tversky metric, but it does not prove that explanation or reveal the hidden test labels.
- **Can a new method beat it?** It is possible in principle, but **this review cannot show that any candidate will beat H33**. No new method was trained or tested. No organizer-confirmed score for H33 or a GEMSDOE88 artifact is present here. The current dense-witness rule blocks every non-empty prediction before placement; that is a protocol stop, not evidence that all geological methods are incapable of improving.
- **Which public benchmark is current?** User-provided values conflict (`0.3195` and `0.4413` are both cited in the request). Neither was independently checked in this review. Treat both as dated/USER-REPORTED context until verified on the official page; neither is a candidate score.

## Evidence classes and score ledger

| Value | Label and source | What it does and does not mean |
|---|---|---|
| `0.2778` for H33 | **USER-REPORTED** in repository notes; no submission-page receipt is stored | A public-score claim, not an independently confirmed organizer score. |
| `0.3195`, `0.4413` | **USER-PROVIDED / UNVERIFIED** conflicting leaderboard snapshots | Not freshly fetched; date, round, and public/private status are unresolved. |
| `HOLDOUT-DTI 0.0038851763`, 95% CI `[0.0033163453, 0.0044778909]`, `22,893` withheld positives, evaluator `gems57-pooled-hide-v2` | Stored fixed-raster H33 diagnostic in `registry/mdps88_run_card.json` / `docs/data/protocol_review_43d08c7a.json` | A historical **fold-unfair fixed-raster catalogue hide-and-recover diagnostic**, not a fair retraining comparison and not a leaderboard estimate. It cannot explain or refute the reported public value. |
| `HOLDOUT-DTI 0.1413781360`, 95% CI `[0.1276877737, 0.1561120556]`, `22,893` withheld positives, evaluator `gems57-pooled-hide-v2` | Stored H88-DHTC run card and holdout ledger | A prior local holdout result for an existing artifact; not a public score, not a new run in this review, and not evidence of beating H33. |
| `HOLDOUT-DTI 0.1962369466`, 95% CI `[0.1796859281, 0.2117291340]`, `22,893` withheld positives, evaluator `gems57-pooled-hide-v2` | Stored H88-TDKL run card | A historical local result on the repository's blocked-catalogue holdout; not an organizer score and not evidence about private leaderboard performance. |
| Organizer-confirmed scores | **None found** for H33 or the reviewed GEMSDOE88 artifacts | Only a copied submission-page receipt would qualify. |

The local evaluator hides whole catalogue components and scores recovery of withheld catalogue pixels. The competition's undiscovered-fault population may differ. Therefore, local holdout results, owner reports, and public leaderboard snapshots must not be compared as if they were measurements of the same target.

## What the SHA-pinned rasters establish

The fresh geometry review reopened the aligned registry rasters. These are **REGISTRY-MEASUREMENTS**, not performance scores:

| Raster | Positive pixels | SHA-256 | Relationship to H33 |
|---|---:|---|---|
| H19-5 | 121,131 | `ef2ae808eb7179861b9f1ff753fd3ded625ace7b7c158e29cec45bbd8fa3cfaa` | Ancestor support. |
| D2.8 | 44,090 | `3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd3091845cd9bcc30` | Strict subset of H19-5; no added pixels. |
| SOLO-D2.8 | 40,199 | `2fc94a38d77f74d4f4ed1a97a83e7bb71a1ceea090515ec641e6681cc47c44c8` | Strict subset of D2.8; no added pixels. |
| H33 | 37,654 | `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` | Strict subset of SOLO-D2.8; no added pixels. |

All four grids align. The measured inclusion chain is `H33 ⊂ SOLO-D2.8 ⊂ D2.8 ⊂ H19-5`. The D2.8-to-H33 difference removes `6,436` pixels; each removed pixel is `1–2` pixels from the mapped catalogue in the local distance transform. In H33, minimum catalogue distance is `2.2361` pixels, median is `19.6469` pixels, `41.74%` of dots lie more than `25` pixels away, and nearest-neighbour spacing has a `3.0`-pixel median (`81.46%` between `2` and `4` pixels). The raster audit is recorded in [`h33_forensics_20261024.json`](../evidence/h33_forensics_20261024.json) and the follow-up catalogue-distance measurement in the 2026-10-25 session record.

These observations establish **subtractive lineage and spatial geometry only**. They do not establish that removed pixels were false positives, that H33 was generated by any particular model, or that thinning caused the reported score increase. The H33 file contains no hidden truth. The old forensic prose that asserted zero truth credit, a measured `10–15%` precision, a score-correlation law, or a guaranteed path to `0.3539–0.4413` exceeded the available evidence and is withdrawn here.

## Why thinning is a plausible explanation—but remains a hypothesis

The pinned local metric implementation is `vendor/gems57/metric.py`. It computes weighted true-positive credit `T` from truth pixels, weighted prediction self-credit `M` from prediction pixels, `FP_w = n - M`, and `FN_w = |G| - T`, then

\[
\mathrm{DTI}=\frac{T}{T+0.2\,FP_w+0.8\,FN_w}.
\]

With the binary-dot form this can be rearranged as

\[
\mathrm{DTI}=\frac{T}{0.8|G|+0.2T+0.2(n-M)}.
\]

Because truth credit uses a maximum within the triangular kernel, a second nearby dot can add little or no new `T` while still adding prediction-side mass. Removing a genuinely low-marginal-credit dot can therefore help. For an added isolated dot with marginal truth credit `ΔT` and self-credit `q`, the local break-even condition under this formula is `ΔT > 0.2 × DTI × (ΔT + 1 - q)`; if `ΔT ≈ q = k`, this reduces to `k > 0.2 × DTI`. At the **USER-REPORTED** H33 value, that conditional threshold is about `0.0556` kernel credit. This algebra is a *mechanism hypothesis*, not a measurement of any H33 pixel's credit: the hidden truth needed to compute `ΔT` and `q` is unavailable.

Potential non-fault mimics for any lineament-based H33-like method include Pleistocene shoreline benches, alluvial-fan terrace risers, lithologic contacts, volcanic flow margins, and geophysical survey seams. The repository does not establish which of these H33's original method used or how often they occur in its hidden-test detections.

## Candidate directions: status, not promises

The ranked, evidence-qualified shortlist is maintained in [`session-20261025-review.md`](session-20261025-review.md). It separates methods that are unimplemented but previously proposed from genuinely untested code, assigns only qualitative potential/cost, and records external-source/access blockers. None was implemented in this review; no numeric DTI lift is projected.

## Current GEMSDOE88 decision

The existing H88-DHTC TIFF is locally format/grid-valid for **research download only**: single-band float32, finite values in `[0,1]`, aligned EPSG:32611 grid, matching shape/transform, and no mass outside the footprint. Its recorded **HOLDOUT-DTI** remains `0.1413781360 [0.1276877737, 0.1561120556]` (`gems57-pooled-hide-v2`, `22,893` withheld positives). However, its freshly rechecked forward 3-pixel overlap with `data/registry/dense_17gemdoe.tif` is `1.0`, above the binding `0.70` ceiling. The registry witness is positive throughout every allowed cell. **Do not submit it; do not generate another non-empty candidate under this rule.**

No raster, model experiment, weekly slot, or organizer submission was created or used in the 2026-10-25 review. `DOWNLOAD FOR RESEARCH: YES` describes existing, hash-verified research files only; it is not a submission authorization or organizer-acceptance claim.

## Official sources and verification boundary

Links retained for manual primary-source verification:

- [DrivenData problem, metric, and data page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) and [submission receipts](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [USGS Landsat Collection 2 surface temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)
- [NASA Alaska Satellite Facility DAAC](https://asf.alaska.edu/)
- [AWS Open Data Sentinel-2 L2A COG registry](https://registry.opendata.aws/sentinel-2-l2a-cogs/)

These pages were **not fetched in this session**: the sandbox's permitted outbound hosts do not include DrivenData, USGS, NASA ASF, or the AWS Open Data Registry. The competition feature stack is absent from this checkout, and the validation restore fetched only hash-pinned owner-mirror validation inputs. Source availability, exact-area coverage, current competition rules, redistribution permission, and current standings remain unverified. Owner mirrors are not organizer authentication.
