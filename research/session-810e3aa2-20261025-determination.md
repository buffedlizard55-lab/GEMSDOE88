# GEMSDOE88 — Session determination, 2026-10-25 (branch `arena/810e3aa2-gemsdoe88`)

**Core values applied:** Maximize P(Win); Own the Outcome. Every number below is tagged as HOLDOUT-DTI (evaluator version, withheld positives, 95% CI) or ORGANIZER-CONFIRMED (submission-page receipt). A projection is never written as a score. No claim here is an organizer acceptance.

## 1. Primary determination — no new submission TIFF was generated

**Verdict: NEGATIVE. `ok_to_download = true` (research artifacts only) · `ok_to_submit = false` · 0 competition slots spent.**

A freshly generated, protocol-unique competition TIFF could **not** be produced in this session. The binding pre-placement gate (`scripts/generation_guard.py` → `scripts/preflight_mtas88.py`) returned `DUPLICATE_STOP` (exit 2) before any feature construction, holdout fit, dot placement, or TIFF writing.

Concrete, line-by-line verified preflight output (`2026-10-25T16:54:36Z`):

| Field | Verified value |
|---|---|
| `decision` | `DUPLICATE_STOP` |
| `generation_allowed` | `false` |
| `ok_to_submit` | `false` |
| `new_rasters_generated` | `0` |
| `experiments_run` | `0` |
| `weekly_slots_used` | `0` |
| `verdict` | `negative` |
| Witness file | `data/registry/dense_17gemdoe.tif` |
| Witness SHA-256 | `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be` |
| Witness source | `https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` |
| `positive_pixels` | 5,167,373 |
| `allowed_pixels` | 5,106,385 |
| `uncovered_allowed_pixels` | **0** |
| `covered_allowed_fraction` | **1.0** |
| `universal_overlap_blocker` | `true` |
| `overlap_limit` | 0.70 |
| Implication (preflight) | *"Every nonempty candidate dot set in the allowed domain has forward overlap 1.0 with this prior; therefore it cannot pass the 0.70 gate."* |

**What this means:** the SHA-pinned `17GEMSDOE` probability raster has strictly positive support at every allowed footprint cell. The shared template defines dots as `finite > 0`, so every nonempty candidate has 100% forward 3-pixel overlap with that prior — above the 0.70 limit. No sparse-only exemption exists; reversing or renaming a TIFF does not change the pixel support. This rule was re-verified independently in three prior reviews on 2026-10-25 and is unchanged here.

**Consequence for the user's highest-urgency request:** I cannot hand you a new submission TIFF that is "OK to download AND OK to submit." Generating one now would violate the binding protocol (a prior scratch-TIFF generation was already logged as a protocol breach and its outputs removed). I will not present a research TIFF as submission-ready. The honest deliverable is this negative determination plus the evidence that blocks generation.

### 2. What IS downloadable, and why it is obviously NOT for submission

The GitHub Pages site already presents, at the top of every page, an alert strip:

> **NO NEW TIFF · RESEARCH DOWNLOAD ONLY · DO NOT SUBMIT**

and a decision pill `DOWNLOAD FOR RESEARCH: YES` / `SUBMIT: NO — DO NOT SUBMIT`. All archived TIFF/ZIP pairs carry `DO-NOT-SUBMIT` in the filename and are listed with a `DO NOT SUBMIT` tag in the download inventory. This satisfies "it must be obvious whether it is OK to download and submit": **download yes for research/education, submit no.**

Canonical easy downloads (all format-validated, all DO-NOT-SUBMIT):

| Artifact | Download | SHA-256 (TIFF) | Holdout (historical, not new) |
|---|---|---|---|
| BPWD88 — Baranov Poisson + worm conduit (holdout record) | `docs/downloads/gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT.tif` (+ one-TIFF ZIP) | `b8543782dde52b42253d15b9d6db04b09a1351574ff54077581345c904d7d777` | HOLDOUT-DTI `0.205991 [0.188105, 0.223344]`, `gems57-pooled-hide-v2`, n=22,893 |
| TDKL88 — knickpoint + LiDAR polarity PoE (canonical research release) | `docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif` (+ ZIP) | `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf` | HOLDOUT-DTI `0.1962` (historical) |
| Full inventory | `docs/index.html` → "All 46 archived research TIFFs · automated file audit" | — | — |

**Validator output (concrete, no human inspection):** I ran `scripts/validate_artifact.py --template data/bridge/sample_submission.tif` on the BPWD88 TIFF:

