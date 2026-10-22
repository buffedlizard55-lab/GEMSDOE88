# Scientific review — 2026-10-22

## Scope and evidence discipline
The initial checkout contained only `README.md`. No previous-session tasks or pipeline existed here. A method lane is not specified in the supplied prompt. No geological experiment is authorized under the parallel-run lane rule until that assignment exists. No external data have been silently replaced by an earlier prediction. Hypotheses below are **provisional**, not globally novel claims and not an assigned lane.

Competition predictions concern missing fault traces, not directly geothermal vents. Vent discovery is an application hypothesis; a good fault prediction does not establish a productive geothermal resource.

## Why the reported H33 result might have worked
The downloaded GEMSDOE32 `registry/submission_build.json` describes H33-2-B2 as deleting dots within two pixels of the catalogue from a previously generated emission. Its manifest says that no organizer score existed at build time. The user reports a result of 0.2778; without the submission-page receipt this is **USER-REPORTED, NOT ORGANIZER-CONFIRMED**. Conflicting leaderboard claims in the prompt are likewise not current verified standings.

The shared metric implements TP as the sum, over truth pixels, of maximum distance-weighted prediction support, FP as prediction mass not credited by truth proximity, and FN as missing truth coverage. For fixed truth count G, DTI = T / (T + 0.2 F + 0.8 (G - T)). Redundant dots can add F without increasing T. Removing such dots can improve the objective. Catalogue-adjacent pruning could therefore help if those dots cover little new truth. It could also remove useful undiscovered continuations. An actual causal explanation requires paired evaluation or organizer evidence, not a manifest's projected result. No numerical leaderboard improvement is promised.

The H33 evidence mixes catalogue-hidden evaluation, prevalence calibration, drift correction, and live-anchored projections. Those are not interchangeable with the requested pooled hide-and-recover HOLDOUT-DTI. We deliberately do not import their values as a new baseline. The manifest's ZIP entry claims a tiny archive relative to its TIFF: inspect archive contents before trusting it. No upstream ZIP is published here.

## Ranked provisional hypotheses (qualitative expected benefit / cost)
Ordering is expert prior judgment, **not a measured score**. Physical interpretations remain hypotheses. Required cached band identities and source provenance must be verified before implementation. Features must be catalogue-independent or rebuilt using only each fold's visible catalogue.

| Rank | Hypothesis and layers | Physical signature | Missing-fault rationale | Named mimic | Difference and viability |
|---|---|---|---|---|---|
| A | Cross-contact displacement: magnetic RTP, radiometric K/Th and DEM | Local phase displacement of matched lithologic contacts across narrow linear breaks, rather than contact amplitude | Detects offsets in low-relief areas where no scarp was mapped | Depositional unconformity | Not a generic edge/ridge or catalogue-tip model; absent from this initially empty repo. Best prior benefit, high cost. Needs verified cached bands; not runnable yet. |
| B | Radiometric disequilibrium corridor: K, Th, U and relief | Locally standardized U/Th and K/Th residuals coherent across relief strata | Hydrothermal redistribution could expose buried permeability outside mapped traces | Weathering and groundwater redistribution unrelated to faulting | Ratio residuals, not the already listed radiometric/slope fusion. Moderate benefit, moderate cost. Cached band definitions must confirm all three elements; no new source assumed available. |
| C | Multiscale displacement discontinuity: RTP magnetic and gravity | Disagreement of local phase gradients across scales, excluding simple coincident edges | Offset basement fabric may outlive surface expression | Intrusive contact | Not Euler-depth clustering, tilt-ring, or cross-scale edge persistence. Moderate benefit, high cost. Requires independent gravity coverage in cache, not verified. |
| D | Topographic terrace interruption: DEM and drainage context | Paired terrace-height steps transverse to drainage with a consistent displacement sign | Small displacements can be missed by catalogue mapping | Fluvial incision and anthropogenic embankments | Not generic scarp curvature, Radon, or hydrologic conduit ranking. Lower prior benefit, high cost. Cached DEM resolution may be inadequate; do not propose as runnable without coverage audit. |

No candidate has yet passed the leakage canary or holdout. No claim is made that these ideas have never appeared in the many other repositories. An inventory-wide semantic audit is required before selecting a lane. No experiment was run; synthetic software tests are not experiments.

## Sources and obtainability
| Source | Role | Verification state |
|---|---|---|
| [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | Official implementation starting point | README fetched via GitHub API; snapshot stored in evidence. It requests competition data separately; GPU is faster, not mandatory. |
| [Competition description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Authoritative scoring and format description | Link supplied; direct access unavailable under this sandbox's network allowlist. Not freshly verified. |
| [Data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Official inputs and rules | Direct host unavailable here; no authenticated session used. Do not claim a verified login redirect this session. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Potential official magnetic/radiometric source | Link supplied; availability and download terms not checked here. Not proposed as an immediately obtainable new input. |
| [GDR INGENIOUS](https://gdr.openei.org/submissions/1391) | Potential official geothermal context | Link supplied; not fetched. |
| [NLR report](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | User-provided competition report | Not fetched; no contents attributed to it. |
| [GEMSDOE32 manifest](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/registry/submission_build.json) | Historical method evidence, not organizer receipt | Fetched via GitHub API; snapshot included. |
| [Pinned shared template](https://github.com/buffedlizard55-lab/60GEMSDOE/tree/b99591eede63c6d45c8a896255b8cd34824fa00b/src/gems57) | Reuse evaluator and submission writer without private changes | All package files fetched and SHA-256 recorded. Source comments are inherited claims, not newly verified official facts. |

## Irregularities and remaining work
- No single lane was provided; assigning our own risks violating the explicit parallel protocol.
- Cached feature receipt refers to `/tmp/gems32/work/feature_stack.npy`, not a downloadable object. It is not in this checkout.
- Mirrored data are obtainable through GitHub according to the historical manifest, but hashes authenticate mirror consistency, not organizer origin. The large feature file was not restored because an authorized lane and cache are missing.
- The historical data manifest identifies labels and existing faults as byte-identical. Treat them as catalogue context, never independent new-fault truth.
- Template segments are cut into short chunks according to its docstring. Whether these represent the intended whole geological segments needs auditing before approving holdout. Do not quietly change the shared evaluator locally.
- Registry comparisons must cover both surface and final dots, preserve exact thresholds, and stop as duplicate on a failing comparison. No registry rasters were evaluated here; uniqueness is unknown.
- Baseline, withheld-positive count, paired CI, and all feature-alone AUCs are missing. Null values in the run card mean unmeasured, not zero.
- Next authorized work: resolve lane, obtain immutable cached feature stack and its channel provenance, restore pinned grid/catalogue, audit segment withholding, freeze registry inventory and incumbent, run at most three experiments, and use the shared writer only after scientific gates pass.
- A complete registry and assigned lane are coordination inputs, not human visual inspection. The goal remains automated validation; missing coordination cannot be fabricated.

## Three passes
Pass 1 builds the evidence ledger, unmodified shared tooling, negative run card, static submission guide and gate schema.
Pass 2 tests fail-closed behavior, broken/missing values, hash pins, metric behavior, and local links; fixes found are recorded in the pull request.
Pass 3 checks the original requirements against deliverables. The unique competition TIFF, full spatial validation and leaderboard improvement remain explicitly unmet, rather than being represented by an unsafe download. No competition slot is consumed.
