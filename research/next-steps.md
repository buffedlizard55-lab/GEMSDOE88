# Next Steps & Handoff Brief (`GEMSDOE88` · Updated `2026-10-22`)

Read `README.md` and `registry/run_card.json` first at the start of any future session.

## 1. Current Verified State (Do Not Re-Run Blindly)
- **Primary Candidate Generated & Validated (`Exp 03`, `H88-ADHR`):**
  - File: `docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.tif` (`131,557` bytes, `35,034` discrete `{0.0, 1.0}` dots, `SHA-256: 4e62f632f0b6857b048f9573cd8efe9a5a8003045b6df79f7947789999015cd0`).
  - Single-TIFF ZIP: `docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.zip` (`SHA-256: 1a34997961fdf7420697a922824f77ae016ba8de339a20b8aff14deca0b76463`).
  - Pooled `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `n = 22,893` withheld positive pixels across 8 spatial folds):
    - `raw_control`: `0.03134` (`95% CI [0.02082, 0.04535]`)
    - `mgc_88` (`Exp 01`): `0.03612` (`95% CI [0.02641, 0.04830]`)
    - `cgo_88` (`Exp 02`, 26 competition physics features only): **`0.09042` (`95% CI [0.07950, 0.10132]`, `2.50×` `MGC-88`)**
    - `h88_adhr` (`Exp 03`, full 67-feature ADHR-88): **`0.19210` (`95% CI [0.17547, 0.20796]`, `5.32×` `MGC-88`, `8 / 8` fold wins)**
  - Single-feature leakage canaries: **`74 / 74 PASS`** (`max symmetric AUC = 0.771627 ≤ 0.90`).
  - Uniqueness across all 19 SHA-pinned registry rasters:
    - **Sparse / dot-field siblings (`18 / 18`):** **PASS** (`0` firings; `max 3-px overlap = 0.6744 ≤ 0.70`, `max |ρ| = 0.0971 ≤ 0.90`).
    - **Literal all-positive continuous surface (`17GEMSDOE`):** `forward_dot_overlap_3px = 1.0000 > 0.70` (`5,167,373 / 5,167,373` positive footprint pixels) -> **`ok_to_submit: false` (`verdict: "negative"`)**.

## 2. Highest-Priority Actions for Next Session
1. **Protocol / Human Portfolio-Selector Decision on `IR-88-01` (`17GEMSDOE` Full-Footprint Prior):**
   - `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` mathematically forces `forward_dot_overlap_3px == 1.0000` for every non-empty raster inside the footprint.
   - If the human portfolio selector explicitly amends the protocol so continuous surfaces (`> 20%` positive footprint) are tested by rank correlation (`ρ = +0.47411` pre-placement, `+0.09710` final — both well below `0.90`) while sparse dot rasters are tested by 3-px overlap (`max = 0.6744 ≤ 0.70`), `H88-ADHR` is already format-validated, hash-pinned, and ready for human review against other weekly candidates. **Never self-authorize or silently exempt this rule.**
2. **Organizer-Authenticated Byte Check (`IR-88-02`):**
   - Verify SHA-256 of `sample_submission.tif` from an authenticated DrivenData download against owner mirror `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` before uploading any file.
3. **Scientific Frontier #1 — Far-Basin Blind Volcanic / Alluvial Faults (`d_cat > 25 px`):**
   - `H88-ADHR` raised off-catalogue `d_cat > 10 px` share to `23.7%` (`8,289` dots) and `> 1 km` withheld `HOLDOUT-DTI` to `0.11637` (`5.51×` `MGC-88`), yet `d_cat > 25 px` remains `2.5%` (`888` dots) whereas `H33` places `41.8%` at `d_cat > 25 px`.
   - Test **Hypothesis 4 (`MRR-88` — Intra-Magnetic Vertical-to-Regional Polarity Asymmetry)** + **connected ridge-skeleton continuity prior** specifically evaluated on a **pure blind-basin whole-fault split (`d_vis > 25 px`)** to raise far-basin recall without sacrificing Dinkelbach precision.
