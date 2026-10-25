# GEMSDOE88 independent repository review — Arena branch `f8d5d693` (2026-10-25)

## Executive decision

**Current review: negative / `DUPLICATE_STOP`. No new TIFF was generated. Do not submit any file from this repository.** This is a deliberate fail-closed result, not evidence that a new unique candidate is ready. A historical H88-MTAS TIFF is already in the repository and downloadable for research, but its own saved-byte audit confirms literal 3-pixel overlap of `1.0` with the full-support 17GEMSDOE raster; it is **not unique under the requested rule** and is marked `DO-NOT-SUBMIT`.

This turn independently restored only the hash-pinned validation tier, re-ran the MTAS pre-placement guard, re-opened the historical MTAS TIFF/ZIP, and ran the automated suite and Pages/download checks. It did not restore the training feature stack, run an experiment, create a raster, select a weekly slot, contact DrivenData, or obtain an organizer receipt.

## Why H33 is reported as the strongest GEMSDOE-site result

The prompt's `0.2778` is a **USER-REPORTED claim**, not an organizer receipt in this repository. The result must not be called an organizer-confirmed score. The on-disk H33 lineage analysis supports a plausible *mechanical* explanation, not a causal demonstration:

- The measured mirrored rasters form a strict nested thinning chain: H19-5 → D2.8 → SOLO-D2.8 → H33 had 121,131 → 44,090 → 40,199 → 37,654 positive pixels. The D2.8-to-H33 removal set contains 6,436 pixels, all within 2 grid cells of the known-fault mask. H33's minimum nearest-neighbour spacing is 2.828 pixels; median distance to mapped catalogue is 19.647 pixels. These are **REGISTRY-MEASUREMENTS**, not hidden-truth scores.
- The local metric implementation is a weighted, distance-tolerant Tversky score. Under the commonly described form, its false-positive term is weighted 0.2 and false-negative term 0.8, with a 300 m triangular kernel. With a saturating nearest-prediction credit, deleting redundant predictions can reduce the false-positive burden while preserving much of the covered truth. Removing predictions close to already mapped faults can also reduce wasted budget if the scored target excludes those known faults.
- The measured lineage and user-reported score progression are *consistent with* those effects. They do not establish that any removed dot lacked hidden-fault credit, that the thinning caused the score changes, or that the reported `0.2778` is authentic. The sequence is not an independent controlled experiment: it reuses ancestry and may incorporate live-feedback tuning.
- The prompt also quotes `0.3195` and `0.4413`. They are conflicting snapshots. Repository snapshots dated 2026-10-24/25 record a public leaderboard first-place entry at `0.4413`; this review did not fetch the current DrivenData page, so it is not a current leaderboard assertion. None of these values is a score for a GEMSDOE88 file.

**Can this project claim it can beat H33? No.** It can test hypotheses on catalogued-fault holdout, but that proxy is not the organizer's hidden off-catalogue labels. No local holdout result can be represented as a leaderboard projection or organizer-confirmed score. The historical MTAS test, discussed below, was decisively negative on its own holdout.

## Ranked geological hypotheses already preregistered

The repository's frozen lane file contains five untried proposals with feature layers, physical signature, missing-catalogue rationale, non-fault mimics, repo-method distinctions, and qualitative gain/cost ranking: [`research/candidate-hypotheses-20261025-mtas.md`](candidate-hypotheses-20261025-mtas.md). Those ranks are qualitative, not predicted DTI values. No new experiment was started in this review because the shared pre-placement proof blocks all nonempty outputs before any feature construction.

