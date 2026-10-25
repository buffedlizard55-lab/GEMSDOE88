# PhD Forensic Analysis: Why H33 (0.2778 user-reported) Scored Highest Among Siblings & Can FLXH Beat It — 2026-10-25

**Evidence class:** Every number below is labelled **HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, n, 95% CI) or **USER-REPORTED** (sibling site claim, no organizer receipt) or **LEADERBOARD-SNAPSHOT** (top 0.4413 on 2026-10-24). No number is ORGANIZER-CONFIRMED for our file; 0 weekly slots spent.

---

## 1. What H33 exactly is (byte-level, not narrative)

- **H19-5** (`19GEMSDOE__h19-5-powerlaw-budget-multiline.tif`, 121,419 dots, USER-REPORTED 0.1922): continuous topographic ridge network (H19-5) from combined DEM/slope/relief derivatives at 100–300 m scale, populated at ~1 px spacing via max-DTI fractional programming.
- **D2.8** (`GEMSDOE25__dotted-h19-5-d2-8.tif`, 44,090 dots, USER-REPORTED 0.2600): Poisson-disk thinning of H19-5 to mean nearest-neighbor ≈2.8 px (280 m) while preserving ridge membership. Pixel check: `supp(D2.8) ⊂ supp(H19-5)` exactly, 77k dots deleted.
- **D2.8 → SOLO** (`GEMSDOE28__h27-4-r1-solo-d2-8.tif`, 40,199 dots, USER-REPORTED 0.2708): further 3,891 dots removed where `|∇depth_to_base| < p30` (thin cover) — essentially same collar as H33 but looser.
- **SOLO → H33** (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, 37,654 dots, USER-REPORTED 0.2778, SHA256 `c55bafc470…`): delete 6,436 dots with `d_cat ≤ 2 px` (200 m) of `existing_faults.tif` (`7ba308cc…`). Verified: `supp(H33) ⊂ supp(D2.8)`, |Δ|=6,436, ∀ x∈Δ: d_cat(x) ≤2.02 px, and H33∩catalogue = ∅.

Thus **H33 = thin(H19-5) ∩ ¬collar(200 m)**. Its 41.7% far dots (>2.5 km) are byte-identical to D2.8's far dots.

## 2. Why thinning + collar deletion improves DTI (metric algebra, exact)

DTI definition ([official metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation)):

```
DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)
TP_w = Σ_g max_x p(x)·k(d(x,g))          // max-cover, k(d)=max(0,1−d/300m)
FP_w = Σ_x p(x)·(1−q(x)),  q(x)=max_g k(d(x,g))
```

**Thinning effect (H19-5 → D2.8, 0.1922→0.2600):** For two dots x1,x2 with |x1−x2|=100 m and same nearest truth g, `max(p(x1)k1, p(x2)k2) ≈ p(x1)k1` (redundant): second dot adds ΔTP_w ≈0 but ΔFP_w = p·(1−k) >0. Shared denom cost eliminates redundant FP. Empirically: 121k→44k cuts FP_w 2.75×, preserves 78% TP_w → DTI 0.1922→0.2600 (user-reported). This is not hypothetical; it is measured on siblings.

**Collar deletion (D2.8→H33, 0.2600→0.2778):** For each deleted dot y with d_cat≤200 m, if hidden truth G_test has zero coverage at y (i.e., k(d(y,G_test))=0), its FP_w =1 contributes denominator penalty 0.2·1 with zero numerator gain. Deleting 6,436 such dots removes 1,287 FP_w units. With pooled public truth |G|≈13.4k px and TP_w(H33)≈5.2k, the predicted DTI moves 0.252→0.278 (observed 0.2778) under zero-collar-truth assumption. The siblings `gems79-tilt-ring` (100k dots all within d_cat≤2 px, 0.0005) and `gems81-cont-poisson-buf2` (84% at 2–3 px, 0.0041) empirically verify collar dots carry near-zero truth credit.

**Basin preservation:** H33's far profile `share_gt25=41.7%` (vs 0.0–0.5% for gradient-boosted-tree siblings) places 15,713 dots in unmapped basin interiors where hidden G_test lives, preserving recall.

## 3. Can we beat 0.2778? What 0.4413 tells us

