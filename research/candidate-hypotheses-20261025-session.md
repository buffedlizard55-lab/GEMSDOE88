# GEMSDOE88 — session 2026-10-25: ranked, unvalidated hypotheses

Status: **pre-implementation proposals only**. None was fitted, scored, or submitted this session. The binding pre-placement gate (`scripts/preflight_mtas88.py --gate-generation`) returned `DUPLICATE_STOP` (exit 2): the SHA-pinned `17GEMSDOE` witness covers all 5,106,385 allowed pixels, so every nonempty candidate dot set has forward 3 px overlap 1.0 > 0.70 and must stop before feature construction, holdout, placement, or writing. These hypotheses are therefore queued for a future session that holds a separately authorized protocol revision clearing the registry gate.

Method lane (kept): shared cached feature stack, buffered whole-segment hide-and-recover holdout, visible-faults-only catalogue features, pixel-exact visible-fault masking, pooled DTI alpha 0.2 / beta 0.8 / 300 m triangular kernel; every feature's leakage canary (single-feature AUC <= 0.90) before any score is trusted; no private forks of `vendor/gems57/evaluate_holdout.py`, `holdout.py`, or `submission_writer.py`.

Competition context (claims, not organizer receipts unless noted): GEMSDOE32 `h33-h33-2-b2-...-zeros` user-reported 0.2778 (no organizer receipt; H33 geometry audited as a subset/pruning of D2.8, not proven causal); repo all-time holdout record H88-BPWD HOLDOUT-DTI 0.205991 [0.188105, 0.223344]; leaderboard highs cited in the user prompt (0.4413, 0.3195) are not verifiable from this unauthenticated sandbox. A projection is never written as a score.

---

## H1 — Radiometric alteration + curvature concordance (priority 1; low cost)

- **Layers:** USGS GeoDAWN airborne radiometrics (equivalent Th, K, U from the survey grid) + 10 m DEM-derived curvature/openness (already cached in the feature stack; no new external data).
- **Physical signature:** fault-controlled hydrothermal alteration produces potassium enrichment and clay (Th/K response) co-located with scarp curvature/openness along concealed or splayed structures. Joint occurrence is the discovery signal; either layer alone is weak.
- **Why it catches catalogue-missing faults:** alteration halos and subtle scarps exist on unmapped splays and blind segments that have no USGS/INGENIOUS trace; the catalogue supplies context only (visible faults masked exactly), so a concordance hotspot away from catalogue traces indicates a missing structure.
- **Difference from repo:** existing lanes (BPWD gravity-admittance, HGVC sinter/up-dip, MTAS cross-scale gravity/RTP) target geophysical edges; no lane joins radiometric chemistry with curvature concordance on visible-only features. Distinct from H33-style "remove near-catalogue dots" precision tuning.
- **Leakage canary:** single-feature AUC of radiometric-only and curvature-only rasters on the holdout; AUC > 0.90 = leakage until proven otherwise.
- **Expected DTI improvement:** modest (+0.005 to +0.015 over incumbent, unproven); **implementation cost:** low (cached bands, shared evaluator).
- **External data:** none beyond pinned GeoDAWN/3DEP mirrors already restored.

## H2 — Multi-aspect lineament density from DEM curvature (priority 2; low cost)

- **Layers:** 1 m / 10 m DEM (3DEP) curvature in four cardinal aspect bins (N, E, S, W) plus plan/profile curvature.
- **Physical signature:** conjugate and transtensional fault sets generate linear curvature anomalies aligned perpendicular to strike; density of aspect-consistent anomalies in directions *not* parallel to mapped catalogue faults highlights undiscovered cross-faults and relay structures.
- **Why it catches catalogue-missing faults:** catalogue traces reflect mapped, dominantly strike-parallel faults; cross-cutting splay and relay faults of different aspect are systematically absent. Lineament density measures the fabric, not the trace.
- **Difference from repo:** scarp-relief/openness lanes use a fixed scale aligned to mapped scarps; multi-aspect lineament density is direction-agnostic about catalogue orientation and has not been implemented in `src/gems88/*`.
- **Leakage canary:** single-feature AUC per aspect bin; the maximum bin must pass <= 0.90 or the feature is rejected.
- **Expected DTI improvement:** modest (+0.005 to +0.012); **implementation cost:** low (DEM cached).
- **External data:** none beyond pinned 3DEP mirror.

## H3 — Contemporary geodetic strain concentration (priority 3; medium cost; external data required)

