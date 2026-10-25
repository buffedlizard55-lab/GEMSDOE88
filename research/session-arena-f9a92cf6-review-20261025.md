# GEMSDOE88 repository review — 2026-10-25

**Decision: NEGATIVE — NO NEW TIFF — DO NOT SUBMIT ANY FILE FROM THIS REPOSITORY.** This review used no competition slot and did not build a prediction surface, place dots, run a holdout or create a TIFF. The shared generation preflight stopped first with `DUPLICATE_STOP`; the current formal record is [`registry/session_f9a92cf6_run_card.json`](../registry/session_f9a92cf6_run_card.json).

## Why H33 may have received the supplied 0.2778, and what can be established

The value **0.2778 is USER-REPORTED, not ORGANIZER-CONFIRMED**: this checkout contains no submission-page receipt. Likewise, the user supplied competing leaderboard values **0.4413** and **0.3195**; neither was live-verified in this review. No score claim for any file built here is made.

The repo's re-run lineage audit (`scripts/audit_h33_lineage.py`) re-opened SHA-pinned owner-mirror rasters and found that H33's support is nested inside SOLO-D2.8, D2.8 and H19-5. It removed 6,436 D2.8 pixels, all within 2 pixels of the mapped-fault catalogue; H33 has no positive pixels within 2 pixels of that catalogue. Its nearest-neighbour spacing minimum is 2.828 pixels, approximately one 300 m kernel radius on the 100 m grid, and its median catalogue distance is 19.647 pixels. These are **REGISTRY-MEASUREMENTS**, not scores or hidden-truth observations. Exact hashes and caveats are in [`docs/data/h33_lineage_recheck.json`](../docs/data/h33_lineage_recheck.json).

A plausible metric-based explanation is that (a) catalogue-masked or catalogue-adjacent predictions offer little useful test-set credit and can still incur false-positive cost, (b) the 300 m triangular kernel gives diminishing marginal benefit to nearby redundant dots, and (c) H33's thinning reduces near-catalogue emission while preserving a broad, spaced label-blind ridge set. In DTI, each truth pixel receives its maximum kernel credit, while false-positive cost accumulates across predictions; therefore thinning redundant/low-credit predictions can improve precision. This is a mechanism consistent with the raster geometry and metric algebra, **not proof that this caused the user-reported public score**. The inputs share ancestry and public labels are hidden, so attribution from successive reported scores is confounded.

The archived CON88 run card contains **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 60,988 withheld positives) for the fixed archived H33 raster: `0.006697 [0.005990, 0.007368]`. That is a historical hide-and-recover result, not a public leaderboard estimate and not rerun in this review. The historical H88-BPWD per-fold baseline is **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 22,893 withheld positives): `0.205991 [0.188105, 0.223344]`. The large disparity between these holdout values and the USER-REPORTED H33 value illustrates that this particular catalogue hide-and-recover setup does not reliably rank label-blind, off-catalogue raster strategies. Thus the repository cannot show, from its available holdout, that a new candidate would beat H33's claimed public value.

**Answer:** it is possible in principle to beat the supplied value; the evidence here does not demonstrate that it is likely or that a specific new candidate will do so. Do not use a submission slot to find out while the uniqueness prerequisite is unsatisfied.

## Preflight and generation result

