# Official source audit — 2026-10-25

This file records only pages fetched or repository refs/hash-checked on 2026-10-25 UTC. A source link is not evidence that competition data bytes were authenticated or that a submission was accepted.

## DrivenData competition #306

- **Problem, data, metric and submission format:** <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
  - The page states that the target is geological faults indicative of geothermal resources.
  - It describes a 100 m projected UTM zone 11N feature GeoTIFF (EPSG:32611), a single-band float32 prediction raster, values between 0 and 1, and a 300 m triangular distance kernel.
  - It states that the hidden test faults were expert-labelled new faults not in the existing public USGS database, and that final-round labels are expanded by expert review.
  - It says the competition provides `training_features.tif`, labels, and `1m_DEM_links.csv` through the data page. It does **not** make an unauthenticated mirror in this repository an organizer-authenticated download.
- **Leaderboard:** <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> — fetched 2026-10-25; the page displayed xiaofanhu at **0.4413**. This is `OBSERVED-PUBLIC` snapshot evidence, not a GEMSDOE88 score, a private score, or an organizer receipt for any local file.
- **Data page:** <https://www.drivendata.org/competitions/306/competition-doe-gems/data/> — manual review link; authenticated access remains a project limitation in this sandbox.

## Official rules and reference implementation

- **NLR official rules:** <https://docs.nlr.gov/docs/fy26osti/96647.pdf> — fetched 2026-10-25, September 2026 edition. Sections 3.2–3.5 say competitors submit a single 100 m GeoTIFF, may submit multiple files subject to the website's limit, and must select one submission for both prize rounds. The rules also say generative-AI use must be disclosed and that competitors remain responsible for accuracy and authorship. The project has spent zero slots and has no portal receipt.
- **Reference solution:** <https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b> — the commit was obtained from the public Git repository; its README directs competitors to download data from the competition site and documents CPU-only and GPU setup paths.

## Official science/data context

- **USGS GeoDAWN:** <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> — fetched 2026-10-25. The landing page describes the magnetic/radiometric survey, coordinated lidar, survey areas and flight specifications, processing, included deliverables, DOI `10.5066/P93LGLVQ`, and CC0 1.0 rights.
- **DOE GDR INGENIOUS:** <https://gdr.openei.org/submissions/1391> — fetched 2026-10-25. The page identifies the regional compilation and DOI `10.15121/1881483`, links a CC BY 4.0 license, and lists geophysical, seismic, geodetic, thermal, well/spring and fault resources. Component-level derivative/licensing review remains required before sharing new products.
- **CRS authority:** <https://epsg.io/32611> — fetched 2026-10-25. EPSG identifies 32611 as WGS 84 / UTM zone 11N with metre units. The competition sample grid's exact affine transform and shape are checked separately from this CRS definition.

## Local evidence boundaries

- `data/bridge/sample_submission.tif`, `data/bridge/existing_faults.tif`, and `data/registry/dense_17gemdoe.tif` are restored from SHA-256-pinned public owner mirrors. Their hashes and grid metadata are recorded by `scripts/review_repo_20261025.py`.
- `H33 = 0.2778` is retained as `USER-REPORTED CLAIM — NOT HOLDOUT-DTI AND NOT ORGANIZER-CONFIRMED`; no DrivenData receipt is present.
- The literal duplicate stop is a local registry measurement: the dense witness covers every allowed cell, so every nonempty allowed candidate has forward 3-pixel overlap 1.0. It is not a leaderboard score and not a claim about the organizer's hidden labels.
- The downloadable H88-TDKL TIFF passes local format/range checks only and is marked `DO-NOT-SUBMIT`. No new MTAS TIFF was created because the pre-placement proof fires first.
