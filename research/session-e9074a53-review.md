# Session `e9074a53` — Three-Pass Scientific, Engineering & Protocol Review (`2026-10-25`)

## 1. Executive Decision & Submission Gate Status

| Gate / Field | Verified Status (`2026-10-25`) | Evidence Class |
|---|---|---|
| **Session decision** | **`DUPLICATE_STOP` (`verdict: "negative"`)** | `REGISTRY-MEASUREMENT` |
| **New competition GeoTIFF generated?** | **`NO` (`0` new rasters; `ok_to_download_new_file: false`, `ok_to_submit: false`)** | `LOCAL-AUDIT` |
| **Weekly submission slots picked / spent** | **`0` (`approved_for_weekly_slot: false`)** | `LOCAL-AUDIT` |
| **Experiments run in session `e9074a53`** | **`0 / 3` (`DUPLICATE_STOP` fired before placement per `AGENTS.md` Rule 3)** | `LOCAL-AUDIT` |
| **Canonical archived research package** | `docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif` (`sha256=db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`) — **`OK TO DOWNLOAD FOR RESEARCH ONLY — DO NOT SUBMIT`** | `HOLDOUT-DTI` (`0.196237 [0.179686, 0.211729]`, `gems57-pooled-hide-v2`, `n=22,893`) |
| **Audited archive inventory** | **`46 / 46` Pages TIFF/ZIP pairs** (`45` in `docs/downloads/` + `1` in `docs/research-variants/`) + **`20 / 20` `submissions/` pairs** pass dual-decoder (`rasterio` + `tifffile`) `[0, 1]` portal checks; **`0` submission-eligible** | `LOCAL-AUDIT` |
| **Repo holdout records (all `DO NOT SUBMIT`)** | Overall & Far `>10 px` #1: **`H88-BPWD` = `0.205991 [0.188105, 0.223344]`** (`b8543782…`); Overall #2: **`H88-HGVC` = `0.202947 [0.185869, 0.219790]`** (`d5329f31…`); Blind `>25 px` #1: **`H88-VHGD` = `0.092061 [0.068634, 0.116758]`** (`752dba74…`); Emitted 3-regime #1: **`H88-VCAZ` = `0.152829 [0.135562, 0.170454]`** (`34224a7c…`) | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `n=22,893`) |

---

## 2. Autonomous Data Placement, CPU Stack Preparation & Pre-Placement `DUPLICATE_STOP`

Prior session `4c9e4bed` (`PR #166`) skipped restoring the validation/data stack and accidentally logged `AUDIT_ERROR`. In Pass 1 of session `e9074a53`, we executed the complete data placement and CPU preparation pipeline end to end:

1. **Hash-pinned competition & registry inputs restored (`bash scripts/download_competition_data.sh --validation` & `--registry`):**
   - `data/bridge/sample_submission.tif` (`sha256=2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`, `EPSG:32611`, `3730 x 3292`, `float32`, `Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`).
   - `data/bridge/existing_faults.tif` (`sha256=7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093`, `60,988` mapped in-footprint catalogue pixels out of `5,167,373` valid footprint pixels).
   - `data/training_features.tif` (`sha256=4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`, 19-band `3730 x 3292` `float32` geophysical/topographic stack) + **`18 / 18` external datasets** under `data/external/` + `25` cached registry rasters under `data/registry/`.
2. **CPU manifest verification (`python scripts/prepare_data.py`):**
   - Verified all grids, hashes, and masks on CPU (`exit 0`) and wrote `data/prepared_data_manifest.json` (`in_footprint_pixels=5,167,373`, `catalogue_pixels_in_footprint=60,988`, `external_present_count=18/18`).
