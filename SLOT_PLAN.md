# Latest addendum (2026-10-24): H88-QTSK — DO NOT SUBMIT, 0 slots spent

`H88-QTSK` (`docs/downloads/gems88-qtsk-coverstep-knickwave-20261024-798e3c54-DO-NOT-SUBMIT.tif`, SHA-256 `798e3c54ae318c24…`, `53,876` binary dots) passes portal format/LZW sample parity, 58/58 leakage canaries (`<= 0.5781`), blind-basin fingerprint (`share_gt25 = 46.40% >= 35%`, `share_le2 = 0.00%`), pre-placement surface `|ρ| = 0.2831 <= 0.90` across all 228 rasters, and 222-raster pre-merge like-for-like uniqueness (`0.5644 <= 0.70`). In paired 8-fold holdout (`gems57-pooled-hide-v2`, `n = 22,893`), `Exp 2 (QTSK-DUAL)` reached `0.192759` (`+21.3%` blind `>25 px` DTI `0.079137`, stopped on `0.7995 > 0.70` vs `MRR`), while emitted `Exp 3 (QTSK-STRAT)` scored `0.151511` (`< ADHR 0.189634`), recorded `0.7245 > 0.70` post-merge 3-px overlap vs concurrent `GTHC-88` (`IR-88-103`), and hit literal `1.0000` vs `17GEMSDOE`. **0 weekly slots spent; human selector required (`validate_qtsk88.py --require-submit` exits 2).**

---

# Earlier addendum (2026-10-24): MDPS-88 — DO NOT SUBMIT, no slot

MDPS-88 (`gems88-mdps88-mix-29742dots-20261024-zeros-DO-NOT-SUBMIT.tif`, sha256 `bd64000f…35cd`) is unique and format-valid but **negative** under its frozen gates: HOLDOUT-DTI far paired Δ `+0.0036 [−0.0060,+0.0128]` vs fold-fair control (crosses 0), far `0.0727` < stored ADHR far `0.11478`, overall below control (evaluator `gems57-pooled-hide-v2`; 22,893 withheld, 10,791 far). Budget: E1 + disclosed budget-matched E2 only; E3 packaging. **0 slots spent or recommended** (same for PHASE-88 below). Selector note (IR-88-85): identical folds score shipped H33 at 0.0039 and any >3 px full-catalogue-collar raster at exactly 0 — pre-register the evidence-combination rule before the next lane.

---

# Current decision (2026-10-24): PHASE-88 — DO NOT SUBMIT

PHASE-88 is a new research TIFF ([download](docs/downloads/gems88-phase88-crossgrad-20261024-d7d02ab4-DO-NOT-SUBMIT.tif)); the automated format check passes, but the score/uniqueness gates fail. HOLDOUT-DTI 0.053062 (95% CI [0.046064,0.060233], gems57-pooled-hide-v2, 22,893 withheld positives) versus incumbent 0.187888 on the same split, without paired improvement CI. Final forward 3-px overlap 0.9090 vs GEMSDOE87 and 1.0 vs the dense 17GEMSDOE witness (limit 0.70). No slot spent, no organizer receipt. Literal overlap cannot be passed by ANY nonempty raster while the positive-everywhere prior is included. A separate portfolio selector/protocol decision is required before any future submission; do not treat historical proposals below as current authorization. [Full dossier](research/phase88-20261024.md).

---

## Archived slot plans below (NOT authorization)

> **2026-10-24 LBCAL update (IR-88-78).** No slot was spent.
> - **LBCAL** (`gems88-lbcal-receipt-38278-20261024-0aeb6eed-zeros-DO-NOT-SUBMIT.tif`) is **HOLD** under the written holdout gate: 0.0616 < 0.0763.
> - **The receipt model ranks them the other way.** Its 8-fold repo-blocked CV is ρ 0.941. Projections: LBCAL 0.356, H33 0.264, PROVCREST 0.105 (MODEL-PROJECTION).
> - **Selector decision needed before any slot:**
>   - (a) keep the hide-and-recover gate, so PROVCREST stays slot-eligible, against our recommendation; or
>   - (b) adopt the receipt-CV gate, so LBCAL takes slot 1 and PROVCREST gets no slot.

