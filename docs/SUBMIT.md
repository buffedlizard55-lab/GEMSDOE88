# Competition submission guide (current decision: DO NOT SUBMIT)

**Canonical candidate: H88-TDKL. Research download: YES. Competition submission: NO.** The machine-readable decision is [`data/current_release.json`](data/current_release.json); no weekly slot was used and no `ORGANIZER-CONFIRMED` candidate score exists.

- GeoTIFF: [`gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif`](downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif)
- Single-TIFF ZIP: [`gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip`](downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip)
- Run card: [`data/tdkl88_run_card.json`](data/tdkl88_run_card.json) · Gate: [`data/tdkl88_gate_verdict.json`](data/tdkl88_gate_verdict.json)
- TIFF SHA-256: `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`
- **HOLDOUT-DTI:** 0.196237 [0.179686, 0.211729], 22,893 withheld positives, evaluator `gems57-pooled-hide-v2`; paired delta over ADHR +0.005801 [0.001174, 0.010109].
- **Canaries:** 56/56 pass; maximum symmetric AUC 0.59299 ≤ 0.90.
- **Format:** one float32 band, all 12,279,160 values finite in [0,1], EPSG:32611, shape 3730×3292, exact sample transform, 0 outside footprint, 25,000 positive pixels.
- **Binding stop:** literal 3-pixel overlap 1.0000 against the full-footprint 17GEMSDOE witness; post-merge overlap 0.762280 vs GTHC-88 and 0.752000 vs QTSK-88. Both exceed 0.70.
- **Prepared name:** `GEMSDOE88-TDKL88-POE-20261024`
- **Prepared note (110/140):** `H88-TDKL 79ch knickpoint+LiDAR polarity PoE (25000 dots); HOLDOUT-DTI 0.1962 far 0.1242 blind 0.0769; UNSCORED`

The TIFF is a distinct research artifact, but it is **not an eligible submission under the supplied literal overlap protocol**. Do not upload it. A unique hash or filename does not override a failed scientific gate.

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
python3 scripts/validate_dhtc88.py
python3 scripts/validate_dhtc88.py --require-submit  # expected exit 2
python scripts/check_site.py
```
