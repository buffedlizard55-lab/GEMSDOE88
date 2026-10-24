# Five candidate hypotheses (2026-10-24, TILTZERO session) — ranked, with lane selection

Scoring context (all labels honest): best shipped de-novo in this repo = PROVCREST
HOLDOUT-DTI 0.076277 [0.067653,0.084607] (gems57-pooled-hide-v2, 22,663 withheld,
registry/provcrest_run_card.json). Historical 0.2778 for h33 is a user-reported CLAIM,
not an organizer receipt in this repo. Leaderboard 0.4413 is a stale unverified snapshot.
Why 0.2778 led historically and why sparse dots win is documented in
docs/research/candidate-hypotheses-20261023.md §1 (300 m triangular kernel: TP takes a
pointwise max within 3 px while FP sums every pixel, so ~37,654 spaced binary dots beat
dense rasters; removing ≤2 px catalogue-collar dots stopped paying FP for mapped faults).

| Rank | Hypothesis | Layers / transform | Why it catches *unmapped* faults | Distinct from repo? | Cost |
|---|---|---|---|---|---|
| 1 (SELECTED) | TILTZERO-CONCORD | B3/B9 magnetic + B18/B11 gravity tilt-angle atan2(vg,hg) zero-crossing closeness × analytic-signal amplitude, geometric-mean percentile surface → directional NMS → 37,654 dots ≥3.5 px, >3 px off catalogue | Tilt zero-crossing overlies a potential-field source edge regardless of whether a mapper traced it; requiring *both* fields to cross zero at the same pixel suppresses single-field lithologic noise; buried basement fault steps have no surface scarp for B19 crest methods | PROVCREST used Hessian crests of B19/3/18/15 gradients; no prior lane used tilt zero-crossings, atan2(vg,hg), or analytic-signal products | Low: 4 provided bands, no downloads |
| 2 | Analytic-signal maxima ( worm ) | B2/B3/B9 analytic-signal amplitude maxima lines | Source-edge maxima over blind contacts | GEMSDOE42/29 tried worm ranking on other supports; not as pure provided-band AS product here | Low |
| 3 | Geodetic transtension gate | B7 shear + B8 dilatation ratio gating B19 crests | Actively extending fault zones | H88-ADHR/STR-88 already used strain features — high overlap risk | Low but lane-drift risk |
| 4 | Seismicity alignment | B10/B16 earthquake density ridges | Creep/seismic blind faults | Used as features in CGO/H88; density is catalogue-adjacent, canary risk | Low |
| 5 | Radiometric K/Th alteration | External GeoDAWN radiometrics (USGS GeoDAWN, https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Hydrothermal K alteration along blind conduits | Rad fusion tried in GEMSDOE46 (0.1589 CLAIM); needs new external download + regridding, unverified in sandbox | High |

Named non-fault mimic for Rank 1: unfaulted volcanic/pluton/sedimentary contacts and
reversed-remanence flow edges (see preregistration_tiltzero.json).
Free official sources if Rank 5 were ever pursued: USGS GeoDAWN page above and DOE GDR
1391 (https://gdr.openei.org/submissions/1391); not needed for Rank 1.