# Slot Plan — Current Automated Decision

**Updated 2026-10-24. No competition slot is authorized or recommended by the current run.**

| Candidate | Evidence | Scientific gate | Registry gate | Slot decision |
|---|---|---|---|---|
| `GEMSDOE88-GTHC-SCRD-STRAT-E3C0D9E0` (`docs/downloads/gems88-gthc-scrd-strat-46457dots-20261024-e3c0d9e0-DO-NOT-SUBMIT.tif`) | Unstratified `EXP2 (gthc88_dual_scrd)` **HOLDOUT-DTI `0.190971`** (`95% CI [0.176110, 0.207531]`, beats stored `H88-ADHR` `0.187888` and recomputed `0.189634`); emitted stratified `EXP3 (gthc88_strat_fp, 46,457 dots)` **HOLDOUT-DTI `0.170718`** (`95% CI [0.155970, 0.186645]`, `+14.69%` over `MDC-88` `0.148850`), `n=22,893`, evaluator `gems57-pooled-hide-v2` | **PASS unstratified SCRD vs `H88-ADHR` (`0.190971 > 0.187888`) & fleet fingerprint (`share_gt25 = 0.3671 >= 0.35`, `share_le2 = 0.0`) · FAIL stratified arm vs unstratified `H88-ADHR` (`0.170718 < 0.187888`)** | **PASS like-for-like across all 223 registry rasters** (`worst overlap = 0.6011 <= 0.70`, `worst |rho| = 0.3526 <= 0.90`) · **FAIL literal rule** (`17GEMSDOE` forward overlap `1.0000 > 0.70`) | **DO NOT SUBMIT; 0 slots used** |
| `GEMSDOE88-QTS88-B5D178B3` (`docs/downloads/gems88-qts88-decoupled-thickness-submod-20261024-b5d178b3-DO-NOT-SUBMIT.tif`) | Candidate **HOLDOUT-DTI `0.098210`** (`EXP2`) / **`0.094851`** (`EXP3`, `37,654` dots), 95% CI `[0.084216, 0.112545]` / `[0.080118, 0.110077]`, `n=22,893`, evaluator `gems57-pooled-hide-v2`; paired 19-band no-QTS control `0.091869`; paired QTS lift **`+0.006340`, 95% CI `[+0.001574, +0.011511] > 0`**; stored `H88-ADHR` bar `0.187888` | **PASS paired ablation (`+0.006340 > 0`) & fleet fingerprint (`share_gt25 = 0.4025 >= 0.35`, `share_le2 = 0.0`) · FAIL stored `H88-ADHR` bar (`0.187888`)** | **PASS like-for-like across all 223 registry rasters** (`worst overlap = 0.5373 <= 0.70`, `worst |rho| = 0.5049 <= 0.90`) · **FAIL literal rule** (`17GEMSDOE` forward overlap `1.0000 > 0.70`) | **DO NOT SUBMIT; 0 slots used** |
| `GEMSDOE88-MRR-BPR-20261024-DO-NOT-SUBMIT` | Candidate **HOLDOUT-DTI `0.185256`**, 95% CI `[0.171519,0.199965]`, `n=22,893`, evaluator `gems57-pooled-hide-v2`; paired incumbent `0.189634`; paired delta `-0.004378`, 95% CI `[-0.007902,-0.000623]` | **FAIL** — confidently below paired incumbent | **FAIL under binding literal rule** — 17GEMSDOE forward overlap `1.0000 > 0.70`; sparse-only diagnostic max `0.684178` passes | **DO NOT SUBMIT; 0 slots used** |

## Why no conditional MRR slot exists

The preregistered promotion rule required candidate HOLDOUT-DTI to exceed the recomputed incumbent, with a paired CI not crossing zero. The observed CI is entirely negative. A valid TIFF and like-for-like sparse-raster uniqueness therefore cannot rescue the method. The all-positive registry witness independently forces the literal gate to fail for this and every nonempty raster; no exemption is authorized.

## Historical candidate plans

