# Session 7bf01824 — three-pass review, 2026-10-25

## Decision

**Download archived research TIFFs: yes. Submit: no. New unique TIFF: not generated.** This session preserves the binding duplicate-stop rule, rather than renaming an old file or relaxing the overlap threshold. Zero geological experiments and zero competition submissions were performed. The original request is already recorded in README.md, PROMPT.md and USER_PROMPT_20261025.md; those records were read, not duplicated again.

## Pass 1 — inspect and reproduce

Read the start-of-session contract, recorded request, primary README, canonical status, prior review, shared preflight and ranked research queue. Restored the validation-tier owner-mirror bytes using `bash scripts/download_competition_data.sh --validation`. This is file-identity verification, not authenticated organizer provenance. The full training/external cache was not restored or used.

`python scripts/preflight_mtas88.py --gate-generation` returned expected exit 2, **DUPLICATE_STOP**. The pinned witness directly covers all 5,106,385 allowed cells. Thus any nonempty allowed candidate has forward overlap 1.0, exceeding the requested 0.70 ceiling even before a 3-pixel dilation. No surface, dot placement or holdout was constructed. This is a registry measurement, not a DTI score. Rank correlations and final-dot measurements are unrun, not represented as passing values.

Reused the existing four ranked, untested proposals in [the research queue](session-d0c3adeb-hypotheses.md), rather than inventing a new lane after a stop: magnetic marker restoration; drainage-vetoed scarp-profile restoration; cross-boundary alteration-width asymmetry; conductive basin-breach continuity. That table names layers, transforms, missing-catalogue rationale, confounders, implementation contrasts and qualitative costs. It does not establish novelty across the whole fleet or predict a numerical improvement. Their viability remains conditional on a satisfiable shared protocol. No new external data is proposed in this session.

### Concrete code defect fixed

The offline leaderboard parser previously searched for a plausible score substring: a negative number, a percentage or exponent text could be accepted as an ordinary score. It also silently dropped malformed ranked rows and checked consecutive ranks only for the first three rows. It now requires whole-cell four-decimal scores in the closed unit interval, a nonempty participant, and consecutive ranks throughout the parsed table. Malformed ranked evidence raises before writing; the previous snapshot stays unchanged. Exact endpoints and tied scores remain valid. The synthetic fixtures are not real leaderboard evidence. Network scraping and automatic account uploads remain disabled.

## Pass 2 — bugs and edge cases

Added adversarial tests for signed scores, percentages, explanatory strings, exponents, extra decimals, nonfinite text, duplicate/gapped/malformed later ranks, and a malformed fourth score. Added tests for missing score cells, missing participants, valid endpoints/ties, and refusal to fetch without explicit HTML. The focused parser suite passes 23 tests. The strict parser deliberately fails on changed score formatting instead of guessing; an official markup change needs an explicit parser review.

Full suite before the final two edge tests: **649 passed, 23 skipped**, 61 dependency deprecation warnings. Skipped tests are not claimed as verified; full training and external-stack behavior were not exercised. No shared metric, writer, feature stack or uniqueness exception was added.

## Pass 3 — requirement reconciliation

- `audit_downloads.py --check`: all 43 saved TIFF/ZIP pairs pass research-download checks; zero protocol-eligible files. No new TIFF generated.
- `render_decision.py --check`: canonical overview and executive guide match evidence; no competing banner added.
- `check_site.py` and `python -O scripts/check_site.py`: pass. These are static/evidence checks, not a fresh browser interaction test or deployed-Pages verification.
- `audit_h33_lineage.py`: fresh run reproduces prior geometry; only the audit timestamps change. H33 has 37,654 positive pixels, is a subset of D2.8/SOLO/H19, and has no positive pixels within two pixels of the catalogue. These are geometry counts, not performance scores.
- Official reference HEAD freshly checked through GitHub API: [`aebe92f7c8a990f0e3443451b7a825d9afd6336b`](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b).

## H33 explanation and source boundaries

The [fresh lineage evidence](../evidence/h33_lineage_recheck.json) supports a spatial-thinning and catalogue-collar pruning explanation, not a new geological discovery. Sparse predictions reduce redundant emissions; excluding near-catalogue predictions may remove low-value predictions in an off-catalogue task. This is a plausible precision/coverage tradeoff, not causal proof: the hidden labels and an organizer receipt are unavailable. Nothing here establishes a score above the supplied H33 value or leaderboard claims. Those user-supplied values are **unverified claims**, not HOLDOUT-DTI or ORGANIZER-CONFIRMED evidence, and are not promoted into either class.

Review links: [H33 owner repository](https://github.com/buffedlizard55-lab/GEMSDOE32), [pinned registry witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif), [competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR 1391](https://gdr.openei.org/submissions/1391), [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf). Only the GitHub sources were retrieved here; other hosts are outside the session allowlist. Their contents, live availability, current cap and leaderboard were not freshly verified. The competition predicts fault traces; geothermal-vent discovery is a downstream scientific motivation, not the verified target label.

## Next session priorities and limitations

1. The literal registry rule is unsatisfiable for any nonempty candidate. A separately authorized shared clarification of how continuous surfaces count as dots is required before generation can resume. This review does not grant that clarification or exempt the witness.
2. If unblocked, freeze one method, use the shared visible-only buffered hide-and-recover folds and writer, run single-feature leakage canaries, and compare to the incumbent on identical folds with a paired confidence interval. Check surface uniqueness before placement and full-registry final-dot uniqueness afterward.
3. Keep actual portal submission receipts separate from user reports and offline public snapshots. Current weekly allowance, account access, rules and organizer input provenance remain unverified. No credentials are requested or stored.
4. Keep download instructions in the existing [executive guide](../docs/executive-summary.html). Format validity must never be shown as promotion or slot authorization. The requested eligible new TIFF remains **unmet**, not completed by the software patch.

Machine-readable outcome: [one session run card](../registry/session_7bf01824_run_card.json).
