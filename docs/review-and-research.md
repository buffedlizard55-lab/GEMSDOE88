# GEMSDOE88 repository review and research notes

**Review date:** 2026-10-22 (UTC)
**Scope:** local checkout plus public GitHub API metadata/content from the named GEMSDOE32 repository for forensic learning. No raster was downloaded or copied.
**Disposition:** negative / blocked; no experiment and no submission build.

## 1. What was actually present

Local inspection found only `README.md` (initially 11 bytes), with a single heading. Git tree at the starting commit also contained only that file. There are no scripts, tests, feature cache, input data, TIFFs, registry raster collection, holdout evaluator, writer, or site pages. Python environment also has no NumPy, Rasterio, or pytest installed. Thus claims that a project pipeline is ready, that competition data has been placed, or that a new raster can be scientifically validated do not describe this checkout.

The remote public repository `buffedlizard55-lab/GEMSDOE32` is a prior project, not this template. Its tree includes an H33 audit record and code/evidence. I read its JSON through GitHub's API for analysis only. I did not copy or use its TIFF as this project's submission.

## 2. Forensic answer about the claimed high-scoring H33 artifact

The supplied prompt calls `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` the top GEMSDOE32 submission. The accessible GEMSDOE32 audit file describes the artifact as a catalogue-flank prune of an earlier owner-reported base: remove every positive pixel at catalogue distance <= 2 pixels, leaving 37,654 positives and zero pixels on the catalogue. It records an output range [0,1], EPSG:32611, a 3730-by-3292 grid, and no organizer receipt. The same audit reports a **model projection**, not an observed score, while the submission build record explicitly says that no organizer score exists for that artifact. Those are prior-repository statements, not measurements made in this checkout.

**Plausible mechanism, not proven causation:** where known catalogue pixels are excluded from scoring, removing predictions adjacent to known mapped traces can eliminate predictions that are unlikely to receive credit for the *unmapped* target, while preserving selected sparse off-catalogue positions. With alpha=0.2 and beta=0.8, the metric penalizes false-positive mass less heavily than missed truth, but a candidate still gains only if the added/preserved positions collect enough weighted proximity credit. This pruning may improve the score when deleted dots are mostly low-credit false positives and retained dots remain near withheld faults. It can also hurt if the missing faults parallel or continue mapped traces. A sparse binary support is compatible with that mechanism; the metadata alone cannot prove the actual unseen fault locations or why any live score occurred.

**Irregularity to resolve:** the prompt's reported leaderboard numbers conflict with one another and with GEMSDOE32's own record: its audit has a null receipt and calls the score a projection, not an organizer-confirmed result. Therefore this memo does not adopt the prompt's claimed high score as verified. Check the competition leaderboard as-of a stated UTC time and the submission-page receipt that binds exact bytes/hash to a score. Do not infer a score from a project website, owner log, model projection, or “slot eligible” tag.

**Conclusion:** We cannot truthfully claim that a new raster will exceed the cited score. There is no local data, holdout evaluator, raster to compare, or confirmed baseline. The only responsible outcome is no candidate/no submission until the blockers below are cleared.

## 3. Candidate hypotheses (screening queue only; none is viable or validated yet)

The table satisfies pre-registration planning, not evidence of novelty. It is a *provisional* novelty screen against the user-provided method names and the accessible GEMSDOE32 documents. No local registry rasters are present, and not every prior GEMSDOE site/artifact could be exhaustively compared. Therefore none can be certified as unique; do not place pixels or allocate a submission slot until correlation and dot-overlap gates are run against the actual registry.

