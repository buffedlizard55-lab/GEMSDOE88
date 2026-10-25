# 2026-10-25 — Unique-TIF request, H33 (0.2778) question, and the duplicate gate

**Decision: DO NOT DOWNLOAD FOR SUBMISSION. No new TIFF was generated in this session.**

Evidence labels: **MEASURED** = recomputed here from SHA-pinned bytes; **PUBLIC-PAGE** = read from the public DrivenData page on 2026-10-25; **USER-REPORTED** = claim supplied by the owner with no portal receipt; **ORGANIZER-CONFIRMED** = none exists for any GEMSDOE88 file.

## 1. Why no unique TIFF was produced

1. The project's parallel-run protocol (owner's prompt, recorded in `README.md` and `USER_PROMPT_20261025.md`) says: if any registry raster has more than 70% of its dots within 3 px of one registry raster's dots, log DUPLICATE and stop.
2. `scripts/generation_guard.py` (delegating to `scripts/preflight_mtas88.py`, shared template, no override switch) was run after restoring the validation-tier inputs with `scripts/restore_inputs.py --validation` (all SHA-pinned, all restored OK).
   - Result: **`DUPLICATE_STOP`**, exit code **2**, `generation_allowed: false`, `ok_to_submit: false`.
   - MEASURED: the witness `data/registry/dense_17gemdoe.tif` (SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) has finite positive values on **5,106,385 / 5,106,385** allowed pixels (covered fraction 1.0). Any nonempty candidate therefore has overlap 1.0 > 0.70.
   - Source of the witness (verified by the repo's restoration manifest): `https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif`
3. A unique filename or a unique hash does not clear this. The repo's policy (`AGENTS.md` §2, §5) forbids working around the stop by renaming, changing thresholds, or importing a builder.

**The open interpretation question is for the owner, not for an agent to resolve:** the 17GEMSDOE raster is a dense probability surface, not a dot set. Reading "dots" as "finite value > 0" makes the 70% rule unsatisfiable by construction. The repo's gate v4 (`scripts/reaudit_hgvc88_v4.py`) already measures dot-field overlap and rank correlation separately, but it is a *shared-template change* that the owner must explicitly approve. Until that approval exists, the literal rule stands.

## 2. Why H33 `h33-h33-2-b2` (USER-REPORTED 0.2778) scored high

Full analysis: `research/session-20261024-audit-why-0.2778.md`. Summary, restated without new numbers:

- **Metric algebra.** DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w), 300 m triangular kernel (`vendor/gems57/metric.py`). At a DTI near 0.28 an added dot is worth only about 0.056 of one truth pixel, so the metric rewards many well-separated dots, each with its own kernel. Dots closer than 3 px share kernel area and add FP weight without TP.
- **Geometry.** H33 has 37,654 dots with a median distance of 19.7 px to the mapped catalogue. Among 13 restored rasters with *claimed* scores, median distance to catalogue correlates with claimed score (Spearman 0.891, n = 13, descriptive only, not causal).
- **Limits.** The lineage was tuned on live leaderboard feedback (5 rows in `ledger/historical_climb.csv`). On the local hide-and-recover holdout it scores about 0.004 by construction, because it was built with the full catalogue. Its score therefore contains information about public labels that no local holdout can reproduce.

## 3. Leaderboard check (this session)

- PUBLIC-PAGE, retrieved 2026-10-25: **#1 xiaofanhu = 0.4413**, #2 cfld__ = 0.3916, #3 Batik Shirt Brothers = 0.3904. Source: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>.
- The 0.2778 and 0.3195 figures are USER-REPORTED. The repo's 2026-10-24 read placed 0.2818 at #50 (`docs/data/leaderboard.json`), so 0.2778 sits just below rank 50 if the figure is accurate. This is not verified here.
- Note on the brief: it describes 0.4413, 0.3195 and 0.2778 as "highest" in different places. These are inconsistent, and the repo already flags this as an irregularity.

## 4. Repo checks run this session (all PASS)

| Check | Command | Result |
|---|---|---|
| Restore validation tier | `python scripts/restore_inputs.py --validation` | exit 0, all groups restored |
| Generation guard | `.venv/bin/python scripts/generation_guard.py` | DUPLICATE_STOP, exit 2 |
| Download audit | `.venv/bin/python scripts/audit_downloads.py --check` | exit 0; 43 research pairs; 0 protocol-eligible |
| Decision render | `.venv/bin/python scripts/render_decision.py --check` | PASS |
| Site guard | `.venv/bin/python -O scripts/check_site.py` | PASS |

Environment note: the first guard run failed with `ModuleNotFoundError: numpy` in the system Python, and then with a missing `data/bridge/sample_submission.tif`. Both were environment problems, not scientific results. The guard fails closed, so neither produced a candidate. The fix was `.venv` + `requirements.txt` and the validation-tier restore.

## 5. Hypotheses (3–5 ranked), with pointers

The repo already holds a ranked list of untried hypotheses from 2026-10-24 (`research/session-20261024-audit-why-0.2778.md` §5): (1) crest-junction/termination prior, cost low; (2) dilation-tendency-weighted crests, cost medium; (3) scale-persistence of crests, cost low, with lane-overlap risk against GEMSDOE42; (4) relay/K-Th alteration (RDC-88), cost medium. These are **MODEL** rankings. None has been validated, and none may be built while the literal stop stands. The owner's prompt also asked for a "single method paragraph" that was never supplied. Lane selection is therefore still open.

## 6. What the owner needs to decide (blockers)

1. **Protocol:** approve or reject a shared-template change that defines "dots" for dense priors (gate v4 style), so the 70% rule becomes satisfiable. Without this, no candidate can be generated.
2. **Lane:** supply the single method paragraph, or pick one of the ranked hypotheses above.
3. **Slot cap:** the weekly cap and account state are not visible from this sandbox; `drivendata.org` submission pages cannot be checked here.
4. **Receipts:** no organizer receipt exists for any GEMSDOE88 file. A score is ORGANIZER-CONFIRMED only when copied from a submission-page receipt.

Machine-readable card: `registry/session_20261025_unique_tif_gate_run_card.json`.
