# GEMSDOE88 session review — `arena/c0636fcd-gemsdoe88`, 2026-10-25

## Decision

**Negative / stop. No new TIFF was constructed, no experiment was run, and no competition slot was used. Do not submit an archived TIFF.** The SHA-pinned `17GEMSDOE` registry raster directly covers every pixel in the allowed prediction domain. Under the prompt's literal forward 3-pixel dot-overlap rule, every nonempty prediction has a lower-bound overlap of 1.0, above the 0.70 stop threshold. The guard therefore exits before feature construction, holdout fitting, placement, and writing. This is a measured registry-support result, not an organizer score.

The checkout's `data/` and `.venv/` were initially absent. The validation-tier files were restored from pinned GitHub owner-repository mirrors and verified by the restore script. These mirrors are not an authenticated download from the logged-in DrivenData data page. The full 19-band feature stack was deliberately not restored: the duplicate gate fails before it may be used, and no experiment requiring it was authorized.

## Three-pass review

### Pass 1 — read the contract and inspect the project

- Read `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md`, `AGENTS.md`, current status/run cards, the shared generation guard, restore workflow, candidate queue, H33 forensic report, and relevant feature modules.
- Confirmed the requested unique competition TIFF has not been generated and is not cleared. The site’s existing downloads are explicitly research-only; local format validity is not submission approval.
- The user prompt refers to a single-method paragraph but does not actually supply one. The repository also records the current lane as undefined. I did not invent an assigned lane.
- Restored validation-tier rasters with `python scripts/restore_inputs.py --validation`. No feature fitting, new holdout, or candidate construction was attempted.

### Pass 2 — run repository and safety checks

- `python scripts/generation_guard.py` initially returned `AUDIT_ERROR` because system Python lacked NumPy. This was an environment setup issue, not a data or candidate result. Created ignored `.venv/` and installed the declared `requirements.txt` dependencies from the permitted package index.
- Re-running `.venv/bin/python scripts/generation_guard.py` produced **`DUPLICATE_STOP`** (expected exit 2): the witness covers **5,106,385 / 5,106,385 allowed cells**, with **0 uncovered**. These are `REGISTRY-MEASUREMENT`s from the pinned rasters, not competition scores.
- `.venv/bin/python scripts/review_repo_20261025.py` completed with `DUPLICATE_STOP` and no audit errors. It selected no experiment and reports no new holdout or raster.
- `.venv/bin/python scripts/audit_downloads.py --check`: **46/46** published TIFF/ZIP packages pass local saved-byte research checks; **0** pass the binding protocol eligibility gate. These are local package-audit counts, not organizer acceptance.
- `.venv/bin/python scripts/render_decision.py --check` and `.venv/bin/python -O scripts/check_site.py`: PASS.
- `.venv/bin/python -m pytest -q -ra`: **807 passed, 23 skipped, 0 failed**. The skipped tests concern optional/generated local-only releases; 68 upstream/deprecation warnings were emitted. `git diff --check`: PASS before this review record was added.

### Pass 3 — check the request, science, and remaining blockers

- The user-supplied H33 value **0.2778** is a **USER-REPORTED claim**, not `HOLDOUT-DTI` and not `ORGANIZER-CONFIRMED`; no submission-page receipt for H33 exists in the inspected repository. The user-supplied **0.3195** and **0.4413** leaderboard statements were not freshly retrieved from the organizer during this review and are not attributed to an H88 artifact.
- On-disk H33 lineage analysis (`research/h33-forensics-20261024.md`, `evidence/h33_forensics_20261024.json`) supports a plausible explanation, not proof: H33 is a pruned subset of earlier point sets; the reported lineage removes near-catalogue/redundant dots; H33's nearest-neighbor spacing is approximately one 300 m metric-kernel radius on the 100 m grid. With an asymmetric distance-weighted Tversky objective (alpha 0.2, beta 0.8), a redundant or low-credit dot can add false-positive cost without materially increasing covered truth. Pruning can therefore improve the precision/coverage balance. The geometry does not show which removed dots were false positives on hidden labels, and cannot establish that pruning caused the reported result.
- The prior H88-MTAS experiment is **not** a result of this review. Its archived run card (`evidence/mtas88_experiment_20261025.json`) records `HOLDOUT-DTI = 0.049577 [0.044659, 0.054417]`, evaluator `gems57-pooled-hide-v2`, 22,893 withheld positive pixels; it is a historical negative and not organizer-confirmed. Because MTAS was already run, it is excluded from the new/untried queue below.
- The next qualitative candidate is H88-PRAN, followed by H88-FARC, H88-TCONS, and H88-FLAC. These are prioritizations for information gain and implementation cost—not numerical score forecasts. None was validated on a new holdout in this session. No candidate can be proposed as slot-ready while the pre-placement stop binds.
- No new external data is required by these four proposals as written: they use the project’s cached layers. However, the full cached feature stack was not restored in this review, and authoritative organizer-data provenance requires an authenticated DrivenData download. If a future shared protocol authorizes experiments, retrieve/verify required competition data from the official data page first; for any added external layer, verify official source, acquisition date, license, redistribution and organizer-sharing rights before use.

## Four candidate hypotheses (qualitative ranking only)

