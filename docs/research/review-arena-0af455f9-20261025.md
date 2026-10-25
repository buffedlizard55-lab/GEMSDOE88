# Three-pass repository and scientific review — 2026-10-25

**Branch:** `arena/0af455f9-gemsdoe88`  
**Decision:** **No TIFF is cleared to submit.** The archived CON88 TIFF is downloadable for research only and is explicitly marked `DO-NOT-SUBMIT`.  
**Run card:** [`evidence/repo_review_arena_0af455f9_20261025.json`](../data/repo_review_arena_0af455f9_run_card.json) · Pages mirror: [`docs/data/repo_review_arena_0af455f9_run_card.json`](../data/repo_review_arena_0af455f9_run_card.json)  
**Official public leaderboard snapshot (all 50 displayed rows):** [`evidence/leaderboard_official_snapshot_arena_0af455f9_20261025.json`](../data/leaderboard_official_snapshot_arena_0af455f9_20261025.json) · [`docs/data/leaderboard.json`](../data/leaderboard.json)

## Executive decision and actions

The shared `scripts/generation_guard.py` was rerun after restoring validation-tier pins. It exits `2` with `DUPLICATE_STOP`: the SHA-pinned `data/registry/dense_17gemdoe.tif` has `5,167,373` positive pixels and covers all `5,106,385` allowed pixels (`0` uncovered; covered fraction `1.0`). Under the binding finite-prediction-`>0` support rule, any nonempty allowed prediction has a 3-pixel forward-overlap lower bound of `1.0`, above `0.70`. The correct action is to stop **before** feature construction, model fitting, dot placement, and TIFF writing.

This review ran **0** experiments, generated **0** TIFFs, ran **no** candidate holdout or feature canaries, and used **0** weekly slots. It did not choose a competition slot or make a new score claim. No completed experiment is treated as this session's output.

The stale CON88 exception was a real audit defect, not a reason to bypass the user protocol. The work:

1. Replaced `scripts/con88_preflight.py`'s private `EQUAL_SUPPORT_GATE_REQUIRED` / `generation_allowed: true` path with the shared guard.
2. Put the shared guard first in the CON88 experiment, margin, collar-holdout, and retired validator CLIs; replaced the former validator with a fail-closed retired stub so it cannot write a positive gate.
3. Removed the `cleared_by_con88_gates` promotion exception from `scripts/audit_downloads.py` and `scripts/check_site.py`; all published research pairs must now carry `DO-NOT-SUBMIT` and machine records must remain negative.
4. Renamed the historical CON88 TIFF/ZIP and metadata sidecar with an explicit `DO-NOT-SUBMIT` suffix. **TIFF bytes were not changed** (SHA-256 `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`). The one-member ZIP was rebuilt only so its internal filename also carries the warning (ZIP SHA-256 `23a5c62dee02b4b226d5d11bb0c1e16fe81781c4b9cb005b0820863726e55d1c`).
5. Replaced the CON88 gate/run-card status with a withdrawal record; corrected the landing page, archive page, submission guide, README, and session handoff. Added regression tests for the absence of any positive `ok_to_submit` field, the marked archive, and pre-import shared-guard behavior.
6. Refreshed a dated official public-leaderboard snapshot and displayed it as a **snapshot**, not as a live feed or this project's score.

No model features, evaluator implementation, metric, or submission writer were changed. The retired vendor equal-support function remains only as an informational diagnostic; it cannot grant protocol clearance.

## H33: what the reported `0.2778` can—and cannot—mean

`0.2778` is **USER-REPORTED**, not `ORGANIZER-CONFIRMED`: no DrivenData receipt tying that value to an H33 upload was found in this repository. The forensic record describes H33 (37,654 positive pixels) as an exact strict subset chain: H19-5 (121,131) → D2.8 (44,090) → SOLO-D2.8 (40,199) → H33 (37,654). No dots were added along that lineage. The 6,436 dots removed after D2.8 were measured within 2 pixels of the mapped catalogue; H33's nearest remaining catalogue distance is reported as 2.236 pixels. Its nearest-neighbour spacing is about the scoring-kernel radius (minimum about 2.83 pixels; median about 3 pixels), rather than a densely overlapping trace.