| Priority | Hypothesis and layers | Targeted physical signature / missing-fault rationale | Difference from accessible prior methods | Expected DTI upside / cost | External-data status |
|---|---|---|---|---|---|
| 1 | **Shallow-probe thermal-transect anisotropy.** Official INGENIOUS 2 m temperature-probe measurements, spatial locations and values; only after verifying exact fields/coverage. | Detect elongated, spatially coherent shallow-temperature departures or sharp cross-transect gradients, rather than isolated hot sites. A coherent anomaly outside mapped fault lines could indicate blind fluid upflow or a concealed permeable structure not yet mapped at the surface. | Distinct from point-site geothermometer thresholding: use probe-network topology, lineament orientation, and spatial-block-specific background normalization; explicitly exclude known catalogue buffers and known surface vents from the evidence. Related, not asserted wholly unprecedented: prior H33 notes mention an unbuilt probe-data idea. | **Highest** plausible direct relevance; medium-high cost due location/metadata QC and spatially honest calibration. Expected improvement is qualitative only; no score is projected. | Specific official source listed in prior project evidence: [GDR submission 1391](https://gdr.openei.org/submissions/1391), resource name `2m_temperature_probe_INGENIOUS_regional_data.zip`. Prior record says it was absent/not downloaded. Current direct availability, licence, schema, and reachability were **not verified** from this network; not viable until checked. |
| 2 | **Paleothermal sinter/tufa boundary paired with structural edge.** GDR mapped paleo-geothermal feature polygons/points; GeoDAWN magnetic edge layers and DEM derivatives only if present in the authenticated stack. | Boundary/rim morphology or aligned sinter/tufa occurrences may preserve former discharge zones; co-location with a basement/structural edge could focus a blind or reactivated conduit missed by the modern fault catalogue. | Test a *spatially offset, boundary-conditioned* association, not a plain proximity-to-geothermal-sites or magnetic/radiometric fusion. Must guard against site-selection/catalogue leakage. | Medium upside, medium-high cost; strong risk that mapped palaeofeatures are sparse or spatially biased. | Specific source: [GDR submission 1391](https://gdr.openei.org/submissions/1391), prior record names `paleo_geothermal_regional.zip`. Obtainability/schema were not rechecked; not viable yet. |
| 3 | **Fault-controlled radiometric disequilibrium at magnetic edges.** GeoDAWN U/Th/K channels and TMI/vertical-gradient or analytic-signal edge transform, if authenticated training bands expose these inputs. | A coherent radiometric ratio/contrast boundary co-located with a magnetic source edge may record hydrothermal alteration or lithologic/structural juxtaposition, including concealed faults. | Use preregistered *edge-to-edge cross-physics coincidence and offset tests*, not generic weighted radiometric fusion, raw magnetic edges, or alteration ranking. This is especially high duplicate risk given prior radiometric and magnetic experiments. | Medium-low expected upside, medium cost; strong confounding by lithology, flight-line artifacts, regolith, and survey calibration. | Survey landing page: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). Data layer/coverage access was not checked here. No claim of availability or novelty. |
| 4 | **DEM curvature lineament persistence conditioned on low surface expression.** Official competition 1 m DEM links, local relief, multi-scale profile/plan curvature and slope. | Repeated, collinear micro-scarps or curvature breaks across scale, with a subdued surface-relief condition, could identify subtle blind-fault expressions while suppressing single-scale noise. | Persistence across independently chosen scales plus an explicit low-relief gate differs from a simple scarp/ridge score; nevertheless prior submissions extensively used DEM/scarp/ridge families, so it is the highest duplicate risk. | Low-to-medium expected upside, medium cost; high nuisance risk from roads, drainage, land-use and DEM seam artifacts. | Competition's `1m_DEM_links.csv` is behind [the authenticated competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/). Data placement/access not verified; not viable until provided. |

**Ranking is a research triage, not a score ranking.** Candidate 1 is the only top-ranked idea to take to source-access verification next. If the probes cannot be retrieved and spatially joined to the held-out footprint, stop; do not replace the absent evidence with synthetic data or claim it is obtainable. Before implementation, inspect the exact feature/cache schema and all submission manifests, then test the pre-placement surface against registry rasters. Any rank correlation >0.90 or >70% of emitted dots within 3 pixels triggers a duplicate/stop result.

## 4. Validation gate and missing assets

No holdout result, confidence interval, withheld-positive count, feature-alone AUC, registry rank correlation, dot overlap, or candidate raster hash can be computed from this checkout. Consequently none is reported as zero. Null means **not measured**, not a negative score.

Needed to proceed:

1. Authenticated competition files: training features, labels, sample submission/template, and the DEM links/authorized data; use the competition page and preserve hashes/licence metadata.
2. Shared project template/cache with the requested `evaluate_holdout.py` and `submission_writer.py` equivalents. The current repository does not contain them; implement/reuse them centrally, not via a private fork.
3. Existing candidate/registry raster inventory and corresponding manifests to perform the required pre/post novelty screen.
4. A dated competition leaderboard snapshot and an organizer submission receipt for any purported live baseline.
5. If candidate 1 is selected, the exact official 2 m probe data, schema, coordinate reference, licence, dates, and coverage; verify it is genuinely usable within the scoring footprint before coding.

After prerequisites: pre-register at most three experiments; run feature-alone leakage checks; withhold whole fault segments with buffers; prevent all catalogue-derived features from using withheld segments; pixel-exactly mask visible faults; compute pooled DTI with the official alpha/beta/kernel; report uncertainty; compare versus current holdout best; run pre/post registry uniqueness; then write a candidate. The format validator added here is necessary but not sufficient.

## 5. Verifiable references

### Official/manual review URLs (provided by the project brief; not fetched in this environment)

- [Competition problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Submission guidance (DOE/NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Reference solution (GitHub)](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GDR/INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391)

### Prior-project evidence reviewed (owner-controlled, not official organizer evidence)

- [GEMSDOE32 H33 artifact audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json)
- [GEMSDOE32 H33 validation record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/evidence/h33_validation.json)
- [GEMSDOE32 submission build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/registry/submission_build.json)
- [GEMSDOE32 public repository](https://github.com/buffedlizard55-lab/GEMSDOE32)

These records contain owner-generated measurements and model projections. They are useful for forensic learning but do not constitute organizer confirmation and were not recomputed here.
