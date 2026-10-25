# Session 4c9e4bed — Review, H33 answer, and DUPLICATE_STOP (2026-10-25)

Machine card: [`session_4c9e4bed_run_card.json`](../data/session_4c9e4bed_run_card.json). Verdict: **negative. No new TIF. `ok_to_submit: false`. 0 slots.**

## Why h33 scored 0.2778 (USER-REPORTED, not ORGANIZER-CONFIRMED)
Byte/SHA-verified lineage already in repo (`docs/research/bgcd88-forensics-and-phd-synthesis-20261025.md` §1, `research/candidate-hypotheses-20261023.md`): h33 = 37,654 sparse binary {0,1} dots on multi-physics contact support, kernel-spaced ~2.8 px, with all dots ≤2 px (200 m) from catalogue faults removed (−6,436 vs ancestor). DTI (α=0.2, β=0.8, 300 m triangular kernel) pays for proximity to *hidden* faults and charges denominator mass per dot; collar dots beside already-mapped traces earn little hidden-fault credit, so deleting them raised the reported score 0.2600→0.2778. The `-zeros` encoding (finite 0 outside footprint, no NaN) is also what fixes the portal error *"Predicted values must be in range [0, 1]"*.

## Can we generate a unique, higher TIF this session? No — verified, not assumed
1. `python3 scripts/generation_guard.py` fails closed (`generation_allowed=false`). In this sandbox: `AUDIT_ERROR` — `data/bridge/sample_submission.tif` / cached feature stack absent (gitignored; DrivenData requires login). Flagged IR-4C9E-01.
2. Even with data restored, the binding literal gate stops generation: continuous `17GEMSDOE` witness covers 5,106,385/5,106,385 allowed cells → any nonempty candidate has 3-px overlap **1.0 > 0.70** and rank-correlation saturation (`docs/data/current_release.json`, `vendor/gems57/uniqueness.py`). Per PARALLEL-RUN PROTOCOL §1 and `AGENTS.md` §2: log duplicate, stop. Renaming/re-thresholding to evade is prohibited.
3. Next untried lane is already ranked: **H88-SPRV** (Hanks–Bucknam erf scarp-profile restoration; mimic: fan-channel/terrace risers + Lake Lahontan shoreline benches) in `NEW_HYPOTHESES.md`, with H88-PGTD/CBBC/TAWA/MT3D-GDR behind it. It may only run after the gate/data blocker clears, must pass per-feature canary (AUC ≤0.90), buffered hide-and-recover vs H88-BPWD's HOLDOUT-DTI 0.205991 [0.188105, 0.223344] (n=22,893), and the §1 uniqueness check on surface *and* final dots.

## Site obviousness (already satisfied, unchanged by design)
`docs/index.html` title + alert strip read "DO NOT SUBMIT"; every download is `-DO-NOT-SUBMIT` with research-only labelling; `docs/SUBMIT.md` + `executive-summary.html` give the future-green upload procedure and ≤140-char note format. Per `AGENTS.md` §6 the rendered pages were **not** hand-edited (renderer drift guard).

## Passes
- Pass 1: guard run, repo/status/current-release audit, tests `105 passed, 10 skipped`.
- Pass 2: confirmed no `data/` stack in sandbox; guard failure is fail-closed AUDIT_ERROR, not clearance — recorded as irregularity rather than silently treating stored DUPLICATE_STOP as freshly re-measured.
- Pass 3: re-checked deliverable against protocol §5 run-card fields; all numbers labelled HOLDOUT-DTI (stored, cited) or USER-REPORTED; no projection written as a score.
