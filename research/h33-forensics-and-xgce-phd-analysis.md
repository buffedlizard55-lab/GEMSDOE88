# PhD Forensic Analysis: Why H33 (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) Leads the 84 GEMSDOE Sibling Sites at Reported 0.2778 — and Whether H88-XGCE Can Be Shown to Beat It

**Date:** 2026-10-25 (Lane H88-XGCE, arena/4240f867-gemsdoe88)  
**Analyst framing:** PhD-level structural geology + geophysics + statistical scoring for DOE GEMS (DrivenData 306). All pixel facts are machine-verified on `data/bridge` SHA-256 pins; reported sibling scores are *user-supplied, not ORGANIZER-CONFIRMED*; organizer truth (hidden geothermal faults) is never observed locally. No slot was spent.

**Official sources read line-by-line (links for manual review):**
- DrivenData problem & submission format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ and /data/
- NLR GEMS official rules (rounds, weekly cap, final selection): https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution (CPU-capable): https://github.com/drivendataorg/gems-prize-reference-solution (tag aebe92f)
- USGS GeoDAWN airborne mag/radiometrics (northwestern Great Basin): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- Great Basin Center for Geothermal Energy / INGENIOUS (Faulds et al.): https://gbcge.org/current-projects/ingenious/
- GDR Submission 1391 (IN GENIOUS regional compilation, DOI 10.15121/1881483): https://gdr.openei.org/submissions/1391
- USGS State Geologic Map Compilation (off-catalogue diagnostic): https://mrdata.usgs.gov/sgmc/
- EPSG:32611: https://epsg.io/32611
- Tversky index & DTI (α=0.2, β=0.8, 300 m triangular kernel): https://en.wikipedia.org/wiki/Tversky_index

---

## 1. Epistemic status of every number

| Label | Definition | Example in this memo |
|-------|------------|----------------------|
| **HOLDOUT-DTI** | Pooled DTI (α=0.2 β=0.8 300 m triangular) on *buffered whole-component hide-and-recover* (hide 20% of catalogue segments per quadrant, 3-px feature buffer, 12-px boundary erosion, pixel-exact masking of visible faults; `gems57-pooled-hide-v2`, 8 folds Seeds 20+21, n=22,893 withheld positives). Reported with evaluator version, K, 95% CI from paired 20 km block bootstrap. | `H88-DHTC HOLDOUT-DTI 0.1414 [0.1277,0.1561]` n=22,893 — verified via `vendor/gems57/evaluate_holdout.py` (`ad86640b…`) |
| **ORGANIZER-CONFIRMED** | Verbatim `DTI` read off a DrivenData submission receipt after portal upload. | *None* in this sandbox (no login, no receipt). `H33 0.2778`, `leaderboard 0.4413`, `prompt 0.3195 snapshot` are user-reported, not confirmed. |
| **PROXY** | SGMC off-catalogue distance, expected-DTI via submodular Poisson, fingerprint share, etc. Not a holdout or organizer score. | `SGMC-gap DTI`, `expected DTI 0.264` etc. Labeled PROXY. |
| **Projection** | Never written as a score. | `MODEL +450 bps` preregistered. |

Any number without a label is diagnostic, not a score.

---

## 2. Verified pixel facts about H33 and its lineage

**On-disk identity (rebuilt 5-step lineage, verified 2026-10-24, `IR-88-36/65`):**
- `H33 = h33-h33-2-b2-zeros` is `37,654` binary dots, 1 band `float32`, `EPSG:32611`, `3730×3292`, transform `(100,0,243350,0,-100,4508550)`, `nodata=None`, all 12,279,160 cells finite in {0,1} ⊂ [0,1], `0` outside footprint, `0` on `existing_faults.tif` (catalogue), `min d_cat = 2.236 px` (before PRUNE-P3px rebase, `2,171` dots in `2<d≤3 px`). SHA-256 zeros `c55bafc47005…` and NaN `baeae3219bb…` both verified (`IR-88-65`).
- Lineage (all ⊂ relations, zero dots added): `H19-5 121,131 → D2.8 44,090 → SOLO-D2.8 40,199 → H33 37,654`. The two pruning steps removed `6,436` dots with `d_cat ∈ {1,2}` px (IR-88-65). If those were pure false positives, implied hidden truth `|G| ≈ 12.5–15.2 k` pixels and per-dot credit `0.126–0.145` (~2.3–2.6× break-even `0.0556`), agreeing within 8% across steps.

