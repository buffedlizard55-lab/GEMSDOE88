# Repository review — 2026-10-25

## Executive result

**No new TIFF generated; do not submit any repository artifact as this session's candidate.** This was a review and verification pass, not a geological experiment. The checkout has no `data/` directory, so the pinned competition grids, feature cache, and registry raster files are not available to reproduce the stored pre-placement overlap proof or validate a new candidate. The generation guard failed closed (`AUDIT_ERROR`) on the missing `data/bridge/sample_submission.tif`; it did not authorize generation. A prior tracked status record says the research download is not submit-ready, but its underlying raster/input evidence cannot be freshly re-read from this checkout.

## Review passes

### Pass 1 — implementation and product surface

- Read `README.md`, `PROMPT.md`, and `USER_PROMPT_20261025.md` before reviewing.
- The site has a prominent research-download vs submission distinction, an executive submission guide, and machine-generated status. `scripts/render_decision.py --check` passed.
- `python scripts/check_site.py` passed, including canonical decision, archival links, research artifact records, and negative gates.
- The repository already includes extensive scientific records and candidate pipelines. The request's current text does not identify one unambiguous single-method paragraph to run in this session. Accordingly, no method was selected and no candidate was fitted or written.

### Pass 2 — failure modes, data, and automated checks

- Created an ignored local virtual environment from `requirements.txt`; this changed no tracked files.
- `.venv/bin/python -m pytest -q`: **616 passed, 58 skipped**, 61 rasterio pending-deprecation warnings; runtime 96.38 s.
- `python scripts/audit_session_start.py` could not complete because `data/bridge/sample_submission.tif` is absent. This is an environment/input availability failure, not a passing audit.
- `python scripts/generation_guard.py` returned exit 1 with `AUDIT_ERROR` for the same missing input; its JSON states `generation_allowed: false`, `ok_to_submit: false`, `new_rasters_generated: 0`, `experiments_run: 0`, `weekly_slots_used: 0`.
- No claim is made here that a prior stored overlap or holdout score was independently reproduced. The 0.2778, 0.3195, 0.4413 and other user-supplied competition figures are not organizer-confirmed receipts in this review.

### Pass 3 — requirement cross-check

- Unique TIFF requirement: **not met**; no TIFF was generated. Existing historical TIFFs were not copied, renamed, or presented as new.
- Automatic file/uniqueness validation: current file validation is blocked by absent source grids and registry rasters. Website structural checks passed, which is not TIFF validation or organizer acceptance.
- Submission-slot selection/upload: none performed; `0` slots used according to the fail-closed guard output. No current portal receipt or allowance was accessed.
- Scientific holdout, feature-alone leakage canaries, and candidate-vs-registry correlation/overlap: **not run** because the cached data and registry are absent and generation preflight failed. Do not label any old score as new evidence.
- Full request captured in README and `USER_PROMPT_20261025.md`; no README edits were necessary because README already starts with the unambiguous research-only/DO-NOT-SUBMIT status.

## What worked and what did not

The existing software suite and static website integrity checks pass in this environment. The science-to-submission path cannot be certified from this checkout: the required local raster inputs are missing, so even the shared preflight cannot reproduce its prior measurement. The competing urgency to make a new TIFF does not justify bypassing a failed/missing-input gate or claiming a format-only file is scientifically unique.

## Next steps

1. Restore the exact hash-pinned shared inputs using the repository's documented restore workflow and obtain the registry bundle needed by the uniqueness gate. Confirm SHA-256 values before any modeling.
2. Re-run the start audit and literal pre-placement surface comparison on the full registry. If the literal dense-witness result recorded in historical evidence reproduces, retain the duplicate stop; do not apply an unapproved exemption.
3. Before any new work, resolve the missing/ambiguous lane definition and use only the shared holdout, feature stack, metric, and writer. If the gate is clear, preregister at most three experiments, test every individual feature's leakage canary, then score the pooled spatially blocked holdout with its stated interval.
4. Generate a candidate only after passing surface and final-dot uniqueness, all format checks, and the independent selector. Keep the public download label explicitly research-only until those checks and separate slot authorization actually pass.
5. Verify any eventual leaderboard score only from an organizer submission-page receipt; verify current rules and slot cap from the authenticated competition page.

## One JSON run card

```json
{
  "hypothesis": null,
  "mechanism": null,
  "named_non_fault_mimic": null,
  "holdout_dti": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": null,
    "withheld_positive_count": null,
    "value": null,
    "ci95": null,
    "status": "not run; inputs absent"
  },
  "registry_correlation_overlap": {
    "status": "not run this session; required raster inputs absent",
    "historical_preplacement_gate": "stored evidence reports a saturated-witness duplicate stop; not freshly reproduced"
  },
  "raster_sha256": null,
  "validator": {
    "no_nan_inside_footprint": null,
    "values_in_0_1": null,
    "crs_shape_transform_match": null,
    "status": "not run; no candidate generated"
  },
  "submission_name": null,
  "note": "No new candidate; existing artifacts are not cleared for submission.",
  "verdict": "negative"
}
```
