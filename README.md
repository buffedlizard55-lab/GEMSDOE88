# GEMSDOE88 — DOE GEMS Hidden Geothermal Fault Discovery Research

<!-- CURRENT STATE START -->
## CURRENT STATE (`2026-10-23` · Agent Brief v2 · seven sessions: PRUNE refill-mode (#34) · SPACING on `R1` (#35) · SNAP-clearance audit + hardened gates (#36) · MASS on `R0` (#38/#42) · TRACKB Phase 2 (#40) · SNAP scarp transplant on `R1` (#41) · **MASS on gate-clean `R1` (this session)**)

| Field | Status / Value | Evidence Class & Provenance |
|---|---|---|
| **Parent (`R0`)** | `h33-h33-2-b2`, `N=37,654`; `1,611` dots strictly `<3 px` | `15/15` manifest pins SHA-256 + byte-length verified; R0 rebuilt byte-exactly this session (`zeros c55bafc4…`, `nan baeae321…`, `registry/r0_verification.json`). Historical `0.2778` is **CLAIM**, not a receipt. |
| **Gate-clean parent (`R1`)** | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`, `N=37,654`, `min d_cat=3.1623 px` | Re-derived from the pinned lineage and SHA-asserted (`6f7ae705…`/`dc6f090d…`) before this session's edits; it parents all 15 gate-clean child rows. |
| **Best `RECEIPT`** | **None** — `0` portal receipts, `0` slots used, `50` built rows | Every `receipt_score`/`receipt_date` is empty. The human must paste a verbatim receipt; no session has ever submitted. |
| **`TOP_PUBLIC`** | Blank in the current brief; the repo's `0.4413` (`2026-10-22`) is stale and `UNVERIFIED` (two same-day briefs disagree — IR-88-49) | Human must re-read the leaderboard; the competition page is never accessed from this repo. |
| **Quota & Deadline** | One entity, `3/3` rolling-week slots (human must confirm), `2026-12-03` deadline (unverified) | Human must reconfirm both before any upload. |
| **This session (`AXIS=MASS` on `R1`, agent-chosen)** | Three arms at the brief's 10% dose (3,765 dots), ranked by the parent's own recorded recipe: `r10minus e56b0e5a` (`N=33,889`), `r10plus b2d704df` (`N=41,419`), `r10swap 20dc829f` (`N=37,654`); all `100% >3 px`, validator 6/6 PASS (`registry/mass_r1_validation.json`) | Blind off-catalogue `SGMC` `PROXY` vs `R1 0.096083`: **`0.088680 / 0.098745 / 0.092489`** (`−0.0074 / +0.0027 / −0.0036`). The R0 ordering (`− / + / −`) replicates on a second parent. A same-pool same-count random-donor control (`+0.001252`) shows **half** the `+10%` gain is pure count: ranking premium `+0.001409`. `w`-model `−0.0080 / +0.0085 / +0.0013` `MODEL` (in-sample, optimistic). Holdout proxy structurally `0.000000` (IR-88-20). Report `evidence/mass_r1_axis_report.json`; cards in `ledger/mechanism_cards.json`; IR-88-51. |
| **Instrument reading (report only, never a gate)** | MASS-R1 splits exactly like MASS-R0; scarp-SNAP and spaced-refill arms sit above `R1` but by `<0.005`; SPACING/CONCENTRATION/RELIEF/TRACKB arms sit at or below parent | No local instrument separates any arm from its parent by the brief's `0.01` no-evidence floor. `w` (blind AUC `0.47`) must not adjudicate geometry or ranking edits (IR-88-38/44/50). No PROXY/MODEL value is a score. |
| **Next 3 Candidate Slots (`SLOT_PLAN.md`)** | **1.** `PRUNEp3px 6f7ae705` (`R1` anchor — parents all 15 gate-clean rows; locally rebuildable and validator-clean) · **2.** `MASSr10plus-R1 b2d704df` (largest blind margin of any locally validated gate-clean arm, `+0.0027`, replicated direction; retires MASS if it fails) · **3.** `SNAPscarp1px-R1 1944aaf5` (different mechanism, `+0.0015`) — each conditional on the previous receipt | Candidate sequence only, never an upload recommendation; every upload awaits human quota/`TOP_PUBLIC`/deadline confirmation, a rebuild-or-restore with recorded-hash match, and a fresh `validate_variant.py` run on the actual bytes. Live `\|Δ\| < 0.01` is no evidence. |
| **Holds / limitations** | All R0-parented non-PRUNE arms (`CONCENTRATION`, `RELIEF`, `SNAP`, `MASS m10*/r10*`) stay `HOLD` under the literal `3 px` collar; all SPACING/TRACKB arms are sub-threshold diagnostics; `p3space35`/`p4space35` TIFFs are not present locally and need exact reconstruction first | The human uploads at most one file per slot; TRACKB remains Phase-2 geologist review (`evidence/trackb_traces_geologist.geojson`). |

This block and the current brief supersede historical instructions below, including
rank/overlap uniqueness gates, automatic-upload language, and unconfirmed quota claims.
<!-- CURRENT STATE END -->

> ## AUTOMATED GATE DECISION (READ THIS FIRST — ZERO HUMAN INTERVENTION REQUIRED)
>
> | Gate Question | Automated Machine Decision | Binding Reason & Verifiable Receipt |
> | :--- | :--- | :--- |
> | **IS THIS GEOTIFF OK TO DOWNLOAD?** | **YES (`ok_to_download: true`)** | **100% locally validated, brand-new unique single-band `float32` GeoTIFF (`3730 × 3292`, `EPSG:32611`, `100 m`, `nodata = None`, all `12,279,160` cells finite in `{0.0, 1.0} ⊂ [0, 1]`, `0` `NaN`/`Inf`/sentinels, `0` dots on mapped catalogue faults).** |
> | **IS THIS GEOTIFF OK TO SUBMIT AUTOMATICALLY?** | **NO — DO NOT SUBMIT (`ok_to_submit: false`, `verdict: "negative"`)** | **Scientifically `5.20×` stronger than `MGC-88` (`HOLDOUT-DTI = 0.18789`, `95% CI [0.17170, 0.20326]`, `8/8` fold wins) and unique across ALL `20 / 20` sparse dot-field siblings (`max 3-px overlap = 0.6796 ≤ 0.70`, `max |ρ| = 0.0975 ≤ 0.90`), BUT blocked automatically under the un-exempted literal any-raster rule because hash-pinned continuous prior `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` is strictly positive on ALL `5,167,373 / 5,167,373` valid footprint pixels (`forward_dot_overlap_3px = 1.0000 > 0.70`). Explicit human portfolio-selector override is required before spending any live weekly slot.** |
> | **Unique Candidate Filename** | `gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT` (`61 / 140` chars) | [Download Candidate `.tif` (`133,192` B)](docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.tif) · [Single-TIFF `.zip`](docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.zip) · [Writer Receipt `.json`](docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.json) · [Format Audit `.json`](docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.format-audit.json) |
> | **Candidate Short Note (`138 / 140` chars)** | `ADHR88 67-feat 60deg-dip+GDR1391-2m+scarp+relay Dinkelbach 35894 dots (HOLDOUT-DTI 0.1879); literal 17GEMSDOE overlap=1 blocks auto-submit` | **`.tif` SHA-256:** `f8e56f2a2f5fd6df8738364e2f98bbaf955512c027f9d53b5e404a9fef62eccd`<br>**`.zip` SHA-256:** `729ca35f4aed1ba3c99cf5f420af89032c27d08308471a239ed8d1d46ad3a7fd` |
> | **Archived Baseline (`Exp 01`, Research Only)** | `gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT` | [Archived `Exp 01` `.tif`](docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif) · [`.zip`](docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.zip) · `SHA-256: 3af5d290e7e0f362cd69bc2db416c8e7a2fe25a61189546218169a90e097730b` |
> | **Primary Pages & Machine Receipts** | **0 weekly submission slots used · `ORGANIZER-CONFIRMED` score: None** | [Executive Summary (`How to Submit`)](docs/executive-summary.html) · [Research & Audits](docs/research.html) · [Verified Sources](docs/sources.html) · [Canonical Run Card](registry/run_card.json) · [Live Site](https://buffedlizard55-lab.github.io/GEMSDOE88/) |

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

1. **Core values:** **Maximize P(Win)**: spend scarce weekly submissions only on evidence-backed discoveries; **Own the Outcome**: take responsibility for failures as well as successes. The project aims to find *geological faults indicative of geothermal resources*, not to hallucinate directly observed vents.
2. **Parallel-run protocol / lane:** one explicitly named method per session (the request does not actually contain a separate single-method paragraph); if surface Spearman rank correlation with any registry raster exceeds **0.90**, or >**70%** of emitted dots are within **3 pixels** of any one registry raster, log the duplicate and stop. Check both continuous surface before dot placement and final dots. **No selective exemptions for dense priors.**
3. **Reuse, don't rebuild:** use hash-pinned shared feature stack, `evaluate_holdout.py` and `submission_writer.py`; fix a shared defect upstream once rather than keep a private fork. Hide entire fault components with a **3-pixel context buffer**, use visible faults only for catalogue-derived features, mask known faults pixel-exactly, and score **pooled DTI** (α=0.2, β=0.8, 300 m triangular kernel). The vendor files in this repo are byte-identical to the pinned shared template, not private alternative metrics.
4. **Evidence and leakage:** a number labelled **HOLDOUT-DTI** needs evaluator version, withheld-positive count and 95% CI; **ORGANIZER-CONFIRMED** requires a submission-page receipt. Never market a projection as an organizer score. Test every feature alone on held-out positives; **AUC > 0.90 means possible leakage** until disproven.
5. **Run card and limits:** record hypothesis, mechanism, a named non-fault mimic, holdout DTI+CI, registry correlations/overlaps, raster SHA-256, validator output (no NaN inside the footprint, values [0,1], CRS/shape/transform match), unique name and note ≤140 characters, and a **promote / negative** verdict. Negative findings remain deliverables. Stop after at most **3 experiments or 2 hours**. Promotion/weekly-slot selection are separate; do not silently submit.
6. **Before implementation:** rank 3–5 new, specific geological hypotheses by likely DTI gain versus cost; name their layers, physical transforms, reason they could detect off-catalogue faults and named non-fault mimics. Validate the top on spatially blocked holdout before any weekly slot; no externally dependent hypothesis without a verified free official source and permission to use/share it.
7. **Site:** clean GitHub Pages UI; put the GeoTIFF link, *file-to-submit* decision, unique name and short note and automated evidence at the very top; create an executive-summary subpage explaining exactly how to submit when a candidate is actually cleared. Independently reopen TIFF and one-TIFF ZIP; do not require human inspection for project preflight. Maintain a dated, honest current-feed mechanism with official verification links. Recheck after each change in three passes: implement/verify, review/fix, recheck requirements/fix.
8. **Output:** auditable source inventory with official verified links, data restoration without manual prompts where possible, reproducible train → inference → validate → export path. Answer why owner H33 might have risen and whether this candidate *can be shown* to beat it. Explain limitations, next steps and blockers. Finalize the branch through a PR and merge as requested, without spending a competition slot.

## Measured Results Summary (`2026-10-22` — 3/3 Experiments Complete)

### 1. Three-Experiment Blocked-Holdout Progression (`gems57-pooled-hide-v2`, `n = 22,893`)

---

## PhD Forensic Answer: Why User-Reported `GEMSDOE32` (`H33`, `0.2778`) Leads the Sibling List & What Is Verifiable About Beating `0.2778` / Public `0.4413`

Strict separation of **verified mathematical/pixel facts**, **unverified user-reported sibling numbers**, and **unobservable organizer truth**:

1. **Epistemic Status of Scores:**
   - The prompt lists `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) at **`0.2778`**. That figure is a **user-supplied report, NOT `ORGANIZER-CONFIRMED`**, because this sandbox has no DrivenData portal receipt (`independent_organizer_receipt: false`).
   - On **2026-10-22 UTC**, the [official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) top score is **`0.4413`** (not `0.3195` from the older prompt remark).
