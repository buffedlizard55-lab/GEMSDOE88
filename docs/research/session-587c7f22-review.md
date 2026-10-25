# End-to-End Three-Pass Repository Review, CON88 Clearance Withdrawal & PhD H33 Forensics — Session `587c7f22` (`2026-10-25`)

## 0. Immediate Top-of-Session Decision

- **NEW COMPETITION GeoTIFF GENERATED THIS SESSION:** **NO (`0` files generated)** — blocked before feature construction by the binding literal Parallel-Run Protocol (`python scripts/preflight_mtas88.py --gate-generation` and `python scripts/generation_guard.py` both exit `2`: `DUPLICATE_STOP`).
- **OK TO DOWNLOAD ARCHIVED RESEARCH ARTIFACTS (EDUCATION / AUDIT ONLY)?** **YES** — canonical archived research GeoTIFF [`gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif`](https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`) and [one-TIFF `.zip`](https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip) (`SHA-256: af9945ee27532576c150760f0b30830934c30f67071d0d10f3d1eb9feb51c4a5`), along with all **48/48** published Pages packages (`47` in `docs/downloads/` + `1` in `docs/research-variants/`) and **20/20** repo-side `submissions/` packages, pass automated dual-decoder (`rasterio` + `tifffile`) validation with zero human intervention.
- **OK TO SUBMIT ANY FILE IN THIS REPOSITORY TO DRIVENDATA `#306` TODAY?** **NO — DO NOT SUBMIT (`ok_to_submit: false`, `protocol_eligible_count: 0`, `0` weekly slots spent).**
- **Machine-readable deliverables for this session:**
  - Negative JSON run card: [`docs/data/session_587c7f22_run_card.json`](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_587c7f22_run_card.json) (mirrored identically in `registry/` and `evidence/`)
  - Five ranked untried geological hypotheses: [`session-587c7f22-hypotheses.md`](session-587c7f22-hypotheses.md) + canonical [source-bound JSON queue](https://buffedlizard55-lab.github.io/GEMSDOE88/data/hypothesis_queue.json)
  - `H88-CON88` historical clearance withdrawal certificate: [`docs/data/con88_clearance_withdrawal_20261025.json`](https://buffedlizard55-lab.github.io/GEMSDOE88/data/con88_clearance_withdrawal_20261025.json)
  - Real-Chromium Playwright receipt: [`docs/data/session_587c7f22_browser_check.json`](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_587c7f22_browser_check.json)
  - Automated gate-matrix receipt: [`docs/data/session_587c7f22_gate_check.json`](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_587c7f22_gate_check.json)

---

## 1. Execution of Previous Session Next Steps & Data Placement

1. **Autonomous Competition + Sibling Registry Data Placement:**
   - Ran `bash scripts/download_competition_data.sh` and `python scripts/restore_siblings.py` on CPU inside `.venv` (`Python 3.11.2`, `numpy==2.3.4`, `rasterio==1.4.4`, `GDAL 3.10.3`, `pip check` clean).
   - Verified exact SHA-256 digests of core competition grids (`EPSG:32611`, `3292 × 3730`, 100 m pixel size, affine `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`):
     - `sample_submission.tif`: `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` (`5,167,373` in-footprint cells; `5,106,385` off-catalogue allowed cells)
     - `existing_faults.tif`: `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` (`60,988` in-footprint catalogue fault pixels)
     - `training_features.tif`: `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5` (`19` float32 bands)
   - Verified `prepare_data.py` loads all `9` shared `gems57.geo` planes cleanly on CPU (`data/prepared_data_manifest.json`) and restored `161` sibling `GEMSDOE86..92` GeoTIFFs + `26` fleet GeoTIFFs into gitignored `data/siblings/` and `data/fleet/`.
2. **Pre-Placement Duplicate-Stop Verification:**
   - [Pinned `17GEMSDOE` witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) (`data/registry/dense_17gemdoe.tif`, `SHA-256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) has finite positive predictions (`> 0`) on all `5,167,373` footprint cells (`5,106,385 / 5,106,385` allowed cells).
   - Under the literal Parallel-Run Protocol (`> 70%` of candidate dots within `3 px` of *any* registry raster's dots $\Rightarrow$ log duplicate and stop), **every nonempty allowed candidate has literal 3-px forward overlap `1.0000 > 0.70`**. In addition, sibling `GEMSDOE87` (`gems87-bmtd-20261022-50041440adba-RESEARCH-DO-NOT-SUBMIT.tif`, `4,532,408` positive cells) independently produces literal overlap `0.891220 > 0.70` on `H88-CON88`.
   - Per `AGENTS.md` Rules 2–6, this session stopped before feature construction, did not copy/rename an old TIFF as a new submission, and spent `0` weekly slots.

---

## 2. Critical Irregularities Found & Fixed on `main` (`IR-88-587C7F22-01` .. `IR-88-587C7F22-05`)

When branching from `main`, GitHub Actions (`ci.yml`, `pages.yml`, `checks.yml`) were **FAILING** (`3 failed` in `pytest`) due to incomplete/contradictory merges from PR `#158` (`H88-CON88`), PR `#172`, and PR `#175`:

1. **`IR-88-587C7F22-01` — Unauthorized `H88-CON88` Promotion & Guard Bypass Withdrawn:**
   - PR `#158` introduced `scripts/con88_preflight.py` (`generation_allowed: true`) to bypass `scripts/generation_guard.py`, resurrected equal-support promotion (explicitly forbidden in `AGENTS.md` / `IR-88-B4DFA10C-08`), checked only `77` local rasters while omitting `161` sibling `GEMSDOE86..92` rasters, published unmarked `gems88-con88-*-zeros.{tif,zip,json}` without `-DO-NOT-SUBMIT` (`AGENTS.md` Rule 6 violation), and set `ok_to_submit: true` / `verdict: "promote"` in `run_card_con88.json` and `registry/con88_gates.json` despite `HOLDOUT-DTI = 0.001714 [0.001325, 0.002143]` (`n = 60,988`) failing the repository holdout record (`H88-BPWD` `0.205991 [0.188105, 0.223344]`, `n = 22,893`) by `>120×` and scoring `0.0000` vs `H33` `0.006697` on identical quadrant folds.
   - **Fix:** Renamed/repacked `H88-CON88` to `-DO-NOT-SUBMIT.{tif,zip,json}` with **zero change to GeoTIFF bytes** (`SHA-256: e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`), withdrew `ok_to_submit` to `false` and `verdict` to `"negative"`, published [`con88_clearance_withdrawal_20261025.json`](https://buffedlizard55-lab.github.io/GEMSDOE88/data/con88_clearance_withdrawal_20261025.json), restored mandatory `enforce_generation_preflight()` across all `97` candidate entrypoints (including `run_con88_experiment.py`, `run_con88_exp3_margin.py`, and `con88_collar_holdout.py`), and rewrote `scripts/validate_con88.py` into a read-only `-O`-safe validator (`--require-submit` exits `2`) that no longer crashes when gitignored `.cache/con88_*.npy` is absent.
2. **`IR-88-587C7F22-02` — Removed `ok_to_submit` & Filename Carve-Outs Across Guards and Tests:**
   - PR `#158` added `cleared_by_con88_gates` holes into `scripts/audit_downloads.py`, `scripts/check_site.py`, `tests/test_candidate_gates_20261024.py`, `tests/test_download_inventory.py`, `tests/test_generation_entrypoints.py`, and `tests/test_site_links.py`. All six carve-outs have been removed; `protocol_eligible_count` is `0` and zero JSON records in `root`, `registry/`, `docs/`, or `evidence/` claim `ok_to_submit: true`.
3. **`IR-88-587C7F22-03` — Repaired Broken `pytest` Suite on `main` (`3 failed` $\to$ `0 failed`):**
   - Removed PR `#158`'s ad-hoc `source_sha256` file-skip exemptions in `tests/test_publication_guards.py` and `tests/test_session_d0c3adeb_record.py`, bound a fresh real-Chromium Playwright receipt (`session_587c7f22_browser_check.json`) across all `14` `docs/` targets, and made the `docs/SUBMIT.md` package-count mutation probe in `tests/test_session_78cfb743_fixes.py` read `total_published_tiff_count` dynamically (`48/48`).
4. **`IR-88-587C7F22-04` — Repaired Contradictory Banners & Escaping Links (`index.html`, `docs/con88.html`, `docs/SUBMIT.md`, `PROMPT.md`):**
   - Root `index.html` and `PROMPT.md` still proclaimed `✓ OK TO DOWNLOAD AND SUBMIT` for `H88-CON88`; `docs/SUBMIT.md` line 12 claimed `exactly 1 eligible — H88-CON88` directly beneath a line-3 withdrawal notice; `docs/con88.html` linked to `../registry/con88_gates.json` (escaping the Pages `docs/` root), omitted `executive-summary.html`, and cited third-party `epsg.io`. All four files now present one consistent fail-closed `DO NOT SUBMIT` decision with valid in-`docs/` links.
5. **`IR-88-587C7F22-05` — Retired `H88-CON88` in the Source-Bound Hypothesis Queue:**
   - Added `H88-CON88` (`registry/con88_run_card.json`) to `already_evaluated` in `registry/hypothesis_queue.json` and `docs/data/hypothesis_queue.json` alongside `H88-MMRX`, `H88-MTAS`, `H88-MFS`, and `H88-PGTD`, updating `source_snapshot` to `062d23ee578ea5488049870d51be30cd75802f8e4f762ed42e9c792a47b42042`.

---

## 3. PhD-Level Forensic Analysis of `H33` (`GEMSDOE32`, `USER-REPORTED 0.2778`) & Whether `0.2778` Can Be Beaten

### 3.1 Provenance & Evidence Classification (Zero Hallucinations)
- **Artifact identity (verified on disk & from freshly fetched [`GEMSDOE32/registry/submission_build.json`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) at commit `012e17b2`):**
  - File: `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`
  - SHA-256: `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` (`219,065` bytes, `37,654` binary `{0.0, 1.0}` dots, `0` NaN, `0` outside footprint, `0` on mapped catalogue).
  - Score label: **`0.2778` is `USER-REPORTED`**, NOT `ORGANIZER-CONFIRMED`. `GEMSDOE32/registry/submission_build.json` explicitly records `"NO ORGANISER SCORE EXISTS for this or any artifact in this repository"` at build time (`projected_dti_if_live_credit_matches: 0.2747` was a model estimate, not a receipt). Similarly, `0.4413` and `0.3195` in the prompt are `USER-REPORTED` figures (a parallel session's dated public snapshot recorded `#1 = 0.4413` and `DARD = 0.3358`, not re-fetched here because `drivendata.org` is outside this sandbox's outbound allowlist).

### 3.2 Exact Pixel-Support Ancestry & Why Pure Subtraction Raised DTI
Direct pixel-exact inspection of the restored lineage rasters establishes a **strict nested subset chain**:

$$\underbrace{\text{H19-5}}_{121,131\text{ px}} \;\supset\; \underbrace{\text{D2.8}}_{44,090\text{ px}\;(\text{USER-REPORTED }0.2600)} \;\supset\; \underbrace{\text{SOLO-D2.8}}_{40,199\text{ px}\;(\text{USER-REPORTED }0.2708)} \;\supset\; \underbrace{\text{H33-2-B2}}_{37,654\text{ px}\;(\text{USER-REPORTED }0.2778)}$$

Every single positive pixel of `H33` was already positive in `SOLO-D2.8`, `D2.8`, and `H19-5` (`100.0%` subset; `0` newly discovered pixels added between `D2.8` and `H33`). Specifically, `H33-2-B2` deleted the exact **`2,545` pixels** of `SOLO-D2.8` located at Euclidean distance $d_{\text{cat}} \le 2\text{ px}$ (`200 m`) from mapped catalogue faults (`existing_faults.tif == 1`).

Under the competition's pooled **Distance-Tolerant IoU (`DTI`)** implemented in `vendor/gems57/metric.py` ($\alpha = 0.2$, $\beta = 0.8$, triangular kernel $K(r) = \max(0, 1 - r/3)$ over $3\text{ px} = 300\text{ m}$):

$$\text{DTI}(D, T_{\text{hidden}}) = \frac{\text{TP}_w}{\text{TP}_w + 0.2\,\text{FP}_w + 0.8\,\text{FN}_w}$$

three exact mathematical mechanisms explain why `H33` outperformed all dense, continuous, and catalogue-hugging fleet submissions:

1. **Elimination of Pure False-Positive Flank Collar Dots ($d_{\text{cat}} \le 2\text{ px}$):**
   Because known mapped faults (`existing_faults.tif`) are masked prior to scoring hidden faults $T_{\text{hidden}}$, predicted dots placed within `1–2 px` of a mapped fault trace sit inside the deformation halo of an *already-mapped* structure rather than an unmapped fault. Removing those `2,545` collar dots reduced $0.2\,\text{FP}_w$ by $\approx 509$ denominator units (`18,742` $\to$ `18,233` in `submission_build.json`) while losing almost zero hidden-fault $\text{TP}_w$, yielding a purely algebraic DTI increase (`0.2708` $\to$ `0.2778`).
2. **Asymmetry Between `max`-Pooled Recall and `sum`-Pooled Precision (`nn_min = 2.8284 px`):**
   True-positive credit on hidden fault pixels uses the **envelope maximum** $K(\text{dist}(t, D))$ (a second dot within `< 2.83 px` of an existing dot adds near-zero $\Delta\text{TP}_w$), whereas false-positive penalty sums $(1 - K(\text{dist}(p, T_{\text{hidden}})))$ over **every** predicted pixel $p \in D$. Continuous probability surfaces (e.g., `17GEMSDOE` with `5.17M` positive pixels) or un-thinned ridge maps (`H19-5` with `121,131` pixels) flood the $0.2\,\text{FP}_w$ denominator (`~1,000,000` penalty units for `17GEMSDOE`), collapsing DTI to `< 0.03`. `H33`'s `2.8284 px` ($\sqrt{8}$) minimum spacing matches the `3 px` kernel support almost optimally.
3. **Blind-Basin Spatial Allocation Under $\beta / \alpha = 4$ Asymmetry (`41.7%` of dots at $d_{\text{cat}} > 25\text{ px}$, median $d_{\text{cat}} = 19.65\text{ px}$):**
   In the Great Basin, USGS QFaults / INGENIOUS mapping is heavily biased toward exposed range-front scarps (`Selected-At-Random` observability bias): `47.17%` of the competition footprint lies at $d_{\text{cat}} > 25\text{ px}$ (`> 2.5 km` from any mapped fault), yet only `13.62%` of mapped catalogue pixels lie there. Models trained naively on `existing_faults.tif` place `> 85%` of their budget near known fault tips, starving buried intrabasin faults where $0.8\,\text{FN}_w$ dominates the denominator. `H33` spreads `41.7%` of its `37,654` dots into blind basins ($d_{\text{cat}} > 25\text{ px}$), capturing high-leverage $\Delta\text{TP}_w = -\Delta\text{FN}_w$ gains.

### 3.3 Are We Able to Beat `0.2778` (and `0.3195` / `0.4413`)?
- **Physically and algorithmically: YES, `0.2778` is not a ceiling** — `H33` relies on an early 19-band surface (`H19-5`) without upward-continued Baranov pseudogravity worms (`H88-BPWD`, repo-record `HOLDOUT-DTI = 0.205991 [0.188105, 0.223344]`, `n = 22,893`, `8/8` folds won over `H88-ADHR`), vertical heat-flow/geothermometer disequilibrium (`H88-VHGD`, repo-record blind-basin `> 25 px` `HOLDOUT-DTI = 0.092061 [0.056908, 0.132098]`, `n = 3,117`), or cross-validated scarp-profile restoration (`H88-SPR`). Furthermore, reported public leaderboard scores (`0.3358`–`0.4413`) prove substantially higher hidden-set recovery exists.
- **Scientifically & operationally today: NO score > `0.2778` can be claimed, projected, or emitted in this session**, for three binding reasons:
  1. **Literal Uniqueness Stop (`1.0000 > 0.70`):** While `dense_17gemdoe.tif` (`5.17M` positive cells) and `GEMSDOE87:gems87-bmtd` (`4.53M` positive cells) remain in the literal `> 0` dot-overlap scope, *zero* nonempty candidates can pass preflight without an explicit protocol revision by the user/selector.
  2. **Selected-At-Random Holdout Observability Gap:** Catalogue hide-and-recover (`HOLDOUT-DTI`) evaluates recovery of withheld *mapped* range-front faults, not *unmapped* intrabasin faults (for example, `H33`'s fixed TIF scores `HOLDOUT-DTI = 0.0067` on quadrant hide-and-recover while `H88-BPWD` scores `0.2060`). Beating `HOLDOUT-DTI` is a necessary anti-overfitting gate, never a sufficient proof of beating `0.2778` on hidden organizer labels.
  3. **No Organizer Portal Access:** Only an authenticated DrivenData submission receipt establishes `ORGANIZER-CONFIRMED` performance.

---

## 4. Root Cause & Automated Verification of `"Predicted values must be in range [0, 1]"`

- **Exact failure mechanism:** Several sibling GEMSDOE repositories (including `GEMSDOE32`'s `-nan.tif` twin documented in `submission_build.json`, `GEMSDOE49`, and `GEMSDOE63`) wrote `NaN` outside the valid study footprint (copying `sample_submission.tif`'s `NaN` mask), set negative `nodata` sentinels (`-9999`), or left unclipped floating-point overshoots (`< 0.0` or `> 1.0`). In NumPy/GDAL validation, `np.all((arr >= 0.0) & (arr <= 1.0))` evaluates to **`False`** if *even a single pixel anywhere in the `3730 × 3292` array is `NaN`*!
- **Automated project fix (zero human inspection):** `vendor/gems57/submission_writer.py` and `scripts/audit_downloads.py` enforce `dtype=float32`, `count=1`, `CRS=EPSG:32611`, exact sample `shape=(3730, 3292)` and `transform`, `nodata=None`, `0.0` on all out-of-footprint and mapped-catalogue pixels, `0` `NaN`/`Inf` across all `12,279,160` cells, strict `min >= 0.0` and `max <= 1.0` across two independent TIFF decoders (`rasterio` + `tifffile`), and single-TIFF `.zip` byte parity (`48/48` Pages packages + `20/20` `submissions/` packages pass).

---

## 5. Verifiable Official Links, Retrieval Provenance & Sandbox Limitations

| Source / Resource | Official / Canonical URL | Session `587c7f22` Verification Status |
| :--- | :--- | :--- |
| DrivenData Official Reference Solution (`README.md`) | https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md | **LIVE-FETCHED** (`github.com` allowlisted); confirms CPU (`--extra cpu` / `environment-cpu.yml`) & GPU (`cu126`/`cu130`) workflows |
| `GEMSDOE32` `H33` Build Provenance (`submission_build.json`) | https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json | **LIVE-FETCHED** (`github.com` allowlisted); confirms SHA `c55bafc4...`, `37,654` dots, `d_cat <= 2 px` prune, and `NO ORGANISER SCORE EXISTS` |
| `17GEMSDOE` Dense Witness (`dense_17gemdoe.tif`) | https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif | **RESTORED & SHA-VERIFIED** (`ab0a0a62...`, `5,167,373` positive cells) |
| Sibling Fleet `GEMSDOE86..92` Inventory (`161` TIFFs) | https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/registry/sibling_inventory.json | **RESTORED & SHA-VERIFIED** via `python scripts/restore_siblings.py` |
| DrivenData GEMS Problem Description (`#306`) | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Reference link for manual review (host outside sandbox outbound allowlist) |
| DrivenData GEMS Public Leaderboard | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | Reference link for manual review (host outside sandbox outbound allowlist) |
| DrivenData GEMS Submissions Portal | https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/ | Reference link for manual review (requires user authentication + outside allowlist) |
| NLR / NREL Official Prize Rules PDF (`96647.pdf`) | https://docs.nlr.gov/docs/fy26osti/96647.pdf | Reference link for manual review (host outside sandbox outbound allowlist) |
| USGS GeoDAWN Survey Release | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | Reference link for manual review (cached rasters SHA-verified locally) |
| DOE GDR `#1391` INGENIOUS Regional Data | https://gdr.openei.org/submissions/1391 | Reference link for manual review (cached tables/rasters SHA-verified locally) |
| USGS 3D Elevation Program (3DEP) | https://www.usgs.gov/3d-elevation-program | Reference link for manual review (cached 100 m derivatives SHA-verified locally) |

### Explicit Limitations & What Access Would Unblock Genuine Submission
1. **Protocol clarification needed from user/selector:** Explicit written rule on whether space-filling continuous probability rasters (`dense_17gemdoe.tif` `5.17M` px; `gems87-bmtd` `4.53M` px) are excluded from the binary 3-px dot-overlap denominator or converted via a pre-declared support rule, AND an explicit single-method lane assignment.
2. **Outbound network & portal authentication limits:** Sandbox outbound access is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`. Live DrivenData leaderboard/quota pages, primary `.gov` / `.org` metadata pages, and authenticated submission receipts cannot be retrieved directly from this environment.
3. **Ordered Next Steps for Next Session:**
   - Do **not** weaken `generation_guard.py`, `audit_downloads.py`, or `check_site.py`.
   - Once the dense-prior overlap rule is formally resolved in the shared contract, execute the minimal 1-experiment buffered holdout falsification of **`H88-SPR`** ([`session-587c7f22-hypotheses.md`](session-587c7f22-hypotheses.md)) against fold-rebuilt `H88-BPWD` (`0.205991`), requiring all feature canaries `<= 0.90`, paired physical-block $\Delta\text{DTI}$ 95% CI `> 0`, and full `220+`-raster uniqueness before invoking the separate weekly-slot selector.