```
format_valid: true
submission_ready: false        (format only; holdout/registry/selector are separate gates)
values_in_0_1: true            (minimum 0.0, maximum 1.0)
all_finite / no_nan_inside: true
crs_match / shape_match / transform_match: true
single_band / geotiff / self_contained: true
footprint_audit.ok: true
raster_sha256: b8543782dde52b42253d15b9d6db04b09a1351574ff54077581345c904d7d777
approval: FORMAT_ONLY_NOT_SLOT_APPROVAL
```

This directly answers the portal error you reported: **"Predicted values must be in range [0, 1]"**. That error is a *file numeric-range check* (negative values, infinities, NaNs, or out-of-range nodata), not a scientific score. The audited research rasters pass the strict local `[0, 1]`, finite, single-band, exact-sample-grid check locally; that is **not** an organizer acceptance and does not assert the portal will accept them. Only a submission-page receipt is ORGANIZER-CONFIRMED; this project has none for a new candidate.

### 3. PhD-level answer: why H33 (`GEMSDOE32`, owner-reported 0.2778) scored highest, and can it be beaten?

**Bottom line up front:** `0.2778` for H33 is **owner-reported, not ORGANIZER-CONFIRMED**. No portal receipt for it exists in this repository (`evidence/h33_lineage_recheck.json`: `organizer_confirmed_score: null`). It cannot be treated as a verified score to beat, and whether *any* new raster can exceed it is **not estimable from available instruments**. The verified public leaderboard high is **0.4413** (participant `xiaofanhu`, 29 submissions), fetched from the official DrivenData leaderboard on 2026-10-25.

#### 3.1 Verified leaderboard context (official public snapshot, 2026-10-25)

Source: `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/` (rows 1–50 transcribed verbatim; saved to `docs/data/leaderboard_official_snapshot_20261025.json`).

| Rank | Participant | Public DW-Tversky |
|---|---|---|
| 1 | xiaofanhu | **0.4413** |
| 2 | cfld__ | 0.3916 |
| 3 | Batik Shirt Brothers | 0.3904 |
| 4 | BrandenKMurray | 0.3724 |
| 5 | No Fault of Our Own | 0.3539 (first-round $10k cutoff) |
| 6–20 | plateau | 0.327–0.342 |
| 50 | — | 0.2818 |

- H33's owner-reported **0.2778 would sit below rank 50 (0.2818)** on this snapshot — it is not the competition-high score; 0.4413 is.
- The prompt's **0.3195 is stale** (a 2026-10-04 snapshot value), not the current high.
- Competition ends 2026-12-03 23:59 UTC. One final selection serves both rounds; up to 3 submissions/week but the website limit prevails; external data must be licensed for the challenge and shareable with organizers (`docs.nlr.gov/docs/fy26osti/96647.pdf` §3.2, §3.4–3.6.2).

#### 3.2 What H33 *is* (measured on SHA-pinned files, `scripts/forensics_h33.py` → `evidence/h33_forensics_20261024.json`)

H33 (`h33_education.tif`, SHA `c55bafc4…`, 37,654 positive pixels) is a **strict pixel-subset chain** — no step adds a dot:

- H19-5 (19GEMSDOE, 121,131 px) ⊃ D2.8 (GEMSDOE25, 44,090 px) ⊃ SOLO-D2.8 (GEMSDOE28, 40,199 px) ⊃ **H33 (37,654 px)**.
- Every dot removed after D2.8 lies **within 2 px of the catalogue** (6,436 px removed D2.8→SOLO; 2,545 px removed SOLO→H33). H33: 0% of dots within 2 px of catalogue, 5.8% within 3 px, median catalogue distance 19.6 px, 35.8% beyond 30 px; nearest-neighbour spacing min 2.83 px / median 3.00 px / 81% between 2–4 px (about one kernel radius).
- No single band explains it: largest single-band separation is detrended slope (AUC 0.657); all other bands within 0.5 ± 0.08. H33 is a multi-modal ridge surface, not a one-band threshold.

#### 3.3 Mechanism: why the score rose (inference, not proof)

Reported scores along the chain: H19-5 0.1922 → D1.5 0.2477 → D2.8 0.2600 → SOLO-D2.8 0.2708 → **H33 0.2778**. Because every step is pure subtraction, each gain is attributable to **removed dots**. Under the pooled distance-weighted Tversky metric (alpha 0.2, beta 0.8, 300 m triangular kernel; `vendor/gems57/metric.py`), removing a dot lowers the denominator by `0.2` per pure false positive while lowering the numerator only by that dot's truth credit. So removing near-catalogue false positives raises DTI when those dots were below the marginal bar (~0.0556 credit at DTI 0.2778). Two independent lineage steps give implied credit `T` within 8% of each other (~5,100–5,500), consistent with the pure-FP-removal hypothesis — **but this is inference from owner-reported public scores, not organizer-verified truth.**

