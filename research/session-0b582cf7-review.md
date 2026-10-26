# Session `0b582cf7` (`2026-10-26`, late) — Focus-9 Re-Audit at Advanced HEADs, GEMSDOE27 Promotion Flag, Selector Scoping Packet & Frozen `H88-PTGM` Preregistration

- **Branch / Base Commit:** `arena/0b582cf7-gemsdoe88` (branched from `origin/main` `34066f4c23b24352b49b1c41ea1b41906bcea59a`, merge of PR #198).
- **Automated Gate Decision (unchanged):** **`BLOCKED` (`DUPLICATE_STOP`) — DOWNLOAD FOR RESEARCH: `YES` · SUBMIT TO COMPETITION: `NO — DO NOT SUBMIT`** (`ok_to_submit = false`, `0` weekly slots spent, `0` new GeoTIFFs, `0` geological experiments).
- **What is new in this session:** all nine focus repositories (`GEMSDOE24`, `GEMSDOE25`, `GEMSDOE27`, `GEMSDOE28`, `GEMSDOE30`, `GEMSDOE31`, `GEMSDOE32`, `GEMSDOE33`, `GEMSDOE36`) advanced past the HEADs pinned by the earlier same-day audit (`c59db412`). Their nine new headline `2026-10-26` candidates were downloaded at the new pinned HEADs and re-measured pixel-by-pixel here. **Result: `9/9` are strict full-grid `[0, 1]` portal-safe, `9/9` place `0` dots on the catalogue or within `2 px` of it, `9/9` are genuinely off the historical `H19-5` lineage on sparse tests (`< 0.70` vs `H33-2-B2`), and `9/9` still have literal 3-px overlap exactly `1.0000` with the dense `17GEMSDOE` witness — so `0/9` clear the GEMSDOE88 literal protocol.** Eight sites say so themselves (`DO NOT SUBMIT`); **GEMSDOE27 alone claims `OK TO SUBMIT`** on a narrower screen — flagged `IR-88-0B582CF7-01` below. Do not spend a slot on that badge under this protocol.
- **Canonical educational download (unchanged bytes, research only):** [`gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif`](../downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif) (`SHA-256 db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`, `25,000` dots, strict finite `[0, 1]`, `EPSG:32611`, `3730 × 3292`, exact sample geotransform `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`). It is an educational artifact, not the conditional front-runner (see §5: it fails even like-for-like post-merge at `0.76228`).
- **Prepared audit identifier & note (record only — NOT upload clearance):** Name `GEMSDOE88-LATE-FOCUS9-REAUDIT-20261026-NO-NEW-FILE` · Note (`119/140` chars) `Late 9-site re-audit 20261026: 9/9 dense overlap 1.0>0.70, GEMSDOE27 promote flagged; 0 new TIF; 0 slots; DO NOT SUBMIT`.
- **Machine deliverables:** [late focus-9 audit JSON](../data/focus_latest_20261026b.json) · [CSV](../data/focus_latest_20261026b.csv) · auditor `scripts/audit_focus_latest_20261026b.py` (repo root) · [selector scoping packet](../data/selector_scoping_packet_20261026.json) · [leaderboard snapshot](../data/leaderboard_official_snapshot_0b582cf7_20261026.json) · [negative run card](../data/session_0b582cf7_run_card.json) · frozen `H88-PTGM` preregistration (`registry/preregistration_h88_ptgm_20261026.json` in the repo root).

---

## 1. Executive summary — the only safe download/submit answer today

| Question | Answer (automated, no human inspector) |
|---|---|
| Is there a **new unique TIFF** from GEMSDOE88 in this session? | **NO.** `scripts/generation_guard.py` exits `2` (`DUPLICATE_STOP`) on freshly restored pinned inputs — re-run in this session after `bash scripts/download_competition_data.sh --validation` + `python scripts/prepare_data.py` (both PASS). Generating one anyway would violate Protocol rules 1–2 and `AGENTS.md`. |
| May I **download** a file for research/education? | **YES** — the canonical `*-DO-NOT-SUBMIT.tif` above (and the `50/50` Pages + `21/21` `submissions/` research packages re-audited PASS this session). |
| May I **submit** any current file (GEMSDOE88 or focus-9) to DrivenData? | **NO — DO NOT SUBMIT.** `0` files clear the literal all-registry uniqueness gate; `0` organizer receipts exist in this repo; quota is unverified from this sandbox; slot promotion is a separate selector step (Protocol rule 6). |
| GEMSDOE27's site says **OK TO SUBMIT** — should I? | **NO under this protocol** (`IR-88-0B582CF7-01`, §3). Its badge rests on a 27-raster screen and a private metric; measured here it is `1.0000` vs the dense witness and was never screened against it. |
| Which historical file is the **best-scoring** to learn from? | GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778` **USER-REPORTED**, no organizer receipt). Learn from its geometry (§4); do not copy/resubmit it. |
| What is the **current public leaderboard #1**? | **`0.4437` (xiaofanhu)**, OBSERVED-PUBLIC on `2026-10-26` via the public leaderboard page — superseding the prompt's `0.4413`; `0.3195` is stale (DARD now #9 at `0.3398`). Snapshot: [JSON](../data/leaderboard_official_snapshot_0b582cf7_20261026.json). |

**Maximize P(Win):** preserve scarce slots for an evidence-backed, distinctly-screened candidate. **Own the Outcome:** report the unmet "must generate" requirement with its mathematical proof instead of manufacturing a clearance.

---

## 2. Per-site executive summary (historical champion + latest headline candidate)

Historical champions are the byte-verified `c59db412` results (all **USER-REPORTED**, `0` receipts; `0/9` unique — one `H19-5 → D1.5/D2.8 → SOLO → H33-2-B2` pruning family). Latest candidates are **this session's measurements** (`scripts/audit_focus_latest_20261026b.py`) at the new HEADs; sibling holdouts are **SIBLING-REPORTED** (mutually incompatible private evaluators — never compare them to each other or to a leaderboard).

| Site (new HEAD) | Historical best (USER-REPORTED) | Latest `2026-10-26` headline candidate — measured here (SHA prefix · dots · `>25 px` share · 3-px vs `H33-2-B2` / dense-17) | Sibling's own verdict | GEMSDOE88 verdict |
|---|---|---|---|:---:|
| **GEMSDOE24** (`17496743`) | `h25-1-dotted-h19-5-d1-5` `0.2477` (duplicate) | `H24-DPRF1` stitched-OOF two-regime (`c1257c1d…`, SHA matches sibling claim · `37,654` · `44.31%` · `0.4560 / 1.0000`) | `DO_NOT_SUBMIT` (lattice + unknown quota; sibling holdout `0.16379`, own `gems-segment-pooled-v1`) | **NO** |
| **GEMSDOE25** (`88a29e09`) | `dotted-h19-5-d2-8` `0.2600` (= GEMSDOE30, duplicate) | `H71-HGPC-BLIND` (`44ee6028…` · `59,472` · `48.70%` · `0.1537 / 1.0000`) | `DO NOT SUBMIT` (own holdout FAIL `0.0506` vs `0.1499`) | **NO** |
| **GEMSDOE27** (`426426b4`) | `topo-gap-closure-t-v2` `0.2449` (duplicate); off-lineage `H29-S` `0.2190` already scored | `H31-1-DRCG-WL-CELF28` (`2c002b02…`, SHA matches · `37,654` · `36.74%` · `0.5023 / 1.0000`) | **CLAIMED `OK TO SUBMIT`** (27-raster screen; private blind `0.047302`) — see §3 | **NO — flagged** |
| **GEMSDOE28** (`348ff086`) | `h36-1-rung30-blind-r1` `0.2710` (duplicate) | `S20-NCHC` (`1d629d6c…` · `40,071` · `18.30%` · `0.3114 / 1.0000`) | `DO NOT SUBMIT` (paired Δ CI < 0 vs baseline) | **NO** |
| **GEMSDOE30** (`73db382d`) | `d28-poisson300m` `0.2600` (= GEMSDOE25, duplicate) | `FFL-1` MSDB×LiDAR (`79506070…`, SHA matches · `44,090` · `18.48%` · `0.4633 / 1.0000`) | `DO NOT SUBMIT — DUPLICATE-STOPPED` (`78.28%` vs MSDB-1v2) | **NO** |
| **GEMSDOE31** (`e6e85b35`) | `h27-4-solo-d28` `0.2708` (= GEMSDOE28 solo, duplicate) | `XFCOH31` x-field coherence (`857dd662…` · `37,654` · `27.41%` · `0.2747 / 1.0000`) | `DO NOT SUBMIT` (holdout-negative; lattice STOP recorded) | **NO** |
| **GEMSDOE32** (`9e55d5d6`) | **`h33-h33-2-b2` `0.2778`** (#1 claim; exact subset) | `EXP3_H38_G1_CORROB` 53-ch (`6efe1402…`, SHA matches · `37,654` · `27.62%` · `0.5878 / 1.0000`) | `DO NOT SUBMIT` (SGMC trails champion; `99.71%` lattice; `77.56%` local) | **NO** |
| **GEMSDOE33** (`fded5384`) | `h33d-analog-stepover` `0.2632` (duplicate) | `A33-R2-CSHT` (`14ab452c…`, SHA matches · `37,654` · **`2.60%`** · `0.3586 / 1.0000`) | `DO NOT SUBMIT` (pre-placement surface duplicate) | **NO** (+ §6 `IR-…-03`) |
| **GEMSDOE36** (`4938a123`) | `anderson-pinn-38854` `0.2750` (H33 superset) | `ATVR-36-EXP2` (`54f493f4…`, SHA matches · `37,654` · `16.12%` · `0.3594 / 1.0000`) | `DO NOT SUBMIT — HOLD SLOT` (literal blanket FAIL) | **NO** |

Progress worth crediting, measured not asserted: the fleet has learned the H33 emission hygiene (`0` dots `<= 2 px` from the catalogue in `9/9` new files; all-finite `[0, 1]` containers in `9/9`) and has genuinely left the `H19-5` dot set (vs `H33-2-B2` now `0.15–0.59`, vs the historical champions' `0.98–1.00`). What has **not** changed is the saturated-prior geometry: blanketing registry entries (dense 17GEMSDOE here; spacing-5 lattice in sibling registries) make the literal `>70%`-within-3-px test fire on *every* candidate by construction.

---

## 3. `IR-88-0B582CF7-01` — GEMSDOE27's `OK TO SUBMIT` badge does not survive this protocol

At HEAD `426426b4`, GEMSDOE27 headlines `✅ OK TO DOWNLOAD AND SUBMIT` for `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (`2c002b0279241986…`, byte-verified here). Its gates, as published, are: strict `[0, 1]` format (we **confirm** PASS: `12,279,160/12,279,160` finite, exact grid); canary `<= 0.90` (sibling-reported, not re-run); uniqueness vs **27 rasters** (12 pinned peers + 2 own scored + 13 own research; max `57.70%` vs peers); and a private blind holdout (`gems27.metric.dti_binary v1 + 600m-buffered-quadrant-40cell`, seeds `400–409`) where the candidate pools **`0.047302`** vs in-repo controls `0.014825–0.045202`.

Three protocol defects, each sufficient to hold the slot here:

1. **Registry scope.** The screen omits the blanketing rasters that bind every other fleet member. Measured in this session on the exact promoted bytes: 3-px forward overlap **1.0000** vs `dense_17gemdoe.tif` (`ab0a0a62…`). GEMSDOE24 (lattice), GEMSDOE31 (695-registry lattice `99.93%`), GEMSDOE32 (lattice `99.71%`) and GEMSDOE36 (201-raster blankets) all fail-closed on the equivalent test. A 27-raster screen cannot establish fleet uniqueness conclusively.
2. **Instrument scope.** `0.047302` on a private blind instrument (289,180 *repeated-seed occurrences*) is not `HOLDOUT-DTI (gems57-pooled-hide-v2, n=22,893)` and is not comparable to `0.2778`, to GEMSDOE27's own already-scored `0.2190` claim, or to any sibling holdout. Beating same-repo controls on a private instrument is the same pattern rejected for GEMSDOE32 `R6-1-stepprofile` (`IR-88-C59DB412-02`).
3. **Selector step.** Protocol rule 6 reserves slot promotion to a separate selector within the live weekly cap. A repo-local readiness function flipping its own badge — while recording that the operative screen was narrowed by an in-repo "selector decision" — is not that step, and no quota receipt is published.

**Disposition:** treat the GEMSDOE27 file exactly like the other eight: research-download YES (format is genuinely portal-safe), submit NO until the fleet-wide registry-definition decision in §5 is made and the file passes the resulting full screen + shared holdout comparison. This is a protocol-scope flag, not an accusation about the file's geology: its measured geometry (`37,654` dots, `36.74%` beyond `25 px`, `0.5023` vs champion) is squarely in the credible off-lineage family.

---

## 4. Why `0.2778` won, and what beating it actually requires (PhD answer, verified algebra)

`0.2778` remains **USER-REPORTED** (GEMSDOE32's own record states no organizer receipt; GEMSDOE36's README re-labels such figures `ORGANIZER-CONFIRMED` without receipts visible to us — `IR-88-0B582CF7-02`; we keep the stricter label). The score's *mechanism* is nevertheless byte-proved (`c59db412` audit): `H33-2-B2` (`37,654` dots) `⊂ SOLO-D2.8` (`40,199`) `⊂ D2.8` (`44,090`) `⊂(thinned) H19-5` (`121,131`). Under the official DTI (`vendor/gems57/metric.py`: `α = 0.2` on `FP_w`, `β = 0.8` on `FN_w`, 300 m triangular kernel), a binary submission obeys `DTI = T / (0.2(T + n − M) + 0.8|G|)`, and one more dot helps iff its marginal truth credit `ΔT > 0.2·DTI·(ΔT + 1 − k)` — a `≈ 0.0556` break-even at `0.2778`. The `H19-5` surface's `<= 2 px` dots sit in the *digitization shadow* of already-masked catalogue faults (scarp/gradient halos of known traces): near-zero `ΔT`, full `0.2` denominator cost. Deleting `6,436` of them in two steps bought `0.2600 → 0.2708 → 0.2778` (`≈ +2.8×10⁻⁶` per dot) while 2.8-px thinning kept crest coverage (midpoint kernel credit still `k(141 m) = 0.529`). The symmetric penalties confirm the calculus: `+1,259` gap-closure dots cost `-0.0028` (GEMSDOE27 `0.2449`); `+1,200` off-ridge PINN dots cost `-0.0028` (GEMSDOE36 `0.2750`).

**Can we beat `0.2778` / `0.3195` / `0.4437`?** Not by pruning this surface further (`B≥3` rings are duplicates near break-even), and not at all until §5's registry decision unblocks generation. Arithmetically, at fixed `~37,654` dots, `0.3195` needs `≈ +18%` more weighted truth capture than `0.2778`; `0.4437` needs `≈ +60%`. The fleet's own scored evidence on where that capture lives is consistent: user-reported live results rise monotonically with far-field share (`1.18% >25 px → 0.0742`; `37.87% → 0.2190`; `41.74% → 0.2778`). Beating the champion therefore requires a *detector* that is precise `>10 px` and `>25 px` from the catalogue — the regime catalogue-proximity features cannot reach by construction — which is exactly what the frozen `H88-PTGM` lane (§7) and the external 1-m 3DEP lane target. **No projection is offered as a score; only an organizer receipt can confirm one.**

### The `"Predicted values must be in range [0, 1]"` portal error — root cause, permanently auto-checked

It is a **container** defect, not a score: exterior `NaN`s (the `-nan` twins carry `7,111,787` of them; `NaN >= 0` is `False`, so whole-array range checks fail) or leaked `-3.4028235e+38` float32 sentinels. The fix used fleet-wide and verified here is the `zeros` container (`0.0` outside footprint, `nodata=None`, clip `[0,1]`). This session: all `50/50` GEMSDOE88 Pages packages, `21/21` `submissions/` packages, and all `9/9` new sibling headline files pass strict full-grid finite `[0, 1]` + exact-grid checks with zero human inspection. **Always upload the `-zeros`/`-allfinite` file, never a `-nan` twin** — when a file is ever cleared (none is today).

---

## 5. The real blocker is now a one-page selector decision (packet included)

Next-step #1 from `c59db412` was: *decide how blanketing priors are scoped*. This session turns that into a signable packet — [selector_scoping_packet_20261026.json](../data/selector_scoping_packet_20261026.json) — with three options and computed consequences:

- **A · Keep literal** (current): mathematically zero eligible candidates, forever. The "MUST GENERATE" requirement is then unsatisfiable as written — say so plainly rather than evading it.
- **B · Scope blanketing priors to equal-support (recommended, NOT adopted):** for rasters whose 3-px halo covers the whole allowed domain (non-discriminating for the dot test), use the *already-implemented shared* equal-support/excess readings (`vendor/gems57/uniqueness.py: registry_dots`, `excess_overlap`) while keeping Spearman `<= 0.90` on every raster and literal overlap `<= 0.70` on every discriminating raster, plus preregistered registry inventory hash, post-merge re-screen, and an authenticated quota check. A candidate copied from the dense surface still fails its own top-K test.
- **C · Narrow to focus peers** (GEMSDOE27's unilateral choice): documented for completeness; **not recommended** (false-uniqueness risk, §3).

Conditional consequence table (stored run cards, `HOLDOUT-DTI gems57-pooled-hide-v2 n=22,893`; **not clearance** — every file needs a fresh full-fleet re-screen under any adopted option): `H88-BPWD 0.205991 [0.188105, 0.223344]` (paired win vs HGVC overall, blind-stratum delta crosses 0) and `H88-HGVC 0.202947` (best blind `0.078959`) are the conditional front-runners; `H88-VCAZ 0.200625` is third; the canonical `H88-TDKL 0.196237` download **would still fail** on post-merge concurrent overlap (`0.76228 > 0.70`). Note `docs/data/candidate_matrix.json` omits these top rows — build selector evidence from run cards, not that matrix (`IR-88-0B582CF7-04`).

**This session adopts nothing.** Changing the binding rule unilaterally — by renaming, re-thresholding, or importing a builder — is precisely what `AGENTS.md` rule 2 forbids, and Protocol rule 6 reserves promotion to the selector. The packet's decision record (selector, date, option, registry-inventory SHA-256, quota receipt) is intentionally `null`.

---

## 6. Remaining irregularities flagged this session

- **IR-88-0B582CF7-01** — GEMSDOE27 `OK TO SUBMIT` promotion on a 27-raster screen + private metric; measured `1.0000` vs the dense witness (§3). Fleet outcome is now `8/9` fail-closed vs `1/9` self-promoted — the discrepancy itself is the risk to a scarce slot.
- **IR-88-0B582CF7-02** — Evidence-class inflation in sibling prose: GEMSDOE36's README labels historical figures (incl. `0.2778`) `ORGANIZER-CONFIRMED`; no submission-page receipt is visible to GEMSDOE88 for any of them. All such figures stay **USER-REPORTED** here until a receipt is archived.
- **IR-88-0B582CF7-03** — Holdout/live divergence risk, measured: GEMSDOE33's `A33-R2-CSHT` wins its own catalogue holdout (`8/8` folds, sibling-reported) with only **`2.60%`** of dots `>25 px` from the catalogue (`97.4%` in the collar the live mask discounts). Against the fleet's scored far-field law (`1.18% → 0.0742` … `41.74% → 0.2778`), catalogue-holdout wins at extreme collar concentration should be treated as instrument overfit until a far/blind stratum win is shown. (A measurement, not a score claim.)
- **IR-88-0B582CF7-04** — Internal stale evidence: `docs/data/candidate_matrix.json` (14 rows) omits the repo's top holdout records (BPWD/VCAZ/TDKL/SEPA) that the selector packet needs; superseded for ranking purposes by the run-card-sourced packet table. Regenerating that matrix from all run cards is queued work, not done silently here.

Also noted, not new: the standing prompt contains internal tensions (generate vs duplicate-stop; no manual input vs separate selector; `0.3195`/`0.4413` vs observed `0.4437`) and no single assigned lane paragraph was supplied (Protocol rule 1) — this session therefore froze its own lane by preregistration (§7) without executing it.

---

## 7. Ranked hypotheses & the frozen next experiment (`H88-PTGM`)

The five ranked untried hypotheses from `c59db412` stand (full layer/transform/mimic specifications in [session-c59db412-hypotheses.md](session-c59db412-hypotheses.md)); this session **froze #1 into an executable preregistration** so the unblocked session spends its budget on science, not design: `registry/preregistration_h88_ptgm_20261026.json` (repo root).

| Rank | ID | Signature targeted | Why it finds *missing* faults | Mimic (veto) | Cost |
|---:|---|---|---|---|---|
| 1 | **H88-PTGM** (preregistered) | Cross-field structural-index doublet `N_m − N_g` along `+∇B15`, up-dip slot emission | Blind intrabasin step-faults under `50–800 m` cover; corrects the `300–700 m` basinward gravity-centroid offset outside the DTI kernel | Ash-flow tuff pinchouts / caldera rings (vent + non-linear-strike veto) | Low–Med (local layers only) |
| 2 | H88-BFRK | Advective thermal residual after Rybach radiogenic regression at accommodation twists | Low-throw Synthetic/antithetic meshes hosting blind geothermal systems | Radiogenic plutons / uranyl playas (residualized out) | Low–Med |
| 3 | H88-DRMC | Hanks–Andrews diffusion dipole symmetry (`lapneg≈lappos`, throw-invariant `L_diff`) | Degraded pre-Holocene scarps below slope/hillshade mapping | Lahontan shorelines (non-isohypse veto), gully banks (asymmetry veto) | Medium |
| 4 | H88-VVRD | Vent-radial edifice veto + inter-vent collinear dike corridors × gravity step | Sub-basalt faults mantled by lava, invisible to scarp mapping | Lava-lobe fronts / plugs (requires `B18` basement step) | Low |
| 5 | H88-3DEP-SCARP | 1-m wavelet-packet graben doublets from USGS 3DEP COGs | `3–15 m` antithetic doublets erased by 100-m `uint8` summaries | Roads/berms (straightness + equipotential vetoes) | High — **external machine only** (free official CC0 source `https://www.usgs.gov/3d-elevation-program`; host not in this sandbox's allowlist — not claimed viable here) |

Frozen success bar for PTGM (unchanged shared tools): `gems57-pooled-hide-v2` buffered whole-segment hide-and-recover (`n=22,893`), visible-only catalogue features, every-feature canary `AUC <= 0.90`, strictly-positive paired 95% CI vs the same-fold incumbent (bar: BPWD `0.205991`), surface+dot uniqueness under the registry definition in force, `zeros`-mode writer validation. `0` experiments were run this session; the preregistration's `frozen_before_computation = true` is literal.

---

## 8. Three-pass verification log

- **Pass 1 (implement & verify):** fresh `.venv` from pinned `requirements.txt`; `download_competition_data.sh --validation` PASS (all SHA pins); `prepare_data.py` PASS (grid `EPSG:32611 3730×3292`, affine `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`, 9 feature planes load); `generation_guard.py` / `preflight_mtas88.py --gate-generation` exit `2` as required; new late-focus auditor built + `--regenerate` (9 files fetched at pinned HEADs; 6/6 published sibling SHA-256 claims match); `audit_downloads.py --check` `50/50`, `audit_submissions_dir.py` `21/21`, `render_decision.py --check`, `check_site.py`, `audit_research_state.py`, prior focus auditor — all PASS; leaderboard re-fetched (OBSERVED-PUBLIC `0.4437`).
- **Pass 2 (adversarial review):** tamper test proves the new auditor fails closed if `ok_to_submit` is flipped; `--require-submit` exits `2`; candidate-matrix staleness, GEMSDOE36 evidence-label inflation, GEMSDOE33 collar concentration, and GEMSDOE25's nonstandard `59,472`-dot budget caught and logged (§6); full test suite **928 passed, 23 skipped** (273 s, local `.venv`); shared evaluator/writer/uniqueness code **untouched** (policy options reference existing functions only).
- **Pass 3 (requirement-by-requirement recheck):** site decision pages unchanged and still render `DO NOT SUBMIT` first (`render_decision --check` PASS — deliberately no new "current" banner per `AGENTS.md` rule 6); every number in this note labelled USER-REPORTED / SIBLING-REPORTED / REGISTRY-MEASUREMENT / HOLDOUT-DTI / OBSERVED-PUBLIC — none presented as ORGANIZER-CONFIRMED; run card is a single JSON (×3 identical copies) with `verdict: negative`; limitations below stated, not buried.

### Limitations (explicit)

1. No DrivenData authentication: organizer receipts, live quota, private leaderboard and current competition timing are **unverified** from this sandbox. Competition rasters are owner-mirrored pinned bytes, not authenticated organizer downloads; redistribution terms remain flagged in `registry/data_manifest.json`.
2. Sibling holdouts were **not re-run** (different private instruments per repo); only their saved GeoTIFF bytes, format and geometry were independently measured.
3. Equal-support/excess readings under option B were **not** recomputed fleet-wide this session (that screen only becomes meaningful after adoption + preregistered inventory); conditional rows cite each run card's own snapshot.
4. The public leaderboard snapshot is a single public-page fetch on `2026-10-26` (ranks/scores move; relative-time fields on the page are not archived as absolutes).
5. 1-m 3DEP data cannot be fetched inside the sandbox allowlist; `H88-3DEP-SCARP` needs an unrestricted workstation to produce SHA-pinned derived bands.

---

## 9. Next steps (in order)

1. **Selector signs (or rejects) the scoping packet** (`evidence/selector_scoping_packet_20261026.json`, option A/B/C + registry-inventory hash + quota receipt). Until then: `0` generation, `0` slots.
2. **If B is adopted prospectively:** execute the frozen `H88-PTGM` preregistration (max 3 experiments), then re-screen the result — and, separately, BPWD/HGVC — against the complete current fleet registry (incl. the nine late sibling files measured here) before any slot decision. Do not promote TDKL (concurrent-overlap failure) or any sibling file on a private instrument.
3. **Reconcile GEMSDOE27's badge** with the fleet rule so the public sites stop disagreeing (`IR-88-0B582CF7-01`); archive any organizer receipt that exists anywhere in the fleet to end the USER-REPORTED ambiguity (`IR-…-02`).
4. **External workstation:** build SHA-pinned 100-m summary bands from official 1-m 3DEP COGs (`1m_DEM_links.csv`) for `H88-3DEP-SCARP`; mirror as a GitHub release asset for sandbox reuse.
5. **Regenerate `candidate_matrix.json`** from all run cards (`IR-…-04`) so future selector evidence has one complete source.

*Submission guide (for the day a file is genuinely cleared): open the [executive submission guide](../executive-summary.html), upload exactly the cleared single-band `-zeros` TIFF or its one-TIFF ZIP on the DrivenData submission page, paste that run card's unique name and ≤140-char note, and archive the submission-page receipt — only then may a score be called ORGANIZER-CONFIRMED. Generative-AI use must be disclosed per the official rules (`https://docs.nlr.gov/docs/fy26osti/96647.pdf`); see `AI_USE.md` in the repo root. Official references for manual review: competition overview `https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/`, leaderboard `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`, reference solution `https://github.com/drivendataorg/gems-prize-reference-solution`, USGS GeoDAWN `https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and`, INGENIOUS/GDR `https://gdr.openei.org/submissions/1391`, EPSG:32611 `https://epsg.io/32611`.*
