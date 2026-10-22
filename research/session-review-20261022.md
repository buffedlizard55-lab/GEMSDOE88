# Session review — 2026-10-22 (3 passes, line-by-line re-verification)

## Pass 1 — implement/verify (reproduced from clean state + CGO-88 blocked holdout & 19-band audit)
- Merged concurrent `origin/main` (`db690e4`, PR #6) onto `arena/e822d487-gemsdoe88`.
- Created `.venv` from `requirements.txt` (pinned `numpy`, `scipy`, `rasterio`, `scikit-learn`, `pytest`).
- `python scripts/restore_inputs.py` → `RESTORED/PIN OK` for `grid`, `features` (`training_features.tif`, SHA-256 `4371c82e…`), `witness` (`dense_17gemdoe.tif`, SHA-256 `ab0a0a62…`), and `h33` (`h33_education.tif`, SHA-256 `c55bafc4…`).
- Implemented and executed `scripts/evaluate_cgo88.py` to:
  1. Inspect all 19 bands of `data/training_features.tif` on disk, verifying every `band_name` tag, embedded TIFF description, valid pixel count, 1st/50th/99th percentiles, and single-feature leakage canary symmetric AUC on the 8 spatially-blocked folds (`seeds=(20, 21)`, `22,893` withheld positives; max symmetric AUC = `0.5642` on `det_elev_slope`, all 19 bands $\le 0.90$).
  2. Validate the #1 ranked next hypothesis from the previous session (**CGO-88**: Conductivity–Gravity 200 m lateral offset using verified Bands 13 `iso_grav_anom`, 17 `cond_surf`, 18 `iso_grav_anom_hg`, 15 `depth_to_base_surf`) on the identical `gems57-pooled-hide-v2` blocked folds (`n=22,893` withheld positives, 1,000-draw 20 km spatial block bootstrap).
  3. Record the machine-readable receipt in `registry/cgo88_holdout_and_band19_audit.json` and `docs/evidence/cgo88_holdout_and_band19_audit.json`.
- **Blocked holdout outcome (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`, `n=22,893`):**
  - Incumbent `MGC-88` (Exp 1): **HOLDOUT-DTI `0.0389 [0.0264, 0.0532]`** vs matched raw-layer control **`0.0267 [0.0173, 0.0372]`** (paired $\Delta = +0.0122\ [0.0056, 0.0197]$), reproduced bit-for-bit against `registry/holdout_result.json`.
  - Candidate `CGO-88` pure (Exp 2): **HOLDOUT-DTI `0.0227 [0.0154, 0.0309]`**, paired $\Delta$ vs `MGC-88` = **`-0.0162 [-0.0281, -0.0073]`**.
  - Candidate `CGO-88` joint with `MGC-88` (Exp 2): **HOLDOUT-DTI `0.0230 [0.0162, 0.0308]`**, paired $\Delta$ vs `MGC-88` = **`-0.0158 [-0.0286, -0.0061]`**.
  - Because `CGO-88` failed to beat `MGC-88` (`0.0389`), `CGO-88` is rejected on the holdout gate and `MGC-88` (`gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif`, SHA-256 `3af5d290…730b`) remains the unbeaten holdout best (`ok_to_download=true`, `ok_to_submit=false`).

## Pass 2 — bug, hallucination, and edge-case review
- **Defect found & fixed (`IR-88-07`):** Concurrent PR #6 (`4ef17e8`) had written approximate band names (`mag_anomaly`, `tmi_vertical_gradient`, `surface_conductivity`, `horizontal_gravity_gradient`, `strain_invariant`, `shear_strain`, `dilatation`, `detrended_elevation`, `slope`), falsely claimed radiometric K/Th/U/TC were inside the 19-band `training_features.tif`, and included an unverified URL (`cahill-lake-lahontan`). Direct on-disk inspection of `data/training_features.tif` proved the 19 bands contain zero K/Th/U bands and that Band 6 (`tc`) has embedded description `tc - Tilt angle or total curvature - magnetic field derivative for edge detection` (radiometric K/Th/U/TC reside in the external CC0 USGS GeoDAWN release DOI `10.5066/P93LGLVQ`). Corrected all band names, descriptions, and external-source attributions across `research/candidate-hypotheses-20261022.md`, `docs/research/candidate-hypotheses-20261022.md`, `docs/research.html`, and `knowledge/field-guide.md`, and added regression tests in `tests/test_release.py`.
- **Defect found & fixed (bootstrap block union in multi-arm comparison):** Calling `evaluate_holdout.pooled_summary` with 3 arms simultaneously takes the union of active spatial blocks across all 3 arms (`157` blocks vs `155` for 2 arms), slightly perturbing `MGC-88`'s bootstrap percentile endpoints. Updated `scripts/evaluate_cgo88.py` to compute pairwise `pooled_summary` calls so `mgc88_incumbent` and `raw_control` match `registry/holdout_result.json` bit-for-bit.
- **Defect found & fixed (`.github/workflows/ci.yml`):** Updated push trigger branches to `[main, arena/e822d487-gemsdoe88, 'arena/**']`.
- **Input validation hardened:** Added shape and `step_px > 0` validation to `cgo_features` in `scripts/evaluate_cgo88.py` and unit-tested invalid inputs in `tests/test_science.py`.
- Updated `docs/data/leaderboard.json` with a fresh 10-row public leaderboard snapshot fetched on `2026-10-22` (`#1 xiaofanhu 0.4413`, `#2 cfld__ 0.3904`, `#3 Batik Shirt Brothers 0.3904`, etc.) and archived the verbatim project prompt in `README.md`.

## Pass 3 — recheck against original request
- `pytest -q` → **56 passed**; `scripts/check_site.py` → **PASS**; `scripts/readiness.py` → `BLOCKED` (`ok_to_download_for_research=true`, `ok_to_submit=false`); `scripts/validate_release.py` → `format_ok=true`, `literal_duplicate=true`, `ok_to_submit=false`; `scripts/validate_release.py --require-submit` → **exit code 2** (automatic fail-closed STOP).
- Every local HTML link and every Markdown relative link verified to resolve on disk.
- No projection or HOLDOUT-DTI is ever labeled as `ORGANIZER-CONFIRMED`; 0 weekly slots spent.

## Flagged for protocol owner (not fixable in-repo without rule change or login)
1. **IR-88-01:** Literal overlap rule vs the hash-pinned full-footprint witness (`dense_17gemdoe.tif`, positive at all 5,167,373 footprint cells) makes any nonempty candidate have 100% 3-px forward overlap (`> 0.70`), requiring an explicit selector/protocol rule update to exclude non-discriminating full-footprint continuous rasters from the binary 3-px dot-overlap denominator.
2. **IR-88-02:** Owner-mirrored `sample_submission.tif` values match the 60,988 positive fault pixels rather than "total fault absence"; used strictly for grid/footprint metadata.
3. **Organizer authentication:** DrivenData data and submission pages require participant login (never request credentials in chat).