Earlier PRUNE, H88-ADHR, GHMD, and UGFV slot suggestions remain research history only. They are not current authorizations, have no ORGANIZER-CONFIRMED receipt in this repository, and are subject to the same binding literal any-raster gate. In particular, PRUNE's high exact overlap with H33 was already recorded as disqualifying under the current user rule. Do not upload an older file merely because MRR-BPR-88 is negative.

## Preconditions for any future weekly slot

**Verdict: the 2–3 px annulus is proxy-neutral, and the outer descent is monotone.** (1) Both interior arms move blind SGMC by less than the `~0.0003` instrument noise yardstick (IR-88-51); `p2.236px` matches `R1`'s `+0.00023` while purging `43%` as many dots — no sharp 300 m boundary is visible to the control, so a future `R1` receipt prices the refill/spacing lineage, not a special kernel-radius edge. (2) Hide-and-recover credit survives only while sub-`2.828 px` dots remain (`p2.236px`), then collapses to the structurally-zero value every gate-clean arm shows. (3) `p5px` deepens the outer-collar descent already measured at `p3.7/p4.3` (`-0.00119 → -0.00350 → -0.00660` SGMC), sign-correct against its preregistered `MODEL -0.020`, and pushes `CV_12km` to `0.6195`, outside the reported `0.51–0.59` best-file band. Hardened validator 6/6 PASS on disk bytes (`registry/prune_interior_validation.json`); independent from-scratch rerun reproduces all three masks bit-for-bit; report `evidence/prune_interior_report.json`. **No arm enters the queue** — the largest delta is below the `0.01` no-evidence floor; the queue below is unchanged and the interior-collar question is closed.

### One Blind Final Submission Rule & Proposed Next Axes (Not Built)
- **Final submission (`1` total):** Pick the candidate with the highest verified live `RECEIPT` beating `R1` by `>= +0.01`; if all live deltas remain `< 0.01`, pick `PRUNEp3space35fp` (`8d29a2f7`) on parsimony (gate-clean, zero `w`/RNG, `min_nn = 5.66 px`, highest `300 m` blind `SGMC`).
- **Proposed next single-axis tests (not built here):** (1) `p4space35fp` (`400 m` collar + score-blind farthest-point refill, gated on live receipts); (2) `p3space35provfp` (`100%` provided-band crest pool + farthest-point ranking); (3) `INSTRUMENT_AUDIT` (`1 px` seeded random jitter control beside a receipted arm); (4) `LIVE_COLLAR_PAIR` (IR-88-57): if the Slot 1 `R1` receipt is inconclusive (`|delta|<0.01`), pair it with `p2.236px 93b15124` — blind SGMC cannot separate a partial (`941` purged) from a full (`2,171` purged) collar (`+0.00016` vs `+0.00023`); falsifier: both receipts within `0.01` of each other and of `R0`.

## 2026-10-24 addendum (IR-88-75)
Prior slot ordering above concerns the PRUNE lineage and is unchanged. The PROVCREST file (`13b4155c…`, UNSCORED) is **not slot-eligible**: v3 uniqueness fails (0.7319 > 0.70 vs GEMSDOE85 `geopb-crest-90000dots`). Queued probes (none run, none take a slot before a receipt exists): (a) a PROVCREST variant whose dots avoid that raster's 3-px footprint; (b) a far-from-catalogue spaced-random "geometry-null" probe, to measure how much of a live score is geometry alone; (c) N≈50k crest variant (holdout 0.0853, live regime unknown).

1. A newly preregistered, genuinely different method must beat the current paired holdout incumbent on the identical whole-component folds, with a positive paired 95% CI.
2. Every feature-alone leakage canary must remain at or below symmetric AUC `0.90`.
3. Surface `|Spearman rho| <= 0.90` before placement and final 3-pixel forward overlap `<= 0.70` against every registry raster under the currently authorized rule.
4. Independent format validation must pass on the saved TIFF and one-member ZIP, including all-finite values in `[0,1]`.
5. An authenticated organizer template byte check and a separate explicit human portfolio-selector decision are required.
6. After a manual upload only, log the receipt as ORGANIZER-CONFIRMED. Never treat MODEL, PROXY, HOLDOUT-DTI, or H33's reported `0.2778` as a portal receipt.
