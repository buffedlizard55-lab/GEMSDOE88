# Session f34477d2 — reproducible review, 2026-10-26

## Decision

**No new submission TIFF. DO NOT SUBMIT the archived downloads.** The existing
[executive guide](../docs/executive-summary.html) and
[nine-site audit](../docs/data/focus_sites_20261026.csv) remain the entry points.
This session restored SHA-pinned validation inputs from GitHub owner mirrors,
installed the constrained CPU environment in a virtualenv, and reran the shared
generation guard. This is mirror provenance, not authenticated organizer data.

The fresh guard exits 2: the pinned dense 17GEMSDOE raster directly covers all
5,106,385 allowed pixels. Every nonempty candidate therefore has forward support
overlap 1.0, above the user's 0.70 threshold. This proves infeasibility under the
literal rule before constructing a surface. No ranking can overcome that proof;
no empty, renamed, metadata-only, or random perturbation TIFF is a solution.
The missing single-method paragraph is another ambiguity, not permission to
select a competing parallel lane. No experiments or weekly slots were used.

## Site comparison and H33 interpretation

The existing nine-site table identifies the highest *user-reported* historical
candidate for each site, including GEMSDOE28's rung30 candidate rather than its
slightly lower SOLO candidate. None is presently protocol-cleared. The CSV and
byte-audit JSON contain the exact candidate identities; they were not freshly
recomputed for all nine remote repositories in this session.

H33's reported 0.2778 is neither an organizer receipt nor the current overall
leaderboard maximum. The prompt also supplies incompatible maxima (0.3195 and
0.4413); neither was independently verified here. Archived raster forensics
show thinning and catalogue-collar changes in the H19-5 → D2.8 → SOLO → H33
lineage. Reducing redundant predicted mass while retaining proximity to held-out
faults can improve a precision/recall metric. This is a plausible explanation,
**not causal proof** of the reported improvement or evidence of new geothermal
vents. Fault recovery and vent discovery are different targets. We cannot infer
that a new model will exceed any public score from those historical numbers.

## Ranked conditional research queue (before implementation)

These are the existing source-reviewed unimplemented variants in
[the queue](../registry/hypothesis_queue.json), not claims of fleet-wide novelty.
Rank describes qualitative potential; no projected DTI score is assigned.

| Rank / hypothesis | Specific cached layers and signature | Why potentially off-catalogue / distinct method | Mimic / cost |
|---|---|---|---|
| 1 H88-SPR | Elevation/slope, topo B8–9, LiDAR step/coherence/strike/valid, channel density/validity; held-out cross-strike smooth-profile vs signed-step restoration | Repeated weak piedmont offsets without catalogue seeds; unlike existing scarp response thresholds, requires out-of-profile predictive improvement | Terrace risers and pluvial shoreline benches; medium |
| 2 H88-AWA | Quantized GeoDAWN K/Th/U, RTP, depth-to-base and slope; terrain-matched relative flank decay widths | Asymmetric alteration context without an exposed trace; fitted width rather than existing enrichment/edge levels | Weathering contrasts and transported K-rich alluvium; medium |
| 3 H88-CBC | Elevation, gravity anomaly, depth-to-base, conductivity and drainage cache; narrow cross-basin connectivity vs smooth basin-fill null | Potential buried boundary breach; connectivity test rather than another conductivity-high threshold | Saline paleochannels and clay-rich basin fill; medium–high |

Cached inputs are enough in principle, but only validation-tier inputs were
restored here; full feature pins must be checked before implementation. No new
external layer is represented as obtainable or usable. After a valid shared
protocol change, top-candidate evaluation must use buffered whole-fault hiding,
visible-only catalogue features and pixel-exact visible masks, per-feature AUC
canaries, shared pooled DTI and block-bootstrap CI, and a same-fold incumbent.
Do not transplant a historical best number across incompatible folds.

## Scientific correction: previous PTGM proposal

The prior session-c59db412 hypothesis document called Gaussian smoothing
"upward continuation" and interpreted log-scale derivative amplitude as a
structural index. These are **not established identities**. For planar harmonic
potential fields, physical upward continuation has Fourier multiplier
`exp(-|k| h)`; a Gaussian blur has `exp(-sigma^2 |k|^2 / 2)` (angular spatial
frequency convention). These operators have different transfer functions.
A scale slope of a blurred gradient is not generally an Euler structural index:
source depth, geometry, interference and filtering affect it. The prior fixed
index intervals, offset distances, timings and fleet-wide novelty claim are
untested assumptions, not verified physical laws or measured performance.
PTGM must not be implemented as a calibrated structural-index estimator from
that formula. This correction does not alter any historical TIFF or evaluator.

## Source and access ledger

- [Organizer reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution): official repository link; no fresh full source audit claimed here.
- [Pinned dense witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif): owner mirror; freshly restored and hash-checked by shared preflight.
- [DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/): manual-review links, not retrieved this session; outside outbound allowlist.
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) and [GDR 1391](https://gdr.openei.org/submissions/1391): official discovery links, not freshly retrieved or license-verified here. No new data availability assertion.

## Three passes and remaining work

1. Read standing contract, recorded prompt, current release and queue; restore
   validation inputs; rerun guard. Preserve negative outcome, do not generate.
2. Review scientific assumptions and evidence labels; correct the PTGM operator
   interpretation above; distinguish historical evidence from fresh checks.
3. Run full tests and normal/optimized site guards plus canonical-render check;
   record exact outcomes in the session card. Preserve existing site decision.

Remaining: resolve the *protocol* incompatibility for dense continuous registry
rasters explicitly, without silently exempting any raster; assign one lane;
restore full cached features; run same-fold improvement and uniqueness gates
only when generation is authorized. Organizer receipts, account quota and data
licenses need an allowed authenticated workflow. A local format pass never
establishes high leaderboard performance. No human TIFF inspection substitutes
for these machine gates. Existing prompt copies and README embed remain intact.

Final verification: initial full suite returned **919 passed, 23 skipped, 4
failed**, all caused by editing the root hypothesis document without its Pages
mirror while tests were running. Synchronized both copies and corrected the
cross-site link; all **23 tests in the affected modules pass** on rerun. Normal
and optimized site checks and canonical render check pass. Download audit:
**50/50** published research TIFFs pass, **0** eligible. Current validator exits
0 for research format; its slot gate exits **2**. Full suite was not repeated
after the mirror fix; no claim of a fresh all-green full run is made.