The fleet distance fingerprint (`evidence/fleet_distance_prior_20261024.json`) shows the share of dots >25 px from catalogue is the best single predictor of reported ordering (Spearman +0.90, n=20); catalogue-huggers score lowest (GEMSDOE81 median 2.2 px → 0.0041). H33 does not hug the catalogue. But this is a necessary screen, not a selector: it does not causally prove the score, and n=20 correlated rasters is weak evidence.

#### 3.4 Can it be beaten?

- **Incrementally (small, uncertain):** continuing dot subtraction (e.g. a 3-px catalogue collar) is the only lever with controlled lineage support. Siblings GEMSDOE89–92 carry no scores. I cannot claim a number.
- **Structurally (what winning requires):** at the same ~37,654-dot count, reaching the 0.3539 first-round cut needs roughly **+27–29% more credit T**; reaching 0.4413 needs roughly **+59–63%**. Independent fleet surfaces top out around 0.23–0.25 (GEMSDOE70, 49, 63). This session's pre-registered hypotheses did not deliver the gain on holdout (`research/hypotheses-20261024.md`).
- **Therefore:** P(a new unique raster beats 0.2778 on the public board) is **low and not estimable** from available instruments; P(reaching 0.3539) is lower still. **Do not spend a slot on a raster supported only by a hide-and-recover score.**

### 4. Three-to-five new geological hypotheses (ranked, UNVALIDATED)

Per the parallel-run protocol I must rank 3–5 hypotheses before implementation, naming layers, physical signature, why they catch faults missing from the USGS/INGENIOUS catalogue, the non-fault mimic, how they differ from the repo, and a free official source. **None can be validated in this session: the DUPLICATE_STOP blocks all prediction construction, holdout fitting, and leakage canaries.** They are recorded as next steps, conditional on revising the shared protocol regarding the dense witness.

| Rank | Hypothesis | Layers | Physical signature / transform | Why off-catalogue | Named non-fault mimic | Differs from repo | Free official source |
|---|---|---|---|---|---|---|---|
| 1 | **Blind damage-zone demagnetization: RTP–gravity Poisson admittance/phase discontinuity** | GeoDAWN RTP magnetics; isostatic gravity anomaly; `depth_to_base_surf` (cover) | Baranov pseudogravity from RTP; cross-gradient + phase (quadrature) dislocation vs gravity; admittance collapse where magnetite→hematite/pyrite at 150–280 °C breaks the density–magnetization in-phase step | Hydrothermal alteration destroys magnetism but preserves the density step, creating a blind fault with **no surface trace** → absent from USGS/INGENIOUS surface catalogue | Unfaulted intrusive/volcanic lithologic contacts (density step, weak magnetic contrast); reversely magnetized volcanic mesa rims (Koenigsberger Q>1) | Repo's bpwd uses Baranov pseudogravity amplitude/dip-worm; H1 targets the *admittance/phase-discontinuity gradient*, not amplitude | USGS GeoDAWN (`gdr.openei.org/submissions/1391`); USGS 3DEP (`usgs.gov/3d-elevation-program`) — public, obtainable |
| 2 | **Hydrothermal upflow conduit: geodetic dilation + conductivity + low-density alteration convergence** | `geod_dilaterate`, `geod_shearrate` (GPS/InSAR strain); `cond_surf`; `iso_grav_anom` | Coincident dilation strain, high electrical conductivity, and low-density gravity low = vertical hydrothermal conduit; detects blind upflow without a mapped fault trace | Blind conduit faults have no surface expression → missing from surface catalogue | Unfaulted sedimentary aquifer conductivity highs; paleochannel clay; basin-fill conductivity | Fleet centers mag+gravity; H2 makes geodetic strain + conductivity the primary signal, under-used in the repo | In competition stack (GeoDAWN/GBCGE Ingenious); UNR NGL GPS velocities (CC BY 4.0) |
| 3 | **Seismicity depth-cluster + relay/stepover geometry** | `deq_n100a15` / `ieq_n100a15` (earthquake distance/intensity); `geod_shearrate`; `det_elev_slope` | Hypocenter depth clusters on optimally oriented planes; shear-strain alignment at relay zones / step-overs; blind strike-slip or normal fault segments | Deep or blind segments never breached the surface → not in surface fault catalogue | Volcanic/unrelated induced seismicity; non-tectonic clustering | Repo uses earthquake distance bands; H3 adds depth-clustering + relay-zone geometry as the selector | USGS ANSS ComCat (`earthquake.usgs.gov`, Public Domain 17 U.S.C. §105) |
| 4 | **Detrended-DEM curvature / scarp-face knickpoint** | `det_elev`, `det_elev_slope`, `geod_2ndinv` | 2nd-invariant curvature + slope break on detrended elevation = fault-scarp face and knickpoint lineament; kernel-spaced dots along scarp | Small or buried scarps not digitized in USGS/INGENIOUS | Fluvial knickpoints, landslide scarps, alluvial-fan apexes (non-tectonic) | Repo has LiDAR-scarp lanes; H4 uses 2nd-invariant curvature on detrended DEM with kernel-spaced dot placement matched to the metric | USGS 3DEP LiDAR DEM (public) |
| 5 | **Conductivity-gravity gradient boundary (blind half-graben edge)** | `cond_surf`; `iso_grav_anom_hg` / `_vg` | Co-located sharp conductivity and gravity-gradient edges marking a buried basin-bounding fault; blind fault bounding a half-graben | Basin-bounding fault may be entirely blind under cover → absent from surface catalogue | Unfaulted lithologic conductivity contrast; paleochannel clay lens | Repo combines conductivity indirectly; H5 uses the conductivity-gravity gradient *edge* as the primary detector | In competition stack (GeoDAWN) |

