## Current handoff — repo review on `arena/60f59d16-gemsdoe88` (2026-10-24)

**Read this section before the archived handoffs below.** The latest candidate is KTH-88 (`docs/downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`, SHA-256 `5c7f1cb7a8c37bb4c7f3ba6eef2d42f472a050c6b21436274e4ebc0c259fd7bf`). It is **OK TO DOWNLOAD FOR RESEARCH; DO NOT SUBMIT**. HOLDOUT-DTI is 0.052656 (95% CI [0.045911, 0.059151], 22,893 positives, `gems57-pooled-hide-v2`) versus the same-split incumbent 0.187888; its final overlap is 0.89882 with a GEMSDOE87 raster and 1.0 with the dense witness. Stop: both holdout and literal uniqueness fail. Format validation is not submission clearance. No slot was spent and no organizer receipt exists.

No experiment was run in this review. KTH-88 is already the one completed experiment in its lane. The requested “single method paragraph below” remains unspecified; do not silently select another lane, rebuild a raster, or use a slot. Require an explicit lane and authorized/hash-pinned inputs before future work. H33's 0.2778 is user-reported, not organizer-confirmed; the dated leaderboard snapshot is documented as a public snapshot only. Current readiness, file hashes, ranked future hypotheses, and review passes are in [`repo-review-20261024.md`](repo-review-20261024.md).

## Archived historical handoffs — not current decisions

## 2026-10-24 (LBCAL session): next steps

1. **Selector decision on the slot gate.** Hide-and-recover HOLDOUT-DTI ranks R0/H33 (user-reported 0.2778) at 0.004, so it has no leaderboard validity in this regime. The receipt-CV gate (ρ 0.941, RMSE 0.031) is the alternative.
2. **Ridge-side experiment (needs a 0.70 lane-rule waiver for one slot).** Shift the D2.8 dots 1 px toward the uphill neighbour. Compare against D2.8's 0.2600. Expected sign: positive if px2's uphill coefficient is real.
3. **Feed every new receipt back** into `research/lbcal_user_reported_scores_20261024.tsv`, then refit with `scripts/lbcal_pixel.py --stage fit --cv`.
4. **Explain the residual family** (gems70, gate_ortho, tiltworm, +0.09–0.12) with new localisers. 20 m LiDAR derivatives need 1 m DEM access, which this sandbox does not have.

# Next Steps & Handoff Brief (`GEMSDOE88` · Updated `2026-10-22`)

Read `README.md` and `registry/run_card.json` first at the start of any future session.


# Next Steps & Handoff (`GEMSDOE88` · updated `2026-10-24`)

Read `README.md`, `registry/run_card.json`, and `IRREGULARITIES.md` first. The current run is complete; do not rerun MRR-BPR-88 blindly.

## Current verified state

- **Candidate:** `GEMSDOE88-MRR-BPR-20261024-DO-NOT-SUBMIT`.
- **Artifact:** `docs/downloads/gems88-mrr-bpr-blockresid-dinkelbach-20261024-v1-DO-NOT-SUBMIT.tif`.
- **TIFF SHA-256:** `b9cb36519c2ee91c08f587d3c9c006623d8e2505ece0416fdf263b50e42deb7e`.
- **Format:** independent writer and format-audit PASS; single-band float32, exact competition grid, all finite, `[0,1]`, 36,033 binary dots, no positives outside footprint or on catalogue pixels.
- **Leakage:** 4/4 MRR channels PASS; max symmetric AUC `0.532607 <= 0.90`.
- **Candidate HOLDOUT-DTI:** `0.1852558211`, 95% CI `[0.1715190223,0.1999647712]`, `n=22,893`, `gems57-pooled-hide-v2`.
- **Recomputed paired H88 incumbent HOLDOUT-DTI:** `0.1896338558`, 95% CI `[0.1749708832,0.2054805938]`.
- **Paired delta:** `-0.0043780347`, 95% CI `[-0.0079022116,-0.0006230905]` — a conclusive negative result under the preregistered rule.
- **Blind-basin `d_vis>25 px`:** MRR `0.059095` vs incumbent `0.065263`, `n=3,117` withheld positives.
- **Uniqueness:** pre-placement max `|rho|=0.468709`; final sparse-raster max 3-px overlap `0.684178`; H33 overlap `0.402187`; byte- and pixel-unique across 21 accessible rasters. Literal 17GEMSDOE overlap is `1.0`, so the binding any-raster gate fails.
- **Decision:** `negative`; OK to download for research, **DO NOT SUBMIT**. Zero portal slots used and no ORGANIZER-CONFIRMED score exists.