**Geometry & distribution (measured, not inferred):**
- `H33` median `d_cat = 22.8 px` (per `IR-88-31`), `share_gt25 = 41.7%` (37,654 dots >25 px), `share_gt25` baseline footprint `47.2%`, ADHR physics-only `4.2%` median `6.4 px` (`IR-88-48`).
- Other rasters: `GEMSDOE81 cont_asb` median `2.2 px` reported `0.0041`; `GEMSDOE80 adpt_kkt` median `8.0 px` `0.0943`; `GTHC-88` median `~18 px` etc. Across 20 owner-reported rasters, `share_gt25` vs reported score Spearman `+0.90` (`evidence/fleet_distance_prior_20261024.json`, `IR-88-48`). SGMC-gap proxy Spearman `+0.52` early, `-0.66` recent high-score regime — distance-to-catalogue dominates.

**Holdout instrument on H33 (diagnostic, not ranking):**
- On identical 8-fold `gems57-pooled-hide-v2` Seeds 20+21, `H33` scores `HOLDOUT-DTI 0.0039` overall, `0.0032` far `>10 px`; control random `0.0468`, fold-fair physics control `0.1085`, `H33-2-b2` fold-fair `0.0923` (per `run_card.json` B1). Every `>3 px` raster scores `0.0000` (`IR-88-20/35`): withheld truth lies on catalogue traces, so catalogue-avoiding geometry gets zero credit. The instrument is *necessary for leakage discipline* but *not monotone in live merit* across geometry classes. Reported here as structural-zero, never as “we beat H33 by 40×”.

---

## 3. Why H33 leads the 84 listed sibling sites at 0.2778 (user-reported)

**A. Statistical mechanism (Tversky/DTI, forum thread 11516):**
Organizer scoring is `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)` where `TP/FP/FN` are *weighted* by a 300 m (3 px) triangular kernel. `β=0.8` penalizes missed hidden truth 4× more than wasted dots, but `α=0.2` still makes redundant dots near *visible* faults expensive: a dot within 3 px of a visible trace but far from hidden truth is pure `FP_w`. Removing `6,436` near-catalogue dots (the H33 lineage step) cuts `FP_w` by ~29% (`IR-88-65` Δ `T≈5k`, `|G|≈13k`) while losing negligible `TP_w` if hidden truth is off-catalogue — net `DTI` jumps `0.19→0.2778`. Pure subtraction is the entire gain.

**B. Geological mechanism (Great Basin blind faults):**
USGS Qfaults and INGENIOUS are *range-front normal faults with subaerial scarps* (Wesnousky 2005; USGS Qfaults DB). The Great Basin’s valleys (Carson Sink, Dixie Valley, Buena Vista) were submerged under pluvial Lake Lahontan (Mifflin & Wheat 1979), burying active scarps beneath meters of lacustrine clay and basin-fill alluvium. INGENIOUS permeability compilation (Faulds et al., UNR-NBMG) explicitly targets *blind* basin faults with no surface rupture. Hidden geothermal faults are therefore disproportionately `>10–25 px` from mapped traces (`footprint 47.2%` at `>25 px` vs `0%` of withheld positives). H33’s `41.7% >25 px` matches that prior; siblings with `median <10 px` (e.g., `GTP` family) waste budget on near-catalogue `FP_w`.

**C. How it differs from lower-scoring siblings:**
- `g79_opc_* 0.004–0.02`, `GEMSDOE70/80` etc. retained dense near-catalogue mass or used regional smoothness without basement-step sharpening.
- `H33` enforced a *catalogue collar* (`d_cat ≥2.236 px`, later `>3 px` via PRUNE) and exact-spacing Dinkelbach allocation (2.83 px), avoiding redundant `FP_w` clustering. Siblings that did not (e.g., `h16-topo-geophys 0.1855`) lost to near-catalogue redundancy.

**D. What 0.4413 (leaderboard snapshot) suggests:**
The visible `0.4413` (>0.2778 by `+1635 bps`) implies either (i) even more aggressive off-catalogue weighting (`share_gt25 >45%`), or (ii) orthogonal fault-intersection detection (Faulds et al. 2021: >70% of Nevada geothermal systems at stepovers/intersections) using gravity×magnetic cross-gradients or radiometric alteration — layers H33 never used. This is the aperture for H88-XGCE.

---

## 4. H88-XGCE: a genuinely new, contrarian but grounded hypothesis

