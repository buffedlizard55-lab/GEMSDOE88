# H88-SSA ranked hypotheses (2026-10-25)

Official sources: [DrivenData GEMS overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [EPSG:32611](https://epsg.io/32611), [Tversky index](https://en.wikipedia.org/wiki/Tversky_index), [DOE GDR 1391](https://gdr.openei.org/submissions/1391).

## Why H33 0.2778 is high (user-reported, not ORGANIZER-CONFIRMED)

H33 thins a ridge prior (H19-5 / D2.8 family) by dropping near-catalogue flank mass. That raises precision under the 300 m triangular kernel used by the public DTI (α=0.2, β=0.8). The public leaderboard high fetched in this project is **0.4413**, not 0.2778. Beating 0.2778 on the portal is unproven without a receipt. Local HOLDOUT-DTI on catalogue-collared rasters is often structurally ~0 because withheld truth sits on mapped traces.

## Ranked untried hypotheses (this session)

| Rank | ID | Layers | Signature | Why off-catalogue | Mimic | Cost |
| 1 executed | H88-SSA | RTP, TMI-HG, iso_grav_hg, depth_to_base, DEM, cond_surf | 300 m structure-tensor 2θ circular resultant | Crustal feeders align strike through cover | Tilted dip-slope / batholith contact | Low |
| 2 | CAL-88 | cond_surf, det_elev | Elevation-detrended log-conductivity residual | Range-front smectite without scarp | Playa brine / perched clay | Low (folded into SSA exp3) |
| 3 | CHI-ACROSS | dem10 χ, ksn | Signed cross-divide χ step | Blind piedmont drainage reversal | Lithologic knickpoints | Medium; 10 m 3DEP blocked |
| 4 | H88-INSAR | COMET LiCSAR | Strain-rate curvature hinge | Blind basin floor | Seasonal aquifer | External, sandbox-blocked |
| 5 | TIR-SI | Landsat C2 ST | Nighttime TIR residual | Warm seepage | Basalt talus | External, sandbox-blocked |

## Executed result

HOLDOUT-DTI 0.0000 (gems57-pooled-hide-v2, 22641 withheld). Canary max 0.5608. Like-for-like overlap 0.2883. Literal dense 1.0. Verdict **negative**. Download yes. Submit **no**.
