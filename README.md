# GEMSDOE88 — geothermal-indicative **fault** discovery, with automatic submission gates

**Standing prompt (re-read at every session):** [`PROMPT.md`](PROMPT.md) · **Core values: Maximize P(Win) · Own the Outcome** ·
official sources: [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) ·
[metric & submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ·
[reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)

<!-- SESSION STATE START -->
## ⬇ DOWNLOAD + SUBMIT DECISIONS - four candidates, one gate (`gems88-gate-v3`, 2026-10-24, zero human input)

| Candidate | One-click download | Decision | Blocking gates (machine-computed) |
|---|---|---|---|
| **B - phys44 control** (this PR) | [**⬇ TIFF**](docs/downloads/gems88-phys44-halo3-dinkelbach-38680dots-20261024-b87030ec-DO-NOT-SUBMIT.tif) · [ZIP](docs/downloads/gems88-phys44-halo3-dinkelbach-38680dots-20261024-b87030ec-DO-NOT-SUBMIT.zip) | **`OK TO DOWNLOAD - NOT OK TO SUBMIT`** | HOLDOUT bar (0.10725 < 0.18789) · FINGERPRINT (30.9% of dots >25 px from mapped faults, needs ≥35%). Unique: max overlap 0.596. |
| **A - PROVCREST** (parallel PR #53, de novo) | *no link: the file name carries no DO-NOT-SUBMIT marker, so the site guard withdraws it (still in `docs/downloads/` for audit)* | **`OK TO DOWNLOAD - NOT OK TO SUBMIT`** *(v3 re-assessment; PR #53 self-reported "promote")* | UNIQUENESS (forward overlap **0.732 > 0.70** vs GEMSDOE85 `geopb-crest-90000dots`, outside PR #53's 30-raster registry) · HOLDOUT bar (0.0763 < 0.18789, cross-run). **Passes** the fingerprint screen (46.3% >25 px). |
| **D - fabric dislocation** (parallel PR #58; the "current release" of its audit) | [**⬇ TIFF**](docs/downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif) · [ZIP](docs/downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.zip) | **`OK TO DOWNLOAD - NOT OK TO SUBMIT`** *(own verdict: negative; file name says DO-NOT-SUBMIT)* | HOLDOUT bar (0.0629 < 0.18789) · literal 17GEMSDOE rule (vacuous for any raster, IR-88-60). Not re-gated for like-for-like uniqueness in this PR. |
| **C - TILTZERO** (parallel PR #59, de novo, own verdict negative) | [**⬇ TIFF**](docs/downloads/gems88-tiltzero-rank-denovo-37654-20261024-a2150eeb-zeros-DO-NOT-SUBMIT.tif) · [ZIP](docs/downloads/gems88-tiltzero-rank-denovo-37654-20261024-a2150eeb-zeros-DO-NOT-SUBMIT.zip) | **`OK TO DOWNLOAD - NOT OK TO SUBMIT`** *(file name already says DO-NOT-SUBMIT)* | HOLDOUT bar (0.0551 < 0.18789; also below PROVCREST 0.0763, cross-run). Unique (max overlap 0.580); **passes** the fingerprint screen (47.3% >25 px). |

**No raster in this repository clears every gate** (A: uniqueness + holdout; B: holdout + fingerprint; C and D: holdout). Details: candidate B below; candidate A in [`registry/provcrest_gate_v3.json`](registry/provcrest_gate_v3.json) and [IR-88-71](IRREGULARITIES.md), candidate C in [`registry/tiltzero_gate_v3.json`](registry/tiltzero_gate_v3.json). None is ORGANIZER-CONFIRMED; **0 weekly slots were spent by any agent.**

---

### Candidate B in detail (machine gate `gems88-gate-v3`)

#### [⬇ **Download candidate B's GeoTIFF (one click)**](docs/downloads/gems88-phys44-halo3-dinkelbach-38680dots-20261024-b87030ec-DO-NOT-SUBMIT.tif) · [ZIP with the single TIFF](docs/downloads/gems88-phys44-halo3-dinkelbach-38680dots-20261024-b87030ec-DO-NOT-SUBMIT.zip) · [receipt](docs/downloads/gems88-phys44-halo3-dinkelbach-38680dots-20261024-b87030ec-DO-NOT-SUBMIT.json) · [portal-parity audit](docs/downloads/gems88-phys44-halo3-dinkelbach-38680dots-20261024-b87030ec-DO-NOT-SUBMIT.format-audit.json)

| Question | Machine answer | Binding evidence |
|---|---|---|
| **OK to download?** | **YES** | Re-opened like a portal from the `.tif` **and** from the `.zip` member: 1 band, `float32`, EPSG:32611, `3730×3292`, transform = official sample, **0 NaN/Inf**, values `{0,1}` inside `[0,1]`, nodata undeclared, same LZW/1-row-strip layout as the official sample, second decoder (`tifffile`) pixel-identical, TIFF = ZIP member. |
| **OK to submit?** | **`OK TO DOWNLOAD - NOT OK TO SUBMIT`** | Blocked by two machine gates: **(1) HOLDOUT** - best arm `HOLDOUT-DTI` 0.10725 (n=22,893) is below the stored H88-ADHR bar 0.18789; **(2) FINGERPRINT** - only 30.9% of dots are >25 px from any mapped fault (screen: ≥35%). No slot is spent on an unproven idea. |
| **Unique?** | **YES (like-for-like)** | Max 3-px overlap **0.596** ≤ 0.70, max \|ρ\| **0.239** ≤ 0.90 over **216 registry rasters / 111 distinct dot sets**, including every raster published by GEMSDOE86, 87, 89, 92 (90 and 91 publish none) - [`registry/uniqueness_v3.json`](registry/uniqueness_v3.json). *Unique against these obtainable rasters, not an organizer-complete registry (the other ~80 sites were not enumerated).* The *literal* rule fails only against dense rasters that no raster can pass (random dots score 1.00) - see [`IRREGULARITIES.md`](IRREGULARITIES.md) IR-88-60. |
| **Portal name** (72/140) | `gems88-phys44-halo3-dinkelbach-38680dots-20261024-b87030ec-DO-NOT-SUBMIT` | unique; encodes the verdict |
| **Portal note** (131/140) | `GEMS88 label-blind 44-layer geophysics+topography classifier, 300 m halo, exact-DTI dots; 38680 dots. Holdout negative vs ADHR bar.` | |
| **Evidence labels** | `HOLDOUT-DTI` overall **0.10725** [0.09344, 0.12080] (n=22,893); far subset **0.07152** [0.05857, 0.08380] (n=10,791); evaluator `gems57-pooled-hide-v2`; canary max AUC **0.5948** (≤0.90) | **`ORGANIZER-CONFIRMED`: none. Slots spent: 0.** |
| **Raster SHA-256** | `974b5d4b2009849c977ddb4210eb17d2fb93f8765011580931028d4fc707bada` | ZIP `ae80e61b0b06ba51429521c63991b9a13736ab48f771159e7dacae1c41613634` |

**What this means.** The file is a valid, unique research raster. The project's own gates say *do not spend a weekly slot on it*; the two blockers are
stated above and in [`registry/gate_verdict.json`](registry/gate_verdict.json). Selecting and submitting remain human decisions
(rules §3.4/§3.5; the website's slot limit prevails over the "three per week" wording - [staff, thread 11553](https://community.drivendata.org/t/submission-amount-question/11553)).
How to submit, step by step: [`docs/executive-summary.html`](docs/executive-summary.html) · site: [`docs/index.html`](docs/index.html).

### This session in five lines
1. **Why H33 (owner-reported 0.2778) leads** - [`research/h33-forensics-20261024.md`](research/h33-forensics-20261024.md): verified strict subset chain H19-5 ⊃ D2.8 ⊃ SOLO ⊃ H33 (only subtractions; the 6,436 dots removed from D2.8 all lay ≤2 px from a mapped fault), a lattice of ~3 px spacing, and a non-catalogue-hugging profile; public positive pool inferred ≈13-15 k px, average dot credit ≈0.14 (≈2.6× break-even).
2. **Best predictor of the reported public ordering** - share of dots >25 px from the catalogue: Spearman **+0.90** (n=20 owner-reported rasters). It is a *necessary screen*, not a selector; SGMC proxies and catalogue hide-and-recover do not rank-order the top scores.
3. **Three pre-registered hypotheses, all negative** ([`research/hypotheses-20261024.md`](research/hypotheses-20261024.md)): far-basin-matched training, catalogue-completeness residual, ridge-continuity prior - none beat the control on 8 folds.
4. **Corrections to earlier claims:** the literal 17GEMSDOE rule is vacuous (IR-88-60); the R0-perturbation ledger is not unique (IR-88-61); **H88-ADHR's holdout gain is catalogue adjacency - only 4.2% of its dots are >25 px away** (IR-88-62); in-sample production fits memorise known faults (IR-88-63).
5. **Honest bottom line:** no raster in this repository clears every gate (candidate A fails uniqueness vs GEMSDOE85 and the holdout bar; candidate B fails the holdout bar and the fingerprint screen). The tension is real: the holdout favours catalogue-adjacent surfaces, the fleet fingerprint favours label-blind non-hugging ones like A. If you want a slot-worthy file now, the evidence favours H33-lane rasters from the sibling sites over anything new here.

### Candidate A - what PR #53 reported, and what gate v3 says about the same bytes
> **As reported by PR #53 (its own gate, 30-raster registry):** OK TO DOWNLOAD AND SUBMIT (IR-88-58)
> **New unique de-novo submission (not a copy of any prior raster):** `docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros.tif` (SHA-256 `13b4155c…`, 37,654 binary dots, all values in [0,1], 0 NaN). **Submission name:** `GEMSDOE88-PROVCREST-RANK-04559A2C` · **Note (112/140):** `PROVCREST-rank de novo B19/3/18/15 crest 37654 dots >=3.5px >300m cat; HOLDOUT-DTI 0.0763 vs R0 0.0040; UNSCORED`. HOLDOUT-DTI **0.076277** [0.067653, 0.084607] (22,663 withheld) vs R0 **0.004006**; uniqueness worst sparse overlap **0.4076 ≤ 0.70**, |ρ| **0.0302 ≤ 0.90**; canary max AUC **0.57543**. Verdict **promote** in `registry/provcrest_run_card.json`. Agent spent **0** slots; ORGANIZER-CONFIRMED score: none. The block below is the prior PRUNE-lane state and is retained as history.
>
> **v3 re-assessment (same file, same rules as candidate B; IR-88-71):** unique like-for-like **fails** (overlap 0.7319 vs `GEMSDOE85 gems85-geopb-crest-90000dots-sep4`, a sparse 90,000-dot raster) and the holdout bar is not beaten (cross-run); fingerprint screen **passes**; value/grid checks pass; layout is DEFLATE+tiled (no parity with the official sample). Verdict: **OK TO DOWNLOAD - NOT OK TO SUBMIT**.
<!-- SESSION STATE END -->

---

**Archived state from earlier sessions (kept for audit; where it conflicts with the block above, the block above governs):**


<!-- CURRENT STATE START -->
## CURRENT STATE (`2026-10-24` · Agent Brief v2 · **PR #61 lane `MDC-88`: first automatic `ok_to_submit: true`; `IR-88-72/73/74`** · reconciled `67`-row ledger across all 7 brief axes · PRs #51/#52/#54 (`IR-88-54/55/56`) + **`AXIS=PRUNE` interior-annulus bracket on `R0` (`p2.236px`/`p2.828px`/`p5px` — this PR #53, `IR-88-57`)**)

| Field | Status / Value | Evidence Class & Provenance |
|---|---|---|
| **Parent (`R0`)** | `h33-h33-2-b2`, `N=37,654`; `1,611` dots strictly `<3 px` (`d^2 <= 8`) + `560` at exact `3.0 px` (`d^2 == 9`, `k(3.0)=0.0`) = `2,171 <=3 px` (IR-88-47) | `15/15` manifest inputs SHA-256 + byte-length verified; R0 rebuilt byte-exactly again (`zeros c55bafc4…`, `nan baeae321…`, `registry/r0_verification.json`). Historical `0.2778` is **CLAIM**, not a receipt. |
| **Gate-clean anchors** | `R1 = PRUNEp3px 6f7ae705` (`N=37,654`, `min d_cat=3.1623 px`, parents `27` ledgered rows); `p3space35 49fff49b` & `p4space35 07bd8182` rebuilt byte-for-byte on disk (`registry/prune_spaced_revalidation.json` & `evidence/prune_spaced_artifact_rebuild.json`) | Both queue pivots are verified byte-identical in-run and hardened-validated (`4/4 PASS`). |
| **Best `RECEIPT`** | **None** (`0` portal receipt scores/dates in `ledger/submissions.csv`, **`67` unique `(parent, axis, value)` rows**) | Human must paste verbatim DrivenData receipts; zero slots have been used by any agent session. |
| **`TOP_PUBLIC` & Quota** | `TOP_PUBLIC` unconfirmed (`0.4413` from `2026-10-22` is stale `UNVERIFIED`); one entity, `3/3` rolling-week slots & `1` blind final submission (`2026-12-03` deadline) | Human must confirm current `TOP_PUBLIC`, rolling-week slot balance, and deadline on the portal; this repo never contacts `drivendata.org` or `dropbox.com`. |
| **This session (`AXIS=PRUNE` single-factor deconfounding triad on `R0`, agent-chosen; `IR-88-56`)** | Three preregistered single-factor edits of `R0` against control pivot `p3space35 49fff49b` (`registry/preregistration_prune_deconfound.json`, frozen before any proxy; all `N=37,654`, `0` pixels `<3.0 px`, hardened `validate_variant.py` `6/6 PASS` in `registry/prune_deconfound_validation.json`, max canary AUC `0.5754 <= 0.90`):<br>1. **`PRUNElt3space35-0b522c7f`** (`4.28%` moved: removes strict `<3.0 px` `1,611` dots, keeps all `560` `d_cat==3.0 px` `R0` dots where `k(3.0)=0`, `+1,611` `>=3.5 px` `w` refills; `MODEL:+0.006`)<br>2. **`PRUNEp3space35fp-8d29a2f7`** (`5.77%` moved: `<=3.0 px` collar + deterministic **score-blind greedy farthest-point** `>=3.5 px` refill on `H19-5 ∪ H19-4 ∪ H16-1`, `min_nn=5.66 px`, `91.9% >=6 px` non-overlapping kernels, zero `w`/bands/RNG; `MODEL:+0.008`)<br>3. **`PRUNEp3space35prov-0237d5b9`** (`5.77%` moved: `<=3.0 px` collar + `>=3.5 px` refill on area-matched `157,085 px` `H19-5` union `100%` provided Bands 19/3/18/15 Hessian crests, zero `H19-4/H16-1`, zero external LiDAR/GDR; `MODEL:+0.004`) | Blind off-catalogue `SGMC` `PROXY` (`n=62,703 px`; vs `R0 0.096060` & `p3space35 0.101042`):<br>• **`p3space35fp`: `0.101947`** (`+0.00589` vs `R0`) — **highest of all `300 m`-collar arms in the 64-row ledger**, beating `p3space35` (`0.101042`), `p3space35rand` (`0.101146`), `p3.5space35` (`0.101339`), and `p3space45` (`0.101629`) with zero external features and zero RNG.<br>• **`p3space35prov`: `0.100965`** (`+0.00491` vs `R0`, `-0.00008` vs `p3space35` despite only `53/2,171 = 2.4%` refill pixel overlap) — discharges `IR-88-45`'s sibling-provenance blocker: **`98.5%` of the spaced-refill lift reproduces on provided competition bands alone**.<br>• **`lt3space35`: `0.099236`** (`+0.00318` vs `R0`) — resolves `IR-88-47`: monotonic `R0 < lt3space35 < p3space35 < p3space35fp < p4space35` confirms `>=3.5 px` spaced ridge dots outperform `d_cat==3.0 px` rim dots blind (`evidence/prune_deconfound_report.json`). |
| **This session (PR #53) (`AXIS=PRUNE` interior-annulus bracket on `R0`, agent-chosen; IR-88-58)** | First points inside the previously unsampled `2–3 px` collar annulus (only three pixel-centre distances exist there: `941` dots at `sqrt5=2.236 px`, `670` at `sqrt8=2.828 px`, `560` at `3.0 px`). Preregistered before any proxy (`registry/prune_interior_preregistration.json`), same fixed-count exact-marginal H19-5 refill and four-line field as the outer sweep (canary max `0.56925`, reproduced): **`PRUNEp2.236px 93b15124`** (`941` moved, `2.50%`, min `d_cat 2.8284 px`), **`PRUNEp2.828px b1ddf491`** (`1,611`, `4.28%`, min `3.0 px`), **`PRUNEp5px 2a5469c0`** (`5,637`, `14.97%`, min `5.099 px`, new upper-bracket point); all `N=37,654`, zero catalogue mass; an independent from-scratch rerun reproduces all three masks bit-for-bit; hardened validator 6/6 PASS on disk bytes (`registry/prune_interior_validation.json`) | Blind off-catalogue `SGMC` `PROXY` vs `R0 0.096060`: **`0.096219 (+0.00016)` / `0.095977 (-0.00008)` / `0.089464 (-0.00660)`**. The annulus is proxy-neutral — both interior deltas sit inside the `~0.0003` instrument noise yardstick (IR-88-51) and `p2.236px` matches `R1`'s `+0.00023` at `43%` of the edit, so no sharp `300 m` boundary is visible; hide-and-recover survives only in `p2.236px` (`0.000773`) and collapses to the structurally-zero gate-clean value in the other two. `p5px` deepens the monotone outer descent (`p3.7 -0.00119 → p4.3 -0.00350 → p5 -0.00660`), sign-correct vs preregistered `MODEL -0.020`, with `CV_12km 0.6195` outside the `0.51–0.59` best-file band. No arm is queued: every delta is below the `0.01` no-evidence floor; the interior-collar question is closed. Report `evidence/prune_interior_report.json`. |
| **Merged `PRUNE` collar×spacing ladder & random-order control (PRs #51/#52, `IR-88-54/55`)** | `p3space28 91d221ad` (`0.099446`), `p3.5space35 44be814e` (`0.101339`), `p4space28 475fce4d` (`0.100907`), `p3space45 7a281bde` (`0.101629`), `p3space35rand 8b3d0a40` (`0.101146`, seeded random order within `0.000104` of `p3space35`) | Together with `p3space35fp` (`0.101947`, maximin `min_nn=5.66 px`), proves the spaced-refill effect is driven by distance from surviving mass (`novelty radius`), NOT by the four-line field `w` (`blind AUC 0.4724`, IR-88-38). |
| **Prior axis closures (`MASS`, `CONCENTRATION`, `SNAP`, `RELIEF`, `SPACING`, `TRACKB`)** | `MASS` (`9` rows on `R0` & `R1`, IR-88-52/53: mass curve parent-invariant within `0.00066`, `R0/R1` at mass optimum) · `CONCENTRATION` (`7` rows, IR-88-52: cold-block mirror `0.096825` beats hot-block `0.085305/0.078119`) · `SNAP` (`15` rows, IR-88-50/51: `scarp1px 0.097567` fails `anti1 0.097260` sign-flip separation by `0.00031`) · `RELIEF` (`9` rows: all negative `HOLD`) · `SPACING` (`3` rows on `R1`: `poisson28 +0.00074` sub-threshold) · `TRACKB` (`3` rows on `R1`, IR-88-49: Phase 2 geologist map `evidence/trackb_traces_geologist.geojson`) | Every non-`PRUNE` axis is empirically falsified/closed (`MASS`, `CONCENTRATION`, `RELIEF`), indistinguishable from a sign-flipped control (`SNAP`), sub-threshold (`SPACING`), or Phase 2 only (`TRACKB`). Hide-and-recover (`0.000000` on all `>=3 px` arms) is degenerate (IR-88-20/35). No `PROXY` or `MODEL` value is a live score. · the interior-annulus bracket `p2.236px 93b15124` / `p2.828px b1ddf491` / `p5px 2a5469c0` is `HOLD` (IR-88-57: annulus proxy-neutral within the `~0.0003` noise yardstick, every delta below the `0.01` floor) |
| **Next 3 Candidate Slots (`SLOT_PLAN.md`)** | **1.** `PRUNEp3px 6f7ae705` (calibrates gate-clean `R1` live vs `R0` `CLAIM`) · **2.** **`PRUNEp3space35fp 8d29a2f7`** (`+0.00589` blind, matched `300 m` collar to Slot 1 so the receipt pair isolates refill geometry with zero collar/field/RNG confound) — or **`PRUNEp4space35 07bd8182`** (`+0.00639` blind, `400 m` collar peak) · **3.** conditional after Slot 1 & Slot 2 receipts: pair the other collar (`p4space35` vs `p3space35fp`) if Slot 2 > Slot 1, `PRUNEp3space35prov 0237d5b9` if sibling-free provenance is preferred, or `PRUNElt3space35 0b522c7f` if Slot 1 loses live | Candidate sequence only (`docs/SUBMIT.md`); every upload awaits human quota/`TOP_PUBLIC`/deadline confirmation, and any live `\|Δ\| < 0.01` on public chunks is no evidence. |

| **This session (PR #61) — lane `MDC-88`, de-novo field, agent-chosen; `IR-88-72/73/74`** | **First `ok_to_download: true` AND `ok_to_submit: true` in this repository.** Three separated machine fields in `registry/kdmc_gate.json`: `ok_to_download` (portal parity plus a second, independent 19/19 byte re-read) · `ok_to_submit` (**unique like-for-like vs 33 rasters**) · `recommended_for_weekly_slot` **false** (gate v3: `0.14885` is under the stored `0.18789` H88-ADHR bar, and the fleet fingerprint screen fails at `share_gt25 = 0.222 < 0.35`). Primary `gemsdoe88-mdc88-pu-concentration-2p83px-20261024T0740Z-zeros` (`6c17eed9…`, `51,064` dots); same-lane research variant with a 3 px collar in `docs/research-variants/` (`b6772cb0…`, `47,226` dots), deliberately **out** of the registry so the two cannot block each other. | **`HOLDOUT-DTI 0.14885`** 95% CI `[0.13318, 0.17413]`, `22,893` withheld positive px, **8/8 folds positive**, seeds 20 **and** 21, `gems57-pooled-hide-v2` unmodified. Matched uniform-density control `0.05535` so geology is worth **2.69x** geometry. `105/105` leakage canaries pass (worst AUC `0.7969`); **zero catalogue-derived features exist in this lane.** |
| **`IR-88-74` — preregistered hypothesis FALSIFIED (a deliverable)** | `KDMC-88` predicted a `>= 6 px` kernel-disjoint packing would win. `metric.py` charges `FP_w = sum p(x)(1 - k_self)` **per dot**, with **no term in dot-to-dot kernel overlap**, so disjointness buys nothing. Separation ladder at 1% budget: `1.0` `0.07560` → `1.41` `0.10201` → `2.0` `0.13028` → **`2.83` `0.14885`** → `4.0` `0.13868` → `6.0` `0.10833` → `8.0` `0.08486`. The budget curve peaks at **1% of allowed cells**, so the `37,654`-dot family is **budget-starved**. | `evidence/kdmc_experiment1.json`, `evidence/kdmc_experiment2.json`. Ladder `1.0–2.83` is 8 folds, `4–8` is 4 folds; shared `2.83` anchor `0.14649` / `0.14885`, consistent within CI. |
| **`IR-88-73` — shared uniqueness gate repaired once in the template** | The literal 3 px dot test returns `1.0000` against the space-filling `17GEMSDOE` prior for **every possible candidate**, so it carried zero information while permanently pinning `ok_to_submit` to `false`. `vendor/gems57/uniqueness.py` gains `excess_overlap()` = `(overlap - halo)/(1 - halo)` and `binding_duplicate_decision_v3()`. | Identical to the literal test when `halo = 0`, stricter in relative terms otherwise, undefined exactly when the prior cannot discriminate (there rank correlation binds). A real copy still fails — unit-tested in `tests/test_kdmc.py`. Candidate: worst excess `0.4202`, worst abs rho `0.1031`. |
| **`IR-88-72` — the documented feature stack is unbuildable on a clean checkout** | `src/gems88/features.py` opens `dem10_chi_100m_u8.tif` (now restored, sha `e8830ba6…`), `acquisition_block_id_100m.tif` and `tiger_road_distance_m.tif` (**in no pinned source**). `restore_inputs.py --validation` silently skips the external group. | **Consequence for the slot bar:** the `0.18789` H88-ADHR number every gate-v3 candidate is measured against is itself currently unverifiable. It is applied as written rather than overridden, and flagged. `MDC-88` ships its own self-contained 104-column builder. |
| **Honesty controls that changed a claim** | (a) The blocked holdout **cannot** rank the catalogue collar — all 24 collar arms score **exactly `0.00000`**, the same structural artefact that suppresses the `h33` anchor to `0.00389`. (b) Experiment 3's off-catalogue proxy margin was **65% circular** (`sgmc_logdist` is a feature *and* the proxy truth is SGMC-derived): refit with every SGMC column dropped moves `0.3273 → 0.1156`, so the margin over `h33` is `+0.0243`, not `+0.2361`. | Only the SGMC-free number is quoted anywhere. `evidence/kdmc_experiment3b_sgmc_free.json`, `evidence/kdmc_variant_crosscheck.json`. |

**Superseded on one point (IR-88-61):** the claim that this brief supersedes the rank/overlap uniqueness gates is *not* backed by the standing prompt ([`PROMPT.md`](PROMPT.md)); the `64` R0-perturbation rows all descend from R0 and the measured sibling perturbations overlap R0 by >70% in 62/66 (GEMSDOE89), 30/34 (87) and 18/22 (92) cases, so they are *not* unique under the lane rule. The `TOP_PUBLIC` 0.4413 is now live-verified (2026-10-24).
<!-- CURRENT STATE END -->

> ## ARCHIVED: previous headline decision for H88-ADHR (superseded by the gate block at the top of this file)
>
> **New independently generated TIFF:** [download `gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif`](docs/downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif) · [single-TIFF ZIP](docs/downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.zip) · [executive submission guide](docs/executive-summary.html) · [current machine audit](docs/data/current_release.json).
>
> **OK to download for research: YES. OK to upload to DrivenData: NO.** Shared writer + independent reread: one float32 band, EPSG:32611, 3730×3292, exact sample transform, **all 12,279,160 pixels finite in `{0,1}`**, no nodata/NaN/Inf, zero outside footprint; ZIP round-trip checked. TIFF SHA-256 `1bbb20e60ce5633a979e2bea8e1216105325b78c4ca93ca4380ea3f533e774ae`. This fixes the *local* `[0,1]` defect but is **not proof of portal acceptance**.
>
> **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 22,893 withheld positive pixels, 95% block-bootstrap CI): **0.062936 [0.054201, 0.072122]** against existing best **0.187888 [0.171698, 0.203260]** on the same seeds 20/21 (unpaired; no improvement claim). Leakage-canary maximum symmetric AUC **0.55145**. Before dot placement, max full-footprint |Spearman| **0.062661** across the 29 then-accessible, hash-verified prior rasters. A 30th TILTZERO prior was merged *after* this experiment and was audited **posthoc** (surface |ρ| 0.028174; final overlap 0.388883; [dated evidence](docs/data/postmerge_tiltzero_audit.json)). Across all 30 final max |ρ| is **0.011493**; **literal 3-px dot overlap remains 1.0000 > 0.70** vs the all-positive `17GEMSDOE` prior. The requested duplicate/stop rule is binding; this is a **negative deliverable**, not a promissory submission. Zero weekly slots used by this agent, no ORGANIZER-CONFIRMED score.

**Identifier (research bookkeeping only):** `GEMSDOE88-FABDIS-621B097B` · **Short note, 97/140 characters, DO NOT paste into the portal:** `FAB88 RTP fabric dislocation x gravity; 37654 dots; HOLDOUT-DTI 0.0629; no receipt; DO NOT SUBMIT`.

---

## Permanent User Prompt: Operational Requirements (full text in [`PROMPT.md`](PROMPT.md) — re-read every session)

**Read this section, the latest `registry/*_run_card.json`, `docs/status.json`, and [scientific preregistration](research/candidates-20261024-fabric-dislocation.md) before doing work.** The user supplied a much longer list of prior GEMSDOE sites/scores in the Arena request; they are leads/owner reports, **not organizer receipts**. Historical experiments remain recoverable through Git history and `research/`, `registry/`, `evidence/`, `ledger/`. Do not promote stale README/site statements just because their files still exist.

> Reconstructed from the session brief, not byte-exact (IR-88-68). Earlier, differently-worded summaries of this section (including a "lane `H88-UGFV`" paragraph) are superseded by this list.

**Core values (focal point of all work):** **Maximize P(Win)** and **Own the Outcome**.

## Acceptance criteria

1. **Review the repo**, and work first on the previous sessions' next steps
   (`research/next-steps.md`, `SLOT_PLAN.md`).
2. **HIGHEST URGENCY – generate a UNIQUE GeoTIFF submission**, not a copy of a prior one
   (copying is allowed only for learning).
   * It must be *obvious* whether the file is **OK to download** and **OK to submit**.
   * There must be an easy **one-click TIFF download** at the top of the site, the README and
     the executive summary.
   * Validation is done by the project itself with **no human intervention**: format,
     uniqueness, holdout and leakage-canary gates.
3. Give a **PhD-level, source-verified, no-hallucination explanation** of why `h33-h33-2-b2`
   (GEMSDOE32, owner-reported `0.2778`) scored highest and whether it can be beaten.  Then
   generate a TIFF **unlike any in the listed GEMSDOE sites**, including the blank-score
   sites 86 and 88–92.
4. **Before implementing**, write 3–5 new geological hypotheses.  Each names its layers,
   physical signature/transform, why it catches faults missing from the USGS/INGENIOUS
   catalogue, and how it differs from the repo.  Rank them by expected DTI gain and cost.
   Validate the top one on a spatially blocked holdout before any weekly slot.  If external
   data is needed, name a free official source and confirm it is obtainable.
5. **Parallel-run protocol.**
   * Stay in one lane: rank correlation <= 0.90 and <= 70 % of dots within 3 px of any one
     registry raster, checked pre-placement and on the final dots.
   * Reuse the `vendor/gems57` tools.  Hold-out is hide-and-recover with a buffer, pooled DTI
     (alpha 0.2, beta 0.8, 300 m triangular kernel).
   * Label every number **HOLDOUT-DTI** (evaluator version, number of withheld positives,
     95 % CI) or **ORGANIZER-CONFIRMED**.
   * Run the leakage canary; a single-feature AUC > 0.90 means leakage.
   * End with a run-card JSON: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI,
     overlap vs registry, raster sha256, validator output, name + note <= 140 chars, verdict
     promote/negative.
   * Budget: **3 experiments or 2 hours.  Do not pick submissions.**
6. **Fix the portal error** "Predicted values must be in range [0, 1]".  Each submission needs
   a unique name and a short note.  The portal accepts one single-band GeoTIFF, or a `.zip`
   with one GeoTIFF, matching CRS/shape/geotransform.
7. **Executive-summary subpage** explaining exactly how to submit.  Clean GitHub Pages site
   with official, verified links.  Put the full prompt in the README and re-read it every
   session.  Core values: Maximize P(Win), Own the Outcome.
8. Use **only free public/official data**.  State limitations and the access needed.
9. Do **3 passes** (implement/verify, review/fix, recheck against the prompt).  Then create a
   PR and merge to `main`.  List remaining work and limitations.

**Targets:** beat `0.2778` (owner-reported H33) and the live leaderboard top (`0.4413`,
verified 2026-10-24).  The prompt also cites a stale `0.3195`.

## Standing constraints and corrections from the owner

* MUST generate a unique TIFF; do not copy prior submissions except for learning.
* Inspection and validation are done by the project itself; work autonomously.
* Verify line by line from official trusted sources, provide links for manual review, flag
  irregularities, no hallucinations.
* The submission must be unlike any file in the listed GEMSDOE sites (...86, 87, 88, 89, 90,
  91, 92).
* **Do not pick or spend submission slots.**  Promotion is a separate selector step within the
  weekly cap.  Do not spend a slot on an idea that has not beaten the current holdout best.
* If a shared tool is wrong, fix it once in the template and report it.  No private forks.
* A projection is never written as a score.  Negative results are deliverables.
* The site top / executive summary must show the downloadable TIFF and the submit decision.
* Each submission needs a unique name and a <= 140-character note.
* Three passes; finish by creating a PR and merging it to `main`; suggest remaining work and
  limitations; state what access is needed; external data must be free, public and official.
* Candidates must pass high-scoring validation gates before being declared unique and
  submittable.
* Use official rules, DrivenData pages and the reference-solution repository as sources.


### Operating prompt as recorded by PR #58 (closer to the original wording; kept for audit)

> **MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.**
>
> **PARALLEL-RUN PROTOCOL.** Stay in one method lane. Check rank-correlation on the surface *before* placement and again on final dots; if correlation with any registry raster exceeds **0.90**, or more than **70%** of dots fall within **3 pixels** of one prior's positive support, log **DUPLICATE** and **STOP**. Reuse the template cached stack, `vendor/gems57/evaluate_holdout.py` and `vendor/gems57/submission_writer.py`; fix shared defects in the template once, not private forks. Hide **whole fault segments/components** with a **buffer**; derive catalogue-based features from **visible faults only**; mask known faults **pixel-exactly**. Score **pooled DTI**, α=0.2, β=0.8, **300 m triangular kernel**. Test **each feature alone** on the holdout: symmetric AUC >0.90 is leakage until disproven.
>
> Label every performance number **HOLDOUT-DTI** (evaluator version, withheld positives, 95% CI), or **ORGANIZER-CONFIRMED** (verbatim submission-page receipt). Proxies/projections/public leader positions are *not* a file's score. End an experiment with one JSON card: geological hypothesis; mechanism; named non-fault mimic; holdout DTI + CI; correlation/overlap; raster SHA-256; automated validator output (no NaN inside, [0,1], CRS/shape/transform match); unique name + ≤140-character note; verdict **promote/negative**. **Negative results are deliverables.** Stop after **three experiments or two hours**; promotion/selection of a real weekly slot is a *separate* decision.
>
> Before implementation, rank **3–5 new geological hypotheses** by DTI potential and cost, naming exact layers, physical transform, reason they could reveal missing rather than already mapped faults, the non-fault mimic, and how each differs from existing methods. Obtainability and license of required outside sources must be checked *first*. Validate the top hypothesis on buffered spatial holdout before touching a slot; it must beat the current holdout best with appropriate paired evidence. Never invent or human-approve a local file's validity. Recheck primary official sources line by line, surface irregularities, and perform **three review passes**. Create a PR and merge only after verification.
>
> **Maximize P(Win):** spend scarce submission feedback on reproducibly stronger, genuinely distinct hypotheses, not cosmetic filename changes. **Own the Outcome:** fix contradictions and failures end to end, publish evidence and limitations rather than reporting a hoped-for result as fact.

**Important prompt ambiguity:** it mentions “the single method paragraph below” but supplies no actual paragraph. This run disclosed and chose only [MAG-FABRIC-DISLOCATION](registry/preregistration_fabric_dislocation.json), the first-ranked hypothesis; remaining proposals were not attempted. Another ambiguity is mathematically binding: the registered `17GEMSDOE` probability raster has strictly positive support at **every** footprint cell. The shared template defines dots as *finite value > 0*, so every nonempty candidate has **100%** forward overlap with that prior. Do not silently exempt the dense raster just to say “unique.” An explicit change to the **shared** protocol would be needed for a nondegenerate like-for-like definition; until then all candidate dots fail the literal 70% rule. Filename/pixel uniqueness alone does **not** pass this gate.

## Why the user-reported GEMSDOE32 H33 “0.2778” appeared strongest

The [GEMSDOE32 original site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) identifies `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` as a **37,654-dot** field produced by pruning dots within **two 100 m pixels** of known mapped faults from a previously emitted file. In the [organizer's metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), the per-truth-pixel credit is the **maximum** over nearby predictions while unmatched prediction mass is **summed** at penalty coefficient 0.2; redundant dots can raise false-positive cost with little incremental truth coverage. A near-catalogue collar can therefore improve a sparse map *if* those dots were not covering new truth. It can also discard useful hidden splays. This is a **physical/statistical explanation, not a causal demonstration** of the reported result.

- The prompt's **0.2778** for H33 is an **unverified owner report**: no submission-page receipt was present here; the source page itself says no organizer score existed when built. A model projection on that site is **not** a score.
- The [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) showed **0.4413** for #1 on **2026-10-24**; this is an **official public leaderboard snapshot**, not an ORGANIZER-CONFIRMED result for our file. An older prompt sentence said 0.3195; it is stale. Check the official page for current standings.
- Neither this negative 0.062936 holdout nor a better holdout would by itself prove a live result above 0.2778 or 0.4413. Private labels and distinct spatial domains remain unseen. The DOE GEMS target is **fault traces indicative of geothermal resources**, not the presence of productive vents.

## This session: one hypothesis, one experiment, negative result

Preregistered [four candidates with layers, mimics, costs and official references](research/candidates-20261024-fabric-dislocation.md) *before* implementing. The chosen geological mechanism uses organizer-described **Band 2 RTP magnetic anomalies** and **Band 13 isostatic gravity**. A tensor of magnetic-gradient orientations on opposite sides of a candidate line estimates truncated/rotated basement fabric; independent gravity gradients modulate the signal. The non-fault mimic is an intrusive/volcanic lithologic contact or an airborne flight-line seam. Unlike existing `edge.py` coincident edge magnitudes or `str88.py` multi-sensor orientation persistence, this is a **paired opposite-side fabric discontinuity**, not a copy of a sibling raster. The [USGS Dixie Valley magnetic study](https://pubs.usgs.gov/of/2002/ofr-02-0384/ofr-02-0384_508.pdf) motivates concealed-fault use, but no claim of truth is inferred from a magnetic anomaly alone.

One experiment: inputs restored autonomously from SHA-pinned owner GitHub mirrors; local feature tags and grid verified; all four single-feature canaries passed; score evaluated by the **unmodified shared evaluator** on seeds 20/21, whole-components hidden, visible-catalogue-only exclusion, pixel-exact known mask. The **unmodified shared writer** created a new one-TIFF ZIP and all-finite binary TIFF. The shared literal uniqueness test returned duplicate, and the candidate HOLDOUT-DTI fell below the frozen best; **stop**. Full [run card](registry/fabric_dislocation_run_card.json), [initial 29-prior audit](evidence/fabric_dislocation_uniqueness.json), [posthoc 30th-prior audit](evidence/postmerge_tiltzero_audit.json), [format audit](evidence/fabric_dislocation_format_audit.json), [machine release status](docs/status.json). The concurrently merged [TILTZERO experiment](registry/tiltzero_run_card.json) is also negative, but used seeds 20/30 rather than our 20/21: its HOLDOUT-DTI 0.055083 [0.046419, 0.063081] (22,663 withheld positives, `gems57-pooled-hide-v2`) is **not a matched-fold comparison** with this experiment. Prior PROVCREST's `ok_to_submit=true` was **not an independent strict gate** and is superseded here; no old candidate is approved by implication.

## How to reproduce and automatically inspect

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# Works with the configured public GitHub access. Restores owner-mirrored files
# under gitignored data/ and checks each pinned SHA-256; ~627 MB on disk.
.venv/bin/python scripts/restore_inputs.py
# Preregistration: registry/preregistration_fabric_dislocation.json
# Rebuilding new research output is deterministic; the writer refuses to
# overwrite an existing artifact. Move to a clean checkout to rerun generation.
.venv/bin/python scripts/run_fabric_dislocation.py
.venv/bin/python scripts/validate_current.py
.venv/bin/python scripts/readiness.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
# Fail-closed test of upload clearance: expected exit status 2 (negative).
.venv/bin/python scripts/validate_current.py --require-submit
```

The site is static: new predictions are built by Python scripts and the validated research TIFF is then published in [`docs/downloads/`](docs/downloads/). The page cannot log into your competition account or autonomously submit; it must not claim real-time quota or private leaderboard access. The [executive summary](docs/executive-summary.html) explains precisely what must happen for a *future* eligible file. The source table and verified/uncertain data provenance are at [`docs/sources.html`](docs/sources.html).

## Limitations and next work

1. **Literal `17GEMSDOE` Space-Filling Witness (`IR-88-1`):** Any non-empty set of positive pixels inside the valid footprint mathematically overlaps `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` at `100.00% > 70%`. We never silently exempt it; instead we expose both `literal_reading` (`duplicate: true`) and `like_for_like_reading` (`20/20` dot fields `PASS`, `duplicate: false`) in `registry/two_phase_uniqueness.json` so a human portfolio selector has complete, unvarnished evidence.
2. **Owner-Mirrored Reference Grid (`IR-88-2`):** `sample_submission.tif` (`2176d08e…`) and `existing_faults.tif` (`7ba308cc…`) are SHA-pinned owner mirrors; an authorized human with DrivenData access should verify byte identity against the live portal download before spending any weekly slot.
3. **Far-Basin (`> 2.5 km`) Discovery Frontier:** While `H88-ADHR` places `26.2%` (`9,417` dots) at `d_cat > 1.0 km` and `4.2%` (`1,520` dots) at `d_cat > 2.5 km` (`median d_cat = 6.40 px`), completely unmapped interior basins lacking 1 m LiDAR still carry substantial missed recall toward `0.4413`. Next session should read `research/next-steps.md` first: (a) test intra-magnetic vertical-to-regional polarity residual (`MRR-88`) for blind volcanic-covered grabens (`d_cat > 25 px`), and (b) seek explicit human selector authorization on `IR-88-1` if nominating `H88-ADHR` for one of the `≤ 3` weekly portal slots.

**Limitations recorded by PR #58 (kept for audit):**

1. **Binding registry paradox:** the literal positive-support interpretation of dense `17GEMSDOE` makes it impossible for *any* nonempty candidate to satisfy the stated 70% overlap rule. Preserve the strict failure until an explicit, consistent protocol change is authorized; do not “promote” by renaming or silently switching representations.
2. **Science:** this magnetic dislocation hypothesis did not generalize as well as ADHR on the available holdout; future work should focus on genuinely different geology and the known domain shift, not iterate spacing/dot counts from H33. The incumbent per-block paired terms need regeneration if a future arm approaches its point estimate.
3. **Access:** hash pins establish consistency with the owner's public GitHub mirrors, not authenticated DrivenData files, nor redistribution rights. A registered account must confirm the organizer sample hash and available weekly quota before any portal upload. This sandbox has no account submission-page receipts. No password/token is requested.
4. **Source scope:** 29 locally accessible/pinned raster files were checked at experiment time and a concurrently published 30th was checked only **posthoc**, not every private or unlinked GEMSDOE submission. Current public leaderboard remains a *dated static snapshot* with an official link, not a background scraper. The old site score list is not independently receipt-verified.
5. **Prize documentation:** the [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) require only one selected final submission and disclosure of AI use in the narrative where applicable; do not omit reproducibility assets or treat a format-valid file as winning.

No vendor evaluator/writer change was needed in this run. Three review passes and test results are logged in `research/session-20261024-audit.md`.
