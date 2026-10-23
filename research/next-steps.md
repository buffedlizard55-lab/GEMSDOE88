# Next Steps & Handoff Brief (`GEMSDOE88` · Updated `2026-10-22`)

Read `README.md` and `registry/run_card.json` first at the start of any future session.

## 1. Current Verified State (Do Not Re-Run Blindly)
- **Primary Candidate Generated & Validated (`Exp 03`, `H88-ADHR`):**
  - File: `docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.tif` (`133,192` bytes, `35,894` discrete `{0.0, 1.0}` dots, `SHA-256: f8e56f2a2f5fd6df8738364e2f98bbaf955512c027f9d53b5e404a9fef62eccd`).
  - Single-TIFF ZIP: `docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.zip` (`SHA-256: 729ca35f4aed1ba3c99cf5f420af89032c27d08308471a239ed8d1d46ad3a7fd`).
  - Pooled `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `n = 22,893` withheld positive pixels across 8 spatial folds):
    - `raw_control`: `0.03134` (`95% CI [0.02082, 0.04535]`)
    - `mgc_88` (`Exp 01`): `0.03612` (`95% CI [0.02641, 0.04830]`)
    - `cgo_88` (`Exp 02`, 26 competition physics features only): **`0.09042` (`95% CI [0.07950, 0.10132]`, `2.50×` `MGC-88`)**
    - `h88_adhr` (`Exp 03`, full 67-feature ADHR-88): **`0.18789` (`95% CI [0.17170, 0.20326]`, `5.20×` `MGC-88`, `8 / 8` fold wins)**
  - Single-feature leakage canaries: **`74 / 74 PASS`** (`max symmetric AUC = 0.771627 ≤ 0.90`).
  - Uniqueness across all 21 SHA-pinned registry rasters:
    - **Sparse / dot-field siblings (`20 / 20`):** **PASS** (`0` firings; `max 3-px overlap = 0.6796 ≤ 0.70`, `max |ρ| = 0.0975 ≤ 0.90`).
    - **Literal all-positive continuous surface (`17GEMSDOE`):** `forward_dot_overlap_3px = 1.0000 > 0.70` (`5,167,373 / 5,167,373` positive footprint pixels) -> **`ok_to_submit: false` (`verdict: "negative"`)**.

## 2. Highest-Priority Actions for Next Session
1. **Protocol / Human Portfolio-Selector Decision on `IR-88-01` (`17GEMSDOE` Full-Footprint Prior):**
   - `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` mathematically forces `forward_dot_overlap_3px == 1.0000` for every non-empty raster inside the footprint.
   - If the human portfolio selector explicitly amends the protocol so continuous surfaces (`> 20%` positive footprint) are tested by rank correlation (`ρ = +0.46641` pre-placement, `+0.09750` final — both well below `0.90`) while sparse dot rasters are tested by 3-px overlap (`max = 0.6796 ≤ 0.70`), `H88-ADHR` is already format-validated, hash-pinned, and ready for human review against other weekly candidates. **Never self-authorize or silently exempt this rule.**
2. **Organizer-Authenticated Byte Check (`IR-88-02`):**
   - Verify SHA-256 of `sample_submission.tif` from an authenticated DrivenData download against owner mirror `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` before uploading any file.
3. **Scientific Frontier #1 — Far-Basin Blind Volcanic / Alluvial Faults (`d_cat > 25 px`):**
   - `H88-ADHR` raised off-catalogue `d_cat > 10 px` share to `26.2%` (`9,417` dots) and `> 1 km` withheld `HOLDOUT-DTI` to `0.11478` (`5.44×` `MGC-88`), yet `d_cat > 25 px` remains `4.2%` (`1,520` dots) whereas `H33` places `41.8%` at `d_cat > 25 px`.
   - Test **Hypothesis 4 (`MRR-88` — Intra-Magnetic Vertical-to-Regional Polarity Asymmetry)** + **connected ridge-skeleton continuity prior** specifically evaluated on a **pure blind-basin whole-fault split (`d_vis > 25 px`)** to raise far-basin recall without sacrificing Dinkelbach precision.