3. **Pre-placement uniqueness check (`AGENTS.md` Rule 3):**
   - Both `python scripts/preflight_mtas88.py --gate-generation` and `python scripts/generation_guard.py` exited **`2` (`DUPLICATE_STOP`)**.
   - **Mathematical proof (`REGISTRY-MEASUREMENT`):** `data/registry/dense_17gemdoe.tif` (`sha256=ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, from `GEMSDOE17` `gemdoe17_lingam_causal_discovery_20261004.tif`) has `5,106,385 / 5,106,385` positive pixels across the entire allowed non-catalogue footprint (`5,167,373 - 60,988 = 5,106,385`; `uncovered_allowed_pixels = 0`). Because `vendor/gems57/uniqueness.py:dot_overlap(A, B, radius_px=3)` computes the fraction of candidate positive pixels within Euclidean distance `<= 3 px` of any positive pixel in $B$, **every nonempty admissible GeoTIFF $A$ satisfies $\text{overlap}_{3\text{px}}(A, \text{17GEMSDOE}) = 1.0000 > 0.70$**.
   - Per `AGENTS.md` Rule 3 (*"If either fails, log duplicate and stop"*), candidate placement for our top-ranked untried hypothesis **`H88-ANIS`** was halted immediately before emitting a misleading new TIFF or relabeling an archive copy.

---

## 3. Why `GEMSDOE32` `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` Scored Highest (`0.2778` `USER-REPORTED`), Exact Score Reconciliation, and How to Beat It

### 3.1 Score Provenance & Reconciliation (`0.2778` vs `0.3195` vs `0.3398` vs `0.4413`)

Verified directly against the live official DrivenData competition pages ([leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [official DOE/NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)) on `2026-10-25` (archived in `evidence/leaderboard_official_snapshot_e9074a53_20261025.json`):

| Score | Exact Provenance Label | Source & Meaning on `2026-10-25` |
|---:|---|---|
| **`0.4413`** | **`OFFICIAL-PUBLIC`** | Current `#1` overall on the DrivenData public leaderboard (`xiaofanhu`, `30` submissions; followed by `#2 cfld__ = 0.3916`, `#3 Batik Shirt Brothers = 0.3904`, `#4 BrandenKMurray = 0.3724`, `#5 No Fault of Our Own = 0.3539`). |
| **`0.3195`** | **`HISTORICAL-STALE-PUBLIC`** | External competitor **`DARD`**'s public leaderboard score on `2026-10-04`, **not** a supplied GEMSDOE fleet site score. On `2026-10-25`, **`DARD` is `#8` at `0.3398` (`27` submissions)** (up from `0.3358` earlier on `2026-10-25`). |
| **`0.2818`** | **`OFFICIAL-PUBLIC`** | Current `#50` cutoff on the public 50-row leaderboard (`moongrega`, `16` submissions; `#32 sws-jonathan = 0.3004`). |
| **`0.2778`** | **`USER-REPORTED ONLY`** | User-supplied score in the prompt for `GEMSDOE32` `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`sha256=c55bafc4596cc38da17fab273ad7bfbd7be4fe589bcffbe84d6522e129de6d12`). Because `0.2778 < 0.2818` (`#50` cutoff) and no DrivenData submission-page screenshot/JSON receipt exists in this repository, `0.2778` is **never** labeled `ORGANIZER-CONFIRMED`. |

### 3.2 Forensic Mechanism: Why `H33-2-B2` Beat the Other Supplied GEMSDOE Submissions

Direct byte-level inspection of the cached `GEMSDOE32` family (`evidence/h33_lineage_audit.json`, `docs/data/h33_forensics.json`) establishes an exact four-step nested pixel-subset ablation chain:

$$\text{H33-2-B2 } (37{,}654\text{ dots}) \;\subset\; \text{SOLO } (37{,}682) \;\subset\; \text{D2.8 } (44{,}090) \;\subset\; \text{H19-5 } (44{,}201)$$

Every positive pixel in `H33-2-B2` has exact binary value `1.0`, `0` NaNs (`zeros` outside footprint), `0` positive pixels on `existing_faults.tif`, and satisfies three decisive structural properties aligned with the official Distance-Weighted Tversky Index ([DOE/NLR Rules §7](https://docs.nlr.gov/docs/fy26osti/96647.pdf), linear kernel $K(d) = \max(0, 1 - d/300\text{ m})$, $\alpha = 0.2$ on $\text{FP}_w$, $\beta = 0.8$ on $\text{FN}_w$):

1. **Exact `<= 2 px` (`<= 200 m`) Catalogue-Halo Pruning (`-6,436` dead-weight FP pixels):**
   - Moving from `D2.8` (`44,090` dots, `0.2498` `USER-REPORTED`) to `SOLO` (`37,682`) and `H33-2-B2` (`37,654`, `0.2778` `USER-REPORTED`) removed **`6,436` dots** lying at Euclidean distance $d_{\text{cat}} \in (0, 2]\text{ px}$ (`min_d_cat = \sqrt{5} \approx 2.236\text{ px}` in `H33-2-B2`; `share_le2 = 0.0000`).
   - Why that jumped live DTI by `+0.0280`: expert-annotated **new** faults in the evaluation ground truth do not parallel already-compiled USGS/INGENIOUS traces at `100–200 m` offset; they represent **unmapped basin/piedmont strands, relay bridges, and along-strike continuations**. Thus `<= 2 px` catalogue-halo dots accumulate almost pure $\alpha\,\text{FP}_w$ penalty with near-zero $\text{TP}_w$. Confirmation from negative portal controls (`USER-REPORTED`): `GEMSDOE81` `cont_asb` (`44,090` dots packed at median $d_{\text{cat}} = 2.24\text{ px}$, `0%` `>25 px`) scored **`0.0041`**, and dense corridor strips (`GEMSDOE33/46` `~617k` positive pixels) collapsed under massive $\alpha\,\text{FP}_w$.
2. **Non-Overlapping `2\sqrt{2}` (`2.828 px`) Poisson-Disc Packing:**
   - Every pair of dots in `H33-2-B2` satisfies nearest-neighbor spacing $d_{\text{nn}} \ge \sqrt{8} \approx 2.828\text{ px}$ (`282.8 m`), nearly matching the `300 m` (`3 px`) linear kernel radius. Under `DTI` with $\alpha = 0.2, \beta = 0.8$, a single isolated binary `1.0` dot placed on an unmapped fault strand captures up to $\sim 3$–$5$ truth pixels' worth of distance-weighted $\text{TP}_w$ while paying only `1.0` unit of $\text{FP}_w$ if it misses—so a dot breaks even whenever its marginal hit probability exceeds $\frac{\alpha}{\alpha + \beta}\cdot \text{DTI}^* \approx 0.20 \times 0.30 = 0.06$, **provided** adjacent dots do not waste budget re-covering the exact same `300 m` kernel disk.
3. **Aggressive Blind-Basin Reach (`48.66%` of dots at $d_{\text{cat}} > 25\text{ px} = 2.5\text{ km}$):**
   - `H33-2-B2` places `18,324 / 37,654` dots (`48.66%`, median $d_{\text{cat}} = 24.41\text{ px}$) in genuine off-catalogue terrain (`> 2.5 km` from known faults), guided by multi-scale geomorphometric ridge/scarp openness + potential-field gradients rather than catalogue distance decay.
   - Crucially, **this explains why `H33-2-B2` scores only `0.0258` on local `gems57-pooled-hide-v2` catalogue hide-and-recover (`IR-88-35`)**: withholding 20% of *existing* range-front catalogue segments concentrates 86.4% of withheld truth within `<= 25 px` of remaining visible segments (`only 3,117 / 22,893` withheld pixels lie at `> 25 px`), structurally penalizing any candidate that allocates ~49% of its budget to truly unmapped `> 25 px` blind basins!

### 3.3 Can `0.2778` Be Beaten, and How?

**Yes — `0.4413` (`xiaofanhu`, `#1`) and `0.3916` (`cfld__`, `#2`) prove there is `+0.11` to `+0.16` DTI headroom above `0.2778`,** and the competition's `$250,000` Final Prize will be scored on an **expanded expert-reviewed fault map pooling fault candidates across all participating teams** ([Official Rules PDF p. 7](https://docs.nlr.gov/docs/fy26osti/96647.pdf)). Beating `0.2778` requires two distinct steps—one governance/protocol step (human owner) and three technical upgrades:

1. **Governance prerequisite (Human Owner only):** Update `AGENTS.md` Rule 3 / `SLOT_PLAN.md` so uniqueness is enforced on **like-for-like sparse support** (or top-$k$ level sets against continuous priors such as `17GEMSDOE`), unlocking candidate emission without violating protocol, and open 1 weekly feedback slot (`<= 3/week` cap).
2. **Replace hanging-wall potential-field centroids with $z=0$ dip-extrapolated surface traces (`H88-ANIS`):** `H88-BPWD` (`0.2060` `HOLDOUT-DTI`) and `H88-HGVC` (`0.2029` `HOLDOUT-DTI`) already nearly double `phys44` (`0.1042`) on withheld segments, yet lose precision because upward-continued potential-field worms sit `400–2,000 m` downdip in the hanging wall. Fitting the 5-altitude Cauchy dip trajectory (`H88-ANIS`) projects those detections back onto the `<= 300 m` surface trace kernel.
3. **Sub-grid `090°` GeoDAWN flight-line fault-gouge notches (`H88-FLDC`) + zero-catalogue 3D Mohr–Coulomb reactivation (`H88-FSTD`):** Recovers narrow `50–120 m` oxidized fault-gouge troughs in `> 25 px` blind valleys (`P93LGLVQ`) and weights them by true geodetic principal-strain slip/dilation tendency (`GDR #1391`) without `sdtl.py`'s catalogue distance decay.
4. **Continuous probability calibration (`p_i \in (0, 1]`) along skeletonized strands instead of uniform `{0, 1}` dots:** Under soft Tversky (`TP_w = \sum_g \min(\hat{y}_{\text{conv}}(g), 1)` on truth, `FP_w = \sum_g \hat{y}_{\text{conv}}(g)` off truth), assigning calibrated amplitude $w_i \in [0.25, 1.0]$ proportional to posterior fault probability strictly Pareto-dominates hard `{0, 1}` thresholding on uncertain blind-basin strands while keeping `100%` of cells finite in `[0, 1]`.

---

## 4. DrivenData Portal `"Predicted values must be in range [0, 1]"` Root Cause & Automated Verification

- **Root cause:** DrivenData's competition scorer validates **every raw pixel** of the uploaded `3730 x 3292` `float32` raster with `0.0 <= x <= 1.0` **before** applying the study-area footprint mask. Because `sample_submission.tif` stores `NaN` (`7,111,787` pixels) outside the `5,167,373`-pixel active footprint (`nodata=None`), copying `NaN` outside the footprint—or writing `-9999.0` sentinel nodata or unclipped float overshoot `1.0000001`—triggers immediate `"Predicted values must be in range [0, 1]"` rejection because IEEE-754 `NaN >= 0.0` evaluates to `False`.
- **Automated zero-human-intervention enforcement in `GEMSDOE88`:**
  - `vendor/gems57/submission_writer.py` (`outside_footprint="zeros"`, `nodata=None`, explicit clip to `[0.0, 1.0]`), `src/gems88/gate.py:portal_validate()`, and `scripts/audit_downloads.py --check` verify every published `.tif` and single-member `.zip` via **two independent decoders** (`rasterio`/GDAL and `tifffile`).
  - Live Pass 1 & Pass 3 verification (`python scripts/audit_downloads.py --check`): **`46 / 46` Pages TIFF/ZIP pairs** (`45` main + `1` variant) and **`20 / 20` `submissions/` pairs** have `0` NaN, `0` Inf, `nodata=None`, `min >= 0.0`, `max <= 1.0`, exact `EPSG:32611` / `(3730, 3292)` / `100 m` affine match, `0` positive pixels outside footprint, and `0` positive pixels on `existing_faults.tif`.

---

## 5. Pass 2 Forensic Audit — Repository Defects Found & Remediated (`IR-88-E907-01..05`)

During Pass 2, line-by-line inspection of all validators, workflows, run cards, and concurrent PRs (`#160`, `#162`, `#166`, `#167`) uncovered **five actionable defects** on `main` (`8dc9670`), all fixed and locked down with automated regression tests in this PR:

1. **`IR-88-E907-01` (HIGH) — Fail-Open `scripts/validate_lsc88.py` (`--require-submit` exited `0`) & Missing `literal_dense_witness_overlap_3px`:**
   - *Defect:* `scripts/validate_lsc88.py` ignored `sys.argv` completely (so `python scripts/validate_lsc88.py --require-submit` exited **`0`** instead of **`2`** on a negative `DO-NOT-SUBMIT` artifact!), skipped SHA-256 verification of `sample_submission.tif`, `existing_faults.tif`, and `dense_17gemdoe.tif`, omitted literal `17GEMSDOE` 3-px overlap (`1.0 > 0.70`) from both `lsc88_run_card.json` and its gate calculation, had no `tests/test_lsc88.py`, and was omitted from `.github/workflows/checks.yml` and `ci.yml`.
   - *Fix:* Rewrote `scripts/validate_lsc88.py` with `argparse` (`--require-submit` exits `2`; unknown CLI flags exit `2`), pinned SHA-256 checks for all three reference rasters, added direct `uniqueness.dot_overlap` re-measurement against `dense_17gemdoe.tif` (`1.0 > 0.70`), recorded `literal_dense_witness_overlap_3px: 1.0` in `registry/lsc88_run_card.json` + `docs/data/lsc88_run_card.json`, added `tests/test_lsc88.py`, and wired `validate_lsc88.py --require-submit` into both `.github/workflows/checks.yml` and `.github/workflows/ci.yml`.
2. **`IR-88-E907-02` (HIGH) — Broken `validate_current.fabric_release_report()`, Raw `sys.argv` Flag-Typo Hazard in 9 Validators, & Bare `assert` Stripping Under `python -O` in 5 Lane Validators:**
   - *Defect:* `scripts/validate_current.py:fabric_release_report()` raised `ValueError('accessible registry changed since postmerge audit')` because 17 later audited negative research cards (`sgmc88`, `xgce88`, `ssa88`, `sepa88`, `mtas88_experiment`, `vcaz88`, `mmrx88`, `prism88`, `vhgd88`, `lsc88`, `gzzc88`, `bpwd88`, `psgv88`, `mfs88`, `hgvc88`, `sdtl88`, `relay88`) were missing from its hash ledger; 9 validators used `"--require-submit" in sys.argv` without `argparse` (so typos like `--require-submt` exited `0`); and 5 lane validators (`validate_{cxl88,gthc88,kth88,prism88,vhgd88}.py`) relied on bare `assert` statements that compile away under `python -O`.
   - *Fix:* Registered all 17 negative research run cards with strict `verdict == 'negative'`, `ok_to_submit is False`, `'DO-NOT-SUBMIT'`, and SHA-256 checks in `fabric_release_report()`; added `argparse` CLI validation across all 9 validators; and replaced every bare `assert` across all `scripts/validate_*88*.py` scripts with `-O`-safe explicit `_require(...)` / `require(...)` checks (`0` bare `assert`s remaining across all lane validators).
3. **`IR-88-E907-03` (MEDIUM-HIGH) — `ibl88` Unreceipted Score Mislabeling (`incumbent_organizer_confirmed_live_score: 0.2778`), Dangling Non-`DO-NOT-SUBMIT` Paths, & 3-Way Mirror Drift:**
   - *Defect:* `registry/ibl88_run_card.json`, `docs/data/ibl88_run_card.json`, and `evidence/ibl88_run_card.json` labeled unreceipted `0.2778` as `"incumbent_organizer_confirmed_live_score": 0.2778` (violating `AGENTS.md` Rule 4 after PR `#167` fixed `run_card.json`), pointed `submission.repo_copy` and `validator.file` at nonexistent non-`-DO-NOT-SUBMIT` filenames, and drifted between `registry/` and `evidence/` (plus `docs/downloads/gems88-ibl88-...-DO-NOT-SUBMIT.json`).
   - *Fix:* Set `incumbent_organizer_confirmed_live_score: null` and `incumbent_user_reported_live_score: 0.2778` with explicit provenance note, updated all paths to exact on-disk `-DO-NOT-SUBMIT` files, synchronized `registry/`, `docs/data/`, `evidence/`, and the sidecar JSON byte-for-byte, and added `check_site.py` invariants enforcing mirror & provenance parity.
4. **`IR-88-E907-04` (MEDIUM) — Non-Protocol `"promote-to-selector-only"` Verdicts, Placeholder `ci95: [0.0, 0.0]`, & Double-Counted `45,260` Withheld Positives in `phys_near` & `sgmc88`:**
   - *Defect:* `phys_near` (`HOLDOUT-DTI = 0.002453`) and `sgmc88` (`0.056081`) carried `"verdict": "promote-to-selector-only"` (via `build_{unique,sgmc_distance,sgmc_distance_v2}_submission.py` ignoring `dense_overlap = 1.0 > 0.70` and ignoring whether `pooled_dti` beat `0.205991`), stored invalid `"ci95": [0.0, 0.0]` intervals excluding their own point estimates, summed overlapping `*_all` + `*_detached` fold modes (`45,260` instead of canonical `22,893`), and relied on a `validate_current.py:196` carve-out.
   - *Fix:* Normalized `phys_near` and `sgmc88` run cards & gate verdicts (`registry/` + `docs/data/`) to `"verdict": "negative"` (preserving `"historical_verdict": "promote-to-selector-only"`), replaced `[0.0, 0.0]` with `null` + explicit `audit_remediation_20261025` disclosure, fixed all 3 builder scripts, removed the `validate_current.py` carve-out, and enforced `verdict == "negative"` in `check_site.py`.
5. **`IR-88-E907-05` (LOW-MEDIUM) — Concurrent Session Drift (`PR #162`, `PR #166`) & Missing `docs/data/mmrx88_run_card.json` / Dangling `mmrx88` Download Path:**
   - *Defect:* `registry/mmrx88_run_card.json` pointed `"download"` at a nonexistent `docs/downloads/gems88-mmrx88-...` path (while only `submissions/gems88-mmrx88-...` existed) and lacked its `docs/data/mmrx88_run_card.json` mirror; meanwhile `PR #162` (`810e3aa2`) re-proposed already-tested Baranov pseudogravity (`psgv.py`/`bpwd.py`) and misattributed USGS GeoDAWN (`doi:10.5066/P93LGLVQ`) to GDR `#1391`, and `PR #166` (`4c9e4bed`) skipped data restore (`AUDIT_ERROR`) and omitted `registry/` run-card output.
   - *Fix:* Set `mmrx88` `"download": null` (preserving `"historical_omitted_docs_download"` and valid `"repo_copy"` in `submissions/`), created the synced `docs/data/mmrx88_run_card.json` mirror, logged all concurrent session caveats in `IRREGULARITIES.md`, and verified clean CPU data restore (`0` `AUDIT_ERROR`).

---

## 6. Three-Pass Verification & Honest Scope / Limitations Disclosure

- **Pass 1 (Autonomous Data Placement, Source Verification, Hypotheses & Pre-Placement Gate):** Restored full CPU data stack + `data/prepared_data_manifest.json`; verified pre-placement `DUPLICATE_STOP` (`exit 2`); fetched live DrivenData leaderboard (`2026-10-25`), rules PDF (`docs.nlr.gov/docs/fy26osti/96647.pdf`), and 6 official public-domain/CC-BY-4.0 geoscience catalogs/APIs; ranked 5 genuinely untried hypotheses (`H88-ANIS`, `H88-FLDC`, `H88-FSTD`, `H88-CHFR`, `H88-NWIS-HB`).
- **Pass 2 (Adversarial Code, Validator, Provenance & Edge-Case Remediation):** Fixed `IR-88-E907-01..05` across `validate_lsc88.py`, `validate_current.py`, 8 additional lane validators (`argparse` + `-O`-safe checks), `check_site.py`, `.github/workflows/{checks,ci}.yml`, and `ibl88`/`phys_near`/`sgmc88`/`mmrx88`/`lsc88` JSON mirrors; added `tests/test_lsc88.py` and `tests/test_session_e9074a53_record.py`.
- **Pass 3 (End-to-End Re-Verification Against Original Prompt):** Re-ran every CI gate (`audit_downloads.py --check`, `render_decision.py --check`, `python` & `python -O scripts/check_site.py`, `review_repo_20261025.py`, `review_submission_status.py`, `audit_protocol_integrity.py`, `audit_literal_protocol.py`, `preflight_mtas88.py`, `readiness.py`, `validate_current.py --require-submit`, `validate_release.py --require-submit`, `validate_lsc88.py --require-submit`, and full `pytest -q`).

### Explicit Unmet Requirement & Access Boundaries
- **Unmet user deliverable (blocked by binding `AGENTS.md` Rule 3):** A new, unique, submission-eligible competition GeoTIFF (`ok_to_submit: true`) was **not** emitted in session `e9074a53` because `data/registry/dense_17gemdoe.tif` covers `100.0%` (`5,106,385 / 5,106,385`) of non-catalogue footprint cells (`DUPLICATE_STOP`). Per prompt and `AGENTS.md` rules, negative results are first-class deliverables and no prior submission was copied or relabeled as new.
- **Source & credential boundaries:** (1) No authenticated DrivenData account/submission portal access exists in this sandbox, so remaining weekly team quota cannot be queried live and `0.2778` (`GEMSDOE32`) remains `USER-REPORTED ONLY` without an organizer receipt. (2) Outbound `bash` HTTP is restricted to `github.com`/`pypi.org`/`registry.npmjs.org`; public web pages (`drivendata.org`, `docs.nlr.gov`, `sciencebase.gov`, `gdr.openei.org`, `api.waterdata.usgs.gov`) were verified live via `fetch_page`, while historical sibling `GEMSDOE1..92` raster measurements rely on the hash-pinned local registry cache (`data/registry/`, `registry/`). (3) The 13 browser-pinned `docs/` HTML/CSS/JS files (`evidence/session_b4dfa10c_browser_check.json`) already render the canonical `DO NOT SUBMIT` banner cleanly at `1440px` and `390px` (`0` console errors, `0` horizontal overflow) and were intentionally preserved untouched so historical browser SHA-256 receipts remain valid.
