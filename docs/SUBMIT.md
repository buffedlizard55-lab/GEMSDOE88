# Competition submission guide (current decision: DO NOT SUBMIT)

**Latest evaluated lane (`2026-10-25`): H88-PSGV (5/5 discriminating screens PASS, new all-time repo record `HOLDOUT-DTI = 0.204711`, `8/8` folds won vs `ADHR`, `6/8` vs `HGVC`, `350`-raster like-for-like unique `0.6321 <= 0.70`; held fail-closed under literal `17GEMSDOE` dense witness — `DO NOT SUBMIT`, `0` weekly slots spent).**
- H88-PSGV GeoTIFF: [`gems88-psgv88-baranov-spectral-conduit-37654-20261025-19f22812-zeros-DO-NOT-SUBMIT.tif`](downloads/gems88-psgv88-baranov-spectral-conduit-37654-20261025-19f22812-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: 19f22812894cd8b2498851846525d6d76caf7f87a40f59309ef74ca693f23b45`)
- H88-PSGV Single-TIFF ZIP: [`gems88-psgv88-baranov-spectral-conduit-37654-20261025-19f22812-zeros-DO-NOT-SUBMIT.zip`](downloads/gems88-psgv88-baranov-spectral-conduit-37654-20261025-19f22812-zeros-DO-NOT-SUBMIT.zip) (`SHA-256: 884f3a52e6cea1a88f830815b1ef495143e328f2d22985334d6e05cd75600478`)
- H88-PSGV Run card: [`data/psgv88_run_card.json`](data/psgv88_run_card.json) · Gate v3: [`data/psgv88_gate_v3.json`](data/psgv88_gate_v3.json)
- Prepared Name (`25/140`): `GEMSDOE88-PSGV88-19F22812` · Prepared Note (`114/140`): `PSGV88 107ch Baranov spectral+hydrothermal 3-Spec PoE 37654d; HOLDOUT-DTI 0.2047 far 0.1342 blind 0.0763; UNSCORED`

**Prior record lane (`2026-10-24`): H88-HGVC (5/5 discriminating screens PASS, `HOLDOUT-DTI = 0.202947`, `8/8` folds won; held fail-closed under literal `17GEMSDOE` dense witness — `DO NOT SUBMIT`, `0` weekly slots spent).**
- H88-HGVC GeoTIFF: [`gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif`](downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: d5329f317682ba3ea15eba32aebe9a2000fc0e42cedfd20a36caae03ef3012ef`)
- H88-HGVC Single-TIFF ZIP: [`gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.zip`](downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.zip) (`SHA-256: 5ef9ebf2ff386fc75bd2e5018c2c680f3ac083cb0dea3a08f0140e5c85d9e409`)
- H88-HGVC Run card: [`data/hgvc88_run_card.json`](data/hgvc88_run_card.json) · Gate v3: [`data/hgvc88_gate_v3.json`](data/hgvc88_gate_v3.json)
- Prepared Name (`25/140`): `GEMSDOE88-HGVC88-D5329F31` · Prepared Note (`103/140`): `HGVC88 87ch hydrothermal up-dip+sinter PoE 37654d; HOLDOUT-DTI 0.2029 far 0.1328 blind 0.0790; UNSCORED`

**Canonical archived candidate: H88-TDKL. Research download: YES. Competition submission: NO.** The machine-readable decision is [`data/current_release.json`](data/current_release.json); no weekly slot was used and no `ORGANIZER-CONFIRMED` candidate score exists.

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
.venv/bin/python scripts/validate_psgv88.py
.venv/bin/python scripts/validate_psgv88.py --require-submit  # expected exit 2
.venv/bin/python scripts/validate_hgvc88.py
.venv/bin/python scripts/validate_hgvc88.py --require-submit  # expected exit 2
python3 scripts/validate_dhtc88.py
python3 scripts/validate_dhtc88.py --require-submit  # expected exit 2
python scripts/check_site.py
```