A plausible mechanism follows from the official distance-weighted Tversky metric and the repository implementation (`vendor/gems57/metric.py`): truth-pixel credit is a local **maximum** over predictions, while false-positive cost accumulates per prediction. In the binary-dot form, the repository expresses the pooled score as `T / (0.8|G| + 0.2(T + n - M))`, where `T` is weighted truth credit and `M` is weighted dot-to-truth credit. Removing a dot that contributes almost no marginal truth credit can lower false-positive cost without materially reducing `T`; spacing dots near one kernel radius can also reduce redundant local coverage. That makes a pruning/geometry explanation scientifically plausible.

It does **not** prove that the removals caused the reported score increase. The causal argument assumes that the removed dots earned little hidden-truth credit; that cannot be checked without the relevant hidden labels or an authenticated score receipt. The forensic report's positive association between off-catalogue distance share and owner-reported score uses only 20 related, correlated rasters and is diagnostic—not proof of a geological mechanism, a general law, or a candidate selector. The reported H33 result also cannot be equated with the local hide-and-recover score: different label populations and evaluation targets are involved.

## Leaderboard context (official public split, not a project score)

I fetched all three chunks of the official public leaderboard on **2026-10-25** and transcribed/checked its 50 displayed rows. The snapshot records:

- Rank 1: **xiaofanhu — 0.4413**.
- Rank 5 (the visible top-five boundary): **No Fault of Our Own — 0.3539**.
- Rank 8: **DARD — 0.3398** in this refreshed observation (the earlier saved observation showed DARD at 0.3358 and rank 9).
- Rank 50: **moongrega — 0.2818**.

The prompt's `0.3195` is not in the current 50 displayed rows. The `0.4413` result belongs to xiaofanhu, not GEMSDOE88. H33's `0.2778` is not among the visible 50 rows. If it were a directly comparable public-split result it would be below the displayed 50th score, but there is no receipt here establishing that it was submitted to this exact board, so I do **not** assign H33 a rank.

The GitHub Pages primary decision now displays the dated snapshot and its freshness date. It is **not live** and will not silently poll/scrape DrivenData: `scripts/update_leaderboard.py` deliberately accepts only a separately reviewed offline official-page capture. Thus this review reduces routine manual checking but does not claim an automatic live feed. A public leaderboard observation is never a private score or an owner-submission receipt.

## Ranked, untested scientific hypotheses

These are the three still-unimplemented, source-reviewed candidates in [`registry/hypothesis_queue.json`](../data/hypothesis_queue.json), ranked qualitatively. The queue's “conditional first choice” is **not** an assignment to run: this task does not name a single assigned method paragraph, and the universal duplicate stop currently blocks every candidate. `new_external_data_required: false` means the queue expects owner-mirrored inputs already catalogued; it does **not** establish that the full stack is restored, its hashes were reverified in this review, or that each derivative's licensing/sharing provenance was freshly checked.

### 1. H88-SPR — repeated scarp-profile restoration against a drainage/shoreline null

- **Named layers:** `data/training_features.tif` B12 `det_elev` and B19 `det_elev_slope`; `data/external/topo_10m_derived_100m_u8.tif` B8 `hs_lineament` and B9 `dem_mean` (manifest-decoded); `data/external/lidar_scarp_features_u8.tif` B3 `step_max`, B10 `coh100`, B11 `strike`, B12 `valid`; `data/external/dem10_chi_100m_u8.tif` B1 `chan_n`, B4 `valid_n`.
- **Physical signature / off-catalogue rationale:** on independent along-strike swaths, compare a smooth-landform-plus-signed-step profile with a no-step profile; require the step to recur in held-out profile samples away from channel corridors. A weak or cover-softened piedmont offset could remain unmapped while preserving a resolvable repeated profile. No mapped trace should seed the surface. The 100 m cache cannot justify a claim of metre- or sub-pixel scarp detection.
- **Named non-fault mimics:** fluvial terrace risers and constant-elevation pluvial shoreline benches. These need matched null controls, not just visual exclusion.
- **Implementation difference:** unlike LSC/TDKL/VESS/SHORE's scarp, polarity, knickpoint, or shoreline-context responses, this fits and cross-validates a landform-restoration likelihood; unlike MMRX it restores topographic profiles, not magnetic texture.
- **Cost / falsification:** **medium**, conditional on already-pinned layers. Reject if signed-step evidence disappears across adjacent held-out swaths, depends on drainage pixels, or is equally explained by contour-following terrace/shoreline controls.

