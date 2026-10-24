# GEMSDOE88 agent/session start

Before changing code or running an experiment:

1. Read `PROMPT.md` in full and read the current section of `README.md`.
2. Confirm the current canonical card is `registry/mrrcoh88_run_card.json`: **DOWNLOAD FOR RESEARCH: YES; DO NOT SUBMIT**.
3. Do not tune or rerun MRR-COH-88 to improve its negative result.
4. Verify all restored-input SHA-256 pins in `registry/data_manifest.json`.
5. Use one preregistered method lane and the shared `vendor/gems57` evaluator/writer.
6. Preserve buffered whole-component holdout, visible-only catalogue features, pixel-exact masking, feature-alone canaries, and declared uniqueness stops.
7. Keep HOLDOUT-DTI, owner-reported values, model projections, and ORGANIZER-CONFIRMED receipts distinct.
8. Never upload automatically. Scientific promotion and weekly-slot selection are separate decisions.
9. Perform three passes: implement/verify; review/fix; requirement recheck/fix.
10. Preserve the values **Maximize P(Win)** and **Own the Outcome**.

Current independent checks:

```bash
.venv/bin/python scripts/validate_current.py
.venv/bin/python scripts/readiness.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

`validate_current.py --require-submit` is expected to exit 2 for the current release.
