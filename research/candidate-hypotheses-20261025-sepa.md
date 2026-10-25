# Ranked candidate geological hypotheses — 2026-10-25 — lane H88-SEPA (frozen before computation)

**Session lane (one method paragraph).** Blind, currently-loading geothermal feeder faults that lack a
Quaternary surface scarp should still (i) align microseismicity into anisotropic linear fabrics,
(ii) localise geodetic strain with a characteristic shear-vs-dilatation partition, and (iii) offset
magnetic/gravity basement so their potential-field edge *persists* under upward continuation and
coarse-scale smoothing while shallow volcanic/lithologic edges decay. **H88-SEPA** therefore adds
18 zero-catalogue channels — seismic structure-tensor anisotropy and Hessian ridges/troughs of the
organizer azimuth-sector earthquake fields (`ieq_n100a15` B16, `deq_n100a15` B10), strain-partition
ratios and strain-tensor anisotropy of the geodetic fields (`geod_2ndinv` B4, `geod_shearrate` B7,
`geod_dilaterate` B8), spin-2 orientation agreements between the seismic, strain and
upward-continued magnetic fabrics, and deep/shallow potential-field persistence ratios
(`TMI_up150` vs `tmi` B14; `iso_grav_anom` B13 σ6/σ2) — to the shared 44-channel physics stack and
the 23 fold-visible structural channels, fused by the shared dual-expectation log-odds
Product-of-Experts and emitted as H33-parity kernel-spaced dots (37,654; collar `d_cat > 2.5 px`;
near 21,500 @ ≥2.85 px + far 16,154 @ ≥3.05 px). Named non-fault mimic: **volcanic seismic swarms and
magmatic centres** (isotropic/blob-like seismicity with shallow magnetic edges) and **regional
(Walker-Lane-scale) strain gradients** with no local structure; an explicit seismic-blobness mimic
channel and the persistence ratio are included so the learner can penalise both.

## Why this is not any previous lane in this repo (verified by grep, 2026-10-25)

* `physics.py` collapses B10/B16 to one scalar (`seismic_prox = -log deq - 0.5 log ieq`) and
  B7×B8 to one scalar (`geod_transtension`); no lane (`adhr, hgvc, tdkl, vess, mvrd, gthc, dhtc,
  qts88, qtsk, mrr, sar_csd, phase88, kth_step, fabric_dislocation, ugfv`) computes a seismic
  structure tensor, seismic Hessian ridge/trough, strain-partition fractions, or an
  upward-continuation persistence *ratio*. `ugfv.py` uses a scalar `log deq - log ieq` swarm index
  only. `tdkl.py`/`gthc.py` use a Laplacian/admittance of `TMI_up150` itself, never its
  deep-vs-shallow gradient persistence against B14, and never its spin-2 agreement with seismicity.
* Emission, evaluator, writer and visible-structure machinery are the shared template's
  (`vendor/gems57`, `src/gems88/adhr.py`, `tdkl.py` fold machinery) — reuse, not a private fork.

## Five ranked hypotheses (expected DTI gain vs cost; gains are hypotheses, not results)