2. **Exact Pixel & Metric Decomposition across Sibling Rasters (Read-Only Audit, Zero Copying):**
   - Decoding the SHA-pinned `GEMSDOE25` (`D2.8`, `44,090` binary dots) and `GEMSDOE32` (`H33`, `SHA-256: c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`, `37,654` binary dots) against `existing_faults.tif` (`60,988` public fault pixels) proves mathematically:
     $$\operatorname{supp}(\text{H33}) \subsetneq \operatorname{supp}(\text{D2.8}), \qquad |\operatorname{supp}(\text{D2.8}) \setminus \operatorname{supp}(\text{H33})| = 6{,}436, \qquad \forall x \in \Delta:\; d_{\text{cat}}(x) \le 2\text{ px }(200\text{ m}).$$
   - Every single dot retained by `H33` beyond `200 m` of mapped faults (`68.4%` at `d_cat > 10 px`, `41.8%` at `d_cat > 25 px`, i.e., `> 2.5 km` out into unmapped range-front piedmonts and basins) is **pixel-for-pixel identical** to `D2.8`.
   - Under the [official Distance-Weighted Tversky Index (`DTI`, `α = 0.2`, `β = 0.8`, `300 m` triangular kernel)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation):
     $$\text{DTI}(P, G) = \frac{\text{TP}_w(P, G)}{\text{TP}_w(P, G) + 0.2\,\text{FP}_w(P, G) + 0.8\,\text{FN}_w(P, G)}$$
     two distinct mechanisms govern performance on **unrecorded geothermal faults**:
     1. **Precision / Flank-Deduplication Effect (`D2.8: 0.2600 -> H33: 0.2778` user-reported):** Deleting `6,436` near-catalogue flank dots (`d_cat ≤ 200 m`) eliminates up to `0.2 × 6,436 = 1,287.2` denominator false-positive penalty units wherever new expert-mapped faults do not parallel old traces at `< 200 m` offset. *(Note: sibling write-ups state a marginal inclusion threshold `α S / (1 - β S)`; for an isolated unit dot whose marginal coverage equals its own self-credit `k`, exact algebra gives **`k > α · DTI = 0.2 · DTI`**, which we enforce exactly via `vendor/gems57/emit.py::dinkelbach_allocate`.)*
     2. **Off-Catalogue Piedmont vs In-Sample Halo Collapse (`0.0254–0.0964` vs `0.2478–0.2778` user-reported):** Later repositories that trained unconstrained gradient-boosted trees on smooth regional fields (`gravity`, `strain`, `magnetics`) **in-sample across all 4 quadrants** memorized `200–1,000 m` halos around `existing_faults.tif` (`84–99%` of emitted dots within `1 km` of already-mapped faults; `0.0–0.5%` beyond `2.5 km`), starving unmapped range-front piedmonts and blind basins of predictions. Conversely, models with genuine out-of-fold physical scarp/geophysics generalization place `23–68%` of their dots across unmapped range-front piedmonts (`> 1 km` from mapped traces).
     3. **Continuous `[0, 1]` Surfaces vs Optimal Binary `{0, 1}` Support:** Continuous probability surfaces pay `0.2 × FP_w` across millions of non-fault cells (`17GEMSDOE` covers `5,167,373` pixels), collapsing `DTI`; discrete `{0, 1}` support allocated by Dinkelbach fractional programming achieves strictly superior `DTI`.
