# GEMSDOE88 — DOE GEMS Fault-Discovery Research & Automated GeoTIFF Pipeline

## CURRENT STATE (2026-10-23)

- **Parent:** h33-h33-2-b2 (GEMSDOE32) — 37654 dots, 0 within 2px, sha c55bafc4… (CLAIM 0.2778, no receipt)
- **Best receipt:** none (this repo has no ORGANIZER-CONFIRMED receipt; H33 is CLAIM per brief)
- **TOP_PUBLIC:** 0.4413 by xiaofanhu on 2026-10-22 (verified leaderboard.json, stale after 24h)
- **Slots left this week:** 2/3 (built 3 MASS variants, 0 submitted) — **Slots total used:** 0
- **Next 3 slots (in order):** 1) h33-h33-2-b2-MASSm10-20261023-06d99a7c MASS_m10 (n=31935), 2) h33-h33-2-b2-MASSp10-20261023-8fe48581 MASS_p10 (n=39248), 3) h33-h33-2-b2-MASSswap10-20261023-21cf4658 swap10 (n=35483)
- **Build status:** 3 variants BUILT, validated (CRS EPSG:32611 3730x3292, float32, 0.7/0.3 NaN/zeros pair, zero catalogue mass, sha unique, parent-diff recorded, re-read OK)
- **Evidence labels:** All scores labelled CLAIM/PROXY/MODEL per brief; no HOLDOUT-DTI claimed without receipt; external facts carry URL (see knowledge/field-guide.md)

> **READ THIS FIRST EVERY SESSION — PROJECT OPERATING BRIEF & UNMISTAKABLE STATUS**
>
> - **OK TO DOWNLOAD FOR RESEARCH: `YES`** — [`docs/downloads/gems88-ugfv-submod-22545-20261022-v2-DO-NOT-SUBMIT.tif`](docs/downloads/gems88-ugfv-submod-22545-20261022-v2-DO-NOT-SUBMIT.tif) (`22,545` binary off-catalogue dots, `SHA-256: 15cc6f7875b4bbd382d34b66d7b22bdd76c6f5de34b347e30e69f701ccc20a00`) · [One-TIFF `.zip`](docs/downloads/gems88-ugfv-submod-22545-20261022-v2-DO-NOT-SUBMIT.zip) (`SHA-256: edce6e3f0ba68f6c6142d38cbbd63a2b70d35033cceb7eb66b8554e5bbaacbe2`) · [Byte-level validator receipt](docs/downloads/gems88-ugfv-submod-22545-20261022-v2-DO-NOT-SUBMIT.json) · [Executive summary & submission instructions](docs/executive-summary.html) · [Machine run card](registry/run_card.json)
> - **OK TO SUBMIT INTO THE COMPETITION: `NO — DO NOT SUBMIT`** without explicit selector authorization. While `H88-UGFV` passes **100% of competition format checks**, **48/48 leakage canaries (`max AUC = 0.8321 <= 0.90`)**, **138/138 pre-placement surface Spearman checks (`max |rho| = 0.7222 <= 0.90`)**, and **134/134 genuine fault-prediction dot-overlap checks (`max = 0.6841 < 0.70`, `H33 = 0.3037`)**, **4 archival space-covering calibration rasters** (`dense_17gemdoe.tif` [`100.00%` footprint halo], `calib_r13lattice_00904.tif` [`99.87%`], `r14_union_tips10_lat6.tif` [`76.20%`], `r11_greedy_mp.tif` [`73.97%`]) automatically exceed `0.70` against any full-domain dot set by the Pigeonhole Principle. **Verdict: `negative` under the unamended literal rule · Weekly submission slots spent: `0`.**
> - **Unique Submission Name:** `gems88-ugfv-submod-22545-20261022-v2-DO-NOT-SUBMIT`
> - **Unique Submission Note (`113 / 140` chars):** `H88-UGFV 32ch physics+GDR thermal+self-masked relay CELF (22545 dots); research only: dense witness blocks upload`

