# GEMSDOE88 — Session `6236446d` review (2026-10-30)

> **SUBMISSION DECISION: NO FILE TO DOWNLOAD OR SUBMIT.** No new TIFF was generated. The shared generation guard returns `DUPLICATE_STOP` (exit `2`) on the restored, SHA-pinned inputs. Every TIFF in the repo is `DO-NOT-SUBMIT`. `ok_to_submit: false`, `0` experiments, `0` of `3` weekly slots used.
>
> The user's "unique TIF, must submit" requirement cannot be met inside the protocol the user set. The blocker is explained below in IR-6236446D-01. It is a protocol question for the user to decide, not something to route around.

## 1. Bottom line (answers, in order)

| Question | Answer | Evidence class |
|---|---|---|
| Can a unique TIF be generated and cleared? | **No.** The guard stops before features, fitting, or writing. | REGISTRY-MEASUREMENT |
| Is any existing file OK to download and submit? | **No.** Nine user-listed sites hold 504 TIFFs; none is cleared. | REGISTRY-MEASUREMENT + repo `DO-NOT-SUBMIT` marking |
| Current top public score | **0.4544** (#1 xiaofanhu, 35 submissions). Not 0.4413. | OFFICIAL-PUBLIC |
| Is 0.3195 the highest score? | **No.** 0.3195 is the rank-50 public cutoff. | OFFICIAL-PUBLIC |
| Why did H33 (0.2778) score highest? | **Not established.** The number is user-reported with no organizer receipt. The file exists, is byte-unique among the nine sites, and is below the rank-50 cutoff. | USER-REPORTED |
| Can a score be estimated for a submission? | **No.** No holdout was run on any new candidate. No estimate is written. | NOT ESTIMATED |

## 2. Executive table — nine user-listed sites

Scores are **USER-REPORTED** (from the prompt). Byte-duplicate status is **GITHUB-API-LISTING** (git blob SHA-1, `evidence/site_blob_duplicates_20261030.json`). The **Estimated score** column is intentionally "not estimated" for every row. Submit status is **NOT CLEARED** for every row.

| Site | File named in prompt (score, user-reported) | Byte-identical copies elsewhere in these 9 repos | Estimated score | Unique bytes? | Download? |
|---|---|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` (0.2477) | GEMSDOE32 | NOT ESTIMATED | No | **No** |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` (0.2600) | GEMSDOE24, GEMSDOE30, GEMSDOE32 | NOT ESTIMATED | No | **No** |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` (0.2449) | GEMSDOE28, GEMSDOE32 | NOT ESTIMATED | No | **No** |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` (0.2710) | GEMSDOE32 | NOT ESTIMATED | No | **No** |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` (0.2600) | GEMSDOE32 | NOT ESTIMATED | No | **No** |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` (0.2708) | GEMSDOE32 | NOT ESTIMATED | No | **No** |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (0.2778) | none in these 9 repos | NOT ESTIMATED | Yes (among these 9) | **No** (`DO-NOT-SUBMIT` status not verified in-repo; see §4) |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` (0.2632) | GEMSDOE32 | NOT ESTIMATED | No | **No** |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` (0.2750) | GEMSDOE32 | NOT ESTIMATED | No | **No** |

Uniqueness scope: **only these nine repos were byte-audited.** The prompt lists about 90 sites. They were not audited and no uniqueness claim is made against them.

## 3. Why the gate stops every candidate (IR-6236446D-01)

- `scripts/generation_guard.py` reads the SHA-pinned witness `data/registry/dense_17gemdoe.tif` (`ab0a0a62…3872be`). It covers `5,167,373` positive pixels and `5,106,385 / 5,106,385` (`100%`) of allowed pixels. Its source is the `17GEMSDOE` site (commit `6fc71d1`).
- The guard's rule is `finite prediction > 0` as "support". Under that rule, any nonempty candidate has dot overlap `1.0 > 0.70` with this witness.
- The user's protocol says to stop when "more than 70% of your dots fall within 3 px of one registry raster's dots." Applying that rule to a dense 5.1-million-cell surface makes every nonzero candidate a duplicate. An all-zero raster would pass the gate, but it has no dots and scores 0.
- Measured on the bytes (this session): all `5,167,373` finite cells are `> 0`, values range `0.000463` to `0.984116`, with `4,729,578` distinct values. The witness is a continuous probability surface, not a dot set. The same finding is recorded independently in `research/session-1babc312-gate-review.md`.
- This is the measured result. It is not a rounding issue. I did not change the threshold, the support definition, or the witness, because the protocol forbids that.
- **Decision needed from the user** (same options as `1babc312`): (A) keep the literal rule, so no nonzero TIFF is possible; (B) authorize a defined dense-surface dot rule (for example, the top-`n` cells, as IR-88-SDTL-01 once proposed), keeping the rank-correlation and sparse-raster tests binding; (C) ask DrivenData in writing whether exterior NaN and the dot format are accepted. Option (B) or (C) is a rules change and needs the user's sign-off.

## 4. Verification of the user-listed files

- All nine named files exist in their repos (checked via GitHub API tree listings, HEAD).
- **Byte-identical copies:** 20 blob-SHA groups are shared across the nine sites. The table in §2 lists them.
- **GEMSDOE32** hosts byte-identical copies of files from GEMSDOE24, 25, 27, 28, 30, 31, 33, and 36. The site that reports the top listed score (H33, 0.2778) is the only one of the nine whose headline file is byte-unique among these repos. That is a property of the bytes only, not a claim about score.
- The GEMSDOE32 H33 file name carries `zeros`, and the repo's own `DO-NOT-SUBMIT` convention is not verified for that file in this session. Treat it as **not submission-cleared** under §1 and the repo's rules.

## 5. Format irregularity (IR-6236446D-04) — flagged, not proven

- The official rules page (`page/967`): values in `[0, 1]`, float32, one band, EPSG:32611, 100 m, same bounds, and "data outside the bounds is null or nan."
- The restored official-style `sample_submission.tif` (sha256 `2176d08e…35cbc`, the pinned value) has `nodata = NaN`. Its footprint is `5,167,373` finite cells with values `{0.0, 1.0}`, and `7,111,787` NaN cells outside.
- Repo downloads sampled here (`docs/downloads/*-DO-NOT-SUBMIT.tif`) have `nodata = None` and `12,279,160` finite cells over the full grid. Their finite exterior is not NaN.
- These files are in `[0, 1]` and float32, so this is **not** the literal "[0, 1]" error the user received. It is a difference from the stated rule. It may or may not matter to the portal. The actual upload that produced the user's error is **not identified** in the repo. Flagged for review; not established as the cause.

## 6. Why 0.2778 and what would beat 0.4544

- No organizer receipt exists for 0.2778 or any user-listed site score. Every such number is USER-REPORTED.
- All nine listed scores (0.2449 to 0.2778) are below the public rank-50 cutoff of 0.3195. If those numbers were real public scores, those participants would not be on the top-50 board.
- The repo's prior analysis of the 0.2778 / 0.3195 / 0.4413 figures is in `research/session-3c391d97-review.md`. I did not re-verify that analysis in this session, so I do not repeat its conclusions here.
- Beating 0.4544 requires an approach that passes the gate. Under the current protocol, no approach can. A protocol decision (§3) is therefore the prerequisite for any further scientific work.

## 7. Three review passes

1. **Implement / verify.** Restored the validation inputs (`scripts/download_competition_data.sh --validation`: 28 pinned files in 10 groups, all SHA-verified). Ran the guard: `DUPLICATE_STOP`, exit 2, reproduced. Ran the test suite: `1109 passed, 23 skipped`, exit 0.
2. **Review for bugs / assumptions.** Found that the 0.3195 "highest" figure is the rank-50 cutoff, that 0.4413 is stale, and that the nine sites share 20 byte-identical groups. Checked the sample's NaN footprint against the repo downloads' full-grid finite values. Flagged the dense-witness rule as a protocol issue, not a code bug.
3. **Re-check against request.** Confirmed no TIFF, no score estimate, no slot, and no clearance was produced. Each claim is labelled by evidence class. The unverified items (H33 receipt, portal-error cause, the other ~90 sites) are listed as open.

## 8. Sources (official / verified)

- Problem & metric (DrivenData): <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> — DTI α=0.2, β=0.8, 300 m triangular kernel; submission format rules.
- Leaderboard (DrivenData): <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> — captured 2026-10-30 in `evidence/leaderboard_live_capture_6236446d_20261030.json`.
- Protocol & data restore: `scripts/restore_inputs.py` (SHA-pinned owner mirrors), `scripts/generation_guard.py` (guard), `scripts/preflight_mtas88.py`.
- Byte-duplicate audit (this session): `scripts/audit_site_blob_duplicates.py` → `evidence/site_blob_duplicates_20261030.json`.
- Preflight receipt (this session): `evidence/session_6236446d_generation_preflight.json`.
- Run card (this session): `registry/session_6236446d_run_card.json`.

## 9. Open items (next session)

1. **User decision:** choose option A, B, or C in §3. No work proceeds to features until this is answered.
2. Byte-audit the remaining ~80 sites in the prompt list with `scripts/audit_site_blob_duplicates.py` (extend `SITES`).
3. Identify the upload that produced "Predicted values must be in range [0, 1]" (portal receipt, not a local check).
4. Obtain an organizer receipt or a private-split result for any site score before treating it as more than USER-REPORTED.