- **Layers:** geodetic strain-rate / velocity-gradient field (e.g., UNR Nevada Geodetic Lab GPS strain or NGVDS/GPS-derived strain), intersected with basin-cover and heat-flow priors.
- **Physical signature:** active transtension concentrates strain on blind or concealed structures; strain-rate ridges coinciding with low cover and elevated heat flow indicate a live conduit rather than a fossil trace.
- **Why it catches catalogue-missing faults:** it targets *present-day* deformation, so it finds structures that have not yet breached the surface enough to be mapped — the most catalogue-missing class.
- **Difference from repo:** no lane uses geodetic strain; all existing lanes are geologic/geophysical static layers.
- **Leakage canary:** strain raster alone on holdout; AUC <= 0.90 required.
- **Expected DTI improvement:** uncertain (+0.00 to +0.02); **implementation cost:** medium.
- **External data:** UNR Nevada Geodetic Lab strain products (free, official). **Obtainability from this sandbox:** NOT CHECKABLE — outbound network is limited to github.com / pypi.org; USGS/unr.edu downloads are not reachable here. Name the source, mark deferred pending network/policy approval.

## H4 — Thermal-vegetation proxy from Landsat Collection 2 LST + NDVI anomaly (priority 4; medium cost; external data required)

- **Layers:** Landsat Collection 2 Level-2 land-surface temperature (LST) and NDVI anomaly over the AOI; DEM aspect/slope to remove topographic thermal bias.
- **Physical signature:** concealed fault conduits produce subtle ground-temperature anomalies and phreatophytic vegetation stress (cool/wet or dry depending on setting) aligned with structure after removing aspect-driven insolation effects.
- **Why it catches catalogue-missing faults:** blind faults with surface expression only as subtle thermal/vegetative lines are invisible to trace-based catalogues.
- **Difference from repo:** no lane uses satellite thermal or vegetation data; distinct from all geophysical and structural lanes.
- **Leakage canary:** bias-corrected LST anomaly raster alone; AUC <= 0.90 required.
- **Expected DTI improvement:** uncertain (+0.00 to +0.015); **implementation cost:** medium.
- **External data:** USGS Landsat Collection 2 Level-2 (free, official; EarthExplorer or the public Landsat on AWS bucket `landsat-pds`). **Obtainability from this sandbox:** NOT CHECKABLE — same network limit as H3. Deferred pending approval.

## H5 — Cross-scale magnetic admittance residual (reserve; low cost)

- **Layers:** GeoDAWN aeromagnetic RTP at two spatial scales (short vs long wavelength) demagnetization contrast, conditioned on magnetics/cover.
- **Physical signature:** a buried fault juxtaposes magnetic and demagnetized rock; the difference-of-scales residual isolates narrow edges missed by broad-scale RTP interpretation.
- **Why it catches catalogue-missing faults:** demagnetization halos along concealed faults have no mapped trace.
- **Difference from repo:** closely related to the MTAS lane (gravity/RTP cross-scale) but on magnetics; would duplicate MTAS-like structure unless differentiated by band choice. Ranked last to avoid lane drift.
- **Leakage canary:** residual raster alone; AUC <= 0.90 required.
- **Expected DTI improvement:** low-to-modest; **implementation cost:** low.
- **External data:** none beyond pinned GeoDAWN mirror.

---

## Ranking (expected DTI improvement vs implementation cost)

| Rank | Hypothesis | Expected DTI gain | Cost | External data? | Gate before scoring |
|------|------------|-------------------|------|----------------|---------------------|
| 1 | H1 radiometric + curvature concordance | modest | low | no | canary + holdout vs incumbent |
| 2 | H2 multi-aspect lineament density | modest | low | no | canary + holdout vs incumbent |
| 3 | H3 geodetic strain concentration | uncertain | medium | yes (UNR NGVDS, deferred) | canary + holdout vs incumbent |
| 4 | H4 Landsat LST/NDVI thermal proxy | uncertain | medium | yes (USGS Landsat C2 L2, deferred) | canary + holdout vs incumbent |
| 5 | H5 cross-scale magnetic admittance | low-to-modest | low | no | canary + lane-drift check vs MTAS |

**Session rule:** validate H1 (then H2) on the spatially-blocked holdout *before* any weekly submission slot. No candidate that has not beaten the incumbent holdout (H88-BPWD 0.205991) may touch a slot. Any candidate failing its leakage canary (AUC > 0.90) is rejected as leakage, not promoted.
