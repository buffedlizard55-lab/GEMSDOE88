# Three new geological hypotheses (session 2026-10-22)

All labelled HOLDOUT-DTI or REGISTRY-MEASUREMENT; no projection sold as score.

## H-A — DEM-curvature / buried-valley edge (TOP RANK, LOW COST)
- Layers: raw band 9 (elevation, ~1355 m reference) + existing RTP gradient (band 2/3-feature cache)
- Physical signature: sharp 2nd-derivative curvature break in DEM coincident with magnetic-gradient sign-flip (log_rtp_edge > median, curvature < -threshold)
- Why off-catalogue: surface maps miss buried fault-controlled valleys under basin cover; curvature is independent of mapped trace
- Named mimic: glacial trough, erosional channel
- Cost: uses existing feature stack + simple curvature filter; no external data needed
- Difference from MGC-88: MGC uses RTP/gravity *joint*; this targets topography-only breaks with magnetic confirmation, not co-edge product

## H-B — Residual-gravity / depth-corrected low-density zone (MID RANK, MED COST)
- Layers: raw band 13 (iso_grav_anom) + band 15 (depth_to_base_surf)
- Physical signature: isostatic-gravity anomaly after subtracting basin-depth linear trend; linear lows > 2σ and length > 300 m
- Why off-catalogue: fault gouge reduces density; surface traces disappear under sediment
- Named mimic: volcanic caldera depression, sedimentary basin margin
- Cost: requires new depth-corrected residual computation; external source not needed (both layers in feature stack)
- Difference from MGC-88: MGC uses raw gravity edge; this uses *residual after depth correction* which can reveal buried structures masked by basin fill

## H-C — Radiometric K/Th corridor / alteration halo (LOWEST RANK, HIGH COST / DATA UNCERTAINTY)
- Layers: raw band 11 (radiometric K-like, range -2.5 to 262) + band 14 (Th-like, 179-253)
- Physical signature: K/Th ratio > 1.5 along elongated corridors > 200 m with low DEM curvature (indicating buried, not surface) conduit
- Why off-catalogue: hydrothermal alteration halos extend beyond mapped fault traces
- Named mimic: agricultural fertilizer strip, natural soil variation
- Cost: requires verification of true K/Th band semantics from official feature descriptor (not fully confirmed); if bands are mis-identified, feature collapses
- Difference from MGC-88: MGC uses magnetic/gravity only; this introduces radiometric alteration signatures, independent geochemical mechanism
- External verification needed: official feature-band descriptor from organizer mirror (accessible via `data/bridge/gems-geodawn-numerical-features.tif` tags) — obtainable, not yet inspected

## Ranking by expected DTI improvement vs cost
1. H-A (best cost/benefit; independent mechanism; no new data)
2. H-B (plausible but closer to MGC mechanism; requires careful residual computation)
3. H-C (high potential but highest uncertainty; band semantics unverified in this session; must not claim result without verified source)

## Protocol compliance
- Lane: H-A stays inside own method (curvature + RTP sign-flip) and is checked against registry before placement (rho < 0.90, support overlap logged; universal overlap blocker documented, not hidden)
- Reuse: uses `evaluate_holdout.py` v2 (gems57-pooled-hide-v2) and `submission_writer.py` without private metric forks
- Budget: 2 experiments used in this session (existing MGC-88 negative + H-A new); 1 remaining if needed; 2-hour cap respected
- Leakage canary: each feature tested alone; AUC > 0.90 → stop; expected < 0.60 for H-A given physical independence from catalogue
