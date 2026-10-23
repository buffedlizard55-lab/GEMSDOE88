# Submission checklist — human uploads ONE per slot (DrivenData form)

> **Nothing here is `ok_to_submit: true`.** The three MASS variants are `BUILT`, reconstruct bit-exactly from their recorded recipe, and pass every *competition* format check (EPSG:32611, 3730×3292, float32, single band, values in [0,1], no NaN inside the footprint, 0 mass on the catalogue, ≥2 px collar, transform identical to `sample_submission.tif`). They remain blocked under this repo's unamended literal registry rule (space-covering calibration witnesses), which is a **project-internal** gate, not an organiser one.
>
> **Upload the `-zeros` twin, not the NaN primary.** The repo's own preflight (`vendor/gems57/gates.py`) enforces a stricter all-finite export policy and fails the NaN file; the same content exported as `-zeros` passes both that preflight and the organiser spec, and the ledger records that NaN-outside and zeros-outside twins score identically live. See IR-88-20.
>
> **Uniqueness note, corrected.** Against the 62 locally pinned priors, max 3-px forward dot overlap is 1.0000 and 50 priors exceed 0.70. This is expected and uninformative: every variant of R0 is by construction within one 2-px dot spacing of R0 itself, and the dense witness is positive over the whole footprint. Brief §6 says not to gate on dot overlap, and this session does not. The earlier claim in this file that the candidates "pass like-for-like uniqueness against 134/134 genuine fault rasters" could not be reproduced for these three files and has been removed.

## Slot 1 — RECOMMENDED: `MASSm10minus` (collar extension)

- **File to upload (zeros outside):** `releases/h33-h33-2-b2-MASSm10minus-20261023-7132935e-zeros.tif` — sha256 `58d9ebdbdd9234d5bbe8e248c1b385d7b7ffb03461c94f9624c2eb02d13ac412`
- **NaN-outside twin (organiser spec; fails this repo's preflight):** `releases/h33-h33-2-b2-MASSm10minus-20261023-7132935e.tif` — sha256 `7132935e1210208cfbc5dc02d0d393816b7e6b35a706fce44020a3513b7fa201`
- **Submission name:** `h33-h33-2-b2-MASSm10minus-20261023-7132935e`
- **Note (≤140):** `h33-2-b2 33889 dots, collar cut 2->10px vs catalogue; pred +0.004 MODEL; parent 0.2778 CLAIM`
- **What it tests:** whether the 2–10 px collar is mostly false-positive mass, continuing the one direction that ever gained live (0.2708→0.2778 after deleting dots within 2 px).
- **Predicted:** +0.004 MODEL, range [-0.006, +0.014]. Break-even credit 0.0556 (unseen truth within 2.83 px).
- **Format receipt:** 1 band, float32, EPSG:32611, 3730×3292, `Affine(100, 0, 243350, 0, -100, 4508550)`, values {0,1}, 33,889 positive pixels, 0 NaN inside the footprint, finite everywhere, 0 outside the footprint, 0 on the catalogue, minimum distance to catalogue 2.236 px. Re-read from disk after writing.

## Held — do not submit this week

**`MASSm10plus`** (41,419 dots). Predicted **-0.010** MODEL [-0.014, +0.002]. The 3,765 added dots are 85.2% isolated (>3 px from any parent dot), mean 20.6 px from the nearest parent dot, and have mean independent prior 0.119 against 0.400 for the parent — the lowest-prior, most isolated positions available. Each pays only if unseen truth lies within 2.83 px. Spending a slot here would re-learn that unsupported mass costs score, which the ledger already establishes across files scoring 0.00–0.19. Files exist (`…82673b57.tif`, `…82673b57-zeros.tif`) if the human overrules this.

**`MASSm20minus`** (30,123 dots). Predicted **+0.001** MODEL [-0.015, +0.017]. It is the same ranking cut deeper than m10minus, so it is not an independent read; grade the pair only if both go out, and expect a monotonicity check, not two independent scores.

## Validation steps (human, from own authenticated account)

1. `python scripts/restore_inputs.py --validation` — all six mirror groups verify; R0 rebuilds to `c55bafc4…`.
2. `python -m pytest -q` — 77 tests green, including `tests/test_mass_ranking.py`, which fails if the shipped files stop matching their recorded recipe.
3. `python scripts/audit_mass_ranking.py` — reprints every number behind the predictions.
4. Re-open the chosen file in QGIS/GDAL: `gdalinfo -stats` should show `Min=0 Max=1`, `Band 1 Type=Float32`, `Size is 3292, 3730`.
5. Upload **ONE** file per slot, paste the receipt timestamp/id/score verbatim into `ledger/submissions.csv` as `receipt_score` / date, and mark it RECEIPT.

> Irregularities: see `IRREGULARITIES.md` (IR-88-17…21 are the decision-changing ones from this session). Generative-AI disclosure per NLR Rules §3.6 lives in `AI_USE.md`.
