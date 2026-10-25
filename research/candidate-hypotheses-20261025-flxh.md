# 5 Candidate Geological Hypotheses for Next Submission (Lane H88-FLXH) — 2026-10-25

**Project:** GEMSDOE88 — DOE GEMS Competition 306 (geothermal-indicative fault discovery)  
**Date:** 2026-10-25  
**Preregistration:** `registry/preregistration_flxh88.json`  
**Lane:** H88-FLXH — Flexural-Hinge & Conductance-Trough Coupling with Dilatant-Strain Gating  
**Official sources verified 2026-10-25:**  
- [DrivenData competition format & DTI metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation) — DTI = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w), 300 m triangular kernel  
- [DrivenData leaderboard snapshot 2026-10-24](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — #1 0.4413, #5 0.3539 (see `docs/data/leaderboard.json`)  
- [NLR Official Rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — submission format CRS/shape/transform, values in [0,1]  
- [Reference solution (CPU-capable)](https://github.com/drivendataorg/gems-prize-reference-solution) — official grid EPSG:32611 3730×3292  
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — airborne mag/radiometric (CC0)  
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) — 1 m & 10 m DEM  
- [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/) — geothermal permeability context  
- [EPSG:32611](https://epsg.io/32611) — UTM 11N  

---

## Why H33 (GEMSDOE32, user-reported 0.2778) led siblings and whether 0.2778 can be beaten — PhD forensic summary

**What H33 is (byte-verified):** H33 = 37,654 binary dots (`SHA256 c55bafc47…`) that is a strict pixel-subset of D2.8 (44,090 dots, 0.2600 user-reported) which itself is a thinning of H19-5 (121,419 dots, 0.1922). Every dot of H33 beyond 200 m of `existing_faults.tif` is pixel-identical to D2.8; the 6,436 deleted dots all lay ≤2 px (200 m) of the mapped catalogue. This is verified on-disk in `data/registry/gems25_d28.tif` and `data/registry/h33_education.tif` (see `research/h33-forensics-20261024.md`).

**Three metric facts that explain the climb 0.1922 → 0.2778:**

1. **Thinning precision (0.1922 → 0.2600, D2.8 step).** DTI charges FP_w = Σ p(x)(1−k_self) at α=0.2 per dot, where k_self is truth-kernel self-coverage. Two adjacent dots 100 m apart share the same 300 m triangular kernel support, so the second dot adds near-zero incremental TP_w but full α·FP_w. Poisson-disk thinning at ~2.8 px (≈280 m) spacing keeps ~78% of max-cover TP_w while cutting FP_w by 2.75× → numerator preserved, denominator shrinks.

2. **Collar deletion (0.2600 → 0.2778, H33 step).** Deleting 6,436 dots within 200 m of mapped faults removes 6,436·α = 1,287 denominator FP_w units that earned zero marginal truth credit on the public truth (receipt audit shows 0/22,893 withheld positives within 200 m of mapped faults in the hidden set). This is the H33 forensic mechanism.

3. **Basin placement preserved.** H33 retains 41.7% of dots at d_cat > 2.5 km (15,713 dots across 47% of footprint) — exactly the unmapped piedmont/basin pixels where hidden faults reside. Siblings that memorized near-catalogue halos (84–99% within 1 km) scored 0.03–0.09.

**Can we beat 0.2778 toward 0.4413?** Architecturally yes, but not proven locally. The hide-and-recover instrument (`gems57-pooled-hide-v2`, 22,893 withheld positives) contains **0/22,893 positives at d_cat>25 px**, so stratified basin recall cannot be rewarded there (IR-88-108). Beating H33 on the leaderboard requires higher precision *inside* conceal-basin piedmonts, which this instrument cannot rank. No portal receipt exists for H33; all 0.2778 / 0.4413 numbers are USER-REPORTED or leaderboard-snapshot, not ORGANIZER-CONFIRMED for our file.

---

## 5 Ranked Hypotheses (novel vs current repo + siblings)

| Rank | ID & Status | Exact Verified Layers (on-disk tags) | Physical Signature / Transform | Why Off-Catalogue (missed by USGS/INGENIOUS) | Named Non-Fault Mimic & Mitigation | How Differs from Existing Repo | Expected DTI Δ & Cost |
|---:|---|---|---|---|---|---:|---|
| **1** | **H88-FLXH — Flexural-Hinge & Conductance-Trough Coupling with Dilatant-Strain Gate** *(SELECTED, this session)* | **Competition 19-band stack:** `depth_to_base_surf` (B15), `cond_surf` (B17), `geod_shearrate` (B7), `geod_dilaterate` (B8), `det_elev` (B12), `det_elev_slope` (B19), `iso_grav_anom_slope` (B5), `iso_grav_anom_hg` (B18) + **External 10 m:** `topo_10m_derived_100m_u8.tif` (aspect_coherence, relief_local, curv_prof_absmax) + **External 1 m LiDAR:** `lidar_scarp_features_u8.tif` (strike, cross) — all SHA-pinned in `data/` (see `scripts/restore_inputs.py`) | **Basement flexural hinge curvature:** Laplacian + Hessian-ridge of `depth_to_base_surf` at σ=1.0,3.0,6.0 px (100,300,600 m) → identifies buried normal-fault monocline hinges under alluvium. **Conductive smectite trough:** Hessian-trough + gradient magnitude of log(cond_surf) at σ=2.0 px → fault-gouge clay caps. **Dilatant transtensional gate:** `shear·max(dilate,0)` product isolates dilational step-overs where permeability opens. **Conjunction:** hinge ∩ trough ∩ dilatant > p70, then anisotropic strand smoothing σ_along=2.5 px, σ_cross=0.5 px along `det_elev_slope` strike. | INGENIOUS mappers trace scarps where fault breaks surface (det_elev_slope high). Buried intra-basin horst-bounding faults beneath 10–100 m alluvium lack scarps but produce sharp basement flexure + clay-gouge conductive troughs + active dilatant strain that are invisible to air-photo mapping. | **Pleistocene Lahontan/Bonneville shorelines (≈1330/1555 m) & fan-toe onlap:** constant-elevation benches with hinge signal but no dilatant strain or trough continuity; penalized via shoreline elevation mask and `cond_trough` cross-strike coherence < 0.4. | First to combine **depth_to_base_surf flexural curvature (Laplacian+Hessian) ∩ log(cond) trough (Hessian trough) ∩ dilatant shear product** with anisotropic strand integration. DHTC used deep MT slices + basement steps; QTSK used cover-thickness decoupling; MVRD used magnetite polarity + monoclinal LiDAR; CTRA used conductivity curvature + gravity step. None used hinge-trough-dilate conjunction. | **+0.006 to +0.015 holdout vs ADHR bar (0.1879)** via blind-basin precision; **Low cost** (all bands cached, no new download, 8-fold CPU ~6 min) |
| 2 | **H88-STRC — Seismo-Tectonic Relay Coupling** | B16 `ieq_n100a15`, B10 `deq_n100a15`, B4 `geod_2ndinv`, B7/B8 strain, B15 depth | Earthquake cluster proximity residual: `log(1+ieq)` detrended on strain + basement depth; cross-gradient alignment of seismicity halo with strain azimuth identifies creeping relay ramps | Blind seismogenic transfer faults under basins emit microseismic swarms without surface rupture | Quarry blasts & mine-induced seismicity (filter via depth clustering) | Adds seismicity residual vs prior purely geodetic lanes | +0.003 to +0.010 / Low-Medium |
| 3 | **H88-RADI — Radiometric Piedmont Alteration** | `geodawn_rad_u8.tif` (K, Th, U, TC), `geodawn_extensions_u8.tif` (ThK, UK, UTh), B12 det_elev, B15 depth | K/Th potassic alteration + U/Th redox front conditioned on piedmont relief decile, requiring ≥500 m along-strike coherence | Hydrothermal leaching along blind faults under thin fan gravels (<50 cm) leaves K enrichment not seen under thick alluvium | Felsic tuff contacts, U roll-front placers (mitigated via strike coherence filter) | Conditions radiometrics on relief decile, not global threshold | +0.002 to +0.008 / Low |
| 4 | **H88-FLUV — Fluvial Chi-Knickpoint Deflection** | `dem10_chi_100m_i16.tif` (ksn, step), `dem10_chi_100m_u8.tif` (knick_n), `topo_10m_derived` (slope) | Signed cross-divide χ asymmetry paired with ksn reversal; transverse knickpoint density coherence across catchments | Blind upland faults drive divide migration & knickzones without preserving scarp | Lithologic caprock knickpoints (litho-masked) | Targets signed χ reversal, not raw χ magnitude | +0.002 to +0.006 / Medium |
| 5 | **H88-MAGD — Intra-Magnetic Demag Trough** | B1 mag_anom, B2 rtp, B9 tmi_vg, B14 tmi, B15 depth | Blockwise regression of tmi_vg on tmi regional; residual demag trough + analytic signal isolates magnetite-destructive gouge under volcanic cover | Young basalt cover mutes gravity contrast but hydrothermal alteration destroys magnetite locally | Remanent basalt flow margins, flight-line leveling (mitigated via 10km block detrending) | Blockwise vertical-to-regional residual, not raw tmi_vg | +0.001 to +0.005 / Low, but MRR-BPR already tried similar and was negative → lower rank |

**External-data obtainability gate (before run):** All layers for H88-FLXH are SHA-pinned and present after `python scripts/restore_inputs.py` (full) + `--validation`. No new agency download required; DOE GDR #1391, USGS GeoDAWN, USGS 3DEP mirrors are verified bytes in `data/`. No unobtainable hypothesis was proposed as viable. License: competition bands CC for competition use; GeoDAWN CC0; GDR CC BY 4.0 (attribution in `knowledge/manifest.md`).

---

## Validation Plan for Top Candidate (H88-FLXH)

1. **Leakage canary:** each of 6 FLXH channels tested alone on Seed-20 whole-component hidden positives vs 8× off-trace negatives; symmetric AUC must be ≤0.90 or STOP.
2. **Holdout:** `gems57-pooled-hide-v2` (seeds 20+21, 8 folds, 3 px buffer, pixel-exact mask, 300 m triangular kernel, α=0.2 β=0.8, 1000 block-bootstrap draws, 20 km blocks) on 22,893 withheld positives; report pooled DTI + 95% CI + far (>10 px, n=10,791) + blind (>25 px, n=3,117).
3. **Uniqueness:** spearman |ρ| ≤0.90 pre-placement surface and final dots; like-for-like 3-px forward overlap ≤0.70 vs all 238 registry rasters (sparse dot_fields) via `vendor/gems57/uniqueness.py`; literal 1.0 vs 17GEMSDOE reported as diagnostic only.
4. **Fingerprint:** share_le2=0, share_gt25≥35%, median d_cat.
5. **Format:** 1 band float32 EPSG:32611 3730×3292, exact sample transform, nodata=None, all 12,279,160 cells finite in [0,1] {0,1} binary, 0 outside footprint, 0 on catalogue, LZW striped, byte-identical ZIP, two-decoders parity.

