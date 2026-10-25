# Submission decision — DO NOT SUBMIT (2026-10-25, IR-88-0AB98CD1-01)

> **CURRENT DECISION: `DUPLICATE_STOP` · `ok_to_submit: false` · `verdict: "negative"`.**
> There is no competition-eligible file in this repository and no weekly slot was used.

The former H88-CON88 equal-support clearance is withdrawn. The user-required rule is literal:
stop when more than 70% of final dots are within 3 pixels of **any** registry raster. The SHA-pinned
17GEMSDOE support covers every allowed pixel, making CON88 overlap `1.0 > 0.70`. CON88 also does
not beat the scientific promotion bar (historical per-fold re-emission HOLDOUT-DTI `0.001714`
versus incumbent `0.205991`). A local format pass cannot override either failure. The earlier shared literal correction
`IR-88-B4DFA10C-08` remains in force; this CON88 correction closes the later exception.

## One-click research archive — unsafe to submit

- [H88-CON88 research TIFF — **DO NOT SUBMIT**](downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif)
- [One-TIFF research ZIP — **DO NOT SUBMIT**](downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.zip)
- [Corrected CON88 decision page](con88.html) · [Executive submission guide](executive-summary.html)
- Archived name: `GEMSDOE88-CON88-E830B58E-DO-NOT-SUBMIT`
- Research note (101/140): `H88-CON88 archived research; literal overlap 1.0 and HOLDOUT-DTI 0.0017 fail promotion; DO NOT SUBMIT`
- TIFF SHA-256 (unchanged): `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`

Automated saved-byte audit: **48/48** published Pages TIFF/ZIP pairs (`47` main downloads + `1`
historical variant) pass local research-package checks; **0** are protocol-eligible. All served TIFF and
ZIP names carry `DO-NOT-SUBMIT`, and each ZIP contains one byte-identical, negatively named TIFF.
See the [full audit](data/download_audit.json). The separate repo-side `submissions/` archive remains
negative research as well.

**Unique new submission requirement: UNMET.** No new TIFF, geological experiment, holdout, organizer
receipt, or slot use occurred in the corrective review. Conditional proposals H88-SPR, H88-AWA and
H88-CBC remain stopped before feature construction. See the
[current review](research/session-0ab98cd1-review.md) and
[negative run card](data/session_0ab98cd1_run_card.json).

<details>
<summary>Earlier session records — historical, not current authorization</summary>

# Competition submission guide (current decision: DO NOT SUBMIT)

**Latest evaluated lane: H88-HGVC (5/5 discriminating screens PASS, `HOLDOUT-DTI = 0.202947`, `8/8` folds won; held fail-closed under literal `17GEMSDOE` dense witness — `DO NOT SUBMIT`, `0` weekly slots spent).**
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
.venv/bin/python scripts/validate_hgvc88.py
.venv/bin/python scripts/validate_hgvc88.py --require-submit  # expected exit 2
python3 scripts/validate_dhtc88.py
python3 scripts/validate_dhtc88.py --require-submit  # expected exit 2
python scripts/check_site.py
```


</details>
