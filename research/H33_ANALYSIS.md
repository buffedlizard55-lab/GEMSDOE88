# H33-2-B2 (`0.2778`) — PhD Forensic Analysis

**Question:** Why and how did `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` obtain the highest user-reported score among the nine focus sites (`0.2778`), and can we generate a submission that beats it?

**Bottom line:** `0.2778` is a **USER-REPORTED CLAIM** (no DrivenData submission-page receipt exists in any inspected repository; `GEMSDOE32/registry/submission_build.json` records `"NO ORGANISER SCORE EXISTS"`). Its mechanism is a geometric refinement of the existing mapped-fault ridge skeleton — progressive thinning that moves dots off near-catalogue collar positions to reduce the DTI false-positive penalty. It is **not** demonstrated to discover new geothermal faults. Under the project's binding uniqueness rule it cannot be submitted: it is an exact 0-px subset of the `D2.8`/`SOLO-D2.8`/`H19-5` lineage, and every nonempty candidate in the allowed domain overlaps the pinned `dense_17gemdoe.tif` witness by `1.0000 > 0.70` (measured below). **No file analyzed here is cleared to submit.**

---

## 1. What was measured (IEEE-754 float64, hash-pinned inputs)

The following was re-verified directly against the pinned owner-mirror bytes restored into `data/registry/` (SHA-256 pins checked on read):

| Label | File (registry) | SHA-256 prefix | Positive dots |
|---|---|---|---:|
| `19GEMSDOE H19-5` (power-law budget multiline) | `data/registry/gems19_h19_5.tif` | `ef2ae808…` | 121,131 |
| `GEMSDOE25 D2.8` (dotted H19-5 d2.8) | `data/registry/gems25_d28.tif` | `3e78737f…` | 44,090 |
| `GEMSDOE28 SOLO-D2.8 B=1` | `data/registry/gems28_h27_4.tif` | `2fc94a38…` | 40,199 |
| `GEMSDOE32 H33-2-B2` (the `0.2778` file) | `data/registry/h33_education.tif` | `c55bafc4…` | 37,654 |
| `dense_17gemdoe` witness (universal blocker) | `data/registry/dense_17gemdoe.tif` | `ab0a0a62…` | 5,167,373 px positive |

Direct collar-distance audit (`scripts/audit_h33_collar.py`, `scripts/audit_focus_sites_20261026.py`):

* `D2.8 − H33 = 6,436` dots, **all** within `d_cat <= 2 px` of the mapped catalogue:
  * `d_cat == 1 px` (0–100 m): 3,891 removed by `SOLO-D2.8` (B=1)
  * `1 < d_cat <= 2 px` (100–200 m): 2,545 removed by `H33-2-B2` (B=2)
* `h33_at_most_2px = 0` — H33 places **zero dots within 200 m of any mapped fault.**
* H33 minimum nearest-neighbour to catalogue: `2.8284 px` (~283 m); median catalogue distance `19.65 px` (~1.97 km).
* H33 is an exact 0-px subset of `SOLO-D2.8`, of `D2.8`, and of `H19-5`: `h33_subset_of_d28 == true`, `h33_subset_of_solo == true`, `solo_subset_of_d28 == true`.
* Format: strict full-grid `[0, 1]`, `0` NaN/Inf, `EPSG:32611`, `3730 × 3292`, transform `(100, 0, 243350, 0, -100, 4508550)`.

## 2. Why H33 scored `0.2778` (mechanism)

The competition metric is the pooled **Distance-Weighted Tversky Index** (`alpha = 0.2`, `beta = 0.8`, 300 m triangular kernel). For a truth cell `g` and predicted dots `P`:

```
TP_w = sum_g max_{x in P, d(x,g)<=300m} p(x) * k(d(x,g))
FP_w = sum_x p(x) * [1 - max_g k(d(x,g))]
DTI  = TP_w / (TP_w + alpha*FP_w + beta*FN_w)
```

A predicted dot receives credit only insofar as it lies within 300 m of a held-out truth cell; every dot farther than 300 m from truth is a full false positive (`k = 0`). Dots placed **on or immediately beside a mapped catalogue trace** (`d_cat <= 2 px`) are especially dangerous: they sit where the organiser penalises "a dot near a known trace but far from any new-fault pixel," so they contribute FP weight with little new true-positive credit.

H33 is the end of a monotone pruning chain:

```
H19-5  (121,131 dots)
   | min_dist = 1.5 px Poisson thin
   v
D1.5   (60,069 dots)               user-reported 0.2477
   | min_dist = 2.8 px (~280 m, the 300 m kernel radius)
   v
D2.8   (44,090 dots)               user-reported 0.2600  (+0.0123)
   | remove d_cat == 1 px flank dots
   v
SOLO   (40,199 dots)               user-reported 0.2708  (+0.0108)
   | remove remaining 1<d_cat<=2 px collar dots
   v
H33 B2 (37,654 dots)               user-reported 0.2778  (+0.0070)
```