| Rank | Hypothesis | Layers | Physical signature / transform | Why it catches faults missing from USGS/INGENIOUS | Named mimic | Difference from repo | Expected gain / cost |
|---|---|---|---|---|---|---|---|
| 1 (SELECTED) | **SEPA** — seismic-strain partitioning + potential-field persistence anisotropy | B16 `ieq_n100a15`, B10 `deq_n100a15`, B4/B7/B8 geodetic strain, B14 `tmi`, B13 `iso_grav_anom`, GeoDAWN ext B4 `TMI_up150` | Structure-tensor anisotropy `(λ1-λ2)/(λ1+λ2)` + Frangi ridges of seismic fields; shear/dilatation partition fractions; `|∇up150|/|∇TMI|` and `|∇₆grav|/|∇₂grav|` persistence; spin-2 fabric agreements | Catalogue requires surface evidence; a seismogenic, strain-loading blind fault under basin fill has no scarp but aligns epicentres, partitions strain and roots into magnetic basement | Volcanic swarms (isotropic blobs, shallow edges); regional strain gradients | Above | Hypothesised +0.005…+0.015 HOLDOUT-DTI over ADHR; low cost (all inputs already SHA-pinned locally, no external download) |
| 2 | **RAD-CLR** — compositional (centred-log-ratio) radiometric alteration residual | GeoDAWN rad K/Th/U/TC + ext ThK/UK/UTh | clr ternary coordinates minus 10 km local lithologic mean; Efimov F-parameter; U-migration index | Hydrothermal K-leaching/U-mobilisation along covered conduits changes *relative* radioelement composition where no fault is mapped | Felsic intrusives (all radioelements high together); playa U enrichment | Prior lanes used only scalar K/Th-type ratios (`rad_k_over_th`, redox grads in hgvc/dhtc); no compositional clr residual | Unknown, maybe +0.002…+0.008; low cost. **Not run — 3-experiment budget reserved for Rank 1 arms** |
| 3 | **LAPDIP** — signed LiDAR Laplacian footwall/hangingwall couplet | lidar B4 `lapneg_max`, B5 `lappos_max`, B11 `strike`, B10 `coh100` | Across-strike paired dipole: lapneg crest on one side, lappos trough 1–3 px on the other, along B11 strike | Degraded scarps keep a curvature couplet after the height step diffuses below mapping thresholds | Terrace risers / shoreline benches (couplet follows contour, not strike) | `physics.py` uses `sqrt(lapneg*lappos)` *magnitude* inside `lidar_scarp_dipole`; nobody used the signed across-strike pairing | Maybe +0.002…+0.006 in LiDAR-covered piedmont only (coverage-limited); medium cost. Not run |
| 4 | **FACET** — triangular-facet / wineglass-canyon facet coherence | topo10 B7 aspect_coherence, B3 steep_frac, B4 slope_std, B5 relief_local; dem10_chi raised | Joint high aspect-coherence + bimodal slope + raised-χ at range fronts | Faceted spurs persist along active range-front faults whose free face is buried at the toe | Hogback dip slopes (coherent aspect, no basement step) | `qtsk.py` already used a planar-facet channel — partial lane-collision risk, hence rank 4 | Small; low-medium cost. Not run |
| 5 | **WORM-MIG** — upward-continuation worm lateral migration inversion | B2 rtp, B14 tmi, ext TMI_up150, B13 grav | Track edge-argmax migration vector across continuation heights; invert for dip/depth | Deep basement faults' edges migrate systematically; shallow sources collapse | Dipping unfaulted contacts migrate identically | Fleet lane GEMSDOE42 (`xscale-worm-persistence`, USER-REPORTED 0.0581) already occupies worm-persistence territory — duplicate-lane risk, hence rank 5 | Unknown; medium-high cost. Not run |

## External-data viability

Rank 1 needs **no new external data**: every input is in the SHA-pinned competition stack
(`data/training_features.tif`, 19 bands, tags verified at build) or the already-restored
official-source mirror `data/external/geodawn_extensions_u8.tif` (USGS GeoDAWN,
https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).
Ranks 2–4 likewise use only restored local files. No hypothesis above depends on a source that
could not be checked obtainable first.

## Frozen validation (see `registry/preregistration_sepa88.json`)

Shared evaluator `gems57-pooled-hide-v2` (α=0.2, β=0.8, 300 m triangular kernel), buffered
whole-component hide-and-recover, seeds 20+21, 8 folds, catalogue features from visible faults
only, visible faults masked pixel-exactly. Three experiments maximum:
Exp1 zero-catalogue (44+18 ch PoE), Exp2 single joint (44+18+23 ch), Exp3 dual-head PoE (candidate).
Controls in the same folds: phys44 zero-cat and H88-ADHR incumbent. Every feature alone must pass
the symmetric-AUC ≤ 0.90 leakage canary before any holdout number is trusted.
Promotion bar (pre-registered): Exp3 HOLDOUT-DTI point estimate **above the repo's current holdout
best, H88-HGVC 0.202947** (`gems57-pooled-hide-v2`, n=22,893), paired Δ vs ADHR 95% CI > 0,
fingerprint `share_le2 = 0`, `share_gt25 ≥ 0.35`, and the v4 uniqueness decision in IR-88-118
(rank-correlation vs *every* registry raster; dot-overlap vs dot-field rasters; chance-corrected
excess vs discriminating dense rasters; the literal space-filling reading reported, never hidden).
0 weekly slots are spent by this session regardless of outcome; slot selection is a separate step.

## H33 (0.2778) — what the bytes in this repo actually establish

Recomputed in prior sessions from SHA-pinned mirrors (`evidence/h33_forensics_20261024.json`):
H19-5 (121,131 dots) → D2.8 (44,090) → SOLO-D2.8 (40,199) → H33 (37,654), each an exact subset of
the previous; the last step removed 2,545 dots, all within 2 px of the known-fault raster, and
added no new geography. Under DTI = T / [0.8K + 0.2(T + n − M)] (300 m kernel), deleting
kernel-redundant and catalogue-adjacent dots shrinks the false-positive term `n − M` while losing
little truth coverage `T` — a precision/geometry effect, not new geology. That is *consistent*
with the USER-REPORTED 0.2778 ordering, not causal proof (0.2778 has no organizer receipt in this
repo; GEMSDOE32's own build file calls 0.2747 a projection). SEPA therefore copies only H33's
*emission geometry* (count, collar, spacing, far-share) and must earn any improvement from new
geology on the holdout. Whether any candidate beats 0.2778 — let alone the prompt's conflicting
0.3195 / 0.4413 leaderboard snapshots — is **unknown** until an organizer receipt exists; no
holdout number in this repo is a leaderboard projection.