### 2. H88-AWA — terrain-matched radiometric alteration-width asymmetry

- **Named layers:** `data/external/geodawn_rad_u8.tif` B1 K, B2 Th, B3 U **quantized indices**; `data/training_features.tif` B2 RTP, B15 `depth_to_base_surf`, B19 `det_elev_slope`.
- **Physical signature / off-catalogue rationale:** fit relative cross-strike decay widths of terrain- and parent-material-matched K/Th/U residuals on both flanks; test repeated width asymmetry with a local RTP depression. A covered permeable structure might alter one flank more broadly despite lacking a mapped surface trace. This is a conditional spatial association, not identification of an alteration mineral or proof of fluid temperature. Quantized codes must not be divided and described as calibrated K/Th concentrations.
- **Named non-fault mimics:** differential weathering across adjacent rock units and K-rich transported alluvium.
- **Implementation difference:** KTH/MVRD test radiometric enrichment/redox levels or edges; AWA tests fitted, terrain-matched cross-strike decay-width asymmetry rather than another high-value threshold or magnetic-marker shift.
- **Cost / falsification:** **medium**, with care needed for quantization, saturation and background fitting. Reject if a parent-material/terrain-matched null reproduces the asymmetry or the result depends on quantization/saturation artefacts.

### 3. H88-CBC — conductive basin-breach connectivity against a paleochannel null

- **Named layers:** `data/training_features.tif` B12 `det_elev`, B13 `iso_grav_anom`, B15 `depth_to_base_surf`, B17 `cond_surf`; `data/external/dem10_chi_100m_u8.tif` B1 `chan_n`, B4 `valid_n`.
- **Physical signature / off-catalogue rationale:** compare narrow conductivity connectivity across independently inferred basin-boundary saddles with a smooth basin-fill null; require a boundary-normal gravity change and explicitly test drainage alignment. A buried cross-basin structure might lack a surface trace. Coarse fields do not resolve metre-scale conduits, so the target is a conditional structural pathway—not a detected vent.
- **Named non-fault mimics:** unfaulted permeable alluvial paleochannels and saline groundwater plumes.
- **Implementation difference:** CTRA/DHTC use conductivity curvature or thermal conjunctions; CBC tests topology-preserving cross-basin connectivity against a drainage/paleochannel alternative.
- **Cost / falsification:** **medium-high**; the coarse-field resolution is a major limitation. Reject if basin-fill smoothness or drainage connectivity explains the bridge equally well, or if the boundary-normal gravity signature is absent.

No numerical DTI/leaderboard projection is assigned to any proposal. No proposal has been run in this review. All future validation, if the shared gate is legitimately revised and the method lane is explicitly assigned, must reuse the existing feature stack, shared `evaluate_holdout.py`, shared `submission_writer.py`, whole-segment buffered hide/recover, visible-only catalogue features, exact visible-fault masking, pooled alpha 0.2 / beta 0.8 DTI with the official 300 m triangular kernel, and per-feature leakage canaries (AUC > 0.90 is a stop until explained). No private evaluator/writer fork is acceptable.

## Publication and artifact status

- **No newly generated TIFF exists.** Current candidate TIFF SHA-256 and submission name are `null` in the run card; the submission verdict is `negative`; note length is recorded and remains below 140 characters.
- **Browser verification: PASS (2026-10-25 18:46 UTC).** Seven desktop/mobile page cases passed; the existing archived research-download HTTP response and actual click both matched SHA-256 `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`. A failed audit fetch and a no-JavaScript visit stayed explicitly negative. This tests download integrity and presentation only; it does not authorize submission. [Receipt](../data/review_arena_0af455f9_browser_check.json).
- **CON88 historical TIFF:** research download **YES**; competition submission **NO — DO NOT SUBMIT**. TIFF SHA-256 is `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`; format checks are historical local checks only and do not override `DUPLICATE_STOP`.
- The new ZIP carries the marked TIFF basename as its sole archive member and extracts byte-identical TIFF content. The rename did not generate a prediction or a new model result.
- The site and README now say no artifact is cleared to submit; the previous CON88 submit-ready copy and command instructions have been removed. The machine download audit must report **0** protocol-eligible files. Research-download safety is not competition clearance.

