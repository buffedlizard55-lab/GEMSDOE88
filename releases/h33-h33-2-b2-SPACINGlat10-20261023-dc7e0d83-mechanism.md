# Mechanism card — h33-h33-2-b2-SPACINGlat10-20261023-dc7e0d83  (AXIS = SPACING, structural-geologist audience)

**Parent:** `h33-h33-2-b2` (h33-h33-2-b2, 37,654 dots; exact rebuild verified against both SHA-256 pins, registry/r0_verification.json).
**Mode:** lattice re-spacing of 3,765 dots (10.00% of parent).
**Mandatory collar relocation:** 2,171 R0 dots at 2 < d_cat <= 3 px moved beyond 3 px (brief hard constraint #4 for non-PRUNE axes).
**Crowded-dot relocation:** 1,594 dots by nearest-neighbour rank among dots already at d_cat > 3 px.

## Hypothesis
Dots spaced closer than the ~300 m triangular DTI kernel share kernel credit (overlapping credit cones) and inflate the S - M denominator term without adding true-cover credit. Re-spacing the most crowded R0 dots apart at strictly matched count tests whether dot self-interference suppresses live DTI on unmapped (off-catalogue) faults; lattice, Poisson-disk and along-strike re-placement are three null-spacings that isolate pure spacing from ranking or support changes.

## Mechanism
DTI = T / (0.2 T + 0.2 (S - M) + 0.8 |G|) with T the triangular-kernel credit (R = 300 m = 3 px). A dot beyond 3 px from the masked catalogue earns full line credit against new-fault truth; two dots within ~6 px of each other partially contest the same truth pixels, so M is shared and S still counts both dots. Moving crowded dots to unoccupied support cells beyond the collar keeps S = 37,654 fixed while reducing contested credit. GeoDAWN's 400 m flight-line spacing makes 100-300 m repositioning well within lineament position uncertainty.

## Non-fault mimic
Apparent spacing is also produced by map-digitization generalization, 400 m aeromagnetic/gravity gridding shoulders, and GeoDAWN tie-line corrugation - none of which is fault density. A spacing-only edit cannot create fault evidence; it can only reallocate existing credit.

## Predicted sign and size
MODEL predicted live delta = 0.000 vs R0, range [-0.006, +0.006]: matched count, matched support, matched collar, same seed. Treat |live delta| < 0.01 as no evidence (public chunks only).

## Falsifier
A live delta >= +0.01 or <= -0.01 vs R0, or an SGMC off-catalogue control delta beyond +/-0.005, falsifies the null-spacing hypothesis and shows the placement rule matters at this scale.

## Held constant

- Count: 37654
- Support: H19-5 ridge mask (121,131 px)
- Catalogue Collar Px: > 3.0 for every dot
- Seed: 20261023
- Window Px: +/-6
- Min Dot Spacing Px: 2.0

**Report-only diagnostics:** SGMC off-catalogue DTI 0.0968 (R0 0.0961); block-density CV 12 km 0.5587 (R0 0.5590); holdout-DTI degenerate at 0.0 (IR-88-20).

**Artifact:** `releases/h33-h33-2-b2-SPACINGlat10-20261023-dc7e0d83.tif` (NaN outside) / `...-zeros.tif` (fallback); SHA-256 dc7e0d835353601b9912f8e26e5f7a61083e33773c6eeecd60dbeb2f4b5a016f; format receipt `releases/h33-h33-2-b2-SPACINGlat10-20261023-dc7e0d83.json`; gate summary `registry/spacing_validation.json`.
