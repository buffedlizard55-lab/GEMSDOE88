# GEMSDOE88 — auditable fault-discovery research

## Submission status: **BLOCKED — DO NOT SUBMIT**

**No new competition TIFF has been generated or validated.** No previous submission has been copied as a deliverable. No weekly slot was used. [Executive summary](docs/executive-summary.html) · [Website](https://buffedlizard55-lab.github.io/GEMSDOE88/) · [Scientific review](research/review.md) · [Run card](evidence/run-card.json)

The initial repo contained only this README. Core input rasters have now been restored autonomously from hash-pinned GitHub mirrors, including the numerical feature stack. Mirror integrity is verified; organizer provenance is not. The missing method-lane paragraph, shared template/evaluator/writer, segment holdout and comparison registry prevent a compliant experiment. An all-zero or renamed historical TIFF would not solve these blockers.

## Start every session here — condensed user operating brief

This is a condensed operating brief, **not the full verbatim prompt**. Read this file and `research/review.md` before further work.

- Generate a scientifically distinct TIFF, not a renamed/copied submission; clearly distinguish downloadable research files, format-valid files and promoted candidates. Make a successful candidate easy to download at the beginning of the site.
- Stay in the assigned single-method lane. Stop and log duplicates above rank correlation 0.90 or candidate-dot overlap 70% within three pixels; compare surface before placement and final dots against the complete registry.
- Reuse the shared cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; repair shared tools once upstream, not in private forks.
- Hide whole fault segments with a buffer; recompute catalogue features from visible faults; mask visible pixels exactly. Use pooled DTI, alpha 0.2 / beta 0.8, 300 m triangular kernel. Run feature-alone leakage canaries; AUC above 0.90 requires investigation.
- Label measured performance HOLDOUT-DTI with evaluator version, withheld positives and 95% CI, or ORGANIZER-CONFIRMED with a submission receipt. A projection is not a score. Supplied historical scores remain unverified user reports.
- Propose and rank three to five geological hypotheses before implementation, naming layers, transforms, hidden-fault mechanism, non-fault mimic, novelty limits and cost. Test the top assigned candidate against the frozen holdout best before promotion.
- Stop after three experiments or two hours. Selecting a real slot is a separate step within the currently verified weekly cap. Do not automatically submit to DrivenData.
- End each run with the JSON card specified in the prompt, including negative outcomes. Automate validation; do not substitute human inspection.
- Audit free official sources; retain provenance and limitations. Never invent results, claim unvisited sources verified, or equate detected faults with geothermal vents.
- Review in three passes, test edge cases, publish an executive summary, and retain next steps. The requested PR and merge are part of this session.

**Maximize P(Win):** spend scarce submission slots on independently tested improvements, not hopeful projections. **Own the Outcome:** surface defects, fix what can be fixed, and report blocked outcomes without manufacturing evidence.

## Reproduce

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# Requires configured gh access; never put credentials in files.
.venv/bin/python scripts/restore_inputs.py --features
.venv/bin/pytest -q
.venv/bin/python scripts/check_site.py
# Format audit only, after a legitimate candidate exists:
.venv/bin/python scripts/validate_artifact.py candidate.tif \
  --template data/sample_submission.tif --output evidence/format-check.json
```

Data are ignored by Git and can be restored using the pinned manifest. The independent format audit rejects nonfinite values, values outside [0,1], masking/nodata, multiband files and mismatched CRS/shape/transform. It does not clip invalid predictions or declare a candidate submission-ready. It is **not** a private replacement for the shared evaluator or writer.

## Next steps

Resolve the missing lane and shared template pins; retrieve the complete comparison registry and frozen segment folds/baseline; validate data provenance and current rules; then run one preregistered geological experiment. See [review](research/review.md) for ranked proposals and the source/access table. GPU is optional according to the official reference repository; scientific validation, not GPU availability, is the immediate blocker.
