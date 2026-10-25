# Session `838cc402` — Post-PR-#152 Integrity Audit, Live Source Verification, PhD `H33` & Shared-Allocator Synthesis, and Ranked Untried Hypotheses (`2026-10-25`)

**Branch:** `arena/838cc402-gemsdoe88` · **Negative Run Card:** [`registry/session_838cc402_run_card.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/registry/session_838cc402_run_card.json) ([Pages mirror](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_838cc402_run_card.json)) · **Ranked Untried Hypotheses:** [`research/session-838cc402-hypotheses.md`](session-838cc402-hypotheses.md) · **Live Leaderboard Snapshot (`50` rows):** [`evidence/leaderboard_official_snapshot_838cc402_20261025.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/evidence/leaderboard_official_snapshot_838cc402_20261025.json)

**Mandatory Evidence Labels (`AGENTS.md` Rule 8):**
- **`ORGANIZER-CONFIRMED`**: Copied verbatim from an authenticated DrivenData submission receipt. **None exists anywhere in `GEMSDOE88` (`0` confirmed scores).**
- **`HOLDOUT-DTI`**: Measured by the shared hide-and-recover evaluator (`gems57-pooled-hide-v2`, `22,893` withheld positive catalogue pixels across `8` buffered spatial folds, `alpha = 0.2`, `beta = 0.8`, `R = 300 m` / `3 px` triangular kernel, 95% block-bootstrap CI). **No new holdout experiment was run in this session (`0/3` experiments used).**
- **`OFFICIAL-PUBLIC`**: Read directly on `2026-10-25` via `fetch_page` from official public competition/agency pages (`drivendata.org`, `docs.nlr.gov`, `usgs.gov`, `gdr.openei.org`, `gbcge.org`, `epsg.io`). Public leaderboard figures reflect only the public test split, not private Round 1 or expert-expanded Round 2 labels.
- **`REGISTRY-MEASUREMENT`**: Deterministic read-only byte/raster arithmetic on SHA-pinned workspace files.
- **`USER-REPORTED`**: Unverified figures supplied in `USER_PROMPT_20261025.md` (`92` sites, `115` claims).

---

## Executive Verdict (Top-Line Machine Gate Summary)

| Gate / Question | Machine Verdict | Verified Evidence |
|---|---|---|
| **New protocol-unique `.tif` generated in session `838cc402`?** | **NO (`0` rasters generated — REQUIREMENT UNMET)** | `.venv/bin/python scripts/preflight_mtas88.py --gate-generation` and `scripts/generation_guard.py` exit `2` (`DUPLICATE_STOP`). Pinned `17GEMSDOE` (`ab0a0a62…`) is positive on all **`5,106,385 / 5,106,385` (`100.00%`)** allowed non-catalogue footprint cells, forcing literal 3-px forward overlap **`1.0000 > 0.70`** for every nonempty prediction (`AGENTS.md` Rule 2). |
| **OK TO DOWNLOAD existing archived `.tif` / `.zip` packages for research & education?** | **YES — RESEARCH / EDUCATION ONLY (`46/46` Pages + `20/20` `submissions/`)** | `audit_downloads.py --check` passes all **`46/46`** Pages packages (`45` in `docs/downloads/` + `1` in `docs/research-variants/`), and after repairing `IR-88-838C-02` in this session, all **`20/20`** repo-side `submissions/` pairs also pass dual-decoder (`rasterio` + `tifffile`) format, `[0,1]`, finite-footprint, catalogue-mask, and `-DO-NOT-SUBMIT` ZIP extraction checks (`66/66` total). |
| **OK TO SUBMIT any file in this repository to DrivenData?** | **NO — DO NOT SUBMIT (`0` protocol-eligible packages; `0` slots spent)** | `protocol_eligible_count = 0`; `ok_to_submit = false`; `verdict = "negative"`; all expected-exit-2 `--require-submit` / `--gate-generation` CLIs return exit `2`. |
| **Prepared negative run-card identifiers (`<= 140` chars, not for upload)** | Name (`29/140`): `GEMSDOE88-S838CC402-DUPLICATE` | Note (`119/140`): `DO NOT SUBMIT: session 838cc402 DUPLICATE_STOP (17GEMSDOE 1.0000>0.70); 0 new TIFs; 46/46 Pages+20/20 repo audits pass.` |

---

## 1. Post-PR-#152 Repository Review & Concrete Defects Repaired in Session `838cc402`

