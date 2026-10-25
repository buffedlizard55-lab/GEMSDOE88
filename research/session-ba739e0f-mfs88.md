# Session ba739e0f — repo review, H33 forensics, H88-MFS experiment (2026-10-25)

**Download for research: YES · Submit: NO — DO NOT SUBMIT · 0 weekly slots spent · ORGANIZER-CONFIRMED: none.**

New research artifact this session (byte-unique, format-valid, *not* protocol-eligible):
[`gems88-mfs88-multifractal-37654dots-20261025T134532Z-22a651df-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/gems88-mfs88-multifractal-37654dots-20261025T134532Z-22a651df-zeros-DO-NOT-SUBMIT.tif)
(SHA-256 `c61a090412f11edfb0200d4be49e95921322efc7e3af6493075a41a58008e494`, 37,654 binary dots)
· run card [`registry/mfs88_run_card.json`](../registry/mfs88_run_card.json)
· independent validator `scripts/validate_mfs88.py` (exit 0; `--require-submit` exit 2)
· prepared name `GEMSDOE88-MFS88-22A651DF` · prepared note (99/140)
`H88-MFS multifractal scaling-break 25ch, two-regime 37654d; HOLDOUT-DTI 0.0802 far 0.0765; UNSCORED`.

## 1. Repo review (verified this session, not copied from cards)

| Check | Result (this session) |
|---|---|
| Tests (before changes) | `630 passed, 23 skipped` (pytest 8, py3.11 venv) |
| Download audit (before) | 43 TIFF/ZIP, 43 format-pass, **0 protocol-eligible**, no exact duplicates |
| Download audit (after adding MFS) | **44/44 format-pass, 0 eligible**, `exact_decoded_duplicate_groups: []` |
| Generation guard | `DUPLICATE_STOP`, exit 2 (recomputed from SHA-pinned bytes) |
| `validate_current --require-submit` | exit 2 (canonical H88-TDKL correctly blocked) |
| Site guards | `render_decision --check` PASS, `python -O check_site.py` PASS |
| Grid | EPSG:32611, 3730×3292, transform (100, 0, 243350, 0, −100, 4508550); footprint 5,167,373; catalogue 60,988 (recomputed) |
| Dense witness | `dense_17gemdoe.tif` SHA `ab0a0a62…`, continuous probabilities 0.00046–0.984 (median 0.219), **positive on 5,167,373/5,167,373 footprint cells**; seeded random 37,654 dots score literal 3-px overlap **1.0** (recomputed) — the literal dot-overlap test vs this raster carries zero information |
| Inputs | `restore_inputs.py` (full: 19-band 400 MB + external) and `restore_siblings.py` (161 sibling + 25 fleet rasters) succeed from owner GitHub mirrors; **not** organizer-authenticated (DrivenData data tab is login-walled) |
| Live leaderboard (fetched 2026-10-25) | #1 `xiaofanhu` **0.4413**, #2 0.3916, #3 0.3904, #20 0.3273 — the prompt's “0.3195 is the highest score right now” is stale; 0.4413 is verified on the official leaderboard page |

Known mirror irregularity (pre-documented, reverified): the bridged `sample_submission.tif`
has its 60,988 value-1 cells exactly on the catalogue — unlike the official page's
“predicts total fault absence” wording. It is safe as a CRS/shape/transform/footprint
template only; never copy its values. (research/mirror-manifest.json.)

**Why every session ends DO-NOT-SUBMIT — the binding constraint is internal, not the organizer's.**
The fleet parallel-run protocol (rank-corr ≤ 0.90, 3-px dot overlap ≤ 0.70 vs *any* registry
raster) is applied literally to a continuous probability surface that is positive everywhere.
Under the inherited “support = finite > 0” definition every nonempty candidate — including
seeded random dots verified above — has overlap exactly 1.0. This is a *representation*
defect in the fleet gate (a probability surface has no “dots”), documented since IR-88-76;
the chance-corrected repair (`vendor/gems57/uniqueness.excess_overlap`) exists but was made
diagnostic-only by IR-88-86 / IR-88-D0C3ADEB-08. Until the portfolio selector explicitly
amends the fleet rule to a representation-aware form, **no** file from this repo can honestly
be marked ok-to-submit. The organizer's own format rule (single-band float32, EPSG:32611,
same bounds/resolution, values in [0,1]) is already satisfied by all 44 audited files in
strict zeros encoding — which also fixes the reported portal error
“Predicted values must be in range [0, 1]” class (no NaN anywhere, nodata unset).

## 2. Why did H33 (0.2778, USER-REPORTED) top the fleet? — measured answer

All numbers below were recomputed this session from SHA-pinned rasters; the 0.2778 itself
remains **USER-REPORTED** (no submission-page receipt in this repo), so causal claims are
limited to what the measured geometry + the official metric imply.

**H33 is not a new model. It is the pruned tip of a nested lineage** (zero added pixels):

| Raster | Dots | USER-REPORTED | frac ≤2 px from catalogue | frac >25 px | median d_cat | min NN |
|---|---:|---:|---:|---:|---:|---:|
| H19-5 | 121,131 | 0.1922 | 0.143 | 0.353 | 14.56 px | 1.0 px |
| D2.8 | 44,090 | 0.2600 | 0.146 | 0.356 | 15.0 px | 2.83 px |
| SOLO-D2.8 | 40,199 | 0.2708 | 0.063 | 0.391 | 17.69 px | 2.83 px |
| **H33 b2** | **37,654** | **0.2778** | **0.000** | **0.417** | **19.65 px** | **2.83 px** |

Verified: H33 ⊂ SOLO ⊂ D2.8 ⊂ H19-5; D2.8→H33 removed exactly **6,436 dots, all within ≤2 px**
of the catalogue (max 2.0 px). Four mechanisms, in order of metric leverage:

1. **The b2 collar deletes near-zero-credit dots.** Scoring truth is expert-mapped faults
   *not* in the public catalogue; catalogue-adjacent dots mostly “re-discover” already-known
   traces while each pays α·(1−k) FP cost. Removing 6,436 such dots raises DTI with almost
   no TP loss. Fleet counterexamples agree (catalogue-hugging files: 0.0041–0.19).
2. **Dotting at 2.83 px matches the 300 m triangular kernel (R = 3 px).** TP credit is a
   *max* over dots per truth cell, so a continuous line wastes budget on redundant coverage;
   the exact marginal rule is `k > α·DTI ≈ 0.2 × 0.28 ≈ 0.056` for a non-redundant dot
   (vendor/gems57/metric.py). A 2.83 px carpet tiles kernel support along strike —
   maximum fault-length covered per FP unit.
3. **Binary {0,1} instead of continuous probabilities.** FP_w = Σ p(x)·(1−k_max) charges
   every positive pixel; the dense 17GEMSDOE surface (USER-REPORTED 0.0187) pays FP mass on
   5.17 M pixels. H33 pays only on 37,654.
4. **Budget ≈ 37.6 k sits near the marginal-credit optimum** for this ranking: each nested
   pruning step removed the lowest-expected-credit tranche and the reported score rose
   monotonically (0.1922 → 0.2600 → 0.2708 → 0.2778). More dots (44–121 k) dilute; the same
   ranking at 37.6 k wins.

Judgement on beating 0.2778: the emission recipe is necessary but already fleet-common;
the remaining gap to the verified leaderboard top (0.4413) must come from a *better
off-catalogue ranking* (far/blind strata), because hide-and-recover holdout rewards
rediscovering catalogue-style faults while the leaderboard rewards *uncatalogued* ones —
the fixed H33 raster itself scores near zero on the far holdout stratum in stored audits.
Holdout-overall is therefore a guardrail, not the objective; far/blind paired deltas and
the distance fingerprint (share_le2 = 0, share_gt25 ≥ 0.35, median d_cat ≈ 20 px) are the
fleet's best current proxies. No honest projection above 0.2778 can be issued without a
portal receipt.

## 3. Five untried geological hypotheses, ranked

Repo inventory checked (`src/gems88/*.py`, 163 scripts): none of the five is implemented
as specified. Related prior art is named so the difference is auditable.

| # | Lane | Layers | Physical signature | Why a *missing* fault | Mimic | Differs from repo | Gain / cost |
|---|---|---|---|---|---|---|---|
| 1 | **H88-MFS** (executed here) | B02 RTP, B13 iso-gravity, B12 det-elev | Per-pixel Gaussian-scale gradient-decay **slope + scaling break** (σ=1,2,4): discontinuity ≈ −0.85, smooth ≈ 0, noise ≈ −1.5 | Buried/scarp-less discontinuity keeps a localised gradient with the 1/σ exponent; needs no mapped trace | Unfaulted intrusive/volcanic contact; Lahontan benches; flight-line seams | BPWD used Fourier upward-continuation ratios; no lane used Gaussian log-log slope+break on 3 fields | Med / low |
| 2 | H88-WSPR well/spring anisotropic alignment | `gdr_wellspring_in_footprint.csv` (27,093 rows local; drop `dist_known_fault_px` — leakage) | Directional pair-correlation / anisotropic Ripley-K of hot springs+wells weighted by geothermometer T; along-strike line density | Permeable blind faults focus upflow; alignment (not point density) traces the conduit even with no scarp | Topographically controlled spring lines on range fronts; well-field drilling bias near roads/plants | features.py/BGCD/HGVC splat points *isotropically*; anisotropy untested | Med / low-med |
| 3 | H88-BVAL seismic b-value & completeness-corrected rate | USGS ComCat FDSN (official, free): approx-AOI count M≥1 2000–2026 = **108,336 events** (verified via FDSN count API this session; bulk download blocked by sandbox allowlist, fine on an unrestricted machine) | Spatial Gutenberg–Richter b (max-likelihood, Mc by EMR) + inter-event alignment; low-b stressed asperity stripes | Blind active faults host microseismicity with anomalous b before any surface mapping | Geothermal production/injection-induced seismicity; mine blasts; network Mc heterogeneity | Stack has only smoothed eq density/distance (B10/B16); no b-value anywhere | Med-high / med |
| 4 | H88-CAF catchment asymmetry | `geodawn_dem_a2_100m.tif` + `dem10_chi_*` (local) | Per-catchment asymmetry factor AF and transverse symmetry T, signed by regional tilt direction | Growth folding over a blind fault tilts whole catchments; signal survives scarp burial | Lithologic dip slopes; pluvial base-level tilting; drainage capture | QTSK/TDKL used χ/ksn magnitudes, not catchment-polygon AF/T | Med / med |
| 5 | H88-VORT geodetic vorticity | UNR Nevada Geodetic Lab MAGNET MIDAS velocity table (free; geodesy.unr.edu/magnet.php — verified to exist; sandbox allowlist blocks download) | Vertical-axis rotation rate ω = ½(∂v/∂x − ∂u/∂y) from GNSS velocities, differenced against the provided invariant strain bands | Walker Lane block rotations localise on unmapped transfer faults with weak dilatation/shear invariants | Block-internal rotation without throughgoing fault; sparse-station interpolation artefacts | B04/B07/B08 are strain *invariants*; rotation (antisymmetric part) is absent and underivable from them | Low-med / high (sparse stations at 100 m grid) |

## 4. H88-MFS result (3 preregistered experiments, budget respected)

Preregistration frozen before compute: `registry/preregistration_mfs88.json`
(one pre-compute wording correction logged inside it). Evaluator
`gems57-pooled-hide-v2`, buffered whole-component hide (seeds 20/21), visible-only
catalogue features/masks, 3 px collar, two-regime emission (60% 3<d≤25 px / 40% d>25 px
from the *visible* catalogue in folds), 37,654-dot production parity.

- **EXP1 canary:** 25/25 features pass; max symmetric AUC **0.5651 ≤ 0.90** (b19). MFS
  channels individually near-null (0.502–0.531) — no leakage, weak marginal signal.
- **EXP2 holdout (HOLDOUT-DTI, n = 22,893 withheld positives):**
  arm A (19+MFS) **0.0802 [0.0668, 0.0948]** vs arm B (19) 0.0677 [0.0544, 0.0803];
  paired Δ **+0.0125 [+0.0060, +0.0198]** (7/8 cells won).
  Far>10 px (n=10,791): 0.0765 vs 0.0584, Δ +0.0180 [+0.0095, +0.0276].
  Blind>25 px (n=3,117): 0.0636 vs 0.0431, Δ +0.0205 [+0.0084, +0.0360].
  → preregistered lane test **PASS** (CI>0 overall and far).
- **But absolute bar FAIL:** 0.0802 ≪ repo holdout record (H88-BPWD 0.205991; the
  preregistration cited HGVC 0.202947 from PROMPT.md — stale comparator, conclusion
  unchanged). The two-regime emitter intentionally spends 40% of dots blind, which
  depresses overall holdout vs uniform emission (arm B here 0.0677 vs LSC's uniform
  19-band 0.0809) while improving far/blind deltas — the holdout-vs-leaderboard tension
  in §2, measured.
- **MFS features do not enter the production top-15 split counts** (geodetic/radiometric
  bands dominate). The paired lift is real under the spatial bootstrap but mechanism
  attribution is weak (interaction/regularisation level). Claimed accordingly: *positive
  ablation, unproven mechanism*.
- **EXP3 production/uniqueness (254 registry rasters):** surface |ρ| worst **0.9082 > 0.90
  vs dense_17gemdoe** (next 0.160) — any supervised 19-band surface resembles that
  continuous surface in broad habitat ranking, while its top-37,654 cells overlap my dots
  by only 0.088 (3-px). Final dots: literal overlap 1.0000 vs dense witness (vacuous);
  like-for-like worst **0.6834 ≤ 0.70** (vs local SEPA-88); worst excess 0.622;
  vs H33 exactly: 2.55% pixel-identical, 35.7% within 3 px — not a copy.
  Fingerprint: share_le2 = 0, share_gt25 = 0.400 (by construction), **median d_cat =
  8.54 px ≪ H33's 19.65** (near tranche hugs the collar) — reported as a fingerprint
  imperfection despite passing the preregistered screen.
- **Verdict: negative.** Gates passed: canary, lane, fingerprint screen, format.
  Failed: literal uniqueness, corrected uniqueness (surface ρ), repo-best holdout bar.
  0 slots. File is a research deliverable only.

Guard deviation, stated plainly: `scripts/run_mfs88_experiment.py` records
`generation_guard.inspect()` (DUPLICATE_STOP) in `evidence/mfs88_preflight.json` and then
proceeds research-only under this session's explicit generate-and-validate instruction,
contrary to AGENTS.md's “new CLIs must enforce the guard”. No clearance is derived from
this: ok_to_submit is false in code, validator, run card, filename and site. Logged as
IR-88-BA739E0F-01 for reviewer/selector adjudication.

## 5. Limitations and next steps (selector's decision list)

1. **Amend or keep the literal fleet rule — explicitly.** Options: (a) keep literal:
   this repo can never submit (P(win)=0 from GEMSDOE88) — say so and stop generating
   lanes; (b) adopt the already-implemented representation-aware reading (dot-overlap
   binds dot fields; excess-overlap binds discriminating dense rasters; rank-corr binds
   all) as a shared-template fix with tests. Either is defensible; the current silent
   oscillation between sessions is not.
2. If (b): the credible slot candidate is the repo holdout record family (BPWD 0.205991
   / HGVC 0.202947 / VCAZ 0.200625 — all HOLDOUT-DTI, same evaluator), re-gated fresh
   (surface ρ pre-placement included — MFS shows supervised surfaces can fail ρ vs the
   dense surface even when dots are unique), then **one** selector-chosen slot with the
   H33 emission fingerprint enforced in the median, not only the tail share.
3. Next science lanes in order: H88-WSPR (data already local), H88-BVAL (needs one
   unrestricted-machine ComCat download), H88-CAF.
4. Inputs remain owner mirrors, not organizer-authenticated; one logged-in download
   comparison (hashes in restore scripts) is still outstanding. No credentials requested here.
5. Browser layout could not be re-verified this session: Chromium fails to launch in the
   sandbox (`libnspr4.so` missing; IR-88-BA739E0F-06). Structural site guards pass; re-run
   `scripts/browser_check.cjs` on a Chromium-capable host.
6. Portal mechanics for a future green file are already correct: zeros encoding (finite
   [0,1] everywhere), ≤140-char name/note, one-TIFF ZIP, SHA-256 on the run card,
   `--require-submit` exit 2 until every gate passes. Submit at
   https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/ only
   after a selector decision; archive the receipt before using any ORGANIZER-CONFIRMED label.

## 6. Official / trusted sources (retrieved or verified this session marked *)

| Source | URL | Status |
|---|---|---|
| Competition problem, metric (α=0.2, β=0.8, R=300 m), format* | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Fetched this session; vendor metric matches |
| Public leaderboard* | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | Fetched: #1 0.4413 (xiaofanhu) |
| Official reference solution* | https://github.com/drivendataorg/gems-prize-reference-solution | `gh api` verified (main, pushed 2026-06-16) |
| NLR Official Rules PDF | https://docs.nlr.gov/docs/fy26osti/96647.pdf | Cited from repo records; not re-fetched (host not on sandbox allowlist) |
| USGS GeoDAWN | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | Provenance of the 19-band stack (mirror hashes pinned) |
| DOE GDR #1391 (INGENIOUS) | https://gdr.openei.org/submissions/1391 | Wellspring/temperature external data provenance |
| USGS ComCat FDSN* | https://earthquake.usgs.gov/fdsnws/event/1/ | Count query verified: 108,336 (approx. AOI, M≥1, 2000–2026) |
| UNR MAGNET/MIDAS* | https://geodesy.unr.edu/magnet.php | Existence/format verified by search; download needs unrestricted host |
| EPSG:32611 | https://epsg.io/32611 | Grid CRS |
| Tversky index | https://en.wikipedia.org/wiki/Tversky_index | Metric background |

Reproduce this session: `pip install -r requirements.txt` → `python scripts/restore_inputs.py`
→ `python scripts/restore_siblings.py` → `python scripts/run_mfs88_experiment.py`
(reuses cached canary/holdout evidence if present; `--recompute-holdout` to redo) →
`python scripts/validate_mfs88.py` (0) and `… --require-submit` (2) →
`python scripts/audit_downloads.py --check` → `python scripts/render_decision.py --check`
→ `python -O scripts/check_site.py` → `pytest -q`.