| Rank / expected value of information / cost | Existing layer(s) | Target signature and missing-catalogue rationale | Main non-fault mimic | Difference from implemented repo lanes |
|---|---|---|---|---|
| 1 / medium potential; low–medium cost — **H88-PRAN** | `rad_k_over_th`, detrended slope, profile curvature, basement depth | Terrain-bin-matched K:Th residual with along-strike coherence. Hydrothermal alteration or soil redistribution over a covered structure might persist where no discrete scarp is expressed; matching terrain aims to prevent a simple relief/slope proxy. | K-rich transported alluvium, parent-rock contacts, or moisture effects. | MVRD already combines radiometry and scarp evidence; this proposes a terrain-conditioned residual/null rather than a radiometric-plus-scarp conjunction. The named inputs are cached, but no PRAN experiment is evidenced as run. |
| 2 / medium potential; medium cost — **H88-FARC** | `chi_step_max`, `ksn_jump_norm`, hillshade lineament, LiDAR scarp coherence | Replicated signed cross-channel drainage offsets normalized by catchment and stream order, tested against an along-channel / matched pseudo-crest null. A weak blind rupture may perturb several channels even if no single scarp meets mapping confidence. | Lithologic knickzones, drainage capture, regional base-level change or climate-driven incision. | QTSK/TDKL rank individual knickwaves and scarp polarity; this requires spatial replication across independent catchments and a matched null. |
| 3 / medium potential; medium–high cost — **H88-TCONS** | local 2 m probe anomaly, well-temperature anomaly, 300 m conductivity edge, basement depth | Depth-conditioned temperature residual relative to conductance and basin depth. Focused fluid advection along a blind permeable fault could differ from broad conductive basin fill. | Playa/lake brine, groundwater circulation, or unfractured permeable lithology. | DHTC/GTHC use heat, conductivity and structural conjunctions; this candidate asks whether temperature adds residual information after those background controls, with head-/depth-matched negatives. |
| 4 / low–medium potential; low cost — **H88-FLAC** | RTP and gravity gradients, conductivity edge, geodetic shear/dilation | Cross-sensor edge persistence with an explicit flight-line-direction / leveling-artifact veto. A real buried discontinuity should be supported across sensors rather than follow an acquisition seam. | Gridding or tie-line leveling artifacts; broad lithologic contacts aligned with acquisition geometry. | MGC/XGCE compare cross-field edge geometry, but the proposed preregistered directional null targets a specific acquisition confound. |

The relative expected-gain labels are scientific judgment for queue ordering, not score projections. None of the four requires new external data at this stage. H88-PRAN is a plausible next candidate only **after** the shared protocol is resolved and the authorized holdout can be run; today it is unvalidated and not slot eligible.

## H33 and the score question

**Why might H33 have had the best score among the supplied GEMSDOE examples?** The strongest available explanation is metric-aligned thinning: successive subsets apparently removed locally redundant / near-known-fault pixels and retained a more spaced, less catalogue-hugging set. Given alpha 0.2 / beta 0.8 and distance-weighted matching, redundant predictions can pay false-positive cost while adding little marginal truth coverage. This is mechanistically plausible and consistent with the measured raster lineage. The supplied `0.2778` remains USER-REPORTED, and the available evidence does not isolate causality or reconstruct the hidden organizer labels.

**Can this project beat 0.2778?** The local evidence cannot answer yes. Archived holdouts are only proxies based on visible mapped faults, and no current candidate has a valid paired HOLDOUT-DTI test in this session. Any score claim requires a portal receipt and must be tagged ORGANIZER-CONFIRMED; any local experiment must be tagged HOLDOUT-DTI with evaluator, withheld-positive count and 95% CI. No score is forecast here. The public leaderboard, even when freshly viewed, would not establish H88’s performance.

## Source links and freshness

These are links for review, not claims that each page was freshly fetched on this branch. The active outbound-host policy allowed GitHub and package-index hosts, not the organizer, USGS, DOE GDR, EPSG or GitHub Pages domains.

- [DrivenData problem statement and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [official competition data page (authentication may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [DOE GDR INGENIOUS collection](https://gdr.openei.org/submissions/1391) · [EPSG:32611](https://epsg.io/32611)
- [GEMSDOE32 H33 project page named in the request](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) · H33 disk lineage in this repo: `evidence/h33_forensics_20261024.json` and `research/h33-forensics-20261024.md`.

## Remaining work / limitations

1. **Resolve the protocol contradiction through an explicit shared decision.** The dense witness is in-scope under the literal all-registry rule. Do not delete/exclude it, change thresholds, relabel supports or create a local exception to force a candidate through. The decision needs a documented owner/selector ruling about whether probability rasters count as “dots” for overlap, and then a matching shared template implementation and tests. Until then, no new surface or final dots should be built.
2. **Define the missing lane paragraph** in a shared, approved session contract before another parallel run. Do not infer it from this review’s ranked queue.
3. **After a protocol resolution:** preregister one lane; obtain the authenticated required input stack and verify hashes/rights; use the shared cached feature stack, buffered whole-component hide-and-recover evaluator, pixel-exact visible-fault mask, per-feature leakage canaries, and paired incumbent comparison. Only if holdout beats the same-fold incumbent with uncertainty reported should a separate selector evaluate a weekly slot.
4. **Submission evidence:** account access is required to verify current quota, portal acceptance, actual organizer receipts, or the prior `[0,1]` upload failure. Local format validation does not establish any of these.
5. **Current request status:** a unique new TIFF suitable for competition upload is not delivered. The existing archived TIFFs are research-only and should not be uploaded.

## Negative run card

Machine-readable card: [`../evidence/session_c0636fcd_run_card.json`](../evidence/session_c0636fcd_run_card.json). No candidate TIFF exists; its hash and validator fields are intentionally null. The prepared no-file name/note are not an upload recommendation.