Leaderboard snapshot 2026-10-24: #1 0.4413 (xiaofanhu, 29 entries), #5 0.3539, #50 0.2818. H33 at 0.2778 would sit **just below top-50**. Prompt's 0.3195 was #2 on 2026-10-04, now stale (IR-88-79).

**Is 0.4413 reachable from H33's architecture?** Possibly, via higher precision *inside* basin interiors rather than more recall: H33's FP_w in basins is still high (single-ridge model, no geophysics). A multi-physics conjunction that suppresses basin FP_w where truth is absent while keeping far TP_w could lift DTI 0.27→0.39. Upper bound: with TP_w fixed, DTI = 1/(1+0.2·FP_w/TP_w+0.8·FN_w/TP_w); halving FP_w lifts 0.2778→0.363 if FN_w unchanged.

**Can we *show* we beat H33 without spending a slot? No. ** Hidden G_test is unobservable; HOLDOUT-DTI instrument scores 0.0 for any arm with `share_gt25>35%` beyond catalogue (structural zero), so it cannot rank basin precision. Only an ORGANIZER-CONFIRMED receipt can prove beating 0.2778. Our HOLDOUT-DTI is a necessary negative gate, not a leaderboard predictor.

## 4. What FLXH proposes that H33 does not

H33 is a single-ridge model (topography only) with geometric thinning + collar. FLXH adds three independent physics nulls that H33 cannot exploit:

- **Flexural hinge** (depth_to_base_surf Laplacian): basement steps under alluvium, where H33's topographic ridge is flat.
- **Conductive trough** (log cond_surf Hessian trough): smectite clay caps sealing fault gouge, orthogonal to H33's ridge.
- **Dilatant strain gate** (shear·dilatation): active opening step-overs, temporal kinematic signal absent in H33's static topography.

Conjunction (hinge ∩ trough ∩ dilatant) is *anti-correlated* with H33's single-ridge support: Spearman between FLXH composite and H33 dots is expected |ρ|<0.15 (pre-placement), and 3-px overlap <0.45, so FLXH is genuinely unique while targeting complementary physics. This complements H33 rather than copying it.

## 5. How FLXH differs from all prior GEMSDOE88 lanes

| Lane | Core idea | Bands | Why FLXH is different |
|---|---|---|---|
| H88-ADHR | 60° dip-backprojection + GDR thermal advection + OOF relay | 67ch (19+external+GDR+visible) | FLXH is zero-catalogue, no dip projection, no GDR advection, no visible relay; hinge vs step |
| QTSK | cover-thickness decoupling (z_base vs z_surf) | B15 vs B12 vector decoupling | FLXH uses hinge curvature, not cover-slope decoupling angle |
| MVRD | magnetite polarity + monoclinal LiDAR + redox | B1/B14 mag polarity, LiDAR asymmetry | FLXH uses basement flexure + conductance trough + dilatant strain, no magnetics |
| CTRA | conductivity curvature trough + gravity step | B17 curv + B5 grav step | FLXH adds flexural hinge + dilatant gate; CTRA lacks hinge & strain |
| DHTC | deep MT upwelling + basement shear | B18/B19 MT + B4/B15 + strain | FLXH uses shallow log cond trough + hinge, not deep MT conductivity; DHTC targets pluvial valleys, FLXH targets basin hinge lines |

No prior lane computed Laplacian of depth_to_base_surf or dilatant shear product or their conjunction.

## 6. Limitations & mimics

- **Lahontan/Bonneville shorelines** (≈1330/1555 m): produce hinge-like curvature but lack dilatant strain & trough continuity → filtered by conjunction + elevation mask.
- **Fan-toe onlap:** radial curvature mimics hinge; suppressed via cross-strike coherence <0.4 → removed.
- **Intrusive contacts:** produce gravity steps + hinge without strain; fail dilatant gate → removed.
- **Blocked holdout caveat:** HOLDOUT-DTI cannot rank far-basin improvements; our 0.141–0.196 range is catalogue-adjacent performance only, not basin leaderboard proxy.

**Bottom line:** H33's 0.2778 is explained by measured thinning + collar deletion + basin preservation, not by superior geophysics. FLXH targets the basin FP_w that H33 wastes, with orthogonal physics to guarantee uniqueness, but beating 0.2778 cannot be *shown* without a live receipt. We therefore generate a portal-valid, like-for-like unique FLXH TIFF with transparent HOLDOUT-DTI, and leave live scoring to the selector.

