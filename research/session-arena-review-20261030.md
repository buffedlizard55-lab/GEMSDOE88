# Repository review — Arena session 2026-10-30

## Executive decision

**No new TIFF was generated; do not submit any file from this checkout.** The shared pre-placement check, run after restoring the pinned validation-tier inputs, returned `DUPLICATE_STOP` (exit 2). Its SHA-pinned dense witness covers all 5,106,385 allowed pixels; with the repository's binding literal support definition (`finite prediction > 0`), every nonempty candidate would have 3-pixel overlap 1.0000, above the 0.70 ceiling. The stop precedes feature construction, placement, holdout, canaries, and TIFF creation. A fabricated score estimate or a zero-only file would not be a compliant substitute.

The user-provided H33 value `0.2778` and other site scores remain **USER-REPORTED CLAIMS**, not holdout measurements or organizer receipts. Historical H33 geometry/lineage is summarized in [`session-5aeeb70b-review.md`](session-5aeeb70b-review.md); its reported performance could plausibly reflect pruning redundant near-catalogue predictions under a distance-weighted metric, but that causal explanation is unproven. It is not evidence that it beats the current public leaderboard or that a new submission will score higher.

## Focus-site comparison requested

The existing pinned nine-site review is the only evidence available in this checkout; it is a dated historical audit, not current site status. All historical scores below have evidence class USER-REPORTED CLAIM. None is certified as unique against the full cross-site registry or approved for submission. Current (2026-10-30) README/TIFF/score refresh was not performed, so current file and score state is unknown.

