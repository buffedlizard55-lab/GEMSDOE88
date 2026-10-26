# Submission decision — DO NOT SUBMIT (2026-10-25, updated session 587c7f22)

> **Historical CON88 clearance is withdrawn (`IR-88-96F5F523-01` / `IR-88-3C391D97-01` / `IR-88-587C7F22-01`).** The binding current preflight is `DUPLICATE_STOP`; no TIFF is currently cleared to submit. CON88 has been archived with unchanged GeoTIFF bytes under `-DO-NOT-SUBMIT` (`ok_to_submit: false`, `verdict: "negative"`). See [`docs/status.json`](status.json), [`data/con88_clearance_withdrawal_20261025.json`](data/con88_clearance_withdrawal_20261025.json), and the latest negative run card [`data/session_587c7f22_run_card.json`](data/session_587c7f22_run_card.json).

> Historical decision record for the lanes listed here. This repository's **current**
> decision is **`DUPLICATE_STOP` (`ok_to_submit: false`, `verdict: "negative"`, `0` protocol-eligible packages)**,
> computed in the [executive summary](executive-summary.html), [`data/current_release.json`](data/current_release.json),
> and [README.md](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/README.md) (`H88-SDTL` clearance was withdrawn in `IR-88-B4DFA10C-08` and `H88-CON88` clearance was withdrawn in `IR-88-96F5F523-01` / `IR-88-3C391D97-01` / `IR-88-587C7F22-01`; nothing in this file authorizes upload).

**No new TIFF is eligible, and no competition slot was used by this session.** The primary [submission guide](executive-summary.html) and [canonical manifest](data/current_release.json) are authoritative. The [existing TDKL research TIFF](downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif) and [single-TIFF ZIP](downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip) are downloadable for education only; neither is a new or protocol-unique prediction.

- Automated saved-byte audit: **50/50** published Pages TIFF/ZIP pairs (`47` main downloads in `docs/downloads/` + `1` historical variant in `docs/research-variants/`, **`0` protocol-eligible** — `H88-CON88` upload clearance withdrawn in `IR-88-96F5F523-01` / `IR-88-3C391D97-01` / `IR-88-587C7F22-01` and renamed to `gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif` / `.zip`; see [con88.html](con88.html) and caveat `IR-88-21256734-06` noting `HOLDOUT-DTI = 0.0017` vs `0.205991` `BPWD`; all `48/48` lanes remain `ok_to_submit: false`) plus **20/20** repo-side `submissions/` archives pass two independent decoders, finite/`[0,1]`, exact grid, footprint/catalogue masks and extraction labels (`IR-88-838C-01`, `IR-88-838C-02`). [Full audit](data/download_audit.json).
- **Critical legacy `releases/` safety warning (`IR-88-21256734-05`):** Never upload any of the `6` legacy `HOLD` `releases/h33-h33-2-b2-MASS*` artifacts — `3` non-`-zeros` files lack `-DO-NOT-SUBMIT` in their filenames AND contain `7,111,787` exterior `NaN`s (`nodata=NaN`), reproducing the `"Predicted values must be in range [0, 1]"` portal rejection class.
- Parallel three-pass review `f9a92cf6`: [review report](research/session-arena-f9a92cf6-review-20261025.md) · [negative run card](data/session_f9a92cf6_run_card.json); final integrated suite **911 passed / 23 skipped**; no candidate or slot.
- Session 587c7f22 integrated parallel CON88 withdrawal, hardened `run_con88_experiment.py` and `run_con88_exp3_margin.py` (`97/97` candidate entrypoints guarded by `enforce_generation_preflight()`), repaired broken unmarked download links in root `index.html`, retired `H88-CON88` in `hypothesis_queue.json`, and published [five ranked untried geological hypotheses](research/session-587c7f22-hypotheses.md) and [three-pass PhD H33 review](research/session-587c7f22-review.md) ([negative run card](data/session_587c7f22_run_card.json)). Zero rasters generated; zero slots spent.
- Session 21256734 re-verified preflight (`DUPLICATE_STOP`, exit 2 on `17GEMSDOE`), hardened `8` validator/audit/forensics scripts (`124` bare `assert`s replaced with `-O`-safe `_require(...)` + SHA-256 input pins; `IR-88-21256734-01`, `IR-88-21256734-02`), refreshed the [live 50-row official leaderboard snapshot (`#8 DARD = 0.3398`)](data/leaderboard_official_snapshot_21256734_20261025.json), screened sibling fleets (`GEMSDOE86/91/92`) + concurrent `PGTD`/`CON88` merges (`IR-88-21256734-04`, `IR-88-21256734-06`), and published [five cross-fleet-screened geological hypotheses (`H88-ACDR..H88-OPERA-INSAR`)](research/session-21256734-hypotheses.md) and [three-pass PhD-level `H33` review](research/session-21256734-review.md) ([negative run card](data/session_21256734_run_card.json)). Zero rasters generated; zero slots spent.
- Current inventory earlier updated by session 693b10af after the peer PGTD merge; its CLI guard bypass is revoked and tensor family retired. The 838cc402 access/repair claims below are that parallel session’s historical scope.
- Session 838cc402 re-verified preflight (`DUPLICATE_STOP`, exit 2 on `17GEMSDOE`), repaired the post-PR-#152 withdrawn-SDTL-lane and stale package-count merge regression in this file plus the overlooked `submissions/gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.zip` extraction member, verified official primary sources live, and published [five untried post-MMRX geological hypotheses](research/session-838cc402-hypotheses.md) and [three-pass review](research/session-838cc402-review.md) ([negative run card](data/session_838cc402_run_card.json)). Zero rasters generated; zero slots spent.
- Session 249e8cb3 executed the former rank-1 hypothesis (`H88-MMRX` marker restoration): HOLDOUT-DTI `0.188378 [0.170922, 0.204215]` vs the `0.205991` bar, 0/8 folds won, and final-dot overlap `0.797578` vs H88-HGVC — negative; published repo-side in `submissions/` with `-DO-NOT-SUBMIT`, not added to this site's downloads. Zero slots spent.
- Literal prerequisite: `17GEMSDOE` directly covers every one of 5,106,385 allowed pixels; every nonempty allowed candidate has overlap 1.0 > 0.70. **STOP before generation.**
- The old `[0,1]` error is addressed locally by validation of strict finite zero-outside files, not by claiming portal acceptance. Its exact historical upload failure cannot be diagnosed without the uploaded bytes/receipt.
- All validation is automated; no manual TIFF inspection is needed. A future eligible file would still require fold-rebuilt holdout superiority, complete registry checks and a separate selector within the actual authenticated account cap. No fresh cap or official receipt was obtained here.
- Reproduce locally: `python scripts/audit_downloads.py --check`, `python scripts/render_decision.py --check`, `python -O scripts/check_site.py`. Candidate CLIs stop via the existing shared preflight; there is no override switch.

**Unique new submission requirement: UNMET.** See [review and ordered next steps](research/session-d0c3adeb-review.md) and the [H88-MMRX session review](research/review-249e8cb3-mmrx88-20261025.md).

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
