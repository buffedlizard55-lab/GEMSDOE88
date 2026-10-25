# Session f55aff34 — three-pass repository review and CON88 clearance withdrawal

**Date:** 2026-10-25 UTC
**Branch:** `arena/f55aff34-gemsdoe88`
**Lane:** software/evidence review only; no geological method paragraph was supplied in the request.
**Decision:** **DOWNLOAD H88-CON88 FOR RESEARCH: YES. SUBMIT: NO — DO NOT SUBMIT.**
**Weekly slots used:** 0. **New experiments:** 0. **New TIFFs generated in this review:** 0.

## Executive finding

The repository started this review with two contradictory public decisions:

1. the README, root landing page and `docs/con88.html` said H88-CON88 was ready to submit; and
2. the canonical Pages overview, `docs/status.json`, `docs/data/current_release.json`, `AGENTS.md` and the shared generation guard said `DUPLICATE_STOP`, `ok_to_submit: false`.

The green CON88 decision was unsafe. IR-88-F55AFF34-01 withdraws it and keeps the original TIFF bytes only as a reproducible research artifact under a `-DO-NOT-SUBMIT` filename. The project now has one unambiguous decision: **no file is cleared for submission**.

## Why H33 may have been competitive — evidence, not a causal claim

The pinned H33 owner build record was freshly retrieved from GitHub at commit [`012e17b…`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json). It says:

- REGISTRY-MEASUREMENT: H33 contains 37,654 positive pixels.
- OWNER-BUILD-RECORD: it starts from a 40,199-pixel predecessor and deletes every dot within two 100 m pixels of the published catalogue; the local lineage audit confirms the subset relation.
- OWNER-BUILD-RECORD: its `0.2747` value is explicitly a **projection / MODEL, not a score**, and the record says no organizer score exists in that repository.
- USER-REPORTED: `0.2778` was supplied in the request. There is no submission-page receipt in this checkout, so it is not ORGANIZER-CONFIRMED.

Under the shared DTI implementation, a dot with no hidden-truth credit contributes false-positive mass weighted by alpha `0.2`; removing such a dot lowers the denominator without lowering the numerator. This makes the near-catalogue subtraction a plausible precision improvement, because visible catalogue pixels are masked and near-trace emissions can be redundant. The measured approximately 2.83–3-pixel nearest-neighbour spacing is also consistent with avoiding duplicate coverage inside the 300 m triangular kernel. These facts explain *why the design is plausible*; they do not prove what caused a hidden-label leaderboard change.

Can `0.2778` be beaten? **Yes in principle, but not demonstrated here.** The current H88-CON88 evidence fails the explicit holdout-superiority gate, and no organizer receipt exists. Claiming a score above `0.2778` would therefore be unsupported.

## Four independent CON88 blockers

1. **Literal uniqueness fails.** REGISTRY-MEASUREMENT: the SHA-pinned `17GEMSDOE` raster has positive support covering every one of 5,106,385 allowed pixels. Every nonempty candidate therefore has literal 3-pixel forward overlap `1.0`, above the `0.70` stop limit.
2. **The required pre-placement surface test is absent.** The old validator measured Spearman correlation on the final binary dot raster, not the continuous blend before placement. Missing evidence fails closed.
3. **The inventory was incomplete.** The original CON88 validator scanned 77 distinct on-disk rasters. Later lanes used substantially larger restored sibling/fleet inventories. “All on-disk” was not evidence of all registry rasters listed by the request.
4. **Scientific promotion fails.** The archived CON88 re-emission diagnostic is `0.001714 [0.001325, 0.002143]` (`gems57-pooled-hide-v2`, 60,988 withheld positives), below the repository best `0.205991`. More fundamentally, its full-catalogue collar is not the required visible-only hide-and-recover construction, so the integrated review marks it invalid for promotion. H88-SPR never reached holdout because the shared pre-placement guard stopped first.

The equal-support diagnostic is still informative: REGISTRY-MEASUREMENT overlap vs H33 is `0.487`, and the worst equal-support overlap recorded by the old scan is `0.694` vs GEMSDOE49. It cannot replace the binding literal test or missing pre-placement test.

## Saved artifact and automated validator

- Research TIFF: [`gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif`](../downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif)
- TIFF SHA-256: `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68` (unchanged by rename)
- Research ZIP: [`gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.zip`](../downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.zip)
- ZIP SHA-256 after integration: `73ee608ad9401e70bbaeb1b28104118086b554569ae5891146de6430f39bf9cb`
- LOCAL-VALIDATOR: one float32 band; EPSG:32611; shape 3730×3292; exact sample transform; `nodata=None`; no NaN/Inf; minimum `0.0`; maximum `1.0`; 37,654 positive pixels; zero outside footprint and on the catalogue; ZIP contains exactly the byte-identical, negatively named TIFF.
- Competition submission name: none.
- Research note (112/140): `H88-CON88 archived negative: literal overlap, surface audit, and holdout-superiority gates failed; DO NOT SUBMIT`

The finite zero-outside encoding addresses the previously reported “Predicted values must be in range [0, 1]” failure for these exact bytes. That is a local format result, not organizer acceptance.

## Ranked untried geological hypotheses (reviewed before any implementation)

The source-bound queue contains three unimplemented candidates. All use already restored/pinned inputs; none needs a new external download. Priority is qualitative, not a predicted score.

