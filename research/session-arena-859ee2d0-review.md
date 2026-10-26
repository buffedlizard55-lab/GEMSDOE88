# Repository review — Arena branch `arena/859ee2d0-gemsdoe88` (2026-10-26)

## Decision first

**No new TIFF was generated. Do not submit any existing download from this repository or the nine focus sites.** The shared SHA-pinned preflight completed after installing the repository's pinned CPU environment and restoring validation-tier inputs. It returned `DUPLICATE_STOP` (exit 2): the pinned `17GEMSDOE` witness directly covers all `5,106,385` allowed off-catalogue footprint pixels, so every nonempty candidate placed in that domain has literal three-pixel overlap `1.0`, above the protocol limit `0.70`. No candidate surface or dots were constructed, no holdout experiment or leakage canary ran, and no weekly slot was selected or used.

Archived TIFFs remain downloadable **for research only**. A successful local format check is not organizer acceptance and does not clear the uniqueness or holdout gates. No new score is estimated: neither a holdout score nor an organizer receipt was produced in this review.

## The nine requested sites

The values below are exactly the values reported in the user-provided prompt and the existing source-bound site audit. They are **USER-REPORTED CLAIMS — not HOLDOUT-DTI and not ORGANIZER-CONFIRMED**. The pre-existing focus-site audit reports zero organizer receipts and classifies all nine champions as duplicates; its evidence covers 44 cached TIFFs. The current checkout verifies the committed audit package and pinned witness; it does not contain the raw cross-site cache used to recompute all 44 TIFF measurements.

| Site | Highest listed submission | Reported leaderboard value (evidence class) | Unique vs registry/prior submissions? | Download / submit decision |
|---|---|---:|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 — USER-REPORTED CLAIM | No; audit reports 1.0000 3-px overlap with H19-5 and the dense 17GEMSDOE witness | Research download only; DO NOT SUBMIT |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 — USER-REPORTED CLAIM | No; exact duplicate of GEMSDOE30 D2.8 and overlap 1.0000 with the dense witness | Research download only; DO NOT SUBMIT |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 — USER-REPORTED CLAIM | No; 0.9854 3-px overlap with H19-5 and 1.0000 with the dense witness | Research download only; DO NOT SUBMIT |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 — USER-REPORTED CLAIM | No; 1.0000 overlap with the D2.8 lineage and dense witness | Research download only; DO NOT SUBMIT |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 — USER-REPORTED CLAIM | No; pixel-identical to GEMSDOE25 D2.8 and overlap 1.0000 with the dense witness | Research download only; DO NOT SUBMIT |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 — USER-REPORTED CLAIM | No; exact subset/duplicate of the D2.8 lineage and overlap 1.0000 with the dense witness | Research download only; DO NOT SUBMIT |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 — USER-REPORTED CLAIM | No; exact subset of the D2.8 lineage and overlap 1.0000 with the dense witness | Research download only; DO NOT SUBMIT |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 — USER-REPORTED CLAIM | No; 0.9971 overlap with H19-5 and 1.0000 with the dense witness | Research download only; DO NOT SUBMIT |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 — USER-REPORTED CLAIM | No; exact superset of H33-2-B2 and overlap 1.0000 with the dense witness | Research download only; DO NOT SUBMIT |

**Interpretation of H33-2-B2, without claiming causality:** the recorded lineage successively thins the H19-5 ridge pattern and removes dots near mapped catalogue faults. That can reduce redundant nearby predictions and the false-positive contribution under a spatial tolerance metric, which is a plausible explanation for why its user-reported value exceeds nearby variants. The available records do not establish that this mechanism caused a verified organizer score, that it generalizes to hidden positives, or that it beats the current competition leader. The prompt's 0.3195 and 0.4413 standings are also user-supplied claims here, not receipts. The project's hide-and-recover score is a different evidence type from a leaderboard result.

## Three-pass review

### Pass 1 — baseline and task coverage

