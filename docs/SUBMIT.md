# Competition submission guide (current decision: DO NOT SUBMIT)

**Current candidate: MDPS-88. Research download: YES. Competition submission: NO.** Automated gates (frozen in `registry/preregistration_mdps88.json`) failed on holdout; no human inspection is involved in the decision. No weekly slot has been used; no `ORGANIZER-CONFIRMED` score exists.

- GeoTIFF: [`gems88-mdps88-mix-29742dots-20261024-zeros-DO-NOT-SUBMIT.tif`](downloads/gems88-mdps88-mix-29742dots-20261024-zeros-DO-NOT-SUBMIT.tif)
- Single-TIFF ZIP: [`gems88-mdps88-mix-29742dots-20261024-zeros-DO-NOT-SUBMIT.zip`](downloads/gems88-mdps88-mix-29742dots-20261024-zeros-DO-NOT-SUBMIT.zip)
- Run card: [run card](data/mdps88_run_card.json) · Gate record: [`data/mdps88-gate.json`](data/mdps88-gate.json)
- Independent audit: [`data/mdps88_validation.json`](data/mdps88_validation.json) (`scripts/validate_mdps88.py`; `--require-submit` exits 2)
- TIFF SHA-256: `bd64000f96e96f09202d61027fb5ef45cff53baed7591279cc7e971ba1e835cd`
- **HOLDOUT-DTI (`gems57-pooled-hide-v2`, far primary, 10,791 withheld positives):** candidate 0.0727 [95% CI 0.0591, 0.0863]; fold-fair control 0.0691 [95% CI 0.0569, 0.0813]; paired Δ +0.0036 [95% CI −0.0060, +0.0128] (crosses 0). **Overall HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 22,893 withheld positives): candidate 0.0667 [95% CI 0.0551, 0.0784] vs control 0.1085 [95% CI 0.0949, 0.1211].
- **Uniqueness:** **FAIL under the literal lane rule**: final-dot overlap is 1.0 with the positive-everywhere `17GEMSDOE` witness (limit 0.70; no dense-prior exemption). Separate, non-binding v3 sparse/like-for-like diagnostics are worst excess 3 px overlap 0.226 and worst surface |Spearman| 0.106 over 44 restored/tracked priors.
- **Format:** all-finite [0,1] float32, sample CRS/shape/transform, one-member ZIP byte-identical. Local validity, not organizer acceptance.
- **Name (archival only):** `GEMSDOE88-MDPS88-MIX-20261024`
- **Note (archival only, 106/140):** `MDPS-88 matched-domain physics mix, 29742 dots; HOLDOUT far 0.0727 overall 0.0667; UNSCORED; DO NOT SUBMIT`

Do not upload MDPS-88. The name/note are retained for audit only. The legacy `current_release.json` compatibility record (PHASE-88, sha256 `28e6e912…324b`) is likewise **DO NOT SUBMIT** (HOLDOUT-DTI 0.0531; literal overlap 0.9090/1.0 — see `data/phase88_validation.json`).

## Why a previous upload attempt returned “Predicted values must be in range [0, 1]”

NaN-outside-footprint files (or nodata sentinels like −9999) put non-finite/out-of-range cells in the raster. Files published here use the strict zeros encoding: every cell finite, values in [0,1], 0 outside the footprint, nodata unset — verified on written bytes (min 0.0, max 1.0).

## Procedure for a future, separately authorized candidate

1. Require the candidate's run card `ok_to_submit: true` (all gates) and its validator `--require-submit` exit 0, with TIFF SHA-256 matching the card.
2. Obtain separate human selector authorization; confirm the live weekly limit on the portal.
3. Sign in at the [official DrivenData submissions page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/); upload only the approved single-band TIFF or one-TIFF ZIP; enter its unique name and ≤140-character note.
4. Archive the portal receipt; label a score `ORGANIZER-CONFIRMED` only when copied from it.

Official sources: [metric & format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [INGENIOUS](https://gbcge.org/current-projects/ingenious/) · [EPSG:32611](https://epsg.io/32611)

## Recheck commands

```bash
python scripts/restore_inputs.py
.venv/bin/python scripts/validate_mdps88.py
.venv/bin/python scripts/validate_mdps88.py --require-submit  # expected exit 2 for MDPS-88
.venv/bin/python scripts/check_site.py
```
