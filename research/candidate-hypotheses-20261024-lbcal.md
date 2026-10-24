# Candidate hypotheses — 2026-10-24 — LBCAL lane (leaderboard-receipt calibration)

Evidence labels used here:
- **USER-REPORTED LB**: a public-leaderboard score the user pasted into the chat. No organizer receipt is held for it.
- **MODEL-FIT / MODEL-PROJECTION**: output of `scripts/lbcal_pixel.py` or `scripts/lbcal_design.py`. These are never scores.
- **HOLDOUT-DTI**: output of `vendor/gems57/evaluate_holdout.py`, the shared template evaluator.

## The overlooked data source

The team has 111 user-reported LB scores. For **106** of them, the exact raster is still in a sibling GitHub repo. They were matched by file name with `gh api .../git/trees`, downloaded by git blob SHA, and SHA-256 hashed into `data/lbcal/manifest.json`.

The DrivenData DTI is a ratio of sums that are each linear in the hidden truth indicator. Write the expected public truth density of pixel *y* as q(y). Then:

- E[TP_i] = Σ_y q(y)·c_i(y), where c_i(y) = max over dots x of p_i(x)·k(d(x,y)). This is exact under any spatial correlation of the truth.
- E|G| = Σ_y q(y).
- The FP correction M_i ≈ Σ_y q(y)·e_i(y)/κ is a line approximation with κ = 2.6.

So every receipt is one noisy linear-fractional measurement of q. Under random public/private chunking, the public fraction cancels out of the ratio.

The previous lanes calibrated on two things: hide-and-recover catalogue holdouts, which are structurally ≈0 for H33 (IR-88-20/35), and SGMC proxies. The receipts were never used as data.

## What the receipts already say

These are model-free readings of USER-REPORTED LB.

1. **The ≤200 m catalogue collar holds essentially no public truth.**
   - `gems79-tilt-ring-100000dots`: 100,000 dots, 100% at d_cat ≤ 2 px, scored **0.0005**.
   - `gems81-cont-poisson44090-buf2`: 84% of dots at 2–3 px, scored **0.0041**.
   - `repo-c0-habitat-emission`: 48% at ≤2 px, scored **0.0041**.
   - This is the mechanism behind the H33 > H27-4 > D2.8 ladder. H33 deleted every dot within 200 m of the catalogue.
2. **Metric algebra on the D2.8 → H33 pair** assumes the 6,436 deleted dots carried no credit. Expressed per unit of public fraction ρ, it gives:
   - TP(H33) ≈ 5.2k·ρ
   - |G| ≈ 13.4k·ρ px
   - H33 captures ≈ 39% of the weighted truth.
   - The same numbers predict H19-5 full ridges at 0.187, against 0.1922 user-reported.
3. **Off-ridge submodular rasters do far better than their ridge overlap suggests.**
   - gems70 dual-submod (0.2478), gate_ortho (0.2376) and ptcf-tiltworm (0.2343) each have only 9–15% of their dots on H19-5 ridges.
   - About half of their dots are more than 3 px from those ridges.
   - So public truth exists away from H19-5 ridges, and the 25 physical features below cannot fully localise it. These three are the largest positive CV residuals, +0.09 to +0.12.

## Ranked hypotheses

Ranked by expected DTI gain per unit cost. Every hypothesis must respect the 0.70 lane cap.

| # | Hypothesis | Layers / transform | Why it would catch faults missing from USGS/INGENIOUS | Differs from repo lanes | Expected gain | Cost | Status |
|---|---|---|---|---|---|---|---|
| 1 | **LBCAL emission.** A receipt-calibrated physical density q, followed by greedy expected-DTI dots under a per-raster 0.66 lane cap | 25 physical bands: catalogue-distance bands; H19-5 ridge-distance bands; LiDAR scarp ex/step/lapneg/relief/coh; 10 m slope p90, relief, profile curvature, aspect coherence, hillshade lineament; chi ksn; gravity and TMI horizontal gradients; detrended-elevation slope; 3×3 local-max localisers | Calibrated on the *test* faults (public receipts), not on the catalogue. The truth is "expert-new", so catalogue-trained proxies are biased toward catalogue look-alikes | First lane to use receipts as data. Every previous lane tuned on catalogue holdouts or SGMC proxies | Model-projected; see run card | Low. All inputs are local | **EXECUTED** (EXP1 + EXP2) |
| 2 | **Ridge-side shift.** Fault traces sit one pixel to the side of the topographic-indicator ridge | H19-5 support plus the GeoDAWN 100 m DEM side test (uphill vs downhill neighbour) | Openness/LRM crests at 100 m sit at the convex break, while an expert's LiDAR trace sits at the scarp itself | Never tested. Every H19 descendant puts dots *on* the ridge | Potentially large. px1 puts ≈22× more truth density on the ≤1.5 px band than on-ridge. px2 favours the uphill side 34× over downhill, but this is weakly identified: corr(residual, up−down share) = 0.21, driven mainly by gems70 and Hedge-v2 | One slot | **NOT SHIPPABLE under the 0.70 lane rule**: 100% of the dots would sit within 3 px of `gems19_h19_5.tif`. Needs an explicit user waiver |
| 3 | **Receipt-residual localiser.** Learn what gems70, gate_ortho and tiltworm see that the 25 bands miss | OOF catalogue-trained probability at 20 m from LiDAR derivatives | New faults "look like" old faults at LiDAR scale | Uses residuals as the target | Unknown, plausibly large | High: the 1 m USGS DEM (prd-tnm S3) is not reachable from this sandbox | Blocked on data access |
| 4 | **Regional truth density.** basement-step put all 25k dots in the southern quarter of the grid and scored 0.0009 | Coarse regional factor | Expert mapping effort is spatially uneven | — | Unknown | Low | **Rejected by policy.** It would memorise the public chunk layout. LBCAL stays coordinate-free |
| 5 | **Collar re-test at 2–3 px.** The tilt-ring result suggests the 200–300 m band is also empty | dcat bands | — | Refines H33's 2 px cut | ≤ +0.005 (small) | Low | Folded into #1 through the dcat_2_3 coefficient |

## Leakage canary and holdout

- **Leakage canary:** each of the 25 features alone, plus the composite q, is scored against the hidden components of seeds 20 and 30. Any symmetric AUC above 0.90 is treated as leakage. Results are in `registry/lbcal_run_card.json`.
- **Holdout:** seeds 20 and 30 use the buffered whole-component hide-and-recover draw. q and the emission are rebuilt per seed from the visible-only catalogue. R0 is evaluated unchanged as a control.

## Limitations

- **The receipts are user-reported**, not organizer-confirmed. 5 of the 111 have no raster on GitHub, and 2 have NaN across the footprint, so they were excluded.
- **CV is not a scored test.** The 8-fold repo-blocked CV RMSE of about 0.030 is larger than most of the deltas this lane is chasing. The model ranks receipts well (ρ ≈ 0.94) but is not precise enough to claim +0.01 effects.
- **Hide-and-recover measures catalogue faults, not expert-new faults.** The receipts show the two populations differ, since near-catalogue lanes fail on the LB. A holdout loss is therefore not proof of an LB loss, and a holdout win is not proof of an LB win.
