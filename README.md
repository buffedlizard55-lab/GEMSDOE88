# GEMSDOE88 — evidence before submission

**Start every session here and read [the scientific review](research/review.md).**

## Submission status: BLOCKED — do not submit
There is no generated submission TIFF in this repository. No score, global uniqueness, organizer acceptance, or slot eligibility has been established. This is a negative deliverable, not a ready entry. [Submission guide](docs/executive-summary.html) · [Machine-readable run card](docs/run_card.json).

## Standing project brief (operational condensation of the user prompt)
This section preserves the operative requirements, not a verbatim transcript of the long request.
- Goal: generate an original competition-format single-band GeoTIFF; a download must clearly say whether it is safe to submit. Never copy an earlier prediction as a new entry.
- Stay within the assigned parallel-run geological lane. Stop as duplicate if surface or final-dot correlation exceeds 0.90 or dot overlap within three pixels exceeds 70% against a registry entry.
- Reuse cached features, shared `evaluate_holdout.py` and `submission_writer.py`. Never create a private corrected evaluator.
- Hide whole fault segments with a buffer; build catalogue-derived features only from visible faults; mask visible pixels exactly; pool DTI with alpha 0.2, beta 0.8 and a triangular 300 m kernel.
- Test each feature alone. AUC above 0.90 is leakage until proved otherwise. Report HOLDOUT-DTI with evaluator version, withheld positives and 95% CI; ORGANIZER-CONFIRMED requires a submission receipt. Projections are never scores.
- Propose and rank 3–5 hypotheses before implementation; beat the frozen incumbent on blocked holdout before separate slot selection. Stop after three experiments or two hours. Never upload or spend a weekly slot automatically.
- End with a JSON run card including hypothesis, mechanism, confounder, holdout/CI, registry comparisons, raster hash, validator output, unique name, short note and promote/negative verdict. Negative results count.
- Build an accessible GitHub Pages site with a prominent status/download area and executive submission guide. Automatically reject NaNs inside footprint, out-of-range values, and CRS/shape/transform mismatch. No silent clipping.
- Research official free data; distinguish verified facts from hypotheses and inaccessible sources. Record irregularities, limitations and follow-up work. Do not invent authentication, data, results, receipts or novelty.
- Review in three passes; test, open a PR and merge when checks pass. Core values: Maximize P(Win) through sound evidence and risk management; Own the Outcome end to end.

Conflicting historical score claims in the request are not current verified leaderboard data. The missing lane paragraph, cache, registry and receipts are recorded in the review. The request's assertion that a ready GPU training pipeline exists does not match the initially empty repository.

## Local verification
```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/readiness.py
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```
The readiness command writes a blocked status as a normal negative result; a successful process exit does **not** mean ready to submit. No upload code exists. Vendored shared modules are byte-pinned; `registry/template_pin.json` records source commit and hashes. Scientific output must use those modules after the template audit is resolved. The report gate checks recorded evidence; it is not a model trainer or a substitute for computing evidence.

## Publication
Existing GitHub Pages configuration publishes `main` from the repository root. `index.html` links/redirects into `docs/`; no settings change is required. This session's integration could read Pages settings but received HTTP 403 on an attempted build-mode update. The existing mode is retained.