---

## Permanent User Prompt: Operational Requirements

**Highest urgency: “MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.”**

1. **Core values:** **Maximize P(Win)** — spend scarce weekly submissions (`<= 3/week`, with **only ONE single final submission selected for both Round 1 `$50K` and Round 2 `$250K`**, NLR Official Rules §3.2–§3.5) only on rigorous, evidence-backed discoveries; **Own the Outcome** — take full responsibility for negative gates, data irregularities, and limitations rather than concealing them. Target **geological faults indicative of geothermal resources**, never directly hallucinated surface vents.
2. **Parallel-run protocol / lane:**
   - **LANE:** Stay inside one explicitly defined method lane (`H88-UGFV`). Check surface Spearman rank correlation (`<= 0.90`) before dot placement AND final 3-pixel forward dot overlap (`<= 0.70`) against registry rasters. Never silently exempt dense priors.
   - **REUSE, DON'T REBUILD:** Use shared `vendor/gems57/` tools (`evaluate_holdout.py`, `submission_writer.py`, `holdout.py`, `anatomy.py`, `emit.py`, `uniqueness.py`) with zero private metric forks. Withhold whole fault components with a 3-pixel feature-context buffer, derive catalogue features strictly from visible faults, mask visible faults pixel-exactly, and score pooled DTI (`alpha = 0.2, beta = 0.8`, `300 m` triangular kernel).
   - **LABEL EVERY NUMBER:** Every score must be labelled **`HOLDOUT-DTI`** (with evaluator version, withheld-positive count, and 95% CI) or **`ORGANIZER-CONFIRMED`** (copied verbatim from a DrivenData submission receipt). Never write a projection as a score.
   - **LEAKAGE CANARY:** Test every single feature alone on held-out positives; symmetric `AUC > 0.90` means leakage until disproven.
   - **RUN CARD:** Machine-readable JSON run card (`registry/run_card.json`, synced byte-for-byte to `docs/data/run-card.json`, `docs/run_card.json`, and `evidence/run-card.json`) recording hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation/overlap, raster SHA-256, validator output, unique name + `<= 140`-character note, and `promote / negative` verdict.
   - **BUDGET:** At most **3 experiments or 2 hours**. Promotion to a weekly competition slot is strictly separate.
   - **THREE-PASS WORKFLOW:** Pass 1 implement & verify; Pass 2 review bugs, missing requirements, edge cases & fix; Pass 3 re-verify line-by-line against original prompt, commit cleanly, open PR, and merge into `main`.

---

## Measured Results Summary (`2026-10-22` — 3/3 Experiments Complete)

### 1. Three-Experiment Blocked-Holdout Progression (`gems57-pooled-hide-v2`, `n = 22,893`)

| Exp | Method / Lane | Catalogue Features? | `HOLDOUT-DTI` & 95% Block-Bootstrap CI | Paired Gain vs `Exp 01` | Emitted Dots / Key Terms |
|---|---|---|---:|---:|---|
| **`Exp 01`** | `MGC-88` (7-ch RTP/gravity co-edge HGB + fixed 2-px spacing, retained control) | None | **`0.0389`** `[0.0263, 0.0526]` | baseline | `37,654` prod dots (`TP_w = 1,269.4`, `FP_w = 70,352.8`) |
| **`Exp 02`** | `H88-UGFV-BlindPhys` (32-ch zero-catalogue physics: `60 deg` basement advection, `deq/ieq` swarm excess, GeoDAWN `K/Th` & `U/Th`, 1-m LiDAR scarps + 10-m `chi`-knickpoints with Lahontan shoreline veto, DOE GDR 1391 2-m probes & sinter vents + CELF submodular) | **Zero** (`0` fault channels) | **`0.0894`** `[0.0762, 0.1011]` | **`+0.0505`** `[+0.0352, +0.0650]` (**`2.30x`**) | `TP_w = 3,534.4`, `FP_w = 102,538.5` |
| **`Exp 03`** | **`H88-UGFV-Submod`** (Independently fitted 32-ch blind physics + 48-ch strictly nested self-masked fault-tip beam/relay completion fused out-of-sample via Noisy-OR + Dinkelbach CELF submodular emitter) | Strictly fold-visible (`vis` only) | **`0.1770`** `[0.1618, 0.1921]` | **`+0.1381`** `[+0.1209, +0.1555]` (**`4.55x`**) | **`22,545` prod dots** (`TP_w = 5,739.7`, `FP_w = 64,836.8`) |

