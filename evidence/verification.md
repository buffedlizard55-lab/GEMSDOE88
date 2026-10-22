# Three-pass verification

## Pass 1 — implementation and observed inputs

- Confirmed initial checkout only contained README, rather than the pipeline described in the request.
- Retrieved organizer reference and GEMSDOE32 owner source through GitHub API.
- Restored four core input entries (including the duplicated label/catalogue bytes) using pinned hashes and expected sizes. No competition output copied.
- Implemented the independent all-finite format audit, source review, four provisional hypotheses, blocked run card and static Pages site.

## Pass 2 — defects and edge cases

- Fixed an unclosed input stream in the restoration script.
- Added explicit complex-raster rejection and rejection of a multiband reference template.
- Tested negative values, overshoot, NaN, both infinities, sentinel values, multiband predictions, different CRS, dimensions, transform, nodata, and hidden masks.
- Inspected the actual restored example template: it contains nonfinite/masked pixels. It fails this project's deliberately stricter all-finite output policy. This is **not** evidence that the organizer's example format is invalid; use it for grid metadata, not as a candidate. See `template-format-diagnostic.json`.

## Pass 3 — request reconciliation

- `pytest -q`: 15 tests passed. Rasterio emitted upstream PendingDeprecationWarning messages; no test failures.
- `python scripts/check_site.py`: local links, blocked banners, note length and no misleading TIFF/ZIP links passed.
- `git diff --check`: passed before commit.
- No new prediction, HOLDOUT-DTI, CI, registry comparison, organizer score or weekly slot use claimed.
- No lane assigned or experiment started. Neither shared evaluator nor writer was privately recreated.
- Outstanding requirements remain explicit: a unique validated candidate, complete registry comparison, verified scoring improvement, entire-prompt verbatim archive, exhaustive multi-site review and live official feed are **not completed**.
- This is a blocked research/infrastructure deliverable, not full completion of the user's competition objective. Next session must first resolve lane/template/registry/folds and authenticate applicable rules/provenance.