1. Python packages were installed into the ignored local `.venv` from the repository's constrained requirements. No repository data or model weights were added to Git.
2. `scripts/restore_inputs.py --validation` restored the pinned sample grid, fault catalogue and validation-tier registry rasters. This is an owner-mirror restoration, **not** an authenticated DrivenData download.
3. `scripts/generation_guard.py` returned exit code `2`, `DUPLICATE_STOP`. Its measured witness is `data/registry/dense_17gemdoe.tif`, SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`. It has positive support at every allowed cell (`5,106,385 / 5,106,385`); therefore every nonempty prediction has literal support overlap `1.0`, greater than the protocol ceiling `0.70`.
4. This is a proof of a **pre-placement impossibility under the supplied rule**, not a candidate's measured rank correlation or final-dot overlap. There is no current candidate surface or dot set to measure; both are recorded null in the run card. No exception for saturated/dense priors was authorized.
5. `scripts/audit_session_start.py` cannot complete its historical parent-R0 verification from the validation-only restore because the full `data/training_features.tif` stack is absent. That verification is an audit error, not authorization. The main generation guard does independently reproduce the duplicate stop from the restored witness.
6. No holdout, single-feature canary, candidate builder, submission writer, candidate validator, or slot selector was run in this session. That respects the preflight stop and the experiment budget.

## Ranked, not-executed geological hypotheses

The repo's source-bound queue contains three untested proposals. Their novelty is **relative to this checkout's reviewed methods**, not a claim of worldwide novelty. They do not authorize experiments while the preflight stop binds. No numerical DTI projection is offered.

| Rank | Hypothesis and layers | Physical signature / off-catalogue rationale | Named non-fault mimic | Difference from implemented lanes | Relative potential / cost |
|---|---|---|---|---|---|
| 1 | **H88-SPR — repeated scarp-profile restoration**. `training_features` B12 `det_elev`, B19 `det_elev_slope`; cached terrain B8 `hs_lineament`, B9 `dem_mean`; LiDAR B3 `step_max`, B10 `coh100`, B11 `strike`, B12 `valid`; channel controls B1 `chan_n`, B4 `valid_n`. | Compare smooth-landform-plus-signed-step against no-step fits over independent along-strike swaths; validate restoration on held-out profile samples and exclude channel-aligned corridors. A subtle or cover-softened offset could be absent from the fault catalogue while retaining a repeatable profile signature. | Fluvial terrace risers and constant-elevation Lake Lahontan shoreline benches. | LSC/TDKL/VESS/SHORE use scarp response, polarity, knickpoint or shoreline context; SPR fits a cross-validated profile-restoration likelihood with explicit geomorphic null controls. | Highest relative priority; moderate but uncertain potential; medium implementation cost. Uses cached layers, but full stack restoration is still required. |
| 2 | **H88-AWA — terrain-matched alteration-width asymmetry**. GeoDAWN-derived radiometric K/Th/U indices plus `rtp`, `depth_to_base_surf`, and `det_elev_slope`. | Fit relative two-flank cross-strike residual decay widths after terrain matching; test whether one-sided alteration-like response aligns with a local RTP depression. A broad covered response may reveal a structure without a crisp scarp. | Parent-rock boundary, K-rich alluvium, differential weathering and soil-moisture effects. | KTH/MVRD assess radiometric levels/redox or edges; AWA evaluates fitted flank-width asymmetry. U8 values are quantized indices, not calibrated concentrations. | Second; low-to-moderate and uncertain; medium cost due to quantization, saturation and parent-material controls. |
| 3 | **H88-CBC — conductive basin-breach connectivity**. `det_elev`, `iso_grav_anom`, `depth_to_base_surf`, `cond_surf`, and channel-count/validity controls. | Compare topology-preserving conductivity connectivity across independently inferred basin saddles against smooth basin-fill and drainage-connected nulls; require a boundary-normal gravity change. A buried cross-basin structure may lack a surface trace. | Paleochannels and saline groundwater plumes. | CTRA/DHTC use conductivity curvature or thermal conjunctions; CBC tests boundary-crossing connectivity against drainage nulls. | Third; low uncertain potential; medium-high cost and limited by coarse conductivity resolution. |

No new external data is required for these *proposals*: their listed layers are described in the hash-pinned queue and cached owner mirrors. However, the full feature stack is not in this workspace, owner mirrors are not organizer-authenticated, and licenses/use-rights were not freshly checked here. Before a future experiment, restore and hash-check the shared cached stack and verify that source data can be used and shared with the organizers. If a necessary layer is missing, the official-source targets already recorded in the repo are USGS GeoDAWN/3DEP and DOE GDR submission 1391; this session did not fetch those non-allowlisted domains.

## Important repository correction: stale CON88 clearance withdrawn

A high-risk inconsistency was present in the checkout: README and `docs/con88.html` advertised CON88 as “OK TO DOWNLOAD AND SUBMIT,” `registry/con88_gates.json` had `ok_to_submit: true`, the download audit whitelisted those bytes, and tests/site checks treated an equal-support dense-prior comparison as a valid uniqueness clearance. This contradicted the literal prompt and the later binding correction in `AGENTS.md`/IR-88-B4DFA10C-08.

The equal-support top-N calculation is a useful **diagnostic**, but it cannot replace the user's literal support rule. I withdrew the false clearance end-to-end:

- Renamed the historical TIFF/ZIP with `DO-NOT-SUBMIT`; the TIFF bytes remain exactly unchanged (SHA-256 `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`). The ZIP member now matches its negative filename.
- Marked the old gate and run card negative/withdrawn; added mirrored machine-readable withdrawal evidence.
- Removed the `cleared_by_con88_gates` exception from the publication audit and validator; changed `validate_con88.py` so literal overlap, not top-N equal-support overlap, controls G2.
- Updated the legacy page, README, `PROMPT.md`, submission guide and generated Pages overview/executive summary. Added checks/tests so no currently published TIFF/ZIP can be cleared by a stale legacy gate.
- The local package audit now reports 48 of 48 published TIFF/ZIP pairs valid for **research download**, and 0 protocol-eligible packages. Format validity is separate from submission eligibility.

This is a **withdrawal of an erroneous historical policy decision**, not a new candidate experiment or a modification of the TIFF prediction values.

## Official-source boundary and manual review links

The links below are primary or competition reference points. They are included for audit/manual review, **but were not fetched in this review** because outbound access here is restricted to GitHub, codeload.github.com, api.github.com, npmjs.org, pypi.org and files.pythonhosted.org. In particular, no current leaderboard position, submission quota, deadline, portal receipt, or organizer data provenance is asserted.

- [DrivenData competition overview and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — competition description/metric reference.
- [DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — organizer data access requires account authentication according to existing repo records; not accessed here.
- [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — rules and submission requirements; not fetched here.
- [Official DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — code reference; not cloned/fetched in this review.
- [USGS GeoDAWN survey data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) and [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) — candidate official source families; not fetched here.
- [DOE GDR submission 1391 / INGENIOUS](https://gdr.openei.org/submissions/1391) — official data repository record; not fetched here.
- [EPSG:32611 definition](https://epsg.io/32611) — CRS reference; not fetched here.
- [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — live position is unknown from this review.

The local scoring implementation `vendor/gems57/metric.py` documents the distance-weighted Tversky formula: `TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w)` with a 300 m triangular kernel, and its tests compare the optimized implementation with a brute-force oracle. This documents the local code contract; it does not substitute for a freshly retrieved organizer statement.

## Three-pass verification

**Pass 1 — implementation:** identified the literal gate failure and stale CON88 authorization, archived CON88 under a negative filename, removed the equal-support promotion path, updated canonical documentation/metadata and recorded hypotheses/run card.

**Pass 2 — adversarial review:** checked every remaining `con88` path, the generated landing pages, ZIP member identity, the audit/validator decision chain and existing policy tests. Added a focused regression test: dense-raster literal overlap of 1.0 must fail even when equal-support overlap is small. Confirmed no candidate data was generated and no current candidate is marked cleared.

**Pass 3 — requirement re-check:** re-ran the binding preflight, H33 lineage audit, download inventory and site/optimized site checks; ran the relevant and then full test suite. Verified Git diff and repository status remain free of data/cache artifacts. The final summary below distinguishes observed outcomes from unavailable source/portal facts.

### Current status card

See [`registry/session_f9a92cf6_run_card.json`](../registry/session_f9a92cf6_run_card.json). It records: H88-SPR conditional hypothesis; terrace/shoreline mimic; **HOLDOUT-DTI not run** after the binding stop; candidate surface correlation and final-dot overlap not measured because no surface/dots exist; universal registry overlap lower bound 1.0; no raster hash or candidate validator; no file to download or submit; negative verdict.

Verification progressed through two `main` integrations while preparing PR #177. The initial session run passed **875 tests / 23 skipped**; after the first merge it passed **882 / 23**. After incorporating the subsequent fail-closed CON88 audit, validation, and browser-evidence work on `main`, the final full suite passed **900 / 23 skipped** (70 warnings). Normal and optimized site guards, `render_decision.py --check`, `audit_downloads.py --check`, and the research-state audit passed. `validate_current.py` and `validate_release.py` returned 0 for research validation and their `--require-submit` forms returned expected exit `2`; the binding `generation_guard.py` returned expected exit `2`. Inventory: **48/48** local research-format passes; **0** protocol-eligible. The exact guard implementation evolved during those merges, but the binding result remains negative; no local or CI check is organizer acceptance.
