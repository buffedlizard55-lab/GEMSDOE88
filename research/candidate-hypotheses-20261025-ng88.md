# NG88 — Relay-Ramp Dilation-Jog, Volcanic-Vent Corridor & Depth-Decoupled Basement Step (H88-NG88)

**Lane H88-NG88** — *NG88: Geothermal-Permeable Fault Intersections, Relay-Ramps & Shallow-Basement Steps*. Read with [PROMPT.md](../PROMPT.md) · [README gate](README.md) · [Executive submission guide](../docs/executive-summary.html).

Official sources (verified 2026-10-25, manual review):

- Competition problem / format / 300 m triangular weighting: [DrivenData 306 page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- Competition about / data policy: [DrivenData page 968](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- Competition leaderboard (public, live): [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- Official rules (one 100 m GeoTIFF, ≤3/week, one final for both rounds): [NLR PDF §3.2–§3.5](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- Reference solution (CPU+GPU env, obtain data from competition page): [drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- GeoDAWN magnetic/radiometric survey (USGS, CC0): [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- INGENIOUS Great Basin compilation (GDR #1391, DOI 10.15121/1881483, CC BY 4.0): [GDR 1391](https://gdr.openei.org/submissions/1391)
- GBCGE INGENIOUS project: [gbcge.org/ingenious](https://gbcge.org/current-projects/ingenious/)
- CRS EPSG:32611 (WGS 84 / UTM 11N, metre): [epsg.io/32611](https://epsg.io/32611)
- Tversky index (DTI family): [Wikipedia Tversky](https://en.wikipedia.org/wiki/Tversky_index)
- 3DEP LiDAR/DEM: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- Fault interaction / relay-ramp geothermal control: Faulds et al., *Geothermal favorability of structural settings, Great Basin* (2015) — [GRC Transactions](https://www.geothermal-library.org/index.php?mode=pubs&action=view&record=1033567); Peacock & Sanderson, *Relay ramps and accommodation zones* (J Struct Geol 1994); Curewitz & Karson, *Fault intersection permeability* (JGR 1997)

## Why H33 0.2778 rose (PhD forensics, HOLDOUT-DTI vs ORGANIZER-CONFIRMED)

**Label every number.** `0.2778` is **USER-REPORTED / OWNER-CLAIM** from [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, SHA `c55bafc...`). It is **not** `ORGANIZER-CONFIRMED` (no DrivenData receipt in this repo). The public leaderboard snapshot 2026-10-24 shows `#1 xiaofanhu = 0.4413` — that is a *different* competitor's public DTI, not this file's score.

Recomputed on disk (registry measurement, not causal proof):

- Lineage nesting: `H19-5 (121,131 px, CLAIM 0.1922) ⊃ D2.8 (44,090 px, CLAIM 0.2600) ⊃ SOLO-D2.8 (40,199 px, CLAIM 0.2708) ⊃ H33 (37,654 px, CLAIM 0.2778)`.
- H33 removes exactly **6,436 px, all ≤2.0 px from `existing_faults.tif`** (`1.00` of removed dots within 2 px). No new geography is added.
- Geometry: `median d_cat = 19.65 px`, `share_gt25 = 42.9%`, `share_gt30 = 35.8%`, `min_nn = 2.828 px = sqrt(8)` (kernel-matched de-redundancy).

**Mechanism under DTI (α=0.2, β=0.8, 300 m = 3 px triangular).** With a dot field `P` of `n` binary dots:

```
T = Σ_{g∈G} max_{x∈P} k(d(x,g))          (truth-side coverage, saturates at 1 per truth cell)
M = Σ_{x∈P} max_{g∈G} k(d(x,g))          (dot-side self-credit, saturates at 1 per dot)
FP_w = n - M      FN_w = |G| - T
DTI = T / (T + α·(T + n - M) + β·|G|)   (exact; T≠M in clustered fields)
```

β=0.8 dominates recall cost, but α=0.2 still punishes *redundant* clustered dots (M≪n → large FP_w) while a well-spaced field (M≈n) pays almost no FP_w except its precision term α·(T+n-M). A dot within ≤2 px of a mapped trace is almost never within 3 px of a *hidden* geothermal fault that was deliberately withheld >12 px from the scored domain (holdout design), and on the live board it duplicates mapped geology rather than discovering new permeability. Removing those 6,436 catalogue-collar dots therefore **cuts FP_w by ≈6,400·(1-⟨k⟩) while losing T≈0** (they covered no withheld truth cell not already covered by a neighbouring kept dot). The greedy kernel increment `dDTI>0 ⇔ dT > α·DTI·(dT+1-k)` (metric.py) correctly stops adding dots when marginal `k < α·DTI` for non-redundant dots — H33's thinning implements exactly that bar.

**Can we beat 0.2778?** Holdout 8-fold record `H88-HGVC = 0.202947 [0.185869,0.219790]` (22,893 withheld, 8/8 folds won, far 0.1328, blind 0.0790, `gems57-pooled-hide-v2`) proves a *hydrothermal* filter (quartz/chalcedony disequilibrium, sinter/tufa separation, 1→2 m probe gradient) beats pure-structural ADHR by `+0.0081 [+0.0032,+0.0128]` on catalogue-proxy truth. Whether that proxy *generalizes* to live off-catalogue geothermal faults cannot be shown without an organizer receipt — no GEMSDOE88 file has one. NG88 tests the next geothermal control: **extensional relay-ramp jogs + fault-intersection + vent + shallow-basement step** (Faulds 2015), which the current registry has not combined as one tensor. It is viable (uses only restored pinned inputs) and differs from every implemented lane.

## Ranked 5 new hypotheses (before computation)

| Rank | ID | Layers (pinned) | Physical signature ; why off-catalogue fault could respond | Named non-fault mimic & falsification | Differs from this repo | Expected DTI gain / cost |
|---|---|---|---|---|---|---|
| **1 selected** | **H88-NG88** | `existing_faults.tif` intersections, `trace_segments_utm11.csv` strike, `training_features.tif` B8 dilaterate + B7 shear + B13 iso_grav + B15 depth_to_base + B5 slope, `gdr_volcanic_vents_in_footprint.csv`, `dem10_chi_100m_i16.tif` | **Relay-ramp dilation tensor**: intersection density `I = fault-junction count / km²` (3×3 junction mask) × positive dilation `max(0, dilaterate)` × `|shear|` (transtensional opening), gated by shallow basement (`depth_to_base < 400 m` residual) and vent proximity `exp(-d_vent/2km)`, with mapped-scarp veto (`det_elev_slope` high → down-weight). Targets dilational jogs where overlapping fault segments create transient permeability even without surface scarp (Peacock & Sanderson relay model). | Unfaulted lithologic contact with gravity step but no dilation; alluvial-fan toe (shallow basement + low slope but no junction). Test via holdout far>25 px lift; random-junction permutation null. | No lane combines **junction × dilation × vent × shallow-basement** as one product. HGVC uses hydrochemistry; MVRD/ADHR use monoclinal strand orientation; BCSF is elastic Okada; PHASE is mag/grav angular discordance. | **Highest / low-medium** — uses only restored 19-band + 2 CSVs + DEM chi; 4 km Gaussian residual already cached. |
| 2 | H88-AR88 | `topo_10m_derived_100m_u8.tif` B1 slope_p90 B3 relief B7 aspect_coh, `lidar_scarp_features_u8.tif` B6/B7 polarity, `geodawn_rad_u8.tif` | **Alluvial-fan apex conduit**: convex fan curvature + low radiometric K/Th (alteration leach) + bajada polarity, where blind piedmont fault feeds apex channel. | Mojave-type fan apex without fault (climate fan). Null: fan apex off-junction vs on-junction DTI. | SHORE-HINGE masks shorelines; ADHR projects 60° dip; not fan-apex curvature. | Medium / medium |
| 3 | H88-SM88 | `training_features.tif` B13 iso_grav + B2 rtp + B15 depth, `geodawn_rad_u8.tif` | **Depth-conditioned mag-demag trough**: `trough = |∇rtp|·exp(-|r_grav|²/2σ²) / (depth_to_base+ε)`, hydrothermal demag on shallow basement step. | Non-magnetic tuff step. | MTAS is scale-difference admittance; KTH is antisymmetric mag trough alone. | Medium / low-medium |
| 4 | H88-CT88 | `training_features.tif` B17 cond_surf, `gdr_wellspring_in_footprint.csv` temp, `2m_temperature_probe` | **Conductivity-temperature joint residual**: `resid = z(cond)·z(temp_grad) - ρ·z(depth)`, conductive geothermal aquifer vs saline playa. | Saline playa brine (cond high, temp low) → residual negative. | DHTC is deep MT + shear; not shallow probe-conditioned residual. | Medium / medium |
| 5 | H88-VI88 | `gdr_volcanic_vents_in_footprint.csv` + fault strike | **Vent-alignment corridor**: kernel vent density anisotropic along fault strike (`σ_par=2km, σ_perp=0.5km`), Nakamura dike-vent control. | Random vent cluster off-fault. | No prior lane uses vent anisotropy; HGVC uses vent proximity isotropic. | Low-medium / low |

## H88-NG88 lane paragraph (single method, stays inside it)

**H88-NG88.** Build strictly from hash-pinned inputs: compute fault-junction mask `J = (existing_faults>0) ∧ (3×3 neighbour sum ≥4)` (5943 junctions on full grid; recompute per-fold from `visible` for holdout, full catalogue for final emission), distance-transform `d_J` and kernel `exp(-d_J/800m)`, transtensional opening `o = max(0,dilaterate)·|shearrate|` (B8·|B7|), shallow-basement gate `b = 1/(1+exp((depth-400)/80))` (B15), vent gate `v = exp(-d_vent/2000)` from 21 vents, iso-gravity residual `g = |∇iso_grav|` (B18), scarp veto `s = 1 - norm(det_elev_slope)` (B19). Tensor `S = J_ker · (0.6·norm(o)+0.4·norm(g)) · (0.5+0.5·b) · (0.5+0.5·v) · s`. Greedy Dinkelbach emission (α=0.2,β=0.8,R=3px) to 37,654 dots: 21,500 near-ribbon (2.5<d_cat≤25 px, ≥2.85 px spacing) + 16,154 blind (>25 px, ≥3.05 px spacing), 3 px catalogue collar, 0 on catalogue, footprint-clipped. Leakage canary per-feature AUC ≤0.90; holdout `gems57-pooled-hide-v2` 8-fold (seeds 20+21, 3-px visible buffer, pixel-exact mask, pooled DTI); like-for-like uniqueness `|ρ|≤0.90` and 3-px overlap `≤0.70` vs 326 dot-field rasters (dense continuous rasters exempt from dot-overlap, rank-correlation still checked); portal `zeros` mode ([0,1] all-finite, single float32 band, EPSG:32611, 3730×3292, exact transform, LZW 1-row strip, `nodata=None`, 0 outside footprint).

No dense-prior exemption silence — dense `17GEMSDOE` exempt *only* for dot-overlap (it is a continuous probability raster, not a dot set) but remains in Spearman surface check; rationale logged openly as bug-fix `IR-88-121`.

## Budget

Max 3 experiments or 2 h. Promotion to weekly slot is separate selector step (≤3/week).

## Limitations needing external free source check

- S2TIR (Landsat/ECOSTRESS pre-dawn TIR seepage) needs EarthExplorer / LP DAAC (free, official, but sandbox allowlist blocks `earthexplorer.usgs.gov` / `appeears.earthdatacloud.nasa.gov`; verified blocked 2026-10-24).
- IRIS SPUD 3D MT (H88-MT3D) needs IRIS DMC (free, `ds.iris.edu`; not in allowlist).

Neither is used in NG88.
