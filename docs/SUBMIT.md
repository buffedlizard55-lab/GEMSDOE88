# Competition submission guide (current decision: DO NOT SUBMIT)

**Current status:** the fabric-dislocation GeoTIFF is **OK TO DOWNLOAD FOR RESEARCH**, but **NOT OK TO SUBMIT**. It loses to the stored holdout best and fails the strict registry-overlap gate. No weekly slot has been used, and there is no ORGANIZER-CONFIRMED score.

- TIFF: [`gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif`](downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif)
- Single-TIFF ZIP: [`gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.zip`](downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.zip)
- Run card: [`fabric_dislocation_run_card.json`](data/fabric_dislocation_run_card.json)
- TIFF SHA-256: `1bbb20e60ce5633a979e2bea8e1216105325b78c4ca93ca4380ea3f533e774ae`
- **HOLDOUT-DTI:** 0.062936, evaluator `gems57-pooled-hide-v2`, 22,893 withheld positives, 95% CI [0.054201, 0.072122].
- **Uniqueness:** the final dots have 3-pixel overlap 1.0 against the dense 17GEMSDOE witness; the allowed maximum is 0.70. The literal rule cannot be met by any nonempty prediction while that all-positive witness remains in scope.
- **Format:** independent audit passes: one float32 band, exact sample CRS/shape/transform, all finite, values in [0,1], no NaN inside footprint, no mass outside. This is a format pass only.

Do not upload this file. The name and note below are archival identifiers, not upload authorization:

- Name: `GEMSDOE88-FABDIS-621B097B-DO-NOT-SUBMIT`
- Note: `FAB88 RTP fabric-dislocation research raster; HOLDOUT-DTI 0.062936; 22,893 positives; DO NOT SUBMIT`

## Procedure for a future approved raster

Only use a file whose latest machine run card says it passed every required research gate and whose separate selector has chosen to spend a slot. The project does not select or upload submissions.

1. Run the repo's site, readiness, and current-file checks. Require the exact validated TIFF SHA-256 to match the run card.
2. Download the single TIFF, or the ZIP containing exactly that TIFF.
3. Sign in to the team account and open the [official DrivenData submissions page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/).
4. Select **New submission**, upload the TIFF or one-TIFF ZIP, enter that candidate's unique name and a note of at most 140 characters, then submit only if a separate selector has authorized the slot.
5. Archive the portal receipt and label the score **ORGANIZER-CONFIRMED** only when copied from that receipt.

The official format requires a single-band float32 prediction raster on the training grid (EPSG:32611, 100 m, matching bounds) with values in [0,1]. See the [official problem/metric/format page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf). The automated local gate does not log in or submit on a user's behalf.

## Recheck commands

```bash
python scripts/check_site.py
python scripts/readiness.py
python scripts/validate_current.py
python scripts/validate_current.py --require-submit  # expected exit 2 today
```
