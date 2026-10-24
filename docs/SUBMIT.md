# Competition submission guide (current decision: DO NOT SUBMIT)

**Current candidate: KTH-88. Research download: YES. Competition submission: NO. File to submit: NONE. DO NOT SUBMIT KTH-88.** Its holdout is far below the stored comparable incumbent and the literal registry-overlap rule fails. No weekly slot has been used; no `ORGANIZER-CONFIRMED` score exists.

- GeoTIFF: [`gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`](downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif)
- Single-TIFF ZIP: [`gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.zip`](downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.zip)
- Run card: [`../registry/kth88_run_card.json`](../registry/kth88_run_card.json)
- Independent TIFF/ZIP audit: [`data/kth88_validation.json`](data/kth88_validation.json)
- TIFF SHA-256: `5c7f1cb7a8c37bb4c7f3ba6eef2d42f472a050c6b21436274e4ebc0c259fd7bf`
- **HOLDOUT-DTI:** 0.052656, evaluator `gems57-pooled-hide-v2`, 22,893 withheld positive pixels, 95% CI [0.045911, 0.059151]. Same-split incumbent: 0.187888; no paired improvement CI is available.
- **Uniqueness:** final 3-pixel overlap is 0.89882 with a GEMSDOE87 raster and 1.000 with the dense 17GEMSDOE witness; maximum allowed is 0.70. Do not reinterpret this as unique because the file bytes differ.
- **Format:** the saved independent audit reports matching sample-grid metadata, finite float32 values in [0,1], and exact one-member ZIP bytes. The official sample is absent from this checkout, so this follow-up could not rerun the grid comparison. This is local format evidence, not organizer acceptance or slot approval.
- **Name (archival only):** `GEMSDOE88-KTH-BACDC27B`
- **Note (archival only, 105/140):** `K/Th antisymmetric radiometric step + RTP trough, 37654 dots; HOLDOUT-DTI 0.0527; UNSCORED; DO NOT SUBMIT`

Do not upload KTH-88. The submission identifier and note are retained for audit only, not authorization. The K/Th data are uncalibrated indices, not measured elemental abundance. No organizer receipt exists.

## Procedure for a future, separately authorized candidate

Only use a file whose latest run card passes every required scientific, uniqueness, leakage, and format gate, and whose separate portfolio selector authorizes a slot. This repository does not choose a slot or upload on a user's behalf.

1. Restore only authorized, hash-pinned inputs; reread `PROMPT.md` and verify one method lane is explicitly selected.
2. Run the site, readiness, candidate, and current-release validators. Require the **current candidate's** `--require-submit` check to exit 0 and match its TIFF SHA-256 to its run card.
3. Separately obtain selector authorization and confirm the live weekly limit.
4. Sign in to the team account and use the [official DrivenData submissions page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/). Upload only the approved single-band TIFF or one-TIFF ZIP, enter its unique name and note (at most 140 characters), and submit only with authorization.
5. Archive the portal receipt. Label a score `ORGANIZER-CONFIRMED` only when copied from that receipt.

The official problem page defines the submission grid and [metric/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/); use the current [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) and live portal for binding requirements. Local validation cannot authenticate to the portal.

## Recheck commands

```bash
# Needs the authorized, hash-pinned sample at data/bridge/sample_submission.tif;
# it is absent in this checkout, so these two KTH-88 checks cannot currently finish.
python scripts/restore_inputs.py --validation  # only if this mirror is authorized for your use
python scripts/check_site.py
python scripts/validate_kth88.py
python scripts/validate_kth88.py --require-submit  # with inputs restored, the negative gate exits 2
python scripts/readiness.py
python scripts/validate_current.py
python scripts/validate_current.py --require-submit  # expected exit 2 today
```