| Rank | Method / layers | Target mechanism and why a mapped catalogue may miss it | Named non-fault mimic | Difference from existing lanes | Cost |
|---:|---|---|---|---|---|
| 1 | **MTAS** — `rtp_grad_200m/800m`, `grav_grad_200m/800m`, `depth_to_base_log`, `det_elev_slope`, `geod_transtension` | Cross-scale magnetic/gravity edge-admittance residual; a buried density edge under low-relief cover may persist where the magnetic edge is smoothed or demagnetized, without a mapped scarp. | Unfaulted intrusive/volcanic lithologic contact; survey levelling seam. | Cross-field *difference of scale responses*, unlike PHASE angular discordance, MRR within-magnetic residualization, or GTHC continuation amplitude. | Low–medium |
| 2 | **PRAN** — `rad_k_over_th`, `det_elev_slope`, `topo10_curv_prof`, `depth_to_base_log` | Terrain-matched radiometric K:Th residual and along-strike coherence, potentially identifying covered alteration without a discrete scarp. | K-rich alluvium, parent-rock boundary, soil moisture. | Conditional terrain-bin null, rather than MVRD's direct radiometry/scarp evidence. | Low–medium |
| 3 | **FARC** — `chi_step_max`, `ksn_jump_norm`, `topo10_hs_lineament`, `lidar_scarp_coh` | Replicated signed drainage deflections across catchments, relative to a channel-matched erosion null, for a subtle blind rupture. | Lithologic knickzone, inherited capture, regional base-level/climate change. | Replication against a matched null, unlike QTSK/TDKL absolute knickpoint/scarp ranking. | Medium |
| 4 | **TCONS** — `probe2m_dab_local`, `well_temp_anom`, `cond_edge_300m`, `depth_to_base_log` | Depth-conditioned temperature/conductivity residual for focused fluid flow through a blind conduit. | Lake-brine conductivity or unfractured permeable lithology. | Conditional residual with head-matched null, rather than DHTC deep heat/MT conjunction. | Medium |
| 5 | **FLAC** — `rtp_grad_200m`, `grav_grad_200m`, `cond_edge_300m`, `geod_shearrate`, `geod_dilaterate` | Independent-sensor edge persistence after a preregistered flight-direction artifact veto. | Gridding/tie-line seams and broad lithologic contacts. | Adds an explicit survey-direction null not present in MGC/XGCE cross-field edge geometry. | Low |

No external data are needed for these proposed tests as written; they are defined on cached feature planes. The cached stack's owner-mirror provenance and redistribution rights are not equivalent to authenticated organizer downloads. If a later hypothesis needs new data, its free official source must be identified and access checked before it is called viable.

## Binding pre-placement result

The shared preflight ran against SHA-pinned validation inputs restored from owner GitHub mirrors. It rechecked the sample grid, catalogue, and 17GEMSDOE witness:

- `5,106,385` allowed footprint pixels and `5,106,385` directly covered allowed pixels; uncovered allowed pixels: `0` (**REGISTRY-MEASUREMENT**).
- The pinned witness SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`; its positive support includes every allowed location (**REGISTRY-MEASUREMENT**).
- Under the prompt's literal forward-overlap test, every nonempty candidate must therefore have 3-pixel overlap `1.0`, exceeding the `0.70` limit (**REGISTRY-MEASUREMENT**). This is a sufficient universal obstruction, not a complete pairwise audit of all registry rasters.
- `.venv/bin/python scripts/preflight_mtas88.py --gate-generation` returned exit `2`, the documented expected `DUPLICATE_STOP`. No feature generation, canary, holdout, placement, or writer was invoked in this review.

A mathematically empty prediction would avoid “nonempty” support but would not be a scientifically useful fault-discovery product and would not resolve the stated uniqueness requirement. Renaming, re-encoding, or changing the method cannot alter the overlap lower bound. Exempting the dense prior or changing the comparison universe would be a policy change, not something to invent in code.

## Existing MTAS artifact and repository irregularity

A historical file is present at [`docs/downloads/gems88-mtas88-admittance-37654dots-20261025-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/gems88-mtas88-admittance-37654dots-20261025-zeros-DO-NOT-SUBMIT.tif), alongside a one-member ZIP. It is not a file created by this review. The saved-byte validator reproduced:

- TIFF SHA-256 `2cb828939e11cf07e12be7917722f73816550ed4e297e2409b8674ac131479cc`; 37,654 positive pixels; one float32 band; exact sample grid; all values finite and in `[0,1]`; no positive pixels outside footprint or on the known catalogue. This is a **LOCAL-FORMAT-AUDIT** only.
- The historical run card labels the experiment **HOLDOUT-DTI** (`gems57-pooled-hide-v2`), 22,893 withheld positives, `0.049577`, 95% CI `[0.044659, 0.054417]`. This is a historical artifact result, not a new score from this review and not an organizer score.
- Recomputed final-dot overlap with the dense witness is `1.0` (**REGISTRY-MEASUREMENT**); the historical run card's like-for-like scan reported a maximum of `0.423249` across its stated dot-field registry scope. The latter cannot clear the literal all-raster rule.
- The validator exited `0` for **research-file format/identity**, but its card says `ok_to_submit=false`; the `--require-submit` mode is designed to exit `2`. Passing format validation does not authorize submission.

**Irregularity flagged:** the historical execution document says a new MTAS artifact was generated and reports holdout/feature results, whereas the later pre-placement review/run card says no candidate was fit or emitted because the universal blocker fired. The Pages/archive text acknowledges that the TIFF was generated despite the pre-placement stop in another session. Thus there are two distinct records: an earlier run that produced a fail-closed research artifact, and this review's compliant pre-placement stop. Do not collapse them into one timeline, and do not treat the archived TIFF as a newly generated or protocol-unique submission. The current shared guard prevents repeating the generation path; the archive remains explicitly marked `DO-NOT-SUBMIT`.

## Three-pass verification performed

1. **Requirements and evidence review:** read `AGENTS.md`, `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md`, existing MTAS preregistration/reviews, H33 lineage note, and the machine preflight evidence. Confirmed the missing “single method paragraph” ambiguity and used the already preregistered MTAS proposal only as context, not permission to run it.
2. **Adversarial implementation review:** installed the repository requirements in an ignored `.venv`, restored the validation-only input tier, ran the generation preflight (expected exit `2`), re-opened the historical MTAS TIFF/ZIP with its validator (exit `0` for research format, `ok_to_submit=false`), checked literal audit, and checked the historical execution/run-card discrepancy. No candidate writer was run.
3. **Full repository and release recheck:** `pytest -q` → **654 passed, 23 skipped**; `scripts/audit_downloads.py --check` audited **43** TIFF/ZIP research pairs, **0** protocol eligible; `scripts/render_decision.py --check` passed; `scripts/check_site.py` and `python -O scripts/check_site.py` passed. These validate code/site consistency and local artifacts, not hidden-label performance or organizer acceptance.

## Sources and access limits

- [Official competition problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official manual-review link; not fetched during this review.
- [Official competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — requires competition authentication; no logged-in download was made here.
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — official manual-review link; not fetched during this review.
- [DrivenData reference solution on GitHub](https://github.com/drivendataorg/gems-prize-reference-solution) — official code repository; the run used the repository's existing shared evaluator/writer and did not modify them.
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) and [DOE GDR INGENIOUS](https://gdr.openei.org/submissions/1391) — official context references; no new external raster was retrieved.
- [Pinned 17GEMSDOE witness file](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) — owner-repository evidence used for the local uniqueness bound; not competition ground truth.

**What remains blocked:** a nonempty unique submission cannot satisfy the current literal rule while this witness remains in the registry. No direct DrivenData auth/receipt, current quota or live leaderboard was verified. To continue scientifically, a documented shared-protocol clarification must first define an applicable representation-aware comparison, without silently waiving a registry entry; only then can a candidate be re-preregistered, tested on shared buffered holdout with feature-alone leakage canaries, and passed through pre-placement and final uniqueness gates. Slot selection stays separate. No weekly slot was used and no score is ORGANIZER-CONFIRMED.
