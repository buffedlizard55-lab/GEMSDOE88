# Three-pass repository review — session `db4a5e4b`, 2026-10-25

## Executive decision

**New competition TIFF: NOT GENERATED. Submit any GEMSDOE88 download: NO — DO NOT SUBMIT.** This is an explicit negative result, not a claim that the highest-urgency deliverable was met. The site already places the existing H88-TDKL **research-only** TIFF and one-TIFF ZIP at the top and labels both `DO-NOT-SUBMIT`; its executive guide explains the upload workflow but does not authorize a slot.

- Existing research-only download: <https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif>
- Executive guide: <https://buffedlizard55-lab.github.io/GEMSDOE88/executive-summary.html>
- Session run card: `registry/session_db4a5e4b_run_card.json` (mirrored in `docs/data/` and `evidence/`)
- Ranked hypotheses: `research/session-db4a5e4b-hypotheses.md`

No candidate feature, model, dot placement, TIFF, competition upload, or weekly slot was created in this session.

## H33: what the evidence supports

The supplied `0.2778` for `h33-h33-2-b2...` is **USER-REPORTED**, not `ORGANIZER-CONFIRMED`; this repository contains no submission-page receipt. Freshly rerunning `scripts/audit_h33_lineage.py` against pinned owner-mirror rasters reproduced these **REGISTRY-MEASUREMENTS (not scores)**:

1. H33 has 37,654 positive cells and is an exact subset of D2.8, SOLO-D2.8 and H19-5.
2. Moving from D2.8 to H33 removes 6,436 cells; every removed cell is within two pixels of the catalogue.
3. H33 leaves zero positive cells within two pixels of the catalogue, has minimum nearest-neighbour spacing 2.828427 pixels and median catalogue distance 19.646883 pixels.

The defensible mechanism is therefore economical emission geometry, not proof of a newly learned geothermal process: prune catalogue-adjacent predictions that likely re-cover already-known structure, retain a well-ranked H19-5 descendant, and space dots near the 300 m triangular-kernel scale so redundant predictions do not inflate the Tversky false-positive term. This explains why the lineage **could** improve under the metric, but it does not prove causality on hidden labels.

Can this project produce something above `0.2778`? **Not established.** The best stored local result is **HOLDOUT-DTI 0.205991, `gems57-pooled-hide-v2`, 22,893 withheld positives, 95% CI [0.188105, 0.223344]** for H88-BPWD. Holdout and organizer scores are different estimands and must not be compared as if calibrated. The request also gives mutually inconsistent leaderboard maxima (`0.3195` and `0.4413`), neither backed here by a receipt. A better hidden score is scientifically possible, but no evidence in this review supports claiming it.

## Why the required unique TIFF could not lawfully be generated

The requested protocol says that if more than 70% of candidate dots are within three pixels of **one registry raster’s dots**, the lane has drifted and must stop. The shared generation preflight was rerun from restored, SHA-pinned bytes before feature construction:

| Registry measurement — not a performance score | Fresh result |
|---|---:|
| Allowed footprint cells outside catalogue | 5,106,385 |
| Allowed cells directly covered by pinned witness support | 5,106,385 |
| Universal lower bound for any nonempty candidate’s forward overlap | 1.0 |
| Binding limit | 0.70 |
| Guard result | `DUPLICATE_STOP`, expected exit 2 |

Witness: `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif`, SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, pinned at <https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif>.

That witness is positive on every allowed cell under the inherited support rule (`finite & > 0`). Thus every nonempty candidate has literal overlap 1.0 even before its surface exists. A blank TIFF, renamed old TIFF, threshold exception, or private reinterpretation would not satisfy the request. The conflict can only be resolved by an explicitly authorized, versioned shared protocol that distinguishes continuous probability fields from emitted dots; this session had no authority to change the rule.

## Pass 1 — implement and verify

1. Read `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md` and `AGENTS.md`; confirmed that the request contains no actual single-method paragraph.
2. Restored the validation tier through `bash scripts/download_competition_data.sh --validation`. All ten pinned repository groups restored and hash-verified. These are owner mirrors, not authenticated current organizer downloads.
3. Ran `.venv/bin/python scripts/preflight_mtas88.py --gate-generation`; reproduced `DUPLICATE_STOP`, exit 2, with zero experiments and zero rasters.
4. Ranked four not-yet-implemented hypotheses with layers, transforms, off-catalogue rationale, named mimics, local-code distinction and ordinal cost/benefit. No external data is needed for their first test.
5. Reran H33 lineage geometry. `scripts/forensics_h33.py` additionally requires the full 419 MB feature stack and correctly failed when only the validation tier was restored; no result from that failed command is claimed.
6. Ran the automated publication audit: 45 main TIFF/ZIP pairs plus one historical variant passed local research-format checks; zero are protocol eligible. This is local validation, not organizer acceptance.

## Pass 2 — bugs, assumptions and edge cases

- Corrected `NEW_HYPOTHESES.md`: magnetic-marker restoration was still called untested even though H88-MMRX had since executed and finished negative.
- Kept the mandatory stop rather than resurrecting the repository’s revoked representation-aware exception. The dense witness makes the literal rule non-discriminating, but that is a protocol-design irregularity, not permission to bypass it.
- Did not relabel archived TIFFs, modify prediction bytes, duplicate an old submission, or infer surface/final correlations for a candidate that does not exist.
- Separated H33 geometry, user-reported submission values, HOLDOUT-DTI and organizer receipts. No projection is called a score.
- Preserved automatic site/package validation and the prominent `DO NOT SUBMIT` state.

## Pass 3 — final verification

- Focused safety suite: **219 passed**, covering vendor pins, literal protocol, guarded generation entrypoints, artifact validator, download inventory and request evidence.
- Full suite: recorded separately in the run card after completion.
- Automated package audit: **46/46 research packages pass**, **0** protocol eligible.
- Expected-negative guard: `DUPLICATE_STOP`, exit 2.
- Normal and optimized site checks: recorded in the run card after completion.
- New competition TIFFs: **0**. Experiments: **0/3**. Weekly slots: **0**.

## Sources and limitations

Freshly retrieved/verified in this environment:

- Official DrivenData reference repository: <https://github.com/drivendataorg/gems-prize-reference-solution>, freshly queried through GitHub API at `main` commit [`aebe92f7c8a990f0e3443451b7a825d9afd6336b`](https://github.com/drivendataorg/gems-prize-reference-solution/commit/aebe92f7c8a990f0e3443451b7a825d9afd6336b) (commit timestamp 2026-06-16T13:55:26Z).
- Pinned owner repositories and bytes named by `scripts/restore_inputs.py`, including the immutable witness and H33 lineage.

Retained for manual review but not freshly reachable through this sandbox’s host allowlist:

- Competition overview/rules: <https://www.drivendata.org/competitions/306/competition-doe-gems/> and <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- DOE GDR INGENIOUS archive: <https://gdr.openei.org/submissions/1391>
- USGS GeoDAWN: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>

Remaining needs: an authenticated current organizer data comparison, a submission-page receipt for any claimed leaderboard value, and an owner-approved shared resolution of the continuous-raster/dot-overlap ambiguity. Only after that resolution may H88-GTD be run through canaries, buffered holdout, two-stage uniqueness and the separate slot selector.