Each stage removes dots that lie inside the near-catalogue collar (`d_cat <= 2 px`). Because those dots carry FP weight but little marginal truth credit, removing them raises DTI. **H33's high score is therefore explained by collar avoidance, not by finding unmapped geothermal faults.** It is the `B=2` end-member of one family: `D1.5` → `D2.8` → `SOLO-D2.8` → `H33-2-B2`.

This also explains the sibling results:
* GEMSDOE25 `dotted-h19-5-d2-8` = `D2.8` trunk (`0.2600`).
* GEMSDOE30 `d28-poisson300m-offcat-44090` = **exact pixel-for-pixel duplicate** of `D2.8` (`0.2600`, 44,090/44,090 identical positives).
* GEMSDOE31 `h27-4-solo-d28` = `SOLO-D2.8` (`0.2708`), exact duplicate of GEMSDOE28 `h27-4-r1-solo-d2-8`.
* GEMSDOE28 `h36-1-rung30-blind-r1` = near-H33 D2.8/SOLO prune (`0.2710`, `99.88%` 3-px vs H33).
* GEMSDOE33 `h33d` retains `2,794` collar dots plus tip/stepover dots → `0.2632` (worse than H33, consistent with the collar mechanism).
* GEMSDOE36 `anderson-geothermal-pinn` = H33 `+` 1,200 off-ridge PINN dots → `0.2750` (the additions slightly *hurt*: `-0.0028`).

All nine focus-site champions overlap `H19-5` at `0.9775–1.0000` and the `dense_17gemdoe` witness at `1.0000`. **`0 / 9` are unique.** They are all one nested lineage.

## 3. Can we generate a submission that beats `0.2778`?

**Not under the current binding rule, and not by copying H33.**

Two independent blocks:

### Block A — uniqueness (literal all-raster gate)

The pre-placement gate `scripts/preflight_mtas88.py --gate-generation` was re-run against the restored pinned inputs. It returns `DUPLICATE_STOP` (exit `2`) because:

* `dense_17gemdoe.tif` positive pixels: `5,167,373` (every footprint cell).
* Allowed footprint pixels: `5,106,385`.
* Uncovered allowed pixels within the 3 px halo: `0` → `covered_allowed_fraction = 1.0`, `universal_overlap_blocker = true`.
* Implication: **every nonempty candidate dot set in the allowed domain has forward overlap `1.0000` with this prior**, so it cannot pass the `> 0.70` limit. Rank-correlation `> |0.90|` and `> 70%` of dots within 3 px of one registry raster both fire trivially.

H33 itself fails this gate identically (`1.0000` vs `dense_17gemdoe`; `1.0000` vs `H19-5`). So does every focus-site champion and every archived GEMSDOE88 research TIFF. Copying H33 is explicitly a **duplicate** (Protocol Rule 1) and would not be accepted as a new submission.

### Block B — score basis is unverified

`0.2778` has **no organizer receipt**. It cannot be used as a target to "beat" because we do not know the hidden-label truth, and user-reported claims are not `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED`. The highest organizer-confirmed / holdout-validated numbers in this repo (e.g. H88-BPWD `HOLDOUT-DTI = 0.205991 [0.188105, 0.223344]`, `n = 22,893`) are themselves method proxies on withheld catalogue faults, not leaderboard forecasts, and they too fail the uniqueness gate.

## 4. What would be required to submit something new

1. **Break the universal witness.** Because `dense_17gemdoe.tif` covers 100% of allowed cells within 3 px, there is **no location inside the scored footprint** where a dot could be placed that is `> 3 px` from the witness. As long as that witness binds, **no nonempty in-domain raster can be protocol-unique**, regardless of method. Unblocking requires a separately authorized representation-aware policy revision (the `IR-88-76`/`IR-88-SDTL-01` equal-support readings remain diagnostic, not authorized) — i.e. a selector decision, not a local build.
2. **Find genuinely off-catalogue, off-witness signal.** Any new candidate must place `> 30%` of its dots `> 3 px` from every registry raster *and* keep `|rho| <= 0.90` against every registry surface. With a space-filling witness this is impossible today; it would require either a re-scoped witness or new independent data demonstrating registry gaps.
3. **Validate before spending a slot.** Buffered whole-segment hide-and-recover holdout, per-feature leakage canary (AUC `<= 0.90`), matched-fold incumbent comparison, full surface + final-dot registry tests, then a JSON run card with `HOLDOUT-DTI` + 95% CI or an `ORGANIZER-CONFIRMED` receipt. Only then does the separate selector authorize a weekly slot.