| Site | Historical reported leader | Reported value | Existing audit's exact lineage note | Current submission decision |
|---|---|---:|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5…` | 0.2477 | D1.5 thinning; ridge-pruning lineage | No; literal witness overlap blocks |
| GEMSDOE25 | `dotted-h19-5-d2-8…` | 0.2600 | Same positive-pixel support as GEMSDOE30 D2.8 | No; literal witness overlap blocks |
| GEMSDOE27 | `topo-gap-closure-t-v2…` | 0.2449 | D1.5 support plus straight-line catalogue-tip connectors; separate GEMSDOE28 attribution is flagged irregular | No; literal witness overlap blocks |
| GEMSDOE28 | `h36-1-rung30-blind-r1…` | 0.2710 | 37,660 dots; high overlap with H33/H19-5; listed H27-4 also matches GEMSDOE31 support | No; literal witness overlap blocks |
| GEMSDOE30 | `d28-poisson300m-offcat…` | 0.2600 | Exact positive support match to GEMSDOE25 D2.8 | No; literal witness overlap blocks |
| GEMSDOE31 | `h27-4-solo-d28…` | 0.2708 | Exact support match to GEMSDOE28 listed H27-4/SOLO-D2.8 | No; literal witness overlap blocks |
| GEMSDOE32 | `h33-h33-2-b2…` | 0.2778 | 37,654-dot subset of D2.8/SOLO-D2.8; prunes 6,436 D2.8 cells near catalogue | No; literal witness overlap blocks |
| GEMSDOE33 | `h33d-analog-tip-stepover…` | 0.2632 | 41,865 dots; near-total overlap with H19-5 and D2.8 | No; literal witness overlap blocks |
| GEMSDOE36 | `anderson-geothermal-pinn…` | 0.2750 | Contains H33 dots plus 1,200 additions; raw scores do not establish a controlled comparison | No; literal witness overlap blocks |

The historical details, immutable source links, and documented caveats are in [`session-5aeeb70b-review.md`](session-5aeeb70b-review.md). “No” here means not cleared under the current local protocol, not a claim that each file has been freshly downloaded or individually rerun today. There is no new file name, score estimate, submission note, or download to offer.

## Three review passes

### Pass 1 — implementation and current local state

- Read `README.md`, `PROMPT.md`, the three dated user-prompt records, `AGENTS.md`, latest review, and current run card.
- Installed the pinned Python requirements into ignored `.venv/`.
- The first start audit and download audit failed closed because `data/` was absent. Restored only validation-tier data with `scripts/restore_inputs.py --validation`; no training feature stack was restored and no candidate build was attempted.
- Re-ran `scripts/preflight_mtas88.py --gate-generation`; it returned the expected negative `DUPLICATE_STOP` with witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, 5,106,385/5,106,385 covered allowed pixels, and no holdout/canaries/raster.

### Pass 2 — independent integrity checks

- `scripts/audit_research_state.py`: PASS; generation not authorized, `ok_to_submit=false`; source snapshot 156 files and hash `a71a03cbe235a9a4803679c7b9eef9036cfd6df4e4c808944a40aa3abbab3367`.
- `scripts/audit_downloads.py --check`: PASS; 51 published research TIFFs, 0 protocol-eligible, 0 exact decoded duplicate groups in the local inventory. This inventory result is not a global uniqueness clearance.
- `scripts/check_site.py` and `python -O scripts/check_site.py`: both PASS.
- `pytest -q`: **1109 passed, 23 skipped**, 115 warnings.

### Pass 3 — request, lane, scoring and submission gate

- Rechecked that the existing protocol forbids evading the full-domain witness with a private support definition, copied/renamed artifact, or zero surface. Since no candidate is validly buildable, no holdout/CI, canary, surface-correlation, final-dot overlap, submission TIFF, or score projection can truthfully be reported.
- Current scores, portal behavior/quota, and current focus-site files were not fetched/verified. No organizer receipt exists for a new submission. The latest preserved 2026-10-29 focus sample is explicitly historical/partial; its API refresh had nine unknown rows. Treat today’s current site/leaderboard state as **unknown**.
- No submission slot was used. No PR has been created or merged by this review because the safety protocol yields no candidate and there are no code changes that justify a competition submission. This report records a negative review result, not a submission authorization.

## Ranked next hypotheses (conditional, not authorized for execution)

The prior research queue audit ranks H88-SPR first, then H88-AWA and H88-CBC; the ranking is conditional and generation remains unauthorized. Consult [`research/candidate-hypotheses-20261025-mtas.md`](candidate-hypotheses-20261025-mtas.md), [`registry/hypothesis_queue.json`](../registry/hypothesis_queue.json), and source dossiers before proposing a different lane. These are not claims of expected numerical leaderboard improvement; the dense-witness stop prevents a valid holdout comparison under current rules.

Before continuing, resolve the representation/policy conflict through an explicit shared-template decision that preserves the literal protocol, update its common tests and audit artifacts, and ensure the competing-lane rule is satisfied. Do not privately reinterpret “dots” as top-N cells. Once an authorized rule and lane exist, restore authenticated or appropriately provenance-labelled inputs and run the prescribed buffered hide-and-recover holdout plus single-feature leakage canaries before any weekly-slot selector decision.

## Limitations and irregularities

1. Competition data access and redistribution terms are not authenticated here. The restored validation rasters come from hash-pinned owner GitHub mirrors, not a current logged-in DrivenData download.
2. `data/training_features.tif` and external feature layers are absent; full feature-stack experiments cannot run. Their absence does not lift the pre-placement stop.
3. Focus-site table entries and scores are historical user claims; today’s site/leaderboard state is unverified.
4. Local strict format passes on archived downloads do not establish acceptance by DrivenData; the reported `[0,1]` portal error remains undiagnosed.
5. The repository's highest priority is still to satisfy the unique submission request, but it cannot do so without violating the active duplicate stop. No file in `docs/downloads/` marked `DO-NOT-SUBMIT` should be uploaded.

## Reproduction

```bash
.venv/bin/python scripts/restore_inputs.py --validation
.venv/bin/python scripts/preflight_mtas88.py --gate-generation  # expected exit 2: DUPLICATE_STOP
.venv/bin/python scripts/audit_research_state.py
.venv/bin/python scripts/audit_downloads.py --check
.venv/bin/python scripts/check_site.py
.venv/bin/python -O scripts/check_site.py
.venv/bin/python -m pytest -q
```