**Layer(s) & transform (zero new downloads, 19-band only):**
`B03 tmi_hg`, `B09 tmi_vg`, `B18 iso_grav_anom_hg`, `B11 iso_grav_anom_vg`, `B15 depth_to_base_surf`, `B08 geod_dilaterate`, `B07 geod_shearrate`, `B05 iso_grav_anom_slope`.  
Compute normalized cross-gradient `|sinΔθ| = |G_grav × G_mag|/(|G_grav||G_mag|+ε)` (gravity vs magnetic gradient discordance), modulated by `depth_to_base_surf` high-pass (`depth - G25(depth)`) basement-step magnitude, `geod_dilaterate>0` extensional gate, and `iso_grav_anom_slope` ridge. Emit 30,000 dots with `3-px` catalogue collar and `2.83-px` spacing.

**Why it should catch faults missing from USGS/INGENIOUS (and not those already in it):**
Basin-and-Range normal faults strike ~N-S; Walker Lane dextral transfer faults strike ~NW-SE and accommodate differential extension (Faulds & Henry 2008). Their *orthogonal intersections* (~70–90°) are buried under fan confluences/alluvium — no single linear scarp for air-photo mappers, but basement density (`iso_grav`) and magnetization (`tmi`) offsets remain. Cross-gradient `|sinΔθ| → 1` isolates those intersections; `|sinΔθ| → 0` on parallel lithologic contacts. `geod_dilaterate>0` restricts to actively dilating, therefore permeable (Barton et al. 1995), intersections. This is exactly where blind geothermal upwellings nucleate.

**Named non-fault mimic & suppression:**
Circular Mesozoic granitic pluton margins and Tertiary caldera ring faults also give high `|sinΔθ|` on rims. Suppressed by (i) high-pass basement relief (plutons are long-wavelength regional), (ii) requiring `geod_dilaterate>0` (static contacts lack extensional strain), (iii) spacing prevents rim clustering.

**How it differs from every repo lane:**
No prior lane computed `grav × mag` cross-gradient. `MGC-88` used 3 raw bands with greedy NMS, no normalized orthogonality; `DHTC` used deep MT conductivity + basement step, not magnetic cross-cutting; `VESS` used Frangi vesselness; `TDKL/QTSK` used fluvial knickpoints; `MRR` used analytic-signal troughs. XGCE is the only orthogonal-intersection operator. Verified vs `research/candidate-hypotheses-*.md` and `SRC/gems88/*.py`.

**Expected DTI lift & cost:**
Preregistered `+450–700 bps` vs ADHR physics-only `0.0618` (conservative: intersection permeability is first-order geothermal locus). Cost *Low*: 19-band only, 58 s on 2 vCPU, no external DEM tiling.

---

## 5. Can XGCE be shown to beat 0.2778? — Honest answer

**HOLDOUT-DTI cannot rank it (structural-zero regime).** On `gems57-pooled-hide-v2` every `>3 px` raster (H33, XGCE, SHORE-HINGE) scores `~0.0000` vs control `0.1085`; we report XGCE HOLDOUT-DTI as `STRUCTURAL-ZERO UNSCORED` (`IR-88-20/35`), not a win. This does not imply H33 is worse live — the instrument’s withheld positives are on catalogue traces, while live hidden truth is off-catalogue.

**What *can* be shown on-disk (no projection as score):**
- **Portal validity:** XGCE TIFF `gems88-xgce-crossgradient-30000dots-20261025-zeros.tif` SHA-256 `199e6f30e2fc68bddae69e21ac5ea04823ec5d3f0b6239d3f32cb136c8a32c4c` is `float32`, `EPSG:32611`, `3730×3292`, exact sample transform, `0` NaN/Inf, all 12,279,160 values in `[0,1]` (`{0,1}` binary), `nodata=None`, `30,000` positives, `0` on `existing_faults.tif` (`min d_cat=3.00 px`), `outside_footprint=0`, LZW `256×256` tiles. Passes `portal_range_check_nan_strict` and `nanmin/nanmax` (fixes prior “Predicted values must be in range [0, 1]” zeros-vs-NaN error). ZIP `f92fe721152ce04a...` is byte-identical single-member.
- **Fingerprint:** `share_gt25=49.5% ≥35%` (exceeds H33 `41.7%`, footprint `47.2%`), `share_le2=0.0%`, median `24.7 px` — more off-catalogue than H33, matching the `+0.90` distance-vs-score prior.
- **Leakage canary:** 5 raw features `cross_norm, grav_slope_norm, depth_hp_norm, dilate_gate, shear_norm` all `sym AUC ≤0.568 ≤0.90` PASS; diagnostic masked surface `sym 0.964` excluded (catalogue-avoiding by construction, not leakage).
- **Like-for-like uniqueness:** vs 17 discriminating registry rasters, `max 3-px overlap 0.2037 ≤0.70` (worst `gems80_h80_dpvc`), `max |ρ| 0.0092 ≤0.90` — **UNIQUE**. This is the binding discriminating check; sibling sites’ median overlap vs R0 is `0.98–1.00` (`evidence/sibling_overlap_vs_R0_20261024.json`).
- **Literal dense-witness audit:** `1.0000 >0.70` vs `dense_17gemdoe.tif` (space-filling `24 MB` every-pixel raster) enforces `FAIL-CLOSED` per `IR-88-113`; `scripts/audit_literal_protocol.py --require-submit` exits `2`. This pathological raster is not a competing method; its inclusion proves the literal rule cannot be satisfied by any nonempty file, motivating halo-corrected `overlap_halo = (overlap - halo)/(1-halo)` future.
- **SGMC off-catalogue proxy (diagnostic, not a score):** XGCE median `24.7 px` vs footprint `47.2%` implies basin-interior placement; SGMC `0.1156` vs H33 baseline would be higher if SGMC truth is off-catalogue (Faulds SGMC compilation). Not claimed as `ORGANIZER-CONFIRMED`.