3. **Can `H88-ADHR` Be Warranted to Beat `0.2778` or `0.4413`?**
   - **No unverified guarantee is made or permitted.** Because the organizer's expert-labelled hidden fault set `G_test` is unobservable without spending a live submission slot, **no valid confidence interval exists for `H88-ADHR`'s live public/private leaderboard score**, and we never write a projection as a score.
   - **What IS proven locally with `p < 0.001`:**
     - On identical whole-component buffered holdout (`gems57-pooled-hide-v2`, `n = 22,893` withheld positive pixels across 8 spatial folds), `H88-ADHR` achieves **`HOLDOUT-DTI = 0.18789` (`95% CI [0.17170, 0.20326]`)**, beating `CGO-88` (`0.09042`), `MGC-88` (`0.03612`, **`5.20×` improvement**), and `raw_control` (`0.03134`, **`6.00×` improvement**) across **all `8 / 8` spatial folds**.
     - On whole withheld fault components **`> 1.0 km` (`d_vis > 10 px`, `n = 10,791` pixels)** from any visible fault, `H88-ADHR` achieves **`0.11478`** (`5.44×` `MGC-88 = 0.02112`).
     - On independent off-catalogue USGS SGMC concealed/piedmont bedrock fault traces (`n = 10,314` diagnostic pixels outside `250 m` of `existing_faults.tif`, **zero parameters fit to leaderboard**), `H88-ADHR` achieves `0.08797` (`2.24×` `MGC-88 = 0.03922`, `2.85×` `57GEMSDOE = 0.03081`, and exceeding `GEMSDOE78 = 0.07884`, `GEMSDOE80 = 0.07633`, `GEMSDOE85 = 0.07505`, and `GEMSDOE25 = 0.08737`).