## Scientific conclusion

Blockwise removal of the local vertical-to-regional magnetic relation did not add recoverable whole-fault signal beyond H88-ADHR. The failure is unlikely to be simple catalogue leakage because every new channel's feature-alone canary is near chance. The feature family also loses on the intended far-blind-basin subset. Retire `MRR-BPR-88` rather than retuning it after seeing these folds.

## Next actions—separate future session

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
1. **Protocol / Human Portfolio-Selector Decision on `IR-88-1` (`17GEMSDOE` Full-Footprint Prior):**
   - `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` mathematically forces `forward_dot_overlap_3px == 1.0000` for every non-empty raster inside the footprint.
   - If the human portfolio selector explicitly amends the protocol so continuous surfaces (`> 20%` positive footprint) are tested by rank correlation (`ρ = +0.46641` pre-placement, `+0.09750` final — both well below `0.90`) while sparse dot rasters are tested by 3-px overlap (`max = 0.6796 ≤ 0.70`), `H88-ADHR` is already format-validated, hash-pinned, and ready for human review against other weekly candidates. **Never self-authorize or silently exempt this rule.**
2. **Organizer-Authenticated Byte Check (`IR-88-2`):**
   - Verify SHA-256 of `sample_submission.tif` from an authenticated DrivenData download against owner mirror `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` before uploading any file.
3. **Scientific Frontier #1 — Far-Basin Blind Volcanic / Alluvial Faults (`d_cat > 25 px`):**
   - `H88-ADHR` raised off-catalogue `d_cat > 10 px` share to `26.2%` (`9,417` dots) and `> 1 km` withheld `HOLDOUT-DTI` to `0.11478` (`5.44×` `MGC-88`), yet `d_cat > 25 px` remains `4.2%` (`1,520` dots) whereas `H33` places `41.8%` at `d_cat > 25 px`.
   - Test **Hypothesis 4 (`MRR-88` — Intra-Magnetic Vertical-to-Regional Polarity Asymmetry)** + **connected ridge-skeleton continuity prior** specifically evaluated on a **pure blind-basin whole-fault split (`d_vis > 25 px`)** to raise far-basin recall without sacrificing Dinkelbach precision.


---
# Addendum 2026-10-24 (session `arena/6464dbc1`, IR-88-75)
- PROVCREST null-control audit, spacing and count sweeps: `registry/provcrest_nullcontrol_audit.json`, `provcrest_spacing_experiment.json`, `provcrest_count_experiment.json`; narrative in `research/session-20261024-audit-why-0.2778.md`. Crest signal is real (+0.028 over nulls) but the file is blocked on uniqueness (0.7319 vs GEMSDOE85 90k-dot crest raster).
- **Next, in order:** (1) build a PROVCREST variant whose dot placement excludes the 3-px footprint of every registry raster with overlap > 0.65 (a construction fix, then re-run the v3 gate and the null controls); (2) a human pastes real receipts so the lineage geometry (ρ = 0.891, n = 13, CLAIMS) can be re-fitted; (3) the "geometry-null" probe; (4) hypotheses ranked in section 5 of the session note (crest junction/termination prior from Faulds & Hinz 2015 first).
- Do not re-run `scripts/build_provcrest_submission.py` main() (raises FileExistsError, appends to ledgers); use `scripts/audit_provcrest_nullcontrol.py` for reproduction.

1. **No weekly slot for MRR-BPR-88.** Its paired CI is entirely negative even before the universal literal witness is considered.
2. **Do not silently change the registry rule.** The SHA-pinned 17GEMSDOE surface is positive everywhere, making literal forward overlap `1.0` for every nonempty candidate. Only an explicit human protocol amendment can change that; current authorization has not.
3. **Authenticate organizer bytes before any future upload.** Compare a portal-downloaded `sample_submission.tif` with the pinned owner mirror. This session had no DrivenData authentication.
4. **If new work is authorized, preregister a genuinely different method lane.** Do not continue with connected MRR ridges or tune block size on these results; that would be post-hoc reuse of the same failed lane. Re-rank fresh hypotheses against the current 21-raster registry and preserve whole-component blocked evaluation.
5. **Keep scores epistemically separated.** H33 `0.2778` remains a user report/CLAIM. Local values are HOLDOUT-DTI only. ORGANIZER-CONFIRMED requires a real receipt.