## Official/trusted sources and limits

- [Official DrivenData problem/metric/submission-format page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — public description of distance-weighted Tversky, `α=0.2`, `β=0.8`, a 300 m triangular kernel (three 100 m pixels), and the required GeoTIFF grid/values. A format pass is not an upload receipt.
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — public rows only; dated copy and retrieval limitations are in the linked JSON snapshot.
- [DrivenData reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution) — challenge baseline and implementation context; not evidence for a candidate score.
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — official survey description and CC0 release statement. The particular owner-mirrored/derived layers listed in the queue still need their own provenance and challenge-shareability confirmation.
- [EPSG:32611](https://epsg.io/32611) — WGS 84 / UTM zone 11N, metre units.
- [NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — only chunks 0–1 of 7 were fetched in this review; the complete prize rules were **not** reviewed. Do not infer a current submission cap, deadline interpretation, or eligibility from this partial read.

No DrivenData account receipt, private score, current weekly quota, or authenticated upload status was accessed. The full training/external/sibling stack was not restored or hash-checked here; the preflight prevented feature work. The queue fingerprint limits novelty claims to source-reviewed differences in this checkout and cannot prove fleet-wide or worldwide novelty. Fresh provenance/licensing, current competition rules, and a valid shared-policy pathway remain open blockers.

## Final automated verification — 2026-10-25

- Full repository suite: **887 passed, 0 failed, 23 skipped**, 64 Rasterio-related warnings, 233.22 seconds in the existing local environment. This is not a clean-environment reinstall or remote CI result.
- Shared generation guard: expected **exit 2**, `DUPLICATE_STOP`; 5,167,373 positive witness pixels cover all 5,106,385 allowed cells; no candidate, experiment, or slot.
- Saved-byte download audit: **47 main + 1 historical variant = 48** TIFF/ZIP pairs pass research-format checks; **0** protocol-eligible.
- Source-queue audit: **PASS**, 154-file fingerprint `86af024f…db9d4cf5`; `input_pins_checked: false`, so no claim of full-stack hash revalidation.
- Decision renderer: **PASS**; site guard: **PASS** under both normal and optimized Python.
- Browser receipt: **PASS**, seven desktop/mobile cases, exact HTTP and actual-click hash for the existing TDKL research download, and negative missing-audit/no-JavaScript states. It is not a portal receipt or submission authorization.

## Reproduction and next steps

```bash
python scripts/restore_inputs.py --validation
.venv/bin/python scripts/generation_guard.py  # expected exit 2: DUPLICATE_STOP
.venv/bin/python scripts/audit_downloads.py --check
.venv/bin/python scripts/audit_research_state.py
.venv/bin/python scripts/render_decision.py --check
.venv/bin/python -O scripts/check_site.py
.venv/bin/python -m pytest -q
```

1. Preserve the shared literal stop. Do not edit the selector or add a dense/equal-support or creation-order exception merely to produce a TIFF.
2. If the user/policy owner explicitly resolves the contradictory universal blocker, first update the shared policy and tests with provenance; do not silently bypass it in a lane-specific preflight.
3. Before a scientific run, name the single assigned method paragraph. Reverify all required layer hashes and official provenance/licenses; restore the complete shared stack only after the preflight permits work.
4. Then preregister at most three experiments/two hours and use the required shared holdout, canaries, writer, registry checks and complete run card. Negative results remain deliverables.
5. Keep slot selection separate; submit only after a distinct authorized selector and a current portal receipt path are established.

**Maximize P(Win):** keep scarce feedback slots for evidence-backed, protocol-distinct candidates. **Own the Outcome:** the unique submission requirement is unmet; the correct result today is a negative, auditable stop—not an unsafe download relabeled as a win.
