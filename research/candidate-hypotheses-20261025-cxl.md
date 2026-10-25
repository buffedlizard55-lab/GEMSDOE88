# Candidate hypotheses — 2026-10-25 — Lane H88-CXL (chosen)

All numbers labelled HOLDOUT-DTI (evaluator `gems57-pooled-hide-v2`, α=0.2, β=0.8, 300 m triangular)
or ORGANIZER-CONFIRMED / USER-REPORTED. H33 0.2778 is USER-REPORTED (no portal receipt in repo);
its owner build file's 0.2747 is a projection, never a score.

## Why H33 (0.2778, USER-REPORTED) plausibly scored highest in-family (PhD forensic summary)
Reproduced lineage forensics in this repo (`scripts/forensics_h33.py`, prior dossiers) show the
H33/H19-5/H28 family is a *dotted-ridge* emitter: ~37,654 binary dots, ~41.7% of dots >25 px from the
catalogue, median d_cat ≈19.6 px, near-zero dots ≤2 px from catalogue, ≥~2.8 px dot spacing. Under the
official DTI (α=0.2 penalises FP lightly, β=0.8 penalises FN heavily, 300 m triangular cover credit),
a sparse dot field placed on a *continuous surface that ranks concealed-fault corridors above basin
background* harvests partial cover credit on hidden faults while paying little FP cost. Dense/continuous
rasters and catalogue-hugging rasters score far lower in-family (0.00–0.16). Conclusion: score is driven
by (surface ranking quality far from catalogue) × (dot budget/spacing/basin-share fingerprint), not by
any single transform. Beating 0.2778 therefore requires a *better far-from-catalogue ranking surface*
at the same fingerprint — which is exactly what a new, independent feature family can add. No claim is
made that 0.2778's mechanism is proven; it remains USER-REPORTED without a receipt.

## Ranked candidates (expected HOLDOUT-DTI gain vs implementation cost)

1. **H88-CXL — Monogenic phase-congruency / phase-symmetry tensor (CHOSEN).**
   Layers: training_features band 2 (RTP), band 13 (isostatic gravity anomaly), band 12 (detrended DEM).
   Signature: multi-scale (wavelengths 5/11/23 px) monogenic signal via Riesz transform — per-scale
   log local-energy, phase-symmetry (step) response, cross-scale phase-congruency proxy
   Σeven/ΣE, and orientation coherence |Σ E·e^{2iθ}|/ΣE; plus cross-field min/product of PC proxy.
   Why it catches *uncatalogued* faults: phase congruency is contrast/illumination-invariant — a
   low-amplitude basement step under thick cover (blind fault, no scarp, weak gradient) still has
   congruent phase across scales, whereas gradient/Hessian stacks (all prior lanes: physics-44, HGVC-20,
   edge, cross-gradient) rank it below high-amplitude lithologic edges. Phase symmetry specifically
   fires on *step* (fault-like) rather than *ridge* (dike/flow-like) structure.
   Difference from repo: no prior module uses FFT/Riesz monogenic phase, phase symmetry, or
   cross-scale phase coherence (grep-verified 2026-10-25: `phase`, `riesz`, `monogenic` absent from src/).
   Cost: one FFT per field, disk memmap; reuses cached physics-44 + HGVC-20 + vendor evaluator.
   Mimic (named non-fault process): lithologic contacts / volcanic flow fronts also produce phase-
   congruent steps — discriminated only jointly with HGVC hydrothermal channels in the PoE.

2. **Shoreline-datum warping residual.** Layers: band 12 DEM + pluvial shoreline penalty channel.
   Signature: residual of mapped Lahontan shoreline elevation from a planar datum = Quaternary fault
   warping. Why uncatalogued: shorelines are horizontal datums; warping records faults with no scarp
   expression. Cost: high — needs a shoreline polyline layer not in the pinned inputs; no free official
   shoreline-elevation dataset verified obtainable in-session. NOT VIABLE this session (named blocker).

3. **Along-strike spring pair-correlation (Ripley-K anisotropy).** Layers: GDR well/spring CSV already
   pinned. Signature: anisotropic pair-correlation of geothermometer-disequilibrium points at 1–4 km
   lag along regional NNW strike. Why: aligned spring clusters betray concealed feeders. Cost: low,
   but HGVC already splats these points at 6/8 px; incremental independence questionable. Backup.

4. **Depth-to-basement curvature (zbase second derivative).** Partly inside HGVC
   (`hgvc_zbase_slope_decouple`, antithetic step) — not independent. Rejected as lane-drift.

5. **InSAR coherence lineaments.** No InSAR layer in pinned inputs; Sentinel-1 is free (Copernicus)
   but processing exceeds session budget/hardware (3 GB RAM). Named source: Copernicus Data Space
   (https://dataspace.copernicus.eu). NOT VIABLE this session.

## Frozen lane
CXL-26 zero-catalogue channels + physics-44 + HGVC-20, distance-adaptive log-odds PoE
(HGVC Exp03 architecture with CXL added to both specialists), H33-parity allocation
(37,654 dots, d_cat>2.5 px, share_gt25≥0.35). Stop rules (parallel-run protocol): surface or final-dot
rank correlation >0.90 vs any registry raster, or >70% dots within 3 px of one registry raster
(like-for-like sparse rasters; the dense 17GEMSDOE space-filling witness is reported separately as in
all prior lanes — literal 1.0 against it is a property of every non-empty raster, disclosed, and the
verdict is fail-closed if any *sparse* blocker trips). Promotion requires candidate HOLDOUT-DTI >
HGVC stored 0.202947 on the identical evaluator; otherwise verdict=negative, 0 slots spent.