---

## Ranked Pre-Implementation Geological Hypotheses (`research/candidate-hypotheses-20261022.md`)

All 5 hypotheses target **concealed/unmapped geological faults indicative of geothermal fluid pathways** (never vents), specify exact verified input layers, name concrete non-fault mimics, and check free public data licensing prior to implementation:

| Rank | ID & Status | Exact Verified Layers Used | Physical Signature / Transform Targeted & Why Unmapped in USGS/INGENIOUS | Named Non-Fault Mimic | How It Differs from Existing Repo & Sibling Lanes |
|---:|---|---|---|---|---|
| **1** | **`H88-ADHR`**<br>*(Implemented — `Exp 03`, Primary)* | 19-band competition stack (`rtp`, `iso_grav`, `horiz_grav_grad`, `depth_to_base_surf`, `cond_surf`, `strain_2nd_inv`, `seis_mw3/bval`, `dem_rel`, `slope`, `tc/k/u/th`) + SHA-pinned official DOE GDR `#1391` (`F2mDAB` 2 m probes, paleo-sinter, thermal springs, CC BY 4.0) + USGS GeoDAWN `TMI_up150`/`K`/`Th` (CC0) + USGS 3DEP 1 m/10 m `χ`/`k_sn`/scarp + fold-visible relay geometry | **Advection- & Dip-Back-Projected Hydrothermal-Scarp Submodular Discovery:** Back-projects hanging-wall basement density/magnetic gradients up `60°` normal-fault dip (`Δx = z_base / tan 60°`) onto the range-front surface trace; advects shallow 2 m probe (`F2mDAB`) & sinter anomalies upslope (`+∇h_reg`) to feeder faults; suppresses constant-elevation Pleistocene shorelines (`1,330 m` Lahontan / `1,555 m` Bonneville); marginalizes latent basin mapping completeness across 4-quadrant OOF cross-fitting; allocates binary `{0,1}` dots via exact Dinkelbach CELF (`m* ≥ p*`). | Wave-cut Pleistocene Lake Lahontan / Bonneville shorelines (`~1,330 m` / `~1,555 m`), evaporite playa clay pans (`cond_surf`), and laterally outflowing valley-floor thermal plumes. | First architecture combining **dip-angle hanging-wall back-projection (`z_base / tan 60°`) + upslope thermal-plume advection + shoreline-decontaminated `1 m/10 m` scarps + 4-quadrant OOF cross-fitting + exact calibrated Dinkelbach `m*/p*` allocation** (`max 3-px overlap = 0.6796 ≤ 0.70` across all 20 sparse siblings). |
| **2** | **`CGO-88`**<br>*(Implemented — `Exp 02`, Competition-Only Ablation)* | Strictly the 19 provided competition bands (`rtp`, `iso_grav`, `horiz_grav_grad`, `cond_surf`, `depth_to_base_surf`, `strain_2nd_inv`, `seis`, `dem_rel`, `slope`, radiometrics; **zero external data, zero catalogue features**) | **Conductivity–Gravity Dip-Offset Co-Edge (`26` features):** Computes multi-scale basement gravity/magnetic gradients, shallow clay-cap boundary gradient `|∇ log(cond_surf)|`, cover-thickness interaction `z_base · |∇g|`, and `±1..3 px` across-scarp hanging-wall back-projection; trained label-blind out-of-fold with Dinkelbach binary allocation. Catches concealed basin-bounding faults where neither surface trace nor LiDAR exists. | Closed playa evaporite margins, perched saline aquifers, and GeoDAWN `400 m` flight-line leveling seams. | Strictly isolates pure 19-band geophysical/topographic signal (`HOLDOUT-DTI = 0.09042`, `2.50×` `MGC-88`, `8/8` fold wins) without any external dataset or visible-catalogue feature. |
| **3** | **`RDC-88`**<br>*(Partially integrated in `X_cgo`; standalone unrun)* | Competition bands `5–8` (`rad_tc`, `rad_k`, `rad_u`, `rad_th`) + `12` (`dem_rel`) + `19` (`slope`) + USGS GeoDAWN `K`/`Th` (CC0) | **Relief-Stratified Radiometric Hydrothermal Disequilibrium:** Local `K/Th` alteration enrichment & `U/Th` redox anomalies conditioned on slope/piedmont position, identifying leached/potassic fault-zone alteration lacking modern hot springs. | Felsic tuff lithologic contacts, uranium roll-front placers, and airborne gamma leveling stripes. | Conditions radiometric ratios on piedmont relief & basement step rather than raw gamma amplitudes. |
| **4** | **`MRR-88`**<br>*(Unrun reserve)* | Competition bands `1` (`mag_anom`), `2` (`rtp`), `9` (`tmi_vgrad`), `14` (`tmi`), `15` (`depth_to_base_surf`) | **Intra-Magnetic Vertical-to-Regional Polarity Asymmetry:** Regresses `∂T/∂z` on regional `TMI` per `10 km` block to isolate magnetite-destructive hydrothermal fault gouge under young volcanic cover where gravity contrast is muted. | Unfaulted basalt flow margins and remanently magnetized Tertiary dikes. | Uses intra-magnetic vertical/regional residual polarity rather than RTP-gravity co-location. |
| **5** | **`MSDD-88`**<br>*(Unrun reserve)* | Competition bands `2` (`rtp`), `13` (`iso_grav`), `4/10/11` (strain tensor) | **Multi-Scale Strike Dispersion & Strain-Locked Curvature:** Measures cross-scale orientation truncation of pre-Cenozoic fabric aligned with geodetic extension azimuth. | Unfaulted pluton roofs and depositional pinchouts. | Tests cross-scale orientation truncation rather than single-scale gradient magnitude. |

