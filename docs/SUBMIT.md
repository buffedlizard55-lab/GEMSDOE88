# Submission decision — NO SUBMISSION-READY GEOTIFF (updated 2026-10-25)

**Readiness: NO SUBMISSION-READY GEOTIFF. Do not submit or spend a slot.** No candidate was generated in this review. The canonical [current-release manifest](data/current_release.json) points to the archived H88-TDKL research artifact only; it is format-valid but fails the binding literal uniqueness rule. No organizer receipt or weekly-slot approval exists.

- Automated saved-byte audit: **43/43** TIFF/ZIP packages pass local research-format checks; **0** are protocol-eligible under the current literal uniqueness rule. These checks cover local decoding, finite/[0,1] values, grid, and package integrity; they do not establish organizer acceptance. [Full audit](data/download_audit.json).
- Literal prerequisite: `17GEMSDOE` directly covers every one of 5,106,385 allowed pixels; every nonempty allowed candidate has overlap 1.0 > 0.70. **STOP before generation.**
- The reported historical `[0,1]` error is not an authorization to rename or upload an archived candidate. Local format validation does not diagnose an absent portal receipt or override duplicate-stop policy.
- All validation is automated; no manual TIFF inspection is needed. A future eligible file would still require fold-rebuilt holdout superiority, complete registry checks and a separate selector within the actual authenticated account cap. No fresh cap or official receipt was obtained here.
- Reproduce locally: `python scripts/audit_downloads.py --check`, `python scripts/render_decision.py --check`, `python -O scripts/check_site.py`. Candidate CLIs stop via the existing shared preflight; there is no override switch.

**Unique new submission requirement: UNMET.** See the [current review and ordered next steps](research/repo-review-dea470d9-20261025.md).

<details>
<summary>Earlier session records — historical, not current authorization</summary>

# Archived competition submission guide — not current authorization

**Historical H88-HGVC result:** `HOLDOUT-DTI = 0.202947` on its saved split; no slot was used. The old v4 “OK TO DOWNLOAD AND SUBMIT” claim and local rename/upload instructions are **REVOKED** by the binding literal-rule review. No artifact in this archive is cleared for submission.
- H88-HGVC research TIFF (archive only — DO NOT SUBMIT): [`gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif`](downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: d5329f317682ba3ea15eba32aebe9a2000fc0e42cedfd20a36caae03ef3012ef`)
- H88-HGVC Single-TIFF ZIP: [`gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.zip`](downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.zip) (`SHA-256: 5ef9ebf2ff386fc75bd2e5018c2c680f3ac083cb0dea3a08f0140e5c85d9e409`)
- H88-HGVC Run card: [`data/hgvc88_run_card.json`](data/hgvc88_run_card.json) · Gate v3: [`data/hgvc88_gate_v3.json`](data/hgvc88_gate_v3.json)
- Historical suggested name/note in the old gate are retained as audit metadata only; do not paste them into the portal.

**Canonical archived research artifact: H88-TDKL. Research download: YES. Competition submission: NO.** The machine-readable record is [`data/current_release.json`](data/current_release.json); no weekly slot was used and no `ORGANIZER-CONFIRMED` candidate score exists.

- GeoTIFF: [`gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif`](downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif)
- Single-TIFF ZIP: [`gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip`](downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip)
- Run card: [`data/tdkl88_run_card.json`](data/tdkl88_run_card.json) · Gate: [`data/tdkl88_gate_verdict.json`](data/tdkl88_gate_verdict.json)
- TIFF SHA-256: `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`
- **HOLDOUT-DTI:** 0.196237 [0.179686, 0.211729], 22,893 withheld positives, evaluator `gems57-pooled-hide-v2`; paired delta over ADHR +0.005801 [0.001174, 0.010109].
- **Canaries:** 56/56 pass; maximum symmetric AUC 0.59299 ≤ 0.90.
- **Format:** one float32 band, all 12,279,160 values finite in [0,1], EPSG:32611, shape 3730×3292, exact sample transform, 0 outside footprint, 25,000 positive pixels.
- **Binding stop:** literal 3-pixel overlap 1.0000 against the full-footprint 17GEMSDOE witness; post-merge overlap 0.762280 vs GTHC-88 and 0.752000 vs QTSK-88. Both exceed 0.70.
- Historical suggested name/note are retained as audit metadata only; do not use them as authorization to submit.

The TIFF is a distinct historical research artifact, but it is **not an eligible submission under the supplied literal overlap protocol**. Do not upload it. A unique hash or filename does not override a failed scientific gate. The archived procedure/name/note below is not current slot authorization.

## Why an earlier upload returned “Predicted values must be in range [0, 1]”

NaN-outside-footprint files and nodata sentinels can violate the portal range check. This frozen TDKL file uses strict zero encoding: every cell is finite, values are exactly 0 or 1, nodata is unset, and outside-footprint cells are 0. This fixes format only; it does not override the uniqueness stop.

## Procedure for a future green candidate

1. Require its run card to say `ok_to_submit: true` and its validator with `--require-submit` to exit 0.
2. Verify the downloaded SHA-256 exactly matches the card; require one band and sample CRS, shape, and transform.
3. Confirm a separate selector authorizes use of a weekly slot and the portal currently permits one.
4. Upload the approved TIFF or one-TIFF ZIP at the [official DrivenData submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/), then paste the approved name and ≤140-character note.
5. Archive the receipt. Label a score `ORGANIZER-CONFIRMED` only when copied from that receipt.

Official review links: [metric and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)

## Autonomous recheck

```bash
python scripts/restore_inputs.py --validation
.venv/bin/python scripts/validate_hgvc88.py
.venv/bin/python scripts/validate_hgvc88.py --require-submit  # expected exit 2
python3 scripts/validate_dhtc88.py
python3 scripts/validate_dhtc88.py --require-submit  # expected exit 2
python scripts/check_site.py
```


</details>