### 2. Automated Safety, Leakage & 138-Raster Uniqueness Gates

| Gate | Automated Measurement | Source Receipt |
|---|---|---|
| **GeoTIFF & 1-TIFF ZIP format** | **PASS (`100%`)**: 1 band `float32`, `EPSG:32611`, `3730 x 3292`, `100 m` grid `(100, 0, 243350, 0, -100, 4508550)`, `0` NaN/Inf across all `12,279,160` cells, values strictly `{0.0, 1.0}`, `nodata=None`, `0` on mapped public faults, byte-matching single-TIFF `.zip` | [`gems88-ugfv-submod-22545-20261022-v2-DO-NOT-SUBMIT.json`](docs/downloads/gems88-ugfv-submod-22545-20261022-v2-DO-NOT-SUBMIT.json), [`scripts/validate_release.py`](scripts/validate_release.py) |
| **Single-feature leakage canaries** | **PASS (`48 / 48`)**: max symmetric single-feature AUC across all `32` static physics + `16` fold-visible structural channels is **`0.8321 <= 0.90`** | [`registry/leakage_canaries.json`](registry/leakage_canaries.json) |
| **Pre-placement surface Spearman (`138` unique rasters)** | **PASS (`138 / 138`)**: max `|rho| = 0.7222 <= 0.90` across all `138` SHA-256 unique accessible family GeoTIFFs (`rho(H33) = +0.0558`, `rho(dense_prior) = +0.7222`) | [`registry/preplacement_registry.json`](registry/preplacement_registry.json) |
| **Post-placement 3-px dot overlap (`134` genuine fault rasters)** | **PASS (`134 / 134`)**: max 3-px forward dot overlap across all non-space-covering fault rasters (`footprint_3px_cov <= 0.70`) is **`0.6841 < 0.70`** (`H33 = 0.3037`, pixel Jaccard `0.0080`) | [`evidence/uniqueness-audit-139.json`](evidence/uniqueness-audit-139.json), [`registry/final_registry.json`](registry/final_registry.json) |
| **Literal any-raster gate (`4` space-covering witnesses)** | **FAILS LITERAL RULE (`ok_to_submit: false`, `verdict: "negative"`)**: 4 calibration probes cover `73.97%–100.00%` of the footprint with their 3-px halo (`dense_17gemdoe.tif` = `1.0000`) | [`registry/witness_certificate.json`](registry/witness_certificate.json), [`registry/run_card.json`](registry/run_card.json) |

---

## PhD Forensic Analysis: Why Owner-Reported `GEMSDOE32` (`H33`, `0.2778`) Rose — and How to Beat It

Owner-reported sibling scores (`H19-5: 0.1922`, `D1.5: 0.2477`, `D2.8: 0.2600`, `H33: 0.2778`, `PINN: 0.2627`) are **USER-REPORTED, NOT ORGANIZER-CONFIRMED** (no submission-page receipt exists in this repo). Pixel-exact inspection across all `138` unique family GeoTIFFs proved the complete mathematical story:

1. **100.0% Identical Off-Catalogue Geometry (`IR-88-08`):** Outside Euclidean distance `d_cat <= 2.0 px` from public faults, `D2.8` (`44,090` total dots), `H32-1` (`39,825`), `H27-4` (`37,654`), and `H33` (`37,654`) share **the exact same 37,654 pixel coordinates (`100.000%` identity)**! Not a single off-catalogue prediction moved.
2. **Exact Tversky Hyperbola (`R^2 = 0.9994`):** Because mapped public faults are excluded from hidden ground truth, dots inside `d_cat <= 2 px` received virtually zero truth coverage `T` while adding `0.2 * n_near` false-positive weight to the denominator `0.2 * (T + S - M) + 0.8 * |G|`. Regressing `1 / DTI_reported` on `n_near` across `H19-5 -> D1.5 -> D2.8 -> H33` gives **`R^2 = 0.9994`**!
3. **Why `PINN` (`0.2627`) Dropped:** `PINN` kept `100.0%` of `H33`'s `37,654` dots and appended `1,200` extra dots whose marginal expected coverage fell below `[0.2 * DTI / (1 - 0.2 * DTI)] * (1 - m_self) ~= 0.059`.
4. **Why `H33` Hit a Dead Ceiling vs `#1` (`0.4413`):** Once `n_near(d_cat <= 2) = 0`, zero-credit near-catalogue pruning is `100%` exhausted. Advancing from `~0.28` toward the verified live leaderboard leader (**`0.4413`**, `#1 xiaofanhu` on `2026-10-22`, superseding the prompt's stale `0.3195`) requires genuinely superior **blind off-catalogue physics + geothermal fluid observables + submodular 300-m kernel allocation**, which is why `H88-UGFV` achieved a **`4.55x` gain (`0.0389 -> 0.1770`)** on identical held-out components while sharing only `30.37%` 3-px proximity with `H33`.

---

## Autonomous End-to-End Reproduction (Zero Human Input, CPU Only)

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/restore_inputs.py                  # restores SHA-256 verified grid, 19-band features, 13 open USGS/GDR datasets & all 139 family rasters
.venv/bin/python scripts/run_ugfv_experiments.py            # executes 3-experiment ladder, 48 leakage canaries, 138-raster audit & writes flagship GeoTIFF + ZIP
.venv/bin/python scripts/validate_release.py                # independently re-reads GeoTIFF & ZIP bytes (exit 0)
.venv/bin/python scripts/validate_release.py --require-submit  # intentionally exits 2 (blocks accidental portal upload under literal witness gate)
.venv/bin/python -m pytest -q
```

---

## Remaining Limitations & Concrete Next Steps

1. **Formal Selector Protocol Amendment (`IR-88-01` / `IR-88-13`):** The human/portfolio selector should explicitly scope the `<= 0.70` 3-pixel dot-overlap uniqueness rule to genuine fault-prediction rasters (`footprint_3px_cov <= 0.70`), formally excluding space-covering calibration surfaces (`dense_17gemdoe.tif`, `calib_r13lattice_00904.tif`, `r14_union_tips10_lat6.tif`, `r11_greedy_mp.tif`) without ad-hoc code overrides.
2. **Authenticate Official Competition Sample (`IR-88-02`):** Verify byte/grid parity directly against an authenticated DrivenData download of `sample_submission.tif` prior to spending any weekly feedback slot.
3. **Out-of-Fold Cross-Fitted Physics × Tip Interaction (`IR-88-12`):** In a future run, compute K-fold out-of-fold physics probabilities inside each training quadrant before fitting the nested structural model so tree splits can explicitly learn `up-dip gravity gradient × fault-tip propagation beam` interactions without PU memorization.
4. **Known-Catalogue Proxy Caveat:** Withheld segments come from mapped USGS/INGENIOUS faults, whereas Round 2 (`$250K`) adds newly expert-interpreted blind geothermal faults; DOE GDR 1391 thermal/sinter and up-dip basement channels (`Exp 02: 0.0894`) specifically hedge against pure catalogue extrapolation.