---

## Executed 3-Experiment Ledger (`<= 3` Budget Cap Strictly Respected)

All four arms were evaluated **head-to-head on identical folds, identical `22,893` withheld whole-component positive pixels, identical `3 px` feature-context buffer, identical pixel-exact visible-fault mask, and unmodified `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `1,000` `20 km × 20 km` spatial block-bootstrap draws)**:

| Arm / Experiment | Evidence Class | Feature Set & Allocation | Pooled `HOLDOUT-DTI` | `95%` Block-Bootstrap CI | Paired `Δ` vs `MGC-88` (`95% CI`) | Far-Fault `> 1 km` `HOLDOUT-DTI` (`n = 10,791`) | Fold Record |
|---|---|---|---:|---:|---:|---:|---:|
| **Control (`raw_control`)** | `HOLDOUT-DTI` | Raw 3 bands (`rtp`, `iso_grav`, `depth_to_base_surf`) + spaced top-`k` | `0.03134` | `[0.02082, 0.04535]` | `-0.00478` | `0.02133` | Baseline |
| **`Exp 01` · `MGC-88`** *(Archived)* | `HOLDOUT-DTI` | 7 cross-gradient co-edge features (3 bands) + 2 px spaced dots (`37,654` budget) | `0.03612` | `[0.02641, 0.04830]` | `0.00000` (Ref) | `0.02112` | `5 / 8` vs raw |
| **`Exp 02` · `CGO-88`** *(Competition Physics)* | `HOLDOUT-DTI` | **26 verified 19-band dip-projected physics features ONLY** (zero external data, zero catalogue features) + calibrated Dinkelbach `{0,1}` | **`0.09042`** | **`[0.07950, 0.10132]`** | **`+0.05430` `[+0.03861, +0.06976]` (`2.50×`)** | **`0.07683` (`3.64×`)** | **`8 / 8` wins** |
| **`Exp 03` · `H88-ADHR`** *(Primary Candidate)* | `HOLDOUT-DTI` | **67 features** (`26` 19-band physics + `18` official GDR `#1391`/GeoDAWN/3DEP + `23` fold-visible relay/damage features) + OOF latent-completeness fusion + Dinkelbach `{0,1}` (`35,894` prod dots) | **`0.18789`** | **`[0.17170, 0.20326]`** | **`+0.15177` `[+0.13525, +0.16744]` (`5.20×`)** | **`0.11478` (`5.44×`)** | **`8 / 8` wins vs ALL arms** |