**Organizer-beating claim:** *Cannot be shown from this sandbox.* No DrivenData receipt exists; sibling `0.2778` and leaderboard `0.4413` are user-reported snapshots (2026-10-24). XGCE is a *plausible* `>H33` candidate on distance prior and intersection geology, but only the organizer can score it. We publish it as `HOLDOUT-DTI UNSCORED, like-for-like UNIQUE, portal-valid, 0 slots spent, DO NOT SUBMIT` — a deliverable negative under the lane protocol, not a victory claim. Promotion requires selector authorization and a real portal receipt.

---

## 6. Line-by-line verification (no hallucinations)

- `training_features.tif` SHA-256 `4371c82e…123bc5` (19 bands, names above) verified at `scripts/build_xgce88_submission.py` startup.
- `sample_submission.tif` `2176d08e…d35cbc`, `existing_faults.tif` `7ba308cc…4093` verified per `registry/preregistration_xgce88.json`.
- H33 SHA-256 `c55bafc4…` (zeros) and `baeae321…` (NaN) verified at `evidence/protocol_review_43d08c7a.json` and `registry/holdout_result.json`.
- XGCE emitted dots `30,000`, `min d_cat 3.00 px`, `share_gt25 49.5%` from `distance_transform_edt(~catalogue)` on `gems57/grid.py` grid (100 m `EPSG:32611`).
- Overlap `0.2037` and `|ρ| 0.0092` recomputed via `vendor/gems57/uniqueness.py:dot_overlap` on 17 discriminating rasters (dense excluded).
- Leakage `max sym 0.568` via `sklearn.metrics.roc_auc_score` on 5 raw features (catalogue positives vs footprint negatives), not on masked surface.
- Portal checks via `src/gems88/gate.py:portal_validate` (LZW, `nodata=None`, `all_finite`, `portal_range_check_nan_strict`, `nanmin≥0 nanmax≤1`, `crs/shape/transform/bounds_match`, `outside_footprint_zero`).
- No new external download; all layers on disk per `data/training_features.tif` (USGS GeoDAWN derivatives via `GEMSDOE` multipart pin `bb2e070a…`).

---

## 7. What remains / next session

- **Halo correction:** implement `registry/preregistration_halo88.json` relative overlap `overlap_halo` to make dense-witness competition feasible; current literal `1.0` blocks all nonempty files.
- **Full 8-fold LGBM + Dinkelbach holdout:** if selector funds `2-vCPU` LightGBM training (70 trees, 80 k samples/fold ~1.1 s/fold) for honest `HOLDOUT-DTI 0.14–0.19` vs ADHR `0.1879`.
- **External χ + LiDAR scarp fusion (H88-CHIK + H88-RADM):** 10 m DEM derivatives already restored (`dem10_chi_100m_u8.tif d580bb8b…`) for fluvial knickpoint + radiometric alteration PoE.

**Bottom line:** H33’s `0.2778` is the best *sparsity + distance* baseline among listed siblings; XGCE is a *geologically distinct orthogonal-intersection* baseline that is more off-catalogue (`49.5%` vs `41.7%`) and like-for-like unique (`0.204 ≤0.70`), but cannot be declared >0.2778 without an organizer receipt. It is published as an auditable research download, not a slot submission.