- Read `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md`, `USER_PROMPT_20261026.md`, `AGENTS.md`, and the latest committed focus-sites review/run card.
- Confirmed the request and the no-bypass parallel protocol are already recorded in the README; the nine-site summary, research-only download warning, submission steps, and source links already exist. `scripts/render_decision.py --check` confirms the generated overview and submission guide match their machine evidence.
- Verified `registry/hypothesis_queue.json` contains three source-bound, untested ideas: H88-SPR (repeated scarp-profile restoration), H88-AWA (terrain-matched radiometric alteration-width asymmetry), and H88-CBC (conductive basin-breach connectivity). Their costs, layer pins, mimics, and falsification criteria are in that file. The prior d634de37 review separately documents five ranked ideas. These are hypotheses, not validated candidates or score projections.

### Pass 2 — independent checks and irregularities

- The default Python interpreter initially lacked NumPy; this was an environment issue, not permission to skip the gate. Installed `requirements.txt` into the ignored `.venv`, restored only the hash-pinned validation-tier dataset with `scripts/restore_inputs.py --validation`, and reran the shared preflight. The validated dependency versions are pinned by `requirements-constraints.txt`.
- Shared preflight result: `DUPLICATE_STOP`, exit 2; SHA-256 witness `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`; direct coverage `5,106,385/5,106,385` allowed cells. It is mathematically impossible to meet the literal overlap threshold with a nonempty prediction over the allowed domain while this witness and rule remain binding. A different filename, sparse surface, or attractive holdout result cannot change that set relationship.
- `python -O scripts/audit_focus_sites_20261026.py` passed the committed evidence/schema/pin checks and reports `0/9` unique/cleared. This was not a rebuild of 44 remote TIFFs: `.cache/focus_sites/` is not present in this checkout.
- `scripts/audit_research_state.py --check-inputs` is incomplete in this validation-only checkout because the optional cached full-stack input `data/external/dem10_chi_100m_u8.tif` is absent. The source-bound queue metadata audit without `--check-inputs` passes. Full training data were not restored: doing so cannot override the earlier mandatory duplicate stop, and no experiment is authorized after that stop.
- Irregularities already recorded by the prior audit remain important: GEMSDOE27's H31-1 self-promotion conflicts with its reported holdout and omitted-registry checks; GEMSDOE33's A33-R2-HMDT put 80.04% of emitted dots outside the valid footprint, included mapped-catalogue dots, and had no holdout measurement. Do not treat either as a viable submission.

### Pass 3 — final verification and disposition

- Full test suite: **932 passed, 23 skipped** (70 Rasterio warnings; no test failures).
- `scripts/render_decision.py --check`: passed in normal and optimized (`-O`) mode.
- `scripts/preflight_mtas88.py --gate-generation`: correctly stopped with exit 2 and emitted a negative, no-raster record. No feature extraction, model fitting, candidate surface, placement, TIFF writer, or selector step followed.
- No new TIFF SHA-256 exists. For the latest prior audit's archived canonical education file, the recorded SHA-256 is `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`; that file is marked `DO-NOT-SUBMIT` and is not a deliverable created or revalidated as a new candidate here.
- No current submission-page receipt was available. This review did not access the DrivenData login-protected submission interface or independently confirm a live leaderboard.

## Next steps, ordered by actual unblockers

1. **Do not create or submit a TIFF under the present literal rule.** A policy/selector owner must first resolve the universal-witness contradiction through an explicit shared protocol change; no private exception or builder bypass is acceptable.
2. After an authorized policy revision, restore the complete SHA-pinned input stack (including all sibling registry rasters), rerun the full inventory and source-pin audits, then preregister one queued candidate and its non-fault null.
3. Only after the revised shared preflight clears the candidate, run the shared buffered whole-segment hide-and-recover evaluator and a single-feature leakage canary; compare against same-fold incumbents. Stop at three experiments or two hours.
4. Require surface and final-dot uniqueness checks, strict `[0,1]`/footprint/CRS/shape/transform validation, and the separate selector decision before any real weekly slot. Archive an actual portal receipt before using the label ORGANIZER-CONFIRMED.
5. Keep manual-review source links for the official [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/), [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN data record](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS project](https://gbcge.org/current-projects/ingenious/), and [EPSG:32611](https://epsg.io/32611). These are review pointers; this session did not freshly retrieve the non-GitHub/USGS pages or authenticate competition inputs against a logged-in organizer download.

## Run-card summary

See [`registry/session_arena_859ee2d0_run_card.json`](../registry/session_arena_859ee2d0_run_card.json) for the machine-readable negative result. Verdict: **negative / no candidate / no new TIFF / DO NOT SUBMIT**.
