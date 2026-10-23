# SLOT PLAN — GEMS Prize (DrivenData #306)

> **Deadline:** 2026-12-03 17:00 ET (confirm on the competition page). **Quota:** 3 scored / rolling week, 1 final blind pick. **Week claimed:** 2026-10-23. **Slots left this week:** 3/3. **Total to deadline:** ~18 (≈6 weeks × 3).

## Where we actually are

Parent **R0 = h33-h33-2-b2** — 37,654 unit dots, 0 on the catalogue, sha `c55bafc4…` (rebuilt and hash-matched this session). Claimed **0.2778 CLAIM**, no receipt. **TOP_PUBLIC 0.4413** (#1 xiaofanhu, 2026-10-22, `registry/run_card.json`) — a gap of **0.1635**.

The largest live gain anywhere in the ledger is **+0.007** (the ≤2 px catalogue prune). Brief §5 calls anything under **0.010** no evidence. So: *every* dot edit tried to date sits below the evidence floor, and the gap to #1 is **16× the best effect ever measured here**. Continuous dot tweaking cannot close it. Plan accordingly: at most one slot this week on MASS, and keep the quota for a structural question or leave it unspent.

## This session (AXIS = MASS) — 3 built, 1 recommended

All three reconstruct bit-exactly from the recorded recipe (`registry/mass_ranking_audit.json`), pass format gates, and keep 0 catalogue mass with a 2 px collar. **None of them uses a model ranking** — R0's score field is not stored (IR-88-17); the score is `0.6·clip(d_catalogue/50)+0.4·uniform(seed)`, so 40% is noise and 60% points at the catalogue.

| ID | dots | what it really is | predicted | verdict |
|---|---|---|---|---|
| `…MASSm10minus…7132935e` | 33,889 | collar extension 2→~10 px (89.4% of drops within 10 px of catalogue; 2.96× baseline) | **+0.004** [-0.006,+0.014] | **slot-eligible** |
| `…MASSm10plus…82673b57` | 41,419 | 3,765 isolated, lowest-prior dots (85% >3 px from any parent dot, prior 0.119 vs 0.400) | **-0.010** [-0.014,+0.002] | **do not spend** |
| `…MASSm20minus…6c73303c` | 30,123 | same ranking, deeper cut — nested inside m10minus, not independent | **+0.001** [-0.015,+0.017] | hold |

Predictions are the exact algebra at DTI 0.2778: a dot pays only if unseen truth lies within **2.83 px** (credit > 0.2·DTI = 0.0556); every other dot is a flat 0.2 of denominator. `docs/SUBMIT.md` specifies the file, name, note and format receipt per candidate, and says to upload the **-zeros** twin (IR-88-20).

## Next 3 slots, in order

1. **`MASSm10minus` (33,889)** — the only file this week that continues the one direction with a measured gain. *If Δ ≥ +0.010:* the 2–10 px collar is mostly false-positive mass → hand the next slot to PRUNE and push 3/4/5 px. *If Δ ≤ −0.010:* collar dots are net true positives, the 0.2778 prune was inside the noise floor, and R0 is a local max on mass — stop all collar work. *If |Δ| < 0.010:* no evidence; do not submit m20minus, it would repeat the same test.

2. **PRUNE ≤3 px, no refill** (2,171 dots, 5.76%, predicted +0.002…+0.005). The clean single-variable version of what slot 1 did by accident. *If monotone with slot 1,* the collar boundary is the lever and 4/5 px follow in wk3. *If not monotone,* collar position is not the driver and PRUNE is closed for good.

3. **Reserved — spend only if slots 1–2 are informative.** If both land under the floor, the honest options are the SPACING test below (the only proposal here with a plausible effect above 0.010) or not submitting at all. An unspent slot costs nothing; a slot spent on a predictably-null file costs a week of feedback.

## Proposed axes — not built this session

**SPACING — bar-matched coverage (highest upside).** *Mechanism:* credit is a max over a 2.83 px bar, so dots spaced ≤2 px tile a trace with heavy redundancy while covering ~2.8 px of trace per dot; spacing near 2×2.83 px covers roughly twice the traced length per unit mass. Re-space R0's spine at 4 px, hold the count, refill the freed budget onto new ground. *Confounder:* credit drops from 1.0 to ~0.67 at 4 px spacing, which cancels part of the coverage gain, and line-like truth often has sub-4 px structure. *Falsifier:* at matched mass, 4 px spacing scores below 2 px → truth is finer than the kernel and spacing is not the lever.

**MASS-CALIBRATION (null add on R0).** *Mechanism:* add ~2,000 dots at positions with no structure support and measure the realised drop, converting the flat-0.2-per-dot claim into a calibrated constant so every future prediction becomes quantitative instead of assumed. *Confounder:* null positions may still sit within 2.83 px of unseen truth, so the measured price is a lower bound on cost. *Falsifier:* a measured cost far from 0.2/dot means the denominator model — and therefore all of the sensitivity arithmetic in this plan — is wrong. (A 2,000-dot null add already exists on the 0.2600 base: `family_60gemsdoe/gems32-probe-S3-NULLADD-2000px.tif`, 46,090 dots.)

**TRACKB (Phase 2, not a weekly slot).** Strike-consistent traces ≥1 km from R0's spines as GeoJSON + raster, one evidence paragraph each. *Mechanism:* expert-expanded Phase 2 labels reward coherent traces over isolated dots. *Confounder:* a confident-looking trace that is wrong is worse than dots, because Phase 2 reviewers react to structure. *Falsifier:* traces that do not beat dots on the in-block holdout PROXY (never a gate) do not go out.

## Weeks to deadline

- **Wk1 (now → 10-30):** slot 1 m10minus. Read the collar direction.
- **Wk2 (→ 11-06):** slot 2 PRUNE ≤3 px; decide monotonicity.
- **Wk3-4 (→ 11-20):** SPACING bar-matched test, and either PRUNE 4/5 px or SPACING fusion, whichever slot 1–2 justifies. One structural variable per slot.
- **Wk5-6 (→ 12-03):** confirm the leader, re-validate both the final file and the fallback (EPSG:32611, 3730×3292, float32, [0,1], no NaN inside, 0 catalogue), finalise `AI_USE.md`, pick ONE blind file.

> Labels: RECEIPT | CLAIM | PROXY | MODEL. A PROXY or MODEL is never a score. Live Δ < 0.010 is not evidence (public chunks only; the private score may differ).
