# Autonomous repository review — 2026-10-25

## Decision first

**New unique competition TIFF: not generated. Downloadable research TIFF: yes. Competition submission: no — DO NOT SUBMIT. Weekly slots used: 0.**

This is deliberate, not a missing implementation. The binding protocol says to stop when any registry raster gives more than 70% forward overlap within 3 pixels. The SHA-256-pinned `17GEMSDOE` witness is positive on **all 5,106,385 allowed cells**. Consequently every nonempty candidate emitted inside the allowed domain has forward overlap `1.0 > 0.70`. A new TIFF, a renamed TIFF, or a formatting-only copy would not be a unique submission. The proof is recorded in the machine review card [`data/repo_review_20261025.json`](../data/repo_review_20261025.json) (the canonical repository copy is `evidence/repo_review_20261025.json`).

The archived H88-TDKL file remains available for **research-only download** and independently passes the local finite `[0,1]`/grid/ZIP audit. Its link is intentionally marked `DO-NOT-SUBMIT`; local format validity is not organizer acceptance.

## What was verified

1. **Competition target and format.** The official problem page says the target is geological faults indicative of geothermal resources, not direct vent presence. It specifies the UTM zone 11N / EPSG:32611, 100 m feature grid, single-band float32 GeoTIFF, values in `[0,1]`, and the 300 m triangular distance weighting. Source: [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
2. **Metric discipline.** A local hide-and-recover number is only `HOLDOUT-DTI` when it includes the shared evaluator, withheld-positive count and 95% CI. No MTAS feature was fitted, so this review records no MTAS DTI and no confidence interval. No projection is promoted to a score.
3. **Official rules.** The fetched [NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), §§3.2–3.5, states that competitors submit one 100 m GeoTIFF, may submit up to the website limit, and must select only one submission for evaluation across both prize rounds. It also requires disclosure of generative-AI use. The repository has not attempted an upload or login.
4. **Input identity.** `sample_submission.tif`, `existing_faults.tif`, and the witness are checked by SHA-256 and by CRS, shape and transform. The input files are restored from pinned public owner mirrors; they are not claimed to be an authenticated current organizer download.
5. **Research download identity.** The archived TIFF is reopened with rasterio; all cells are finite and in `[0,1]`, it is one band, its grid matches the sample, it has no positive mass outside the footprint, and its ZIP contains exactly the identical TIFF. This is `LOCAL-FORMAT-AUDIT`, not `ORGANIZER-CONFIRMED`.

Run without manual selection:

```sh
python scripts/restore_inputs.py --validation
.venv/bin/python scripts/review_repo_20261025.py
.venv/bin/python scripts/review_repo_20261025.py --require-submit  # expected exit 2
```

The command writes the two identical JSON reports and never trains, places dots, creates a TIFF, calls the portal, or spends a weekly slot.

## Ranked candidates before the stop

The queue contains five specific, currently **UNTESTED** hypotheses. The ranking is qualitative gain-versus-cost planning, not a DTI prediction:

| Rank | Lane | Layers | Signature and missing-fault rationale | Named non-fault mimic | Cost |
|---:|---|---|---|---|---|
| 1 | H88-MTAS | `rtp_grad_200m`, `rtp_grad_800m`, `grav_grad_200m`, `grav_grad_800m`, `depth_to_base_log`, `det_elev_slope`, `geod_transtension` | Cross-scale gravity-to-magnetic admittance residual; a covered basement break can retain a density edge while losing a surface scarp or magnetic response | Intrusive/volcanic lithologic contact; flight-line leveling seam | low-medium |
| 2 | H88-PRAN | `rad_k_over_th`, `det_elev_slope`, `topo10_curv_prof`, `depth_to_base_log` | Terrain-matched K:Th residual and along-strike coherence; seeks alteration over a covered structure rather than a global radiometric high | K-rich alluvium, parent-rock boundary, soil moisture | low-medium |
| 3 | H88-FARC | `chi_step_max`, `ksn_jump_norm`, `topo10_hs_lineament`, `lidar_scarp_coh`, `det_elev_slope` | Repeated signed cross-channel offsets normalized within catchment/channel-order strata | Lithologic knickzone, drainage capture, base-level/climate change | medium |
| 4 | H88-TCONS | `probe2m_dab_local`, `well_temp_anom`, `cond_edge_300m`, `depth_to_base_log` | Depth-conditioned temperature/conductivity residual for a blind fluid pathway | Lake-brine conductivity, groundwater circulation, permeable lithology | medium |
| 5 | H88-FLAC | `rtp_grad_200m`, `grav_grad_200m`, `cond_edge_300m`, `geod_shearrate`, `geod_dilaterate` | Cross-sensor edge persistence after a preregistered survey-line-direction artifact veto | Gridding/tie-line artifact and broad lithologic contact | low |

All five use cached layers and require no new external data. If the protocol contradiction is resolved in a documented way, H88-MTAS remains the top candidate; only then should the shared buffered holdout, per-feature leakage canary and pre/post-placement uniqueness checks run. The current stop happens before that work and therefore no MTAS holdout result is claimed.

## Why H33’s reported 0.2778 was comparatively high

The `0.2778` value is a **USER-REPORTED CLAIM — not HOLDOUT-DTI and not ORGANIZER-CONFIRMED**; there is no portal receipt in this repository. The on-disk lineage analysis nevertheless verifies a narrow geometric explanation:

- `H19-5` → `D2.8` → `SOLO-D2.8` → `H33` are strictly nested supports in the restored rasters.
- H33 contains 37,654 dots, has a measured median distance of about 19.65 pixels from the mapped catalogue, and has a minimum nearest-neighbour spacing of 2.828 pixels.
- Exactly 6,436 D2.8 dots removed by H33 were within 2 pixels of the mapped catalogue.
- Under the published distance-weighted Tversky structure, removing redundant near-catalogue dots can reduce false-positive mass without necessarily losing much hidden-fault coverage; three-pixel de-redundancy also reduces clustered-dot self-competition.

This is a mechanism consistent with the measured lineage, not a causal proof of the hidden labels. A local holdout is a catalogue-recovery proxy and cannot show that H33 would beat the private organizer labels or the public leaderboard.

## Limitations and irregularities

- The prompt contains inconsistent score references (`0.2778`, `0.3195`, and `0.4413`). The fetched public leaderboard displayed `0.4413` for xiaofanhu on 2026-10-25; that is `OBSERVED-PUBLIC` and not a GEMSDOE88 score. The `0.2778` value remains a user claim.
- The dense witness makes the literal uniqueness requirement mathematically unsatisfiable for any nonempty candidate. No dense-prior exemption has been inferred.
- The local mirrors are hash-pinned but not organizer-authenticated in this sandbox. DrivenData authentication and a real submission receipt are unavailable.
- The NLR rules require generative-AI disclosure for an actual prize submission; this project must preserve that disclosure if a future selector clears a candidate.
- Negative results are deliverables. The correct next action is to resolve the protocol/data-scope contradiction, not to relabel an old artifact or hide the witness.

## Official manual-review links

- [DrivenData problem, datasets, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GDR INGENIOUS compilation](https://gdr.openei.org/submissions/1391)
- [EPSG:32611](https://epsg.io/32611)
