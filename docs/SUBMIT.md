# Competition submission guide — current decision: **DO NOT SUBMIT**

> **MRR-COH-88 — DOWNLOAD FOR RESEARCH: YES. OK TO SUBMIT: NO.**
>
> The file is genuinely new, format-valid, and unique under the preregistered expanded-registry policy. It is blocked because HOLDOUT-DTI `0.07700055` is below the same-split stored best `0.18788764`. No weekly slot was used and no `ORGANIZER-CONFIRMED` score exists.

## Current research artifact

- GeoTIFF: [`gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.tif`](downloads/gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.tif)
- One-TIFF ZIP: [`gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.zip`](downloads/gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.zip)
- Web run card: [`data/mrrcoh88_run_card.json`](data/mrrcoh88_run_card.json)
- TIFF SHA-256: `98d8ecc539af4d1743b480c9fe1fc9165488076ba61fa82be4ee9fa2ccea0e24`
- ZIP SHA-256: `37959f896f95511a66241b0fe0a34c854bed203426be021bcd4624f0b7c02d7e`
- Positive pixels: `43,173`
- **HOLDOUT-DTI:** `0.07700055`, 95% CI `[0.06912859, 0.08486633]`, 22,893 withheld positives, evaluator `gems57-pooled-hide-v2`
- **Same-split stored best:** `0.18788764`, 95% CI `[0.17169765, 0.20326012]`
- **Uniqueness:** pre-placement max `|Spearman ρ| = 0.18358174`; final max dot-field overlap within 3 px `0.45873578`; final max excess overlap `0.13015695`; 224 registry rasters checked; no identical file or decoded prediction
- **Format:** finite single-band float32 GeoTIFF in `[0,1]`, pinned sample grid, and ZIP with one byte-identical TIFF; independently reopened from disk
- **Archival name only:** `GEMSDOE88-MRRCOH-5FE6CDD8982F`
- **Archival note only (74/140):** `MRR coherence OOF, 43173 dots; HOLDOUT-DTI 0.0770; UNSCORED; DO NOT SUBMIT`

Do not upload either file. The name and note preserve traceability; they are not authorization.

## Procedure for a future separately authorized candidate

1. Reread `PROMPT.md`; restore and SHA-verify only authorized inputs.
2. Run the current candidate's scientific, leakage, uniqueness, format, site, and readiness checks.
3. Require `python scripts/validate_current.py --require-submit` to exit 0 and match the candidate TIFF hash. It intentionally exits 2 for MRR-COH-88.
4. Obtain a separate portfolio-selector decision and verify the live weekly-slot limit.
5. Sign in to the team account and open the [official submissions page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/).
6. Upload only the selector-cleared single-TIFF archive. Enter the exact approved name and a note of at most 140 characters.
7. Wait for organizer processing. Do not describe queued or failed work as submitted or scored.
8. Save the organizer receipt: submission ID, UTC timestamp, artifact SHA-256, final status, and public/private score if supplied. Label a value `ORGANIZER-CONFIRMED` only from this evidence.

The live [problem/metric/format page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) are binding. Local checks cannot establish organizer acceptance.

## Recheck commands

```bash
python scripts/restore_inputs.py --validation
python scripts/validate_current.py
python scripts/readiness.py
python scripts/check_site.py
python scripts/validate_current.py --require-submit  # expected exit 2 for MRR-COH-88
```