### Per-Fold Breakdown (`registry/holdout_result.json`, `n = 22,893` Withheld Positive Pixels)

| Seed & Quadrant | Withheld Positives | `raw_control` | `Exp 01: MGC-88` | `Exp 02: CGO-88` (Dots) | `Exp 03: H88-ADHR` (Dots) |
|---|---:|---:|---:|---:|---:|
| **Seed 20 · NW** | `1,923` | `0.03016` | `0.04027` | `0.05983` (`8,906`) | **`0.16933`** (`6,304`) |
| **Seed 20 · NE** | `2,367` | `0.03512` | `0.02490` | `0.07616` (`7,036`) | **`0.19549`** (`7,919`) |
| **Seed 20 · SW** | `3,781` | `0.02651` | `0.02575` | `0.09285` (`18,451`) | **`0.19950`** (`12,744`) |
| **Seed 20 · SE** | `3,250` | `0.02794` | `0.02914` | `0.10695` (`16,990`) | **`0.18793`** (`7,191`) |
| **Seed 21 · NW** | `1,918` | `0.02374` | `0.03920` | `0.06845` (`10,425`) | **`0.20120`** (`6,989`) |
| **Seed 21 · NE** | `2,361` | `0.03349` | `0.03715` | `0.10476` (`7,602`) | **`0.17958`** (`7,662`) |
| **Seed 21 · SW** | `3,813` | `0.02939` | `0.03551` | `0.07074` (`19,224`) | **`0.17330`** (`13,360`) |
| **Seed 21 · SE** | `3,480` | `0.04333` | `0.05724` | `0.12344` (`15,942`) | **`0.20685`** (`6,935`) |

---

## Single-Feature Leakage Canary Audit (`registry/leakage_canaries.json`)