**Obtainability check (free, official):** Rank 1 (USGS GeoDAWN + 3DEP), Rank 2 (in-stack), Rank 3 (USGS ANSS ComCat, public domain), Rank 4 (USGS 3DEP), Rank 5 (in-stack) are all free official sources. None requires authenticated DrivenData downloads or the user-provided Dropbox links, which I do not treat as official.

### 5. Why generation is blocked and what would unblock it

The literal rule blocks *every* nonempty candidate because the `17GEMSDOE` witness covers 100% of allowed cells. To allow a new unique TIFF, the **shared** protocol (not a private fork) must be revised to make the uniqueness condition satisfiable — e.g. redefine dots/support, restrict the comparison domain, or replace the dense witness — and that revision must come from the rule owner / selector, not this session. Until then:

- No feature construction, holdout fit, leakage canary, dot placement, or TIFF writing is authorized (`generation_guard.py` exits 2).
- No weekly slot may be spent (`SLOT_PLAN.md`: slots used 0, promote NO).
- No projection may be written as a score.

### 6. Limitations and next steps

**Limitations:**
- All GEMSDOE site scores (including H33 0.2778) are owner-reported; no organizer receipt exists for any GEMSDOE88 candidate.
- DrivenData data/submission pages require login; this environment has no organizer authentication, so no receipt could be inspected and nothing was submitted.
- Holdout DTI values are local instrument outputs on withheld positives, not leaderboard scores, and cannot be ranked across lanes with different catalogue-visibility designs.
- The hypotheses in section 4 are untested; validation is blocked by DUPLICATE_STOP.

**Next steps (in order, for a future session once the shared protocol is revised):**
1. Revise the shared uniqueness condition so a non-degenerate candidate can satisfy it; document the fix in the template with provenance and tests (protocol item 2).
2. Preregister the top hypothesis (section 4, Rank 1) in one lane; run buffered whole-segment hide-and-recover; derive catalogue features only from visible faults; mask visible faults pixel-exactly.
3. Run each feature's leakage canary (AUC > 0.90 = leakage until proven otherwise).
4. Score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel) with paired CI vs the same-fold incumbent; require it to beat the holdout best before any slot.
5. Run surface/final-dot registry tests (|rho| ≤ 0.90; ≤ 70% of dots within 3 px of any one registry raster) — including against `17GEMSDOE` under whatever revised definition governs.
6. Only if all gates pass: use a cleared submission name + note (≤140 chars), upload one single-band GeoTIFF or one-TIFF ZIP to the DrivenData submission page, and retain the receipt as the sole ORGANIZER-CONFIRMED evidence.

**Easy download status:** research TIFFs are one-click downloadable from `docs/index.html`; each is labeled **DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO — DO NOT SUBMIT**. No generated file in this session is OK to submit.

---
*Evidence tags: [ONLINE] read on an official page this session · [DISK] measured from SHA-pinned files · [OWNER] owner-reported, no organizer receipt · [INFERENCE] derived under a stated assumption · [UNKNOWN] not knowable from public data. No number here is a projection written as a score.*
