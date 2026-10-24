# H88-CTRA: Conductivity-Terrain Rupture Anisotropy — Ranked Hypotheses and Validation (2026-10-24)

**Lane:** `H88-CTRA` (single method, zeros encoding, no private metric fork)  
**Preregistration ID:** `PREREG-20261024-CTRA`  
**Artifact:** [`gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.tif`](../downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.tif) ([ZIP](../downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.zip)) · [JSON Run Card](../../registry/ctra_run_card.json)  
**Status:** `DOWNLOAD FOR RESEARCH: YES` · `SUBMIT: NO — RESEARCH ONLY` (format-valid, uniqueness like-for-like PASS, holdout pending/negative on 4-fold quick instrument; see §5)

---

## 0. Why `h33-h33-2-b2` (CLAIM 0.2778) led the owner's fleet and whether we can beat it — PhD-level assessment

**Evidence labels:** `HOLDOUT-DTI` = local hide-and-recover instrument; `CLAIM` = user-reported live score with no portal receipt in this repo; `ORGANIZER-CONFIRMED` = verbatim copy from DrivenData receipt (none in this repo); `OBSERVED-PUBLIC` = read from [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (2026-10-24).

### 0.1 Ground truth from official sources (verified this session)

| Fact | Evidence | Link |
|---|---|---|
| Public #1 = 0.4413 (xiaofanhu), #5 = 0.3539, #50 = 0.2818 | `OBSERVED-PUBLIC` 2026-10-24 ([docs/data/leaderboard.json](../data/leaderboard.json)) | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> |
| CLAIM 0.2778 would rank **below #50** | same page | same |
| Metric: `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)`, `k(d)=max(1-d/300m,0)` | `vendor/gems57/metric.py` transcribed from problem page | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> |
| Format: single-band float32, `EPSG:32611`, 100 m, values in `[0,1]` | problem page | same |
| Portal error `Predicted values must be in range [0,1]` means NaN/sentinel/out-of-range | reproduced locally on `nan` outside-footprint files (see §3) | <https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/> |

**Diagnosis of the owner's sites:** The 60+ GEMSDOE sites cluster `h16→h19-4→h19-5→d1-5→d2-8→h27-4→h33` shows two separable geometric optima that align exactly with the DTI algebra (see [session-20261024-audit-why-0.2778.md](session-20261024-audit-why-0.2778.md) and [evidence/lineage_live_vs_geometry.json](../../evidence/lineage_live_vs_geometry.json)):

| Raster | CLAIM | dots | median d_cat | NN spacing | share >25px |
|---|---:|---:|---:|---:|---:|
| h16-1 / h19-4 / h19-5 | 0.1855–0.1922 | ~121k | 14.6–14.9 px | 1.0 px (89% <2px) | 0.35 |
| d1-5 | 0.2477 | 60k | 14.9 | 2.24 | 0.35 |
| d2-8 | 0.2600 | 44k | 15.0 | 3.0 | 0.36 |
| h27-4 | 0.2708 | 40k | 17.7 | 3.0 | 0.39 |
| **h33 (R0)** | **0.2778** | **37,654** | **19.7** | **3.0** | **0.42** |

1. **Kernel de-redundancy:** 121k → 44k with NN 1.0 → 3.0 px lifts CLAIM 0.192 → 0.260 at constant distance (the 300 m triangular kernel double-charges FP inside one radius; spacing ≥3 px makes dots kernel-disjoint).  
2. **Moving mass off catalogue:** 0.260 → 0.278 coincides with ≤3 px share falling 19.5% → 5.8% and catalogues-hugging controls 0.004–0.111.

Spearman(median d_cat, CLAIM) = 0.891 (n=13, descriptive only; lineage members share tuning history, so part of the score is information about the public labels that no local holdout can reproduce—R0 scores 0.004 on hide-and-recover *by construction* [IR-88-20]).

### 0.2 Can we beat 0.2778?

**Not demonstrable locally; no file in this repo is cleared to try.** `H88-CTRA` reproduces the two geometric optima (spacing 3.0 px, median 23.4 px, 47% >25 px) and is format-valid and like-for-like unique (worst 0.304 ≤0.70), but:

* Its 4-fold quick `HOLDOUT-DTI` is **0.0** on the `all` buffered instrument (vs null 0.042), i.e. **negative** against the bar (`gems57-pooled-hide-v2` would need 8 folds for canonical comparison, but the quick screen is already below null).  
* Even a strong holdout (TDKL achieves `HOLDOUT-DTI 0.1962` vs bar 0.1896, +0.0058, 8/8 folds won) would still require a portal receipt to prove live superiority—holdout and live labels disagree on the optimum N (holdout monotone, live thinned).  
* Beating 0.2778 would still sit below rank 50 (#50 = 0.2818); 15 teams sit 0.326–0.333 and the private leaderboard may differ.

**Honest answer:** We have reproduced the *geometry* of the best public lineage and verified it is buildable without catalogue features, but we have not demonstrated a live gain over 0.2778; only a DrivenData receipt can settle it.

---

## 1. Five ranked candidate hypotheses (pre-registration ordering)

The order was fixed before `CTRA` was built (see `NEW_HYPOTHESES.md` for the ledger). Every hypothesis uses only SHA-pinned official mirrors (see `registry/data_manifest.json`).

| Rank | ID & Title | Layers (verified) | Transform & Physical Signature | Why it catches **off-catalogue** faults | Named non-fault mimic | Diff from existing lanes | Expected DTI lift / Cost |
|---|---|---|---|---|---|---|---|
| **1 (built)** | **`H88-CTRA: Conductivity-Terrain Rupture Anisotropy`** | `training_features` B17 `cond_surf`, B11 `iso_grav_anom_vg`, B15 `depth_to_base_surf`; `topo_10m_derived` `curv_prof_absmax`, `aspect_coherence`, `relief_local` | Conductivity horizontal-gradient + profile-curvature trough + gravity-VG Hessian trough + basement-depth gradient co-occurrence, mimic-penalized by `relief·(1-coherence)`; Poisson disk 3.0 px, collar 3 px, all-finite zeros | Blind intra-basin faults under 5–50 m alluvium have no scarp (`det_elev_slope` low, mapper omits) but retain clay-gouge conductivity and basement step in `iso_grav_vg`/`depth_to_base` | Playa evaporite circular conductive rims (penalized by linear `aspect_coherence` requirement) | No lane uses `cond_surf` gradient + curvature trough as primary (TDKL=knickpoint, MVRD=monocline, QTSK=cover decoupling, KTH=K/Th) | **MODEL `+0.002 to +0.006` in piedmont/basin** / **Low** (no training, 4 pct-ranked channels) |
| 2 | `H88-DLTH: Dilatation-Tendency-Weighted Crests` | `tmi_hg` (B3), `mag_anom` (B1), `geod_shearrate` (B7), `geod_dilaterate` (B8) | `Td=(σ1-σ_n)/(σ1-σ3)` per crest azimuth from strain tensors; high-Td crests more likely to dilate and host geothermal fluid | High-Td orientations open under the ambient stress where catalogue is incomplete; strike alone (h67a, CLAIM 0.0356) lacked a stress model | Lithologic contacts with same strike | Orientation-only lane lacked `Td` | `+0.001 to +0.004` / **Medium** (needs σ1/σ3 azimuth) |
| 3 | `H88-SOSC: Scale-Persistence of Crests` | B19 `det_elev_slope`, B3 `tmi_hg`, B18 `iso_grav_anom_hg` all at σ=1,3,6 px | Real fault expression persists across smoothing scales; 400 m flight-line seams and noise do not | Seams agree across derived gradients at one scale but not across scales | Flight-line leveling corrugation (400 m) | Overlaps `xscale-worm-persistence` (CLAIM 0.0581) — lane risk | `+0.001` / **Low** |
| 4 | `H88-RDC: Relief-Conditioned K/Th Alteration` | GeoDAWN K/Th/U (4 bands), `relief_local`, `det_elev_slope` | K/Th enrichment on piedmont fault zones without modern springs, conditioned on piedmont relief | Alteration haloes survive where springs are extinct | Felsic tuff K-high contacts | Unrun in this repo | `+0.001 to +0.003` / **Medium** |
| 5 | `H88-CJTP: Crest-Junction / Termination Prior (Favorable-Structural-Setting from crests, not catalogue)` | Crest masks of B19, B3, B18 built in `build_provcrest_submission.py` | Thin crest mask; endpoints (horse-tailing), T/X junctions, overlapping parallel crests (step-overs) — step-overs ~32% and terminations ~25% of 250 Great Basin fields ([Faulds & Hinz 2015](https://www.osti.gov/servlets/purl/1724082)) | Computed from geophysics alone, applies where no fault was mapped; relay ramp width 2.5 km ([Giddens 2025](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf)) >> 3 px kernel | En-echelon volcanic flow margins | Catalogue-geometry relay lanes use mapped faults; this uses crest geometry | `+0.002 to +0.005` / **Low** |

**Single-paragraph lane:** `H88-CTRA` above is the lane for this session. Surface Spearman `|ρ| ≤0.90` is checked pre-placement and forward 3 px overlap `≤0.70` post-placement against every registry raster; dense priors are not silently exempted (both readings reported, `like-for-like` is binding under `gems88-gate-v3`).

---

## 2. What we actually built (H88-CTRA, 4 channels, zero catalogue access)

```python
# footprint = sample_submission finite; catalogue = (existing_faults >0) & footprint
# allowed = footprint & (distance_to_catalogue > 3 px)  # collar ensures share_le2 = 0
# cond = safe_band(B17 cond_surf); curv = safe_band(curv_prof)
# grav_vg = safe_band(B11); depth = safe_band(B15)
# cond_grad = grad_mag(cond, σ=1.0) -> pct_rank
# curv_pct = pct_rank(curv)
# grav_trough = hessian_trough(grav_vg, σ=1.5) -> pct_rank
# depth_grad = grad_mag(depth, σ=1.5) -> pct_rank
# mimic = (relief/255)·(1 - coherence/255) -> pct_rank
# surface = 0.35·cond_grad + 0.25·curv + 0.20·grav_trough + 0.20·depth_grad - 0.15·mimic
# surface = clip(surface,0,1); surface[~footprint]=0
# dots = PoissonDisk(surface, allowed, N=36000, min_sep=3.0 px, seed=88)
# out[dots]=1 else 0; write float32 zeros-encoding via vendor.grid.write_submission
```

*Every feature is derived from official 19-band or pinned external u8 bands alone; no `existing_faults` distance, trace geometry, or label-derived column enters the feature stack.* Leakage canary: 4 single-feature symmetric AUCs sampled on withheld-vs-negatives were `cond 0.52, curv 0.51, grav_vg 0.53` (all `≤0.90`, PASS; method: Seed-20 `all` pooled, 8× off-trace negatives; see `scripts/build_h88_ctra_submission.py`).

---

## 3. Production artifact

| Field | Value |
|---|---|
| **File** | [`docs/downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.tif`](../downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.tif) |
| **ZIP** | [`gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.zip`](../downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.zip) (single-TIFF, byte-identical) |
| **JSON** | [`docs/downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.json`](../downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.json) |
| **SHA-256 (tif)** | `bfc4a492a00961c4f44622ae2ec5c0a092268e715959879ca3c1cf739d5582b7` |
| **SHA-256 (zip)** | `506bb595c41549bcb6fcc1807166fac163e2e6845e52bc7f94fff351396b1479` |
| **Tags** | `float32`, `EPSG:32611`, `3730×3292`, `100 m`, `LZW`, `strip 1×3292`, `nodata=None`, classic TIFF |
| **Values** | all finite, `{0.0,1.0} ⊂ [0,1]`; `0` outside footprint; `0` on `existing_faults` (`min_d_cat = 3.16 px`) |
| **Positive pixels** | `36,000` (`0.697%` of 5,167,373 footprint cells) |
| **Portal validation** | `gems88-gate-v3 portal_validate`: **`ok: true`**; `all_finite: true`, `portal_range_check_nan_strict: true`, `outside_footprint_zero: true`, no second-decoder mismatch on rasterio re-open |
| **Fingerprint** | `median_d_cat = 23.41 px`, `share_le2 = 0.0000`, `share_gt10 = 0.7704`, **`share_gt25 = 0.4747 ≥ 0.35`** (**PASS**) |
| **Why `zeros` and why this fixes `Predicted values must be in range [0,1]`** | `nan`-outside files declare `nodata=nan` and store `NaN` outside the footprint; both the reference solution's `nanmin/nanmax` and some portal validators evaluate `NaN` as out-of-range. This file uses **`zeros` encoding**: every cell finite, outside-footprint `0`, `nodata=None`, `min 0.0 max 1.0`. |
| **Name (49/140)** | `gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT` |
| **Note (96/140)** | `H88-CTRA cond gouge+curv trough+grav step 36k dots zeros [0,1] portal-valid; HOLDOUT pending/negative` |
| **Live status** | `UNSCORED` (0 weekly slots spent) |

---

## 4. Uniqueness audit (vs 35-raster sample; dense witness diagnostic included)

| Check | Result | Binding reading (`gems88-gate-v3` like-for-like) |
|---|---|---|
| **Sparse like-for-like 3 px forward overlap** (`35` rasters, incl. `h33`, `TDKL`, `QTSK`, `GTHC`, `MVRD`, `PROVCREST`) | **PASS** — worst `0.3039` vs `PROVCREST` (`limit 0.70`) | **PASS** |
| **Forward overlap vs dense witness** `dense_17gemdoe` (5,167,373 positive footprint cells) | **literal `1.0000 >0.70`** (every non-empty raster scores 1.0); **`like_for_like 0.0177 ≤0.70`** (top-36k by value, `0.0177`) — literature `vacuity_witness` proves a *seeded random* raster also scores literal `1.0`, so literal `0.70` cannot discriminate | **Not binding** — dense is `like-for-like` under v3; literal `1.0` is reported but not a lane-exclusion |
| **Pre-placement surface Spearman** (`|ρ|`) vs sample (`200k` footprint cells) | **PASS** — max `|ρ| = 0.11` vs dense (`limit 0.90`) | **PASS** |
| **Recent stratified lanes individually** | vs `h33 0.209`, vs `TDKL 0.164`, vs `QTSK 0.274`, vs `GTHC 0.252`, vs `MVRD 0.156` (all `≤0.70`) | **PASS** |

*Full 206-raster `data/registry + data/siblings + docs/downloads` scan was used to select the 35-raster representative reported above; the full log is in `docs/data/ctra_run_card.json` (`quick_uniqueness_sample` vs the `uniqueness_report` `worst_like_for_like_overlap 0.3039`). No bytes were copied from any prior submission; the surface is byte/pixel distinct.*

---

## 5. Holdout validation (what the instrument actually says)

**Instrument:** `holdout.build_holdout` buffered whole-components, 4 folds (`seed 20`, `all` mode), evaluator `holdout.evaluate` (pooled DTI, `α=0.2, β=0.8, 300 m` triangular kernel, `domain erode 12 px`, scoring `active = domain & ~visible`, `truth = hidden & domain & active`). This is the quick 4-fold analogue of the 8-fold `gems57-pooled-hide-v2` ensemble used for TDKL (which reports `HOLDOUT-DTI 0.1962`).

| Arm | Pooled HOLDOUT-DTI | Pooled TP/FP/FN (`n_truth`) | Verdict |
|---|---|---|---|
| **`H88-CTRA` (fixed 36k dots)** | **`0.0000`** | `0.0 / 30,964 / 11,318 (11,318)` | **Negative** (below null) |
| `null random 36k` (same N, footprint-uniform) | `0.0416` | — | Baseline |
| `h33` (fixed, full-catalogue built) | `0.0044` | — | Diagnostic (built on full catalogue, IR-88-20) |
| `TDKL` / `MVRD` (fixed re-score, same instrument) | `0.00002 / 0.00005` | — | Diagnostic (fixed re-score suppressed vs fold-fair training) |

**Interpretation:** On this quick 4-fold `all` instrument the handcrafted 4-channel surface sits farther (median 11.4 px) from the withheld truth than a footprint-uniform random allocation, so **no submission slot is spent**. A proper 8-fold `gems57-pooled-hide-v2` pooled comparison (the protocol's canonical instrument) was not run for CTRA in this session; TDKL's 8-fold win (`+0.0058`, 8/8 folds, `95% CI [0.001174,0.010109]`) remains the current holdout best (see [research/hypotheses-20261024-tdkl88.md](hypotheses-20261024-tdkl88.md)). CTRA is published **as a format-valid, like-for-like-unique research artifact** whose science case (blind-basin conductive clay gouge) remains unvalidated on this holdout and is carried as `HOLDOUT pending/negative`.

All `HOLDOUT-DTI` numbers are labeled with evaluator version and withheld-positive count; none is `ORGANIZER-CONFIRMED`. TDKL's 8-fold numbers above are `HOLDOUT-DTI (gems57-pooled-hide-v2, 22,893 withheld overall, 10,791 far >10 px, 3,117 blind >25 px)`.

---

## 6. What remains to beat 0.2778 / 0.4413 and when to spend a slot

1. **Improve holdout before any slot.** The next experiment should re-train a fold-fair `HGB` on CTRA's 4 conductivity-curvature channels (and the already-proven `phys44` stack) and re-score with `gems57-pooled-hide-v2` (8 folds, `seeds 20+21`). Promotion requires beating `H88-ADHR`/`TDKL` with **paired 95% CI >0** on both `overall` and `far >10 px`, and preferably lifting `blind >25 px` (CTRA's design region).  
2. **Keep the next lane stratified.** CTRA's `share_gt25 = 0.475` is sound for blind basins but may under-cover relay zones; the two-stratum `14.5k / 10.5k` split proven by TDKL should be retained.  
3. **Budget discipline.** At most one more holdout-verified lane per week; the selector slot remains **human-only** (NLR rules §§3.4–3.5, ≤3/week).

---

## Appendix — Verified official sources used

| Item | Official source | How it was used |
|---|---|---|
| Problem & metric | [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | DTI formula, 300 m kernel, α/β |
| Leaderboard | [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (read 2026-10-24) | #1 0.4413, #50 0.2818 |
| Submission form | [DrivenData submissions](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/) | `File to submit` + `Note (optional)` |
| Reference solution | [GEMS prize reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | U-Net baseline |
| USGS GeoDAWN | [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | magnetic/radiometric grids (CC0) |
| 3DEP DEM | [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) | 10 m DEM/χ, 1 m LiDAR slopemask |
| GDR INGENIOUS | [GDR submission 1391](https://gdr.openei.org/submissions/1391) | `labels.tif` provenance |
| Data manifest | `registry/data_manifest.json` (SHA-256 pinned) | Owner-mirrored 19-band / external hashes |

> **No new external data was introduced in this lane**; all 4 bands are already in `registry/data_manifest.json` and verified via `scripts/restore_inputs.py`.

---

## Reproduce

```bash
python scripts/restore_inputs.py --validation   # bridge grid + core registry
python scripts/build_h88_ctra_submission.py      # ~30 s, writes docs/downloads/... + registry/ctra_run_card.json
# Portal check (all must be true)
PYTHONPATH=vendor:src python -c "from gems88.gate import portal_validate; from gems57 import grid; ..."
# Uniqueness (like-for-like, 35 rasters, ~22 s)
# Holdout quick screen (~6 s)
```

## Irregularities flagged

* `data/siblings` inventory (IR-88-76 vacuity) makes the literal `>0.70` test unsatisfiable; reported but not bound under `gems88-gate-v3` (see `src/gems88/gate.py::vacuity_witness`).
* No `ORGANIZER-CONFIRMED` score exists for any GEMSDOE88 file; every live number cited is `CLAIM` per the ledger.
* CTRA's quick holdout is below null; it is **negative** as a selection candidate but remains a deliverable (the brief's `Negative results are deliverables`).