- **74 / 74 single features audited** (`67` `H88-ADHR` features + `7` archived `MGC-88` features) on held-out Seed-20 whole-component positives vs off-catalogue negatives inside active regions (`AUC > 0.90` = automatic hard stop).
- **Result: `74 / 74 PASS`** — maximum single-feature symmetric ROC AUC is **`0.771627 ≤ 0.90`** (`d2 = 0.771627`, `d_perp = 0.760499`, `d = 0.754201`, `d_over_w = 0.735155`, `relay_facing = 0.616382`, `lidar_scarp_dipole = 0.589390`).
- **Automated Zero-Leakage Scrambling Verification (`tests/test_adhr_and_zero_leakage.py`):** Corrupting/scrambling ground-truth pixels inside the held-out test quadrant produces **bit-for-bit identical (`np.array_equal`)** features and predictions across the test quadrant.

---

## Complete 19-Raster Pre-Placement & Final-Dot Uniqueness Ledger (`registry/two_phase_uniqueness.json`)

Measured by unmodified `vendor/gems57/uniqueness.py` across **all 21 SHA-256-pinned accessible rasters** (`18` sparse dot-field siblings + `1` full-footprint continuous surface prior, **zero silent exemptions**):

- **Pre-placement continuous surface Spearman `|ρ|` (`limit ≤ 0.90`):** **21 / 21 PASS** (`max |ρ| = 0.46641`).
- **Final binary dots Spearman `|ρ|` (`limit ≤ 0.90`):** **21 / 21 PASS** (`max |ρ| = 0.09750`).
- **Final binary dots 3-px forward overlap vs ALL 20 sparse dot fields (`limit ≤ 0.70`):** **20 / 20 PASS** (`0` firings; `max = 0.67961`, vs `H33 = 0.39709`, vs `MGC-88 = 0.17346`, vs `57GEMSDOE = 0.27896`, vs `GEMSDOE70 = 0.44157`).
- **Literal un-exempted 3-px forward overlap vs `17GEMSDOE` full-footprint surface (`limit ≤ 0.70`):** **`1.00000` -> AUTOMATIC LITERAL STOP (`ok_to_submit = false`)**.

| Repo | Hash-Pinned Registry File | Representation | Positive Cells | Pre-Placement `ρ` | Final `ρ` | Final 3-px Overlap | Jaccard | Gate Status |
|---|---|---|---:|---:|---:|---:|---:|---|
| **`17GEMSDOE`** | `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` | `continuous_surface` | `5,167,373` (`100%`) | `+0.46641` | `+0.09750` | **`1.00000`** | `0.00678` | **LITERAL BLOCK (`>0.70`)** |
| `19GEMSDOE` | `19GEMSDOE__h19-5-powerlaw-budget-multiline.tif` | `dot_field` | `121,131` | `+0.08006` | `+0.02950` | `0.44417` | `0.01769` | PASS |
| `GEMSDOE25` | `GEMSDOE25__dotted-h19-5-d2-8.tif` | `dot_field` | `44,090` | `+0.04519` | `+0.01544` | `0.39904` | `0.01152` | PASS |
| `GEMSDOE28` | `GEMSDOE28__h27-4-r1-solo-d2-8.tif` | `dot_field` | `40,199` | `+0.06128` | `+0.01687` | `0.39573` | `0.01212` | PASS |
| `GEMSDOE32` | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | `dot_field` | `37,654` | `+0.07275` | `+0.01790` | `0.39709` | `0.01255` | PASS |
| `GEMSDOE36` | `gemsdoe36-anderson-geothermal-pinn-38854-...` | `dot_field` | `38,854` | `+0.07320` | `+0.01757` | `0.39073` | `0.01243` | PASS |
| `GEMSDOE49` | `GEMSDOE49__gate_ortho_w0.25-40k.tif` | `dot_field` | `40,000` | `+0.04427` | `+0.00936` | `0.26614` | `0.00832` | PASS |
| `57GEMSDOE` | `57GEMSDOE__h57r2-shipped8-all-flank0-...` | `dot_field` | `40,000` | `+0.04076` | `+0.03882` | `0.27896` | `0.02338` | PASS |
| `60GEMSDOE` | `gems60-h68-dem10-lidar-piedmont-dksn-40000-...` | `dot_field` | `40,000` | `+0.06363` | `+0.01894` | `0.50941` | `0.01317` | PASS |
| `GEMSDOE70` | `gems70-p5-multiphysics-submodular-37654-20261020.tif` | `dot_field` | `37,654` | `+0.08557` | `+0.01973` | `0.44157` | `0.01348` | PASS |
| `GEMSDOE70` | `gems70-p5-dual-submod300-oof38k-20261020.tif` | `dot_field` | `37,654` | `+0.06973` | `+0.01846` | `0.29882` | `0.01283` | PASS |
| `GEMSDOE78` | `gems78-h78-gfv-136b-dink-20261022T070254Z-...` | `dot_field` | `37,654` | `+0.07181` | `+0.04167` | `0.62599` | `0.02478` | PASS |
| `GEMSDOE80` | `gems80-adpt-kkt-lagrangian-36500d-20261022T012049Z-...` | `dot_field` | `36,500` | `+0.07484` | `+0.05907` | `0.65189` | `0.03389` | PASS |
| `GEMSDOE80` | `gems80-h80-dpvc-updip-vent-submod-41600-20261021-...` | `dot_field` | `41,600` | `+0.08531` | `+0.07426` | `0.49272` | `0.04210` | PASS |
| `GEMSDOE81` | `gems81-contasb-poisson44090-buf2-20261021T232312Z-...` | `dot_field` | `44,090` | `+0.08916` | `+0.02749` | `0.45924` | `0.01763` | PASS |
| `GEMSDOE82` | `gems82-h82-csam-dinkelbach-41200-20261021-zeros.tif` | `dot_field` | `41,200` | `+0.09506` | `+0.03348` | `0.54695` | `0.02064` | PASS |
| `GEMSDOE83` | `gems83-h83-gvcd-dink300-37654dots-20261021-...` | `dot_field` | `37,654` | `+0.09993` | `+0.04433` | `0.67961` | `0.02617` | PASS |
| `GEMSDOE85` | `gems85-h85a-foldproper-hgb-maxcov-37654-...` | `dot_field` | `37,654` | `+0.09755` | `+0.04452` | `0.44796` | `0.02628` | PASS |
| `GEMSDOE88` | `gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif` | `dot_field` | `37,654` | `+0.02246` | `+0.01133` | `0.17346` | `0.00922` | PASS |

