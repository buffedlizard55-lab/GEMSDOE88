# Canonical release audit — 2026-10-24

## Finding

The landing page and README correctly advertised H88-TDKL as the latest lane, but the machine feed (`docs/data/current_release.json`), `docs/status.json`, `scripts/validate_current.py`, `scripts/readiness.py`, the submission Markdown, and browser status code still treated older H88-MVRD, PHASE-88, or MDPS-88 artifacts as canonical. H88-TDKL's frozen run card also retained a pre-rename `GATE-PASS.tif` validator path and a `PROMOTE` sentence despite its binding final `negative` verdict.

## Correction

`scripts/validate_tdkl88.py` now independently reopens the exact committed TIFF and one-member ZIP, checks their SHA-256 values, compares the candidate to the restored sample CRS/shape/transform, scans every value for finiteness and range, checks zero outside the footprint and zero on mapped catalogue pixels, verifies the 56-feature leakage canary evidence, verifies labelled HOLDOUT-DTI metadata, and remeasures the hash-pinned dense-witness overlap. `scripts/validate_current.py`, `scripts/readiness.py`, `docs/data/current_release.json`, `docs/status.json`, the browser guard, README, and submission guides now identify the same H88-TDKL bytes.

## Decision

- **Download for research:** YES.
- **Submit:** NO — DO NOT SUBMIT.
- **HOLDOUT-DTI:** 0.196237, 95% CI [0.179686, 0.211729], evaluator `gems57-pooled-hide-v2`, 22,893 withheld positives.
- **Paired HOLDOUT-DTI delta:** +0.005801, 95% CI [+0.001174, +0.010109].
- **Format:** PASS on saved bytes.
- **Binding uniqueness:** FAIL: literal 17GEMSDOE overlap 1.0000 > 0.70; post-merge overlaps 0.762280 vs GTHC-88 and 0.752000 vs QTSK-88.
- **Organizer-confirmed score:** none; zero weekly slots used.

The supplied request still omits the promised single-method paragraph. The literal full-footprint witness also makes every nonempty candidate fail the stated overlap rule. The protocol therefore requires a stop rather than generation of a cosmetic new hash. No new model experiment or competition slot was used in this audit.
