# Session 82dbb5e9 — H88-PGTD execution, H33 forensics, 5 ranked hypotheses (2026-10-25)

## Why H33 (0.2778, USER-REPORTED, no organizer receipt) is highest among GEMSDOE sites
Measured on SHA-pinned files (`research/h33-forensics-20261024.md`, `scripts/forensics_h33.py`):
H33 (37,654 dots) is a strict pixel subset of SOLO-D2.8 ⊂ D2.8 ⊂ H19-5. Every gain
0.1922→0.2477→0.2600→0.2708→0.2778 came from *removing* dots, specifically 6,436 dots
within 2px of the catalogue. Under DTI (alpha0.2 beta0.8, 300m triangular kernel,
`vendor/gems57/metric.py`), removing a pure-FP dot always raises DTI; H33 also has
kernel-spaced lattice (median NN 3.0px) and non-hugging distance profile (median
19.6px from catalogue; fleet Spearman share>25px vs score = +0.90, n=20).
Leaderboard top is 0.4413 (OFFICIAL-PUBLIC snapshot in repo) — H33 would rank below #50.
Beating 0.2778 needs ~+27-29% more truth credit at same dot count (to 0.3539) per
lineage arithmetic [INFERENCE]. No holdout instrument in this repo predicts that.

## 5 ranked untried hypotheses (layers / signature / why off-catalogue / difference)
1. **H88-PGTD (EXECUTED here)** — B02 rtp+B09 tmi_vg, B13 iso_grav+B11 vg, B12 topo;
   Laplace-consistent Marussi tensor det(T)~0 sheetness. Buried sheet faults under
   basin fill have no scarp. Differs: no prior module builds full 3x3 trace-free tensor
   invariants (bpwd/psgv=Baranov phase; vess/hgvc=2D Frangi). Mimic: 2D mafic dikes.
2. **H88-SPRV** — B12 det_elev + dem10 chi + zmean; Hanks-Bucknam erf scarp-profile
   restoration LLR + inflection emission. Degraded scarps missed by slope thresholds.
   Differs from lsc88 single-step detectors by full profile integral. Mimic: shoreline benches.
3. **H88-CBBC** — B17 cond_surf × B15 depth_to_base × B13; Morse-Smale saddle breach
   topology. Clay caps crossing basement highs = transverse relay faults. Mimic: playa evaporites.
4. **H88-TAWA** — geodawn_rad/extensions K/Th,U/Th + B02; exponential cross-strike
   alteration half-width asymmetry ln(wHW/wFW), drape-compensated. Mimic: lithologic contacts.
5. **H88-MT3D-GDR** — external USGS MT conductance (doi:10.5066/P9TWT2LU, CC0) +
   heat flow (doi:10.5066/P9BZPVUC) via DOE GDR #1391 (CC-BY-4.0, https://gdr.openei.org/submissions/1391);
   obtainable free official, needs owner-mirror staging (sandbox cannot fetch doi.org). Highest cost.

## Result (HOLDOUT-DTI, gems57-pooled-hide-v2, n=22,893 withheld, 95% CI)
- Arm A (31ch = 19 raw + 12 PGTD): **0.0811 [0.0674, 0.0957]**; far>10px 0.0741 [0.0560,0.0912]; blind>25px 0.0566 [0.0338,0.0827]
- Arm B control (19 raw): 0.0696 [0.0567,0.0829]; paired Δ **+0.0115 [+0.0047,+0.0188]** — PGTD signal is real.
- BUT absolute 0.0811 << repo best BPWD 0.205991 (which adds catalogue-anatomy features this
  runner deliberately excludes). **Verdict: negative. Do not submit.**
- Canary: 31 features, max symmetric AUC 0.5779 (pgtd_topo_sheetxgrad) ≤0.90 PASS.
- Uniqueness: surface |rho| worst 0.9095 >0.90 FAIL; like-for-like 3px overlap 0.8061 >0.70
  vs MFS88 FAIL; literal vs dense 17GEMSDOE 1.0000 (see IR below).
- Validator: all checks PASS (no NaN, [0,1], EPSG:32611 3730x3292 transform match, zeros outside).
  This fixes the user's "Predicted values must be in range [0,1]" class locally — zeros-mode,
  all-finite. Local PASS ≠ organizer acceptance.
- File: `gems88-pgtd88-marussi-37654dots-20261025T171809Z-af016438-zeros-DO-NOT-SUBMIT.tif`
  SHA-256 f9ac5c5728869bb1c3096046b42cc7a71beec9d7f398d5a34700ff1f42573fd8
  Name (25/140): GEMSDOE88-PGTD88-AF016438 · Note (103/140) in run card.

## Irregularities flagged
- **IR-88-PGTD-01**: Literal 70%/3px rule vs dense continuous 17GEMSDOE raster (positive on
  5,106,385/5,106,385 allowed cells) makes *every* nonempty submission a "duplicate" (random
  dots also 1.0). Rule as written cannot distinguish copies from independent work. Generation
  proceeded under user's explicit instruction with corrected like-for-like gate ALSO applied
  (and failed on its own merits), verdict negative regardless. Selector must fix rule definition.
- **IR-88-PGTD-02**: First run had arm-selection bug (`startswith("mfs")` after rename) making
  A≡B; caught because paired Δ was exactly 0.0, fixed, holdout re-run. First card superseded.
- All scores USER-REPORTED except leaderboard snapshot; ORGANIZER-CONFIRMED: none. 0 slots used.
- Next step: fuse PGTD channels into BPWD 107ch anatomy stack (paired same-fold test) — the
  +0.0115 increment may add to 0.206, but must be re-validated, not assumed.

## Pass2/3 verification
- Independent re-validation of emitted TIF via vendor validate: all 15 checks PASS, SHA matches card.
- tests/test_pgtd88.py PASS; audit_downloads.py fails on 14 PRE-EXISTING published pairs even with PGTD file removed (verified) — flagged, not caused by this session, not fixed here (shared-tool fix needs separate audit).
- Site: PGTD section added after canonical decision block; site guard still fails on pre-existing audit mismatch above.