Working first on immediate post-merge integrity from prior sessions (`HEAD d7f7502`, merge of PR #152 `H88-MMRX`), line-by-line inspection uncovered **four concrete repository defects** plus **one live public-leaderboard shift**, all repaired and locked down with automated regression tests in [`tests/test_session_838cc402_record.py`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/tests/test_session_838cc402_record.py):

1. **`IR-88-838C-01` — `docs/SUBMIT.md` Post-PR-#152 Merge Regression (`(lane H88-SDTL)` & `45/45` Stale Count):**
   - *Found:* PR #152 branched prior to PR #151 (`IR-88-B4DFA10C-08`, which withdrew `H88-SDTL` upload clearance and finalized the `46`-package inventory). When PR #152 edited [`docs/SUBMIT.md`](https://buffedlizard55-lab.github.io/GEMSDOE88/SUBMIT.md), it reintroduced a blockquote stating that the repository's current decision was `(lane H88-SDTL)` — directly contradicting `AGENTS.md` Rule 5 (*"Do not republish or revive `H88-HGVC`, `H88-SDTL`, or legacy `MDC-88` as cleared for upload"*) — and cited `45/45` audited packages instead of `46/46`.
   - *Fixed:* Updated [`docs/SUBMIT.md`](https://buffedlizard55-lab.github.io/GEMSDOE88/SUBMIT.md) to state the truthful canonical decision (`DUPLICATE_STOP`, `ok_to_submit: false`, `verdict: "negative"`, `0` protocol-eligible packages, `H88-SDTL` withdrawn per `IR-88-B4DFA10C-08`, archived canonical research reference `H88-TDKL` `db9d1867…` marked `DO NOT SUBMIT`) and exact `46/46` Pages + `20/20` `submissions/` audit counts, without modifying any of the 13 `docs/` files SHA-pinned in `evidence/session_b4dfa10c_browser_check.json`.
2. **`IR-88-838C-02` — Unrepaired Extraction Member Inside `submissions/gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.zip`:**
   - *Found:* Running `scripts.audit_downloads.audit_one` across all `20` `.tif`/`.zip` pairs in `submissions/` revealed that `submissions/gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.zip` (`SHA-256: 8fa123568a…`) failed `research_download_ok` (`zip_one_byte_identical_tif = False`) because its internal ZIP member was still named `gems88-ibl88-basin-lattice-37654-20261024-zeros.tif` (stripping `-DO-NOT-SUBMIT` on extraction!). Session `d0c3adeb` (`evidence/archive_repairs_20261025.json`) had repaired `docs/downloads/gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.zip` (`0917eec141…`) for that exact defect, but missed the duplicate copy in `submissions/`.
   - *Fixed:* Synced the already-repaired `0917eec141a7d5813e15442c221739a2626c128b647977e40766fe94e0f1dc4e` archive into `submissions/gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.zip` (preserving the exact `3b26b61dc1…` TIFF bytes — `0` new predictions created), logged full cryptographic provenance in [`evidence/session_838cc402_archive_repair.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/evidence/session_838cc402_archive_repair.json), and added a permanent pytest audit over all `20/20` `submissions/` pairs.
3. **`IR-88-838C-03` — Stale Untried Hypothesis Ledger in `NEW_HYPOTHESES.md` After `H88-MMRX` Execution:**
   - *Found:* [`NEW_HYPOTHESES.md`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/NEW_HYPOTHESES.md) still listed *"1. Magnetic-marker restoration across candidate discontinuities"* under *"All four conditional proposals above remain untested"*, even though PR #152 (`PREREG-20261025-MMRX88`) executed `H88-MMRX` (`src/gems88/mmrx.py`) and proved it negative (`HOLDOUT-DTI = 0.188378`, `0/8` folds won, dot overlap `0.797578 > 0.70` vs `HGVC`).
   - *Fixed:* Updated [`NEW_HYPOTHESES.md`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/NEW_HYPOTHESES.md) to record `H88-MMRX` as executed/negative and promoted the five grep-verified untried post-MMRX hypotheses (`H88-SPRV`, `H88-PGTD`, `H88-CBBC`, `H88-TAWA`, `H88-MT3D-GDR`) documented in [`research/session-838cc402-hypotheses.md`](session-838cc402-hypotheses.md).
4. **`IR-88-838C-04` — Python Invalid Escape Sequence `\|` in `scripts/publish_sdtl88.py`:**
   - *Found:* Line 80 of [`scripts/publish_sdtl88.py`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/scripts/publish_sdtl88.py) contained unescaped `\|ρ\|` inside a non-raw f-string, emitting `DeprecationWarning: invalid escape sequence '\|'` under Python 3.11 (a `SyntaxError` in future Python releases).
   - *Fixed:* Escaped `\\|ρ\\|` (preserving identical rendered markdown output and preserving `enforce_generation_preflight()` as the first executable statement).
5. **`IR-88-838C-05` — Live Official Leaderboard Update & Primary-Source Verification (`2026-10-25`):**
   - *Verified live via `fetch_page`:* Retrieving all 3 chunks (`50` rows) of the [official DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) on `2026-10-25` showed participant `anna_ms` improved from `0.2900` (rank `#41`) to `0.3004` (rank `#33`, `20` submissions), shifting ranks `33–40` down by one position while keeping `#1 xiaofanhu = 0.4413`, `#9 DARD = 0.3358`, `#21 nchuzhoy = 0.3262`, and `#50 moongrega = 0.2818`. Recorded in [`evidence/leaderboard_official_snapshot_838cc402_20261025.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/evidence/leaderboard_official_snapshot_838cc402_20261025.json) without altering session `fd5f1d8b`'s earlier snapshot.

---

## 2. Why No New `.tif` Was Generated: Exact Mathematical Proof of the `17GEMSDOE` Blocker

Before importing any model or feature builder, running `.venv/bin/python scripts/preflight_mtas88.py --gate-generation` and `.venv/bin/python scripts/generation_guard.py` on restored SHA-pinned inputs returns `DUPLICATE_STOP` (exit `2`):

| Quantity | Exact Value | Evidence Class | Source |
|---|---:|---|---|
| Template footprint (`sample_submission.tif`, SHA `2176d08e…`) | `5,167,373` finite cells (`3730 × 3292`, `EPSG:32611`, `100 m`) | `REGISTRY-MEASUREMENT` | `data/bridge/sample_submission.tif` |
| Public fault catalogue inside footprint (`existing_faults.tif`, SHA `32eb0927…`) | `60,988` positive cells | `REGISTRY-MEASUREMENT` | `data/bridge/existing_faults.tif` |
| Allowed non-catalogue footprint cells (`F \ C`) | `5,106,385` cells | `REGISTRY-MEASUREMENT` | `preflight_mtas88.py` |
| Pinned registry witness `17GEMSDOE` (`dense_17gemdoe.tif`, SHA `ab0a0a62…`) | Continuous float32 in `[0.000463, 0.9841]`; **`5,106,385 / 5,106,385` (`100.00%`)** allowed cells strictly `> 0` | `REGISTRY-MEASUREMENT` | `data/registry/dense_17gemdoe.tif` |
| Uncovered allowed cells (`distance > 3 px` from `17GEMSDOE > 0`) | **`0` cells** | `REGISTRY-MEASUREMENT` | `saturation_certificate` |
| Forward 3-px overlap of **any** nonempty candidate `P ⊂ (F \ C)` vs `17GEMSDOE` | **`1.0000 > 0.70`** (`DUPLICATE_STOP`) | `REGISTRY-MEASUREMENT` | Mathematical identity |

Notice why the literal support definition (`p(x) > 0`) is non-trivial rather than an arbitrary bug: on the official [DrivenData Problem Description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) (verified live via `fetch_page`), the distance-weighted false-positive penalty explicitly sums over the support `{x : p(x) > 0}`:
$$\text{FP}_w = \sum_{x:\,p(x)>0} p(x)\,\Bigl[1 - \max_{g \in G} k\bigl(d(x, g)\bigr)\Bigr].$$
Because `17GEMSDOE` emitted `p(x) > 0` across 100% of the footprint, applying the Parallel-Run Protocol's literal rule (*"more than [70%] of your dots fall within 3 px of one registry raster's dots"*) treats every pixel of `17GEMSDOE` as occupied support and blocks **every** nonempty sparse or dense candidate (`overlap = 1.0000`). Per `AGENTS.md` Rules 2–6, an agent session cannot unilaterally exempt `17GEMSDOE`, reinterpret `dots` as equal-support top-$N$ (`v4`/`v5` were explicitly revoked as unauthorized promotions in `IR-88-D0C3ADEB-08` and `IR-88-B4DFA10C-08`), or rename an archived raster as new. Resolving this requires **Owner Decision `D1`** (§6 below).

---

## 3. PhD-Level Analysis: Why `GEMSDOE32` (`H33`, `0.2778` Claim) Topped the Supplied List, Reconciliation with `0.3195` & `0.4413`, and How `0.2778` Can Be Beaten

### 3.1 Reconciliation of the Three Headline Numbers (`0.2778`, `0.3195`, `0.4413`)

Live retrieval of primary sources on `2026-10-25` resolves every contradiction in `USER_PROMPT_20261025.md`:

| Number in Prompt | Prompt Attribution | Live Primary-Source Fact (`2026-10-25`) | Evidence Label |
|---:|---|---|---|
| **`0.4413`** | *"Current competition leaderboard GEMSDOE high score: 0.4413"* | Rank `#1` public-split DW-Tversky score of external competitor **`xiaofanhu`** (`30` submissions) on [DrivenData Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). Zero `GEMSDOE` or `buffedlizard55` handles appear in top-50 rows (`0.4413` down to `#50 moongrega = 0.2818`). | `OFFICIAL-PUBLIC` (misattributed to GEMSDOE in prompt) |
| **`0.3195`** | *"The highest score right now on the competition leaderboard is: 0.3195"* | Stale `2026-10-04` snapshot of competitor **`DARD`** (then rank `#3` on `GEMSDOE32/docs/leaderboard.html`). On `2026-10-25`, **`DARD` is rank `#9` at `0.3358`** (`26` submissions). | Stale `OFFICIAL-PUBLIC` (`2026-10-04`) |
| **`0.2778`** | `GEMSDOE32` `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | Highest `USER-REPORTED` figure among the `92` GEMSDOE sites (`115` claims). Sits below rank `#50` (`0.2818`), has **no organizer submission receipt** in any repo, and [`GEMSDOE32/docs/index.html`](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) states verbatim: *"NO ORGANISER SCORE EXISTS for this or any artifact in this repository."* | `USER-REPORTED` (unverified claim) |

### 3.2 Exact Algebraic & Geometric Mechanism Behind `H33`'s Advantage Over Upstream GEMSDOE Files

Byte-level audit of the four SHA-pinned rasters in `evidence/h33_forensics_20261024.json` and `evidence/h33_lineage_recheck.json` establishes an **exact nested subset chain** with **zero added pixels** at any stage:

$$\underbrace{\text{H33-2-B2 (`37,654` px, `0.2778` claim)}}_{\min d_{\text{cat}} = \sqrt{5}\,\approx\,2.2361\text{ px},\ \min d_{\text{nn}} = 2\sqrt{2}\,\approx\,2.8284\text{ px}} \;\subset\; \underbrace{\text{SOLO-D2.8 (`40,199` px, `0.2708` claim)}}_{\min d_{\text{cat}} = \sqrt{2}\,\approx\,1.4142\text{ px}} \;\subset\; \underbrace{\text{D2.8 (`44,090` px, `0.2600` claim)}}_{\min d_{\text{cat}} = 1.0\text{ px}} \;\subset\; \underbrace{\text{H19-5 (`121,131` px, `0.1922` claim)}}_{\text{thick ridge band, } \min d_{\text{nn}} = 1.0\text{ px}}.$$

From the live-verified official metric on [`drivendata.org/.../page/967/`](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ($\alpha = 0.2$, $\beta = 0.8$, $k(d) = \max(1 - d/300\text{ m}, 0)$):
- Let $P \subset \Omega$ be a binary dot set ($p(x) \in \{0, 1\}$, $|P| = n$), $G$ be the hidden expert-labeled **new** fault set ($|G|$ pixels), $T(P) = \sum_{g \in G} \max_{x \in P} k(d(x, g))$ be covered truth credit, and $M(P) = \sum_{x \in P} \max_{g \in G} k(d(x, g))$ be total dot self-credit.
- Since $\text{FN}_w = |G| - T(P)$ and $\text{FP}_w = n - M(P)$, the denominator simplifies identically to:
  $$T(P) + 0.2\,\text{FP}_w + 0.8\,\text{FN}_w = T(P) + 0.2\bigl(n - M(P)\bigr) + 0.8\bigl(|G| - T(P)\bigr) = 0.8|G| + 0.2\,T(P) + 0.2\bigl(n - M(P)\bigr),$$
  yielding the exact binary DTI identity:
  $$\text{DTI}(P) = \frac{T(P)}{0.8|G| + 0.2\,T(P) + 0.2\bigl(n - M(P)\bigr)}.$$

Taking the finite difference $\Delta \text{DTI}$ upon adding or retaining a single dot $x$ with marginal new truth coverage $\Delta T(x) = T(P \cup \{x\}) - T(P) \ge 0$ and self-credit $m(x) = \max_{g \in G} k(d(x, g)) \in [0, 1]$ shows that dot $x$ improves $\text{DTI}$ **if and only if**:
$$\frac{\Delta T(x)}{1 - m(x) + \Delta T(x)} > 0.2\,\text{DTI}(P) \quad \Longleftrightarrow \quad \Delta T(x) > \frac{0.2\,\text{DTI}(P)}{1 - 0.2\,\text{DTI}(P)}\,\bigl(1 - m(x)\bigr) \approx 0.0588\,\bigl(1 - m(x)\bigr) \quad (\text{at }\text{DTI} \approx 0.278).$$

This single inequality explains **all three stages** of the `H19-5 → D2.8 → SOLO-D2.8 → H33` climb (conditional on the `USER-REPORTED` progression):

1. **Kernel-packing de-duplication (`H19-5` `121,131` px → `D2.8` `44,090` px):** Because $\text{TP}_w$ takes a **pointwise $\max_{x \in P}$}** rather than a sum over nearby predictions while $\text{FP}_w$ **sums** $1 - m(x)$ over every emitted pixel $p(x) > 0$, emitting adjacent $100\text{ m}$ pixels along a ridge yields $\Delta T(x) \approx 0$ (the truth pixel is already covered by a neighbor within $283\text{ m}$) while still paying full false-positive denominator tax whenever the ridge misses truth ($m(x) = 0 \implies +0.20$ denominator cost per redundant pixel). Thinning to inter-dot spacing $d_{\text{nn}} \ge 2\sqrt{2} \approx 2.828\text{ px}$ (`282.8 m`, just inside $R = 300\text{ m}$) eliminates `77,041` redundant neighbor pixels while preserving nearly full $300\text{ m}$ triangular-tent coverage along the skeleton.
2. **Catalogue-halo pruning (`D2.8` `44,090` px → `H33` `37,654` px, `-6,436` dots all at $d_{\text{cat}} \le 2.0\text{ px}$):** As verified live on [`drivendata.org/.../page/967/`](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), the test set consists exclusively of **newly identified faults not in the existing USGS/INGENIOUS database**. Dots at $d_{\text{cat}} \le 200\text{ m}$ sit inside the digitization/scarp halo of *already-mapped* faults, where hidden new-fault density is suppressed except at rare branch junctions ($\mathbb{E}[\Delta T(x)] \approx 0$, $\mathbb{E}[m(x)] \approx 0$). Deleting those `6,436` dots removes $\approx 0.2 \times 6{,}436 \approx 1{,}287$ units of pure denominator penalty at negligible numerator loss, leaving `0` pixels within `2.0 px` of the catalogue (`min_d_cat = √5 ≈ 2.2361 px`, `median_d_cat = 19.65 px`, `35.82%` at `d_cat > 30 px`).
3. **Why continuous probability sheets underperform sparse kernel-packed skeletons (`17GEMSDOE` `0.1072` claim vs `H33` `0.2778` claim):** Under $\text{FP}_w = \sum_{x:p>0} p(x)[1 - \max_g k]$, emitting background probabilities $\bar{p} \approx 0.22$ across `5.11M` non-truth cells injects $\approx 0.2 \times 1.1\times 10^6 \approx 2.2\times 10^5$ denominator penalty — overwhelming $\text{TP}_w$ by an order of magnitude unless calibrated probabilities are thresholded and spatially packed.

### 3.3 Can We Beat `0.2778` — and What Did `H88-BPWD` (`0.205991`) vs `H88-MMRX` (`0.188378`) Prove?

**Rigorous scientific answer:**
1. **Not yet demonstrated on organizer truth (`ORGANIZER-CONFIRMED = null`), and currently blocked before generation by `D1` (`17GEMSDOE` literal overlap `1.0000 > 0.70`).** Moreover, local `HOLDOUT-DTI` (`H88-BPWD = 0.205991 [0.188105, 0.223344]`) cannot be compared numerically to `0.2778` or `0.4413` because `gems57-pooled-hide-v2` withholds segments from the **mapped** USGS/INGENIOUS catalogue (`IR-32-PROXY-01`): mapped faults are Selected-At-Random (`SAR`) biased toward exposed range fronts (`86.38%` of withheld catalogue positives lie at `d_cat <= 25 px`, whereas `47.17%` of the GeoDAWN footprint lies at `d_cat > 25 px`). Indeed, `H33` itself scores near zero on on-catalogue holdouts when its `<= 2 px` collar is evaluated against unbuffered neighbors, proving that holdout DTI measures *within-family ranking skill*, not public-split DTI level.
2. **Thinning/re-snapping `H19-5` / `H33` has hit an empirical ceiling:** Every pure post-processing perturbation in `releases/` (`PRUNE`, `MASS`, `SNAP`, `SPACING`, `RELIEF`, `CONCENTRATION`) either remains a near-duplicate of `H33` (`> 0.70` overlap) or moves proxy credit by `< 0.01`.
3. **Why external top-1 (`xiaofanhu = 0.4413` `OFFICIAL-PUBLIC`) sits `+0.1635` above `0.2778`:** At matched sparse dot mass (`~30k–45k` packed dots), raising DTI from `~0.28` to `~0.44` requires increasing covered hidden-truth fraction $T/|G|$ by roughly **1.8×–2.1×** — which is mathematically impossible by rearranging dots on `H19-5`'s existing ridges and can only come from **recovering whole unmapped intrabasinal, piedmont-mantled, and relay fault strands** where `H19-5` had low rank.
4. **The critical post-PR-#152 discovery (`IR-88-127` & `IR-88-249E-02` Shared-Allocator Bottleneck):**
   - In `GEMSDOE88`, physics-informed multi-specialist log-odds Product-of-Experts (`PoE`) models have steadily raised `HOLDOUT-DTI`: `H88-ADHR` (`0.194876`) → `H88-TDKL` (`0.196237`) → `H88-VHGD` (`0.198664`, Blind `>25 px` record **`0.092061`**) → `H88-VCAZ` (`0.200625`, emitted 3-regime record **`0.152829`**) → `H88-HGVC` (`0.202947`) → **`H88-BPWD` (`0.205991 [0.188105, 0.223344]`, Far `>10 px` record `0.136782`)**.
   - However, PR #152 (`H88-MMRX`) proved two vital failure modes that govern all future work once `D1` is resolved:
     - **Single-tree feature dilution:** Concatenating 16 noisy shift-correlation channels onto a 103-channel `HGB` diluted splits (`Exp03 = 0.188378`, `0/8` folds won vs `BPWD`). New physical operators must be trained as **domain-isolated specialists** fused in calibrated log-odds space (as `BPWD`, `HGVC`, `VCAZ`, and `VHGD` succeeded in doing), with `hgvc.REGIONAL_DC_EXCLUSIONS` enforced so zero-catalogue trees cannot memorize quadrant coordinates (`IR-88-129`).
     - **Allocator crest re-selection (`0.7976 > 0.70` overlap):** Even with surface `|Spearman ρ| = 0.218`, feeding `PHYS-44 + HGVC-20 + VIS-23 + X_new` into the identical two-stratum greedy crest allocator (`21,200 near + 16,454 far`) re-selects `79.76%` of `HGVC`'s dots (`PSGV` likewise hit `78.99%`). To achieve genuine fleet-wide structural novelty (`<= 0.70` dot overlap across all `370+` rasters) *and* discover faults missed by `HGVC`/`BPWD`, the next lane must emit its piedmont/blind budget along **operator-native structural loci** (restored scarp inflections in `H88-SPRV`, 3D Marussi $I<0.2$ zero-crossing sheets in `H88-PGTD`, or Morse–Smale horst-breach saddles in `H88-CBBC`).

---

## 4. Portal Format Error `"Predicted values must be in range [0, 1]"` & Zero-Human-Intervention Validation

As verified live on [`drivendata.org/.../page/967/#submission-format`](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format) and [`GEMSDOE32/docs/index.html`](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), two distinct mechanisms trigger the DrivenData portal error `"Predicted values must be in range [0, 1]"`:

1. **Float32 nodata sentinel bleed (`-3.4028234663852886e+38`):** `data/training_features.tif` uses `-3.4028235e+38` on `7,113,308` pixels, including **`3,061` pixels inside the valid `sample_submission.tif` footprint**. Propagating unmasked feature arrays or setting `nodata = -3.4028235e+38` causes a range-check parser that reads raw band values without honoring GDAL nodata tags to see `-3.4e38 ∉ [0, 1]`.
2. **NaN outside-footprint / tag mismatch:** While the problem text permits `null or nan` outside the footprint, strict numerical validators (`np.all((arr >= 0) & (arr <= 1))`) evaluate `NaN >= 0` as `False` unless `NaN` is explicitly masked. Writing **all-finite `float32`** rasters (`0.0` outside footprint, finite `[0.0, 1.0]` inside footprint, `0` `NaN`/`Inf` across all `12,279,160` cells, `nodata = None`, single band, `EPSG:32611`, `3730 × 3292`, `100 m` affine `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`) satisfies **both** `NaN`-aware and strict all-finite validators simultaneously.

**Automated local verification (`0` human intervention):**
- `scripts/audit_downloads.py --check` (`v2`) reopens every published `.tif` and `.zip` with **two independent decoders (`rasterio`/GDAL and `tifffile`)**, rejects hidden second subdatasets/bands, rejects external `.aux.xml`/sidecar georeferencing dependencies, verifies `0` `NaN`/`Inf`, `[0, 1]` bounds, exact CRS/shape/transform parity with `sample_submission.tif`, `0` positive pixels outside footprint or on `existing_faults.tif`, and exact single-member `.tif` byte parity inside every `.zip` (`46/46` Pages packages + `20/20` `submissions/` packages pass; `0` protocol-eligible).
- *Scope honesty:* Local format validation guarantees compliance with the documented GeoTIFF specification, **not** authenticated DrivenData portal acceptance or prize eligibility.

---

## 5. Official & Trusted Sources Verified Live in Session `838cc402` (`2026-10-25`)

Every URL below was retrieved and cross-checked directly via `fetch_page` or local `gh`/SHA-256 audit in this session:

| Source | URL | Live Verification Summary (`2026-10-25`) |
|---|---|---|
| DrivenData GEMS Problem Description & Metric | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> | Verified 2-round structure (`$50k` Initial top-5 private split; `$250k` Final `$100k/$70k/$40k/$25k/$15k` expert-expanded labels), exact `DTI(α=0.2, β=0.8, R=300 m)` equations, worked example (`0.60`), and `EPSG:32611` `100 m` `float32` `[0,1]` submission contract. |
| DrivenData GEMS Public Leaderboard | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> | Verified all `50` visible public rows (`#1 xiaofanhu = 0.4413`, `#9 DARD = 0.3358`, `#21 nchuzhoy = 0.3262`, `#33 anna_ms = 0.3004`, `#50 moongrega = 0.2818`); saved in `evidence/leaderboard_official_snapshot_838cc402_20261025.json`. |
| DrivenData GEMS About Page | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/> | Verified DOE Office of Geothermal sponsorship, EarthMRI/GeoDAWN + 3DEP LiDAR context, and literature references (Mattéo et al. 2021; Hermant et al. 2025). |
| DOE / NLR Official GEMS Prize Rules (Sept 2026 PDF) | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> | Verified `15 U.S.C. § 3719` governance, U.S. eligibility (§1.3), `3` submissions/week feedback cap (§3.2, §3.4), single final selected submission across both phases (§3.5, §3.6.2), and mandatory generative-AI disclosure in narrative (§3.2). |
| USGS GeoDAWN Airborne Survey Release (`CC0 1.0`) | <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> | Verified Glen & Earney (2024), `doi:10.5066/P93LGLVQ`, `149,030` line-km over `51,857 km²`, Area 1 (`200 m` E–W lines, `100–150 m` clearance) & Area 2 (`400 m` E–W lines, `150–200 m` clearance, `22°` max climb/descent drape), CC0 public domain. |
| DOE GDR `#1391` INGENIOUS Regional Compilation (`CC-BY-4.0`) | <https://gdr.openei.org/submissions/1391> | Verified `doi:10.15121/1881483` (Ayling et al. 2022), CC-BY-4.0 license, 9 downloadable archives + linked USGS 3D-MT conductance (`doi:10.5066/P9TWT2LU`) and heat-flow (`doi:10.5066/P9BZPVUC`) releases. |
| GBCGE INGENIOUS Project Page | <https://gbcge.org/current-projects/ingenious/> | Verified DOE award `DE-EE0009254` (`$10M`) and peer-reviewed Great Basin play-fairway / geophysical publications (Glen et al. 2022; Kreemer & Young 2022; Peacock & Bedrosian 2022; Siler 2022). |
| Official DrivenData Reference Solution | <https://github.com/drivendataorg/gems-prize-reference-solution> | Verified official baseline architecture & CPU/GPU support (`cuda`/`mps`/`cpu`). |
| `EPSG:32611` Coordinate Reference System | <https://epsg.io/32611> | Verified `WGS 84 / UTM zone 11N` (`central_meridian = -117°`, `scale_factor = 0.9996`, `false_easting = 500000 m`, `metre` units). |
| Tversky Index Mathematical Reference | <https://en.wikipedia.org/wiki/Tversky_index> | Verified Tversky (1977) asymmetric prototype-variant similarity definition (`α + β = 1`). |
| `GEMSDOE32` Primary `H33` Source Page | <https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html> | Verified `H33-2-B2` (`c55bafc4…`, `37,654` dots, `0` within `200 m` of catalogue) and explicit statement that **no organizer score exists** on that site. |

---

## 6. Three-Pass Verification Log & Line-by-Line Prompt Requirement Matrix

### 6.1 Explicit Three-Pass Review Log
- **Pass 1 — Implement & Verify:**
  - Restored full SHA-pinned core, external (`18` datasets), registry, and sibling inputs (`bash scripts/download_competition_data.sh --registry` → exit `0`, `data/prepared_data_manifest.json` verified).
  - Re-verified `preflight_mtas88.py --gate-generation`, `generation_guard.py`, and all `--require-submit` / candidate runner CLIs → all exited `2` (`DUPLICATE_STOP`) with clean `git diff --exit-code` and `0` new rasters generated.
  - Fetched all official external URLs live via `fetch_page` and audited PR #152 (`H88-MMRX`) + repo-wide `.tif`/`.zip` directories (`docs/downloads/`, `docs/research-variants/`, `submissions/`, `releases/`).
  - Repaired `docs/SUBMIT.md` (`IR-88-838C-01`), `submissions/gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.zip` (`IR-88-838C-02`), `NEW_HYPOTHESES.md` (`IR-88-838C-03`), and `scripts/publish_sdtl88.py` (`IR-88-838C-04`), and authored the 5 untried post-MMRX hypotheses, PhD review, live leaderboard snapshot (`IR-88-838C-05`), negative Run Card, and `tests/test_session_838cc402_record.py`.
- **Pass 2 — Audit for Bugs, Hidden Assumptions, & Edge Cases:**
  - *Caught & prevented `releases/` regression:* Verified `tests/test_concentration_variants.py` explicitly tests committed `releases/h33-h33-2-b2-MASSm*` files, so `releases/` was left untouched while `submissions/` was brought to `20/20` `audit_one` compliance.
  - *Caught subpixel H33 geometry conflation:* Distinguished `H33`'s minimum distance to catalogue (`min_d_cat = √5 ≈ 2.2361 px`, from `d_cat > 2.0 px` integer lattice) from its minimum inter-dot spacing (`min_nn = 2√2 ≈ 2.8284 px`), correcting imprecise prose seen in earlier notes.
  - *Caught browser-receipt SHA pin constraint:* Verified `tests/test_publication_guards.py` and `tests/test_session_d0c3adeb_record.py` assert exact SHA-256 equality on 13 `docs/` files in `evidence/session_b4dfa10c_browser_check.json`. Confirmed all 13 files remain byte-identical (`0` hash drift) rather than invalidating the real Chromium receipt in a sandbox without a Chromium binary.
  - *Caught README marker/count invariants:* Verified `tests/test_request_evidence.py`, `tests/test_arena_review_f8d5d693.py`, `tests/test_session_b4dfa10c_record.py`, and `tests/test_session_26588c79_record.py` all pass after updating `README.md`.
- **Pass 3 — Full Re-Check Against User Prompt, Contract, & CI Gates:**
  - Executed the complete `.github/workflows/checks.yml` & `.github/workflows/ci.yml` command matrix (`audit_downloads.py --check`, `render_decision.py --check`, `check_site.py`, `python -O scripts/check_site.py`, all expected-exit-2 guards, `pytest -q`, and `git status` cleanliness) prior to opening and merging the PR onto `main`.

### 6.2 Requirement-by-Requirement Status Matrix

| Prompt Requirement | Status | Honest Evidence & Notes |
|---|---|---|
| Work on previous sessions' next steps first | **MET** | Audited post-PR-#152 state, repaired 4 concrete regressions/defects (`IR-88-838C-01..04`), and advanced the post-`H88-MMRX` hypothesis queue. |
| Store full prompt in `README.md` as starting point | **MET** | Embedded verbatim between `<!-- USER-REQUEST:START -->` and `<!-- USER-REQUEST:END -->` (`tests/test_request_evidence.py` verified byte-equal to `USER_PROMPT_20261025.md`). |
| Generate a **unique** `.tif` submission | **NOT MET (BLOCKED BY `DUPLICATE_STOP`)** | `17GEMSDOE` covers `100%` of `5,106,385` allowed pixels (`overlap = 1.0000 > 0.70`, exit `2`). Per `AGENTS.md` Rules 2–6, no old file is copied/relabeled and no guard is bypassed. |
| Unmistakable OK-to-download vs OK-to-submit indicators, validated without human intervention | **MET** | Top-of-page & top-of-README banners + `audit_downloads.py --check` (`46/46` Pages + `20/20` `submissions/` = `66/66` research-valid, `0` submit-eligible). |
| Prevent `"Predicted values must be in range [0, 1]"` | **MET (local artifacts)** | Dual-decoder check confirms single-band `float32`, `EPSG:32611`, `3730×3292`, `0` `NaN`/`Inf`, all values in `[0, 1]`, `nodata = None`. |
| Unique submission name & note `<= 140` chars | **PREPARED (FAIL-CLOSED)** | Negative Run Card carries `29`-char name & `119`-char `DO NOT SUBMIT` note; no candidate promoted. |
| Executive summary subpage explaining how to submit | **MET** | [`docs/executive-summary.html`](https://buffedlizard55-lab.github.io/GEMSDOE88/executive-summary.html) + repaired [`docs/SUBMIT.md`](https://buffedlizard55-lab.github.io/GEMSDOE88/SUBMIT.md). |
| PhD answer: why `H33` (`0.2778`) scored highest & whether/how to beat it | **MET (with honest receipt limits)** | Exact binary DTI marginal-credit proof + nested `H19-5 → H33` geometry + post-`MMRX` shared-allocator theorem (§3); `0.2778` remains `USER-REPORTED` without receipt. |
| 3–5 untried, ranked geological hypotheses with layers, physics, mimics, code diff, & official sources | **MET (`5` ranked, `grep`-verified)** | `H88-SPRV`, `H88-PGTD`, `H88-CBBC`, `H88-TAWA`, `H88-MT3D-GDR` in [`research/session-838cc402-hypotheses.md`](session-838cc402-hypotheses.md). |
| JSON Run Card + 3 passes + PR + merge onto `main` | **MET** | Mirrored in `registry/`, `docs/data/`, and `evidence/`; 3 passes completed; PR opened and merged onto `main`. |

---

## 7. Remaining Limitations & Owner Decisions Required for Next Session (`D1–D4`)

1. **`D1` (Rule-Owner Uniqueness Clarification — Primary Blocker):** Under the literal support rule (`p(x) > 0`), `17GEMSDOE` (`dense_17gemdoe.tif`) blocks every nonempty candidate (`1.0000 > 0.70`). To authorize generating and testing `H88-SPRV` (`Rank #1`), the user/rule owner must explicitly state whether continuous probability rasters in the registry should be evaluated by **(a)** Spearman rank correlation `|ρ| <= 0.90` + equal-support top-$N$ dot overlap `<= 0.70` (while keeping literal 3-px dot overlap `<= 0.70` across all sparse/binary dot rasters), or **(b)** exclusion of non-submitted dense diagnostics from the dot-overlap set.
2. **`D2` (Allocator Orthogonality Requirement Once `D1` Clears):** Any newly authorized experiment **must not** reuse the `HGVC`/`BPWD` `VIS-23` greedy crest allocator unchanged (`PSGV` `0.7899` and `MMRX` `0.7976` both failed `<= 0.70` against `HGVC`). Execute `H88-SPRV` with domain-isolated specialist calibration and restored inflection-locus placement.
3. **`D3` (Authenticated Portal Provenance & `sample_submission.tif` Verification):** DrivenData's data-download and submission-history pages require login (never requested here). Notably, owner-mirror `data/bridge/sample_submission.tif` (`2176d08e…`) has `60,988` ones on catalogue pixels rather than all zeros as described on `page/967/` (*"predicts total fault absence"*), and no `ORGANIZER-CONFIRMED` submission receipt is stored in the repo.
4. **`D4` (External Official 3D-MT Mirroring for `H88-MT3D-GDR`):** Because sandbox `bash` only reaches `github.com`/`pypi.org`/`npmjs.org`, executing Rank #5 (`H88-MT3D-GDR`) requires mirroring USGS `doi:10.5066/P9TWT2LU` (Peacock & Bedrosian 2022) and `doi:10.5066/P9BZPVUC` (DeAngelo et al. 2022) into the owner's SHA-pinned GitHub release assets.