| Rank | Hypothesis; exact layers | Physical signature | Why it may find missing faults | Named non-fault mimic | Difference from implemented work | Cost |
|---|---|---|---|---|---|---|
| 1 | **H88-SPR, repeated scarp-profile restoration.** `training_features.tif` bands 12/19 (`det_elev`, slope); `topo_10m_derived_100m_u8.tif` bands 8/9; `lidar_scarp_features_u8.tif` bands 3/10/11/12; `dem10_chi_100m_u8.tif` bands 1/4. | Fit smooth-landform-plus-signed-step versus no-step profiles on independent along-strike swaths; require a repeated step away from channel corridors. | Weak or cover-softened offsets can preserve repeated profile displacement without a mapped trace. | Fluvial terrace risers and constant-elevation pluvial shoreline benches. | Existing LSC/TDKL/VESS/SHORE lanes use response, polarity, knickpoint or shoreline context; none fits a cross-validated landform-restoration likelihood. | Medium; highest expected relative potential. |
| 2 | **H88-AWA, terrain-matched alteration-width asymmetry.** `geodawn_rad_u8.tif` bands 1–3; `training_features.tif` bands 2/15/19. | Compare fitted cross-strike K/Th/U code-value decay widths on two flanks, conditioned on terrain and a local RTP depression. | A covered permeable structure may alter one wall more broadly despite no discrete scarp. | Differential weathering across rock units and K-rich transported alluvium. | KTH/MVRD use enrichment/redox levels or edges, not relative fitted decay-width asymmetry. | Medium; second priority. |
| 3 | **H88-CBC, conductive basin-breach connectivity.** `training_features.tif` bands 12/13/15/17 and `dem10_chi_100m_u8.tif` bands 1/4. | Test narrow conductivity connectivity across independently inferred basin-boundary saddles, requiring a boundary-normal gravity discontinuity and rejecting drainage-aligned alternatives. | A buried cross-basin pathway may have no surface trace. | Unfaulted permeable paleochannels and saline groundwater plumes. | CTRA/DHTC use conductivity curvature or thermal conjunctions; this proposal tests topology-preserving cross-boundary connectivity against a drainage null. | Medium-high; third priority. |

The shared pre-placement guard stopped before H88-SPR feature construction, canaries, holdout fitting or writing. This is the required negative outcome under the current protocol, not permission to skip validation.

## Sources and retrieval status

| Source | Status in this review | Claim supported |
|---|---|---|
| [Official DrivenData reference solution, commit `aebe92f…`](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | Freshly retrieved with GitHub API; README blob SHA `a8814f99…`; commit date `2026-06-16` | Organizer code exists; its README requires separately downloaded competition data and documents CPU/GPU environments. |
| [H33 owner build record, commit `012e17b…`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) | Freshly retrieved with GitHub API; owner record, not organizer receipt | H33 file identity, dot count, subtraction rule, and explicit “MODEL, not a score” disclaimer. |
| [DrivenData competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Not retrievable from this sandbox’s allowed network hosts; not freshly verified | Manual-review links only. No current rank, quota or receipt claim is made from them. |
| [NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Not retrievable from this sandbox’s allowed network hosts; not freshly verified | Manual-review link only. |
| [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) and [DOE GDR 1391](https://gdr.openei.org/submissions/1391) | Pinned owner-mirror inputs exist; official hosts were not freshly retrievable in this review | Source provenance is inherited, not newly authenticated. The three proposed hypotheses require no new data. |

## Three review passes

### Pass 1 — reproduce and identify

- Restored the SHA-pinned validation tier from owner mirrors.
- Reproduced shared `DUPLICATE_STOP` with exit 2 and direct saturated-witness proof.
- Independently reopened CON88 TIFF/ZIP and verified its local format.
- Found the public-decision contradiction and the four omitted gates above.

### Pass 2 — fix and regression-test

- Removed CON88’s lane-specific generation bypass; all candidate runners now reach the shared guard before feature/model imports.
- Replaced `validate_con88.py` with a read-only saved-byte audit that delegates to the shared literal preflight, never loads feature caches, and denies `--require-submit`.
- Removed the audit/site exceptions that could turn a lane-local boolean into submission approval; the integrated correction also guards the collar-holdout CLI before imports.
- Renamed the TIFF/ZIP/receipt with `DO-NOT-SUBMIT`, preserving TIFF bytes and rebuilding the ZIP with one negatively named member.
- Corrected README, root page, CON88 page, submission guide, run card, gate JSON and irregularity ledger.

### Pass 3 — final recheck

After integrating `origin/main` through `3635e108…` (including the stronger read-only CON88 validator and guard hardening), the full suite passed **905 tests** with **23 skipped** and **70 warnings**. All 48 Pages packages and 20 repo-side archives pass local package checks with 0 eligible; normal/optimized site guards, full input pins, four generation stops, validator denial, and an eight-case browser audit pass. Exact results are in `registry/session_f55aff34_run_card.json`. The binding outcome remains `negative`; no new TIFF and no weekly slot were produced. Remote GitHub Actions and actual DrivenData upload acceptance are separate evidence.

## Remaining work and limitations

1. The rule owner must explicitly define a non-vacuous shared dense-raster dot representation if the literal all-positive witness is not intended to bind. Until then, generation must stop; a private exception is not acceptable.
2. If the shared rule is legitimately revised, run H88-SPR first, with every feature’s canary, whole-component buffered folds, visible-only catalogue features, and a same-fold paired comparison against HOLDOUT-DTI `0.205991`.
3. Restore and verify the complete sibling/fleet registry before surface placement and again on final dots.
4. DrivenData authentication is required only for organizer data provenance, current quota and a submission receipt. Do not provide credentials in chat; connect through the competition site.
5. A score can be labeled ORGANIZER-CONFIRMED only after archiving the receipt for the exact submitted SHA-256.