---

## Reproducible End-to-End Workflow (Zero Manual Intervention)

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Mode A: Fast CI / Release & 19-Raster Uniqueness Validation (restores grid + all 18 external registry rasters)
.venv/bin/python scripts/restore_inputs.py --validation
.venv/bin/python scripts/validate_release.py                  # Exits 0: confirms format PASS & honest gate state
.venv/bin/python scripts/validate_release.py --require-submit # Exits 2: automatic STOP under literal 17GEMSDOE witness
.venv/bin/python scripts/check_site.py                        # Verifies all local links, anchors, & safety labels
.venv/bin/python scripts/readiness.py                         # Verifies template pins & updates docs/status.json
.venv/bin/python -m pytest -q                                 # Runs full unit, zero-leakage, & integration suite

# Mode B: Full Training + Holdout + Production GeoTIFF & ZIP Reproduction (~419 MB 19-band stack + 15 official layers)
.venv/bin/python scripts/restore_inputs.py
.venv/bin/python scripts/run_experiment.py                    # Reproduces GeoTIFF, ZIP, & all registry receipts
.venv/bin/python scripts/run_experiment.py --recompute-holdout # Re-runs full 8-fold holdout & 74-feature canary audit from scratch
```

---

## Limitations, Irregularities & Next Steps (`research/next-steps.md`)

1. **Literal `17GEMSDOE` Space-Filling Witness (`IR-88-01`):** Any non-empty set of positive pixels inside the valid footprint mathematically overlaps `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` at `100.00% > 70%`. We never silently exempt it; instead we expose both `literal_reading` (`duplicate: true`) and `like_for_like_reading` (`20/20` dot fields `PASS`, `duplicate: false`) in `registry/two_phase_uniqueness.json` so a human portfolio selector has complete, unvarnished evidence.
2. **Owner-Mirrored Reference Grid (`IR-88-02`):** `sample_submission.tif` (`2176d08e…`) and `existing_faults.tif` (`7ba308cc…`) are SHA-pinned owner mirrors; an authorized human with DrivenData access should verify byte identity against the live portal download before spending any weekly slot.
3. **Far-Basin (`> 2.5 km`) Discovery Frontier:** While `H88-ADHR` places `26.2%` (`9,417` dots) at `d_cat > 1.0 km` and `4.2%` (`1,520` dots) at `d_cat > 2.5 km` (`median d_cat = 6.40 px`), completely unmapped interior basins lacking 1 m LiDAR still carry substantial missed recall toward `0.4413`. Next session should read `research/next-steps.md` first: (a) test intra-magnetic vertical-to-regional polarity residual (`MRR-88`) for blind volcanic-covered grabens (`d_cat > 25 px`), and (b) seek explicit human selector authorization on `IR-88-01` if nominating `H88-ADHR` for one of the `≤ 3` weekly portal slots.
