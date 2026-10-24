# PhD-Level Forensic Answer: Why H33 Scored 0.2778 and Can We Beat 0.3195 / 0.4413?

**Evidence classes:** `[ONLINE]` = read on official page this session; `[DISK]` = measured from SHA-pinned bytes; `[OWNER]` = user-reported score without organizer receipt; `[INFERENCE]` = derived under stated assumption; `[MODEL]` = prediction, never a score.

## Executive Summary

The owner-prompt cites three inconsistent maxima — `0.2778` (GEMSDOE32 H33, `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`), `0.3195` (stale 2026-10-04 #2 from DARD), and `0.4413` (live leaderboard #1 xiaofanhu, 2026-10-24, `[ONLINE]` https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). Only `0.4413` is independently verifiable today; `0.2778` is `[OWNER]` with no receipt in this repository. No local instrument can honestly project to beat `0.2778` without a portal receipt. H33's advantage is *subtractive*: it is a strict 6,436-dot subset of D2.8 (all removed within 2 px of the catalogue) thinning a kernel-spaced lattice from 121k → 37k dots, matching the DTI's `α=0.2` / `R=300m` precision–coverage trade-off. Fleet analysis across 20 rasters shows the single best correlate of the reported ordering is the distance-to-catalogue fingerprint (`share_gt25` Spearman +0.90 `[DISK]`), not any holdout. To reach the first-round cutoff `0.3539` (`[ONLINE]` #5) needs +27–29% more weighted truth credit at fixed dot count; to reach `0.4413` needs +59–63% `[INFERENCE]`.

---

## 1. Official Scoring Mechanics `[ONLINE]`

From https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ and `vendor/gems57/metric.py`:

- **DTI** = `TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)` with 300 m triangular kernel `k(d)=max(1-d/300m,0)` at 100 m pixels (`R=3 px`).
- Known USGS/INGENIOUS pixels are pixel-exactly masked from scoring (`known`); `FP_w` is charged only outside that mask.
- New-fault definition (staff, 2026-09-23, https://community.drivendata.org/t/where-do-you-draw-the-line/11536): any pixel not already captured by USGS/INGENIOUS, *including newly mapped geometry of an existing system*.
- Weekly slot limit is the *portal-displayed limit*, not the parenthetical "three/week" (staff, https://community.drivendata.org/t/submission-amount-question/11553); one final submission is selected for both rounds (NLR Rules §3.4–3.6.2, https://docs.nlr.gov/docs/fy26osti/96647.pdf).

For binary dots with `n` dots, truth `|G|`, per-truth max kernel `T` and per-dot max kernel `M`:

```
DTI = T / (0.8|G| + 0.2·(T + n - M))
```

Marginal gain of one dot with self-credit `k` and new truth credit `dT` is `dT > 0.2·DTI·(dT+1-k)`. For non-redundant dots (`dT=k`), the bar is `k > 0.2·DTI` = **0.0556 at DTI 0.2778**. Pure clutter (`dT=k=0`) *always* hurts (denominator +0.2, numerator unchanged). Two dots <3 px apart share kernel area: `T` saturates at 1 per truth pixel while `n` and `M` grow, so the second dot costs `0.2` without adding `T`. The metric therefore rewards **≈3 px spaced lattices**.

---

## 2. What H33 *is* `[DISK]` (SHA-pinned files)

**Files:** `data/registry/h33_education.tif` (`c55bafc4…`, 37,654 dots, `[DISK]`), `data/registry/gems25_d28.tif` (`3e78737f…`, 44,090), `data/registry/gems19_h19_5.tif` (`ef2ae80…`, 121,131), `data/registry/gems28_h27_4.tif` (`2fc94a3…`, 40,199). Measured via `scripts/forensics_h33.py` → `evidence/h33_forensics_20261024.json` `[DISK]`:

- **Exact subset chain:** `H33 ⊂ SOLO-D2.8 ⊂ D2.8 ⊂ H19-5` with **zero added dots** at every step (`added_vs_a = 0`). `|D2.8 \ H33| = 6,436` dots, all with `d_cat ∈ {1,2} px` (≤200 m of catalogue).
- **H33 geometry:** `min d_cat = 2.236 px`, 0% ≤2 px, 5.8% ≤3 px, median 19.6 px, 41.7% >25 px, 35.8% >30 px. Nearest-neighbor spacing: min 2.828 px, median 3.00 px, 81% in [2,4] px — a lattice at the kernel radius.
- **No single band explains it:** largest separation vs footprint is detrended slope (AUC 0.657, dots avoid flattest/steepest decile); all other 19 bands AUC 0.50±0.08. H33 is a multi-modal ridge product, not a threshold.

---

## 3. Why the lineage climbed `[OWNER]` + algebra `[INFERENCE]`

Reported public scores along the strictly subtractive chain:

```
H19-5 0.1922 (121,131) → D1.5 0.2477 (60,069) → D2.8 0.2600 (44,090) → SOLO 0.2708 (40,199) → H33 0.2778 (37,654)
```

Because no dot is ever added, each gain is attributable to the dots removed. Under `α=0.2`, removing a pure false positive (`dT=k=0`) raises DTI by `+0.2 / D` denominator units, no loss. Assuming the collar dots were pure FP (`k=0`), algebra `T·(1/DTI0 -1/DTI1)=0.2·m` gives independent estimates:

- D2.8→SOLO (m=3,891): `T≈5,073`
- SOLO→H33 (m=2,545): `T≈5,470` (within 8%, supporting the assumption)

**Reading `[INFERENCE]`:** public truth `|G|≈13–15k` pixels; H33 captures `T≈5.2–5.5k` (≈36–39% of weighted truth); average dot credit `≈0.14` (≈2.6× break-even 0.0556). H33 is limited as much by precision (≈10–15% of dots hit) as by recall. At fixed `n=37,654`, gaps:

- to `0.3539` (round-1 cut, `[ONLINE]`): **+27–29% `T` (+6.2–7.3k weighted pixels)**
- to `0.4413` (`[ONLINE]` #1): **+59–63% `T` (+7.7–9.2k)**

Both assume `M/T` 0.33–1.0; no external data needed, only counting.

---

## 4. Fleet fingerprint: distance-to-catalogue `[DISK]` + `[OWNER]`

Twenty rasters with owner-reported scores (H33 lineage, GEMSDOE28/33/36/49/63/66/70/73/75/76/80/81, 16/19GEMSDOE) measured in `evidence/fleet_distance_prior_20261024.json`:

- `share_gt25` (fraction >2.5 km from catalogue) vs reported score: **Spearman +0.90 (n=20), +0.85 (≥0.15, n=17), +0.61 (≥0.23, n=11)**.
- Footprint baseline: 47.2% >25 px, median 23.1 px. H33: 41.7% >25 px, median 19.6 px — not far-biased, simply **not catalogue-hugging**. Low scorers hug: GEMSDOE81 (median 2.2 px) 0.0041, GEMSDOE80 (median 8.0 px, 12% >25 px) 0.0943.
- **Necessary, not sufficient:** GEMSDOE76/66 pass fingerprint but report 0.1555/0.1152 (fit overpredicts by 0.05–0.08).
- **All other proxies fail:** SGMC-gap DTI Spearman vs score = +0.22 (all), −0.25 (≥0.15), **−0.66 (≥0.23, n=11)**; SGMC-all −0.93. Hide-and-recover scores H33-class rasters at **0 by construction** (`IR-88-20/35`): truth sits on catalogue, file avoids it. No local instrument rank-orders the top regime except this fingerprint.

---

## 5. Hypothesis to beat it — and why local proof is impossible

**Mechanisms that remain `[INFERENCE]`:** (a) further collar thinning (siblings GEMSDOE89–92 tested 3–4 px collars, no scores); (b) spaced refills on ancestor pools `H16-1/H19-4` (only 90 H19-5 pixels ≥2.8 px from R0; `p3space35` gained `+0.005` SGMC proxy); (c) shoreline filtering (this session: Lahontan 1330m / Bonneville 1555m shorelines cover 3% footprint; removing them costs nothing in `FP_w` and restores hinge coverage).

**Why no local proof exists:** hide-and-recover measures *catalogue* faults; live truth is *non-catalogue* faults, anti-correlated in distance-to-catalogue space. The fleet shows `share_gt25` predicts live but not holdout; SGMC-proxy predicts holdout but not live. Only a portal receipt can decide.

**Our new lane H88-SHORE-HINGE `[DISK]`:** 37,654 dots, `share_gt25 44.3%` (passes gate), `share_le2 0.0%`, median 21.4 px, hinge 24% of footprint, shoreline mask 3%, score = `hinge·(0.6·rank|S|+0.4·rank cross)`, greedy ≥3.5 px, >3 px collar, LZW 1-row-strip, all finite `[0,1]`, `EPSG:32611`, `3730×3292`. Like-for-like uniqueness `max overlap 0.4028 ≤0.70` `max |ρ| 0.0318 ≤0.90` vs 19 validation rasters (`[DISK]` via `generate_shore_hinge_candidate.py`); literal dense witness `1.0000 >0.70` (vacuous, `IR-88-60`). **HOLDOUT-DTI 0.0000 vs R0 0.0039 `[DISK]` — the expected structural zero for any catalogue-avoiding file — therefore `negative` verdict and `DO-NOT-SUBMIT` name, 0 slots spent.

---

## 6. Can we demonstrate beating 0.2778?

- **Not from local DTI:** H33 scores 0.0039 on our hide-and-recover; any file avoiding the catalogue scores 0.0; the instrument cannot rank the lineage (reported 0.1922→0.2778 vs holdout 0.03→0.0 inversion).
- **Not from SGMC proxy:** fleet Spearman vs live is negative in top regime; our hinge file's proxy is unmeasured live.
- **Only receipt-possible:** the lineage's 0.2778 is `[OWNER]` below visible rank 50 (0.2818 `[ONLINE]`); 15 teams sit 0.326–0.333, 5 teams above 0.3539. What they share is not public. Generative-AI disclosure (§3.2) and diversity factor (A.13) are policy, not metric.

**Bottom line `[INFERENCE]`:** P(beating 0.2778 with a unique, non-hugging, kernel-spaced file) is low and cannot be estimated; P(reaching 0.3539) lower. Do not spend a weekly slot on any file that has not beaten a paired holdout *and* passed fingerprint/uniqueness — our `H88-SHORE-HINGE` passes fingerprint + uniqueness + format, but not holdout, so it remains `DO-NOT-SUBMIT` and is published for learning.

---

## 7. Reproduce

```bash
python scripts/restore_inputs.py --validation  # grid + catalogue + 19 registry rasters
python scripts/restore_inputs.py              # full 400M training_features + 141M external 3DEP/LiDAR
python3 scripts/generate_shore_hinge_candidate.py  # builds docs/downloads/gems88-shore-hinge-*.tif + run_card
python scripts/audit_literal_protocol.py      # verifies 17GEMSDOE vacuity proof
python3 -c "import rasterio, numpy as np; a=rasterio.open('docs/downloads/gems88-shore-hinge-piedmont-20261024-42dc0afa-zeros-DO-NOT-SUBMIT.tif').read(1); print(a.min(), a.max(), np.isnan(a).sum())"
```

**Official sources verified this session:** leaderboard https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (2026-10-24 07:19 UTC), metric https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/, NLR Rules https://docs.nlr.gov/docs/fy26osti/96647.pdf, GeoDAWN https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and, Great Basin geology https://gbcge.org/current-projects/ingenious/, EPSG:32611 https://epsg.io/32611, Tversky https://en.wikipedia.org/wiki/Tversky_index, Faulds & Hinz 2015 https://www.osti.gov/servlets/purl/1724082, Giddens 2025 relay width https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf.