## 5. Hypotheses ranked for a future unblocked session

If the universal witness is re-scoped or lifted, the untried, source-verified proposals in `registry/hypothesis_queue.json` are the ranked starting points:

| Rank | Hypothesis | Layers / signature | Why it could catch off-catalogue faults | Named non-fault mimic | Est. cost | Status |
|---|---|---|---|---|---|---|
| 1 | **H88-SPR** Repeated scarp-profile restoration vs drainage/shoreline null | `training_features.tif` bands 12,19 (det_elev, det_elev_slope); `topo_10m_derived` hs_lineament/dem_mean; `lidar_scarp_features` step_max/coh100/strike/valid; `dem10_chi` chan_n/valid_n | Weak cover-softened offset repeated across smooth piedmont can escape catalogue mapping while keeping a resolvable profile step; no mapped trace seeds the surface | Fluvial terrace risers; pluvial shoreline benches | Medium (cached inputs) | PROPOSED_UNTESTED (conditional_first_choice) |
| 2 | **H88-AWA** Terrain-matched radiometric alteration-width asymmetry | `geodawn_rad` K/Th/U; `training_features` rtp, depth_to_base_surf, det_elev_slope | A covered permeable structure may alter one wall more than the other with no discrete scarp | Differential weathering of adjacent units; K-rich transported alluvium | Medium | PROPOSED_UNTESTED |
| 3 | **H88-CBC** Conductive basin-breach connectivity vs paleochannel null | `training_features` det_elev, iso_grav_anom, depth_to_base_surf, cond_surf; `dem10_chi` chan_n/valid_n | Buried cross-basin structural connection may have no surface trace | Unfaulted permeable paleochannels; saline plumes | Medium-high | PROPOSED_UNTESTED |

**No numerical DTI projection is offered for any of them** (a projection is never written as a score). The top candidate must be validated on the spatially-blocked holdout before any weekly slot is spent; if it cannot be validated without new external data, the specific free official source must be named and confirmed obtainable first.

## 6. Limitations

* All scores above (`0.2449–0.2778`) are **user-reported claims**, not organizer receipts. No `ORGANIZER-CONFIRMED` value exists for any focus-site file in the inspected repositories.
* Geometry is measured from owner-mirror bytes, not hidden organizer truth; causality of the score progression is unproven.
* The `dense_17gemdoe` witness and the restoration hashes come from pinned owner GitHub mirrors; they are not authenticated against logged-in organizer downloads, and redistribution terms are unchecked.
* The local `[0, 1]` format check is stricter than necessary outside the footprint (all-finite exterior) and is **not** proof of portal acceptance; the reported portal range error's cause is unverified.

## 7. Distinct-method research demonstration (this session)

To show the pipeline end-to-end without copying any focus-site champion, one research raster was generated **locally and verified** from a method deliberately outside the `H19-5 → D1.5 → D2.8 → SOLO → H33` ridge-thin lineage: a **normalised distance-to-catalogue off-catalogue structural-position proxy** restricted to the scored footprint, zero on the catalogue and outside it, single-band float32 `[0, 1]`, exact sample CRS/shape/transform.

- SHA-256 `1973061147d571867ce72c7307b7ab59932c4356488ed8dc004e24a8af5ce713`; run card `registry/session_research_offcatalogue_run_card.json`.
- Local format audit: **PASS** (`scripts/validate_artifact.py` vs `data/bridge/sample_submission.tif`: all finite, `[0, 1]`, CRS/shape/transform match, one band, zero mass outside footprint).
- Registry gate: **BLOCKED** — literal 3-px forward overlap vs `dense_17gemdoe` = `1.0000 > 0.70`; surface Spearman `ρ = −0.67` (`|ρ| < 0.90`, so correlation does not fire, but overlap does). Verdict `negative`, `ok_to_submit: false`, `0` weekly slots spent.
- The raster was **not published to `docs/downloads/`**: registering it would require re-running the saved file audit, which cannot currently complete cleanly (15 pre-existing TIFFs lack partner ZIPs, unrelated to this session). Publishing an untracked raster would also trip `scripts/check_site.py`. The canonical, page-linked downloadable research artifact remains `docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif`.

It demonstrates that a distinct, non-copied method still cannot clear the binding universal witness: **NOT OK to submit**.

## 8. Decision

**No new TIFF generated this session; `SUBMIT: NO — DO NOT SUBMIT`; `ok_to_submit: false`; `0` weekly slots spent.** The canonical downloadable research artifact is `docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif` (SHA-256 `db9d1867…`), which is format-valid locally but **not** submission-cleared (`literal 3-px overlap = 1.0000 > 0.70` vs `dense_17gemdoe`).
