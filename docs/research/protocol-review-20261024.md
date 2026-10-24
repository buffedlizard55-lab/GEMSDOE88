# Protocol review — 2026-10-24

## Executive decision

**Existing MDPS-88 TIFF: download for research YES; submit NO. No new TIFF generated.**
This session is a protocol/validation repair, not another geological lane experiment.
The requested single method paragraph is absent. More importantly, the mandatory
literal overlap rule precludes every nonempty in-footprint candidate with the current
registry. Silently excluding dense rasters would change the user's rule.

The automated audit restores pinned sample, catalogue and registry inputs, verifies
hashes and grid alignment, and reads actual raster bytes. The registered dense witness
has positive finite values at **every footprint pixel**. Consequently each allowed dot
is at distance zero from that prior: forward overlap is exactly one, exceeding the
specified limit. This is a preplacement feasibility proof, not a sampled correlation
estimate. The existing MDPS-88 dots independently reproduce that overlap using the
shared `uniqueness.dot_overlap`. See [machine run card](../data/literal_protocol_audit.json).
One witness suffices to reject; it does not certify completeness of the registry.

IR-88-86 corrects the shared template's `binding_duplicate_decision_v3` for all callers.
Chance-corrected overlap remains diagnostic, but cannot override the literal decision.
Missing/nonfinite measurements stop rather than promote. No private evaluator or writer
was introduced. Historical results are not retroactively rescored. MDPS run cards and
site claims now explicitly flag the literal duplicate; earlier v3 metrics are retained.

## Why H33 might have improved — and what cannot be established

The supplied H33 result and competing leaderboard figures are **unverified user-reported
claims**, not ORGANIZER-CONFIRMED scores. They conflict about the current leader and have
no authenticated submission receipt available here. They must not become training targets
or promised performance. No claim of a better leaderboard result is justified.

The stored H33 forensic audit documents a subset lineage: ridge predictions, dotted
thinning, then removal of predictions close to the known catalogue. Its files and hashes
are in `evidence/h33_forensics_20261024.json`; the validation restore obtained the pinned
lineage rasters again. This review did not rerun that full forensic experiment.

Mechanistically, a distance-tolerant kernel can reward geographical coverage more than
redundant nearby predictions. Thinning can reduce false-positive cost while retaining
truth coverage. Removing near-catalogue predictions can also reduce costs **if** those
predictions receive little hidden-truth credit. This is a plausible explanation, not proof
that every removed dot was a false positive. Earlier language asserting 'pure denominator
reduction', knowing where hidden faults live, or inferring the hidden truth size is too
strong: unknown labels and several changed operations prevent causal identification.
A zero-versus-NaN encoding can affect format acceptance, but is not evidence of superior
geology. Predicting geothermal-resource-indicative faults is not direct vent detection.

Higher performance is possible in principle, but must be demonstrated with fold-fair
hide-and-recover tests and eventually an organizer receipt. Do not compare a fixed shipped
H33 raster against a freshly trained fold model as if that were a fair model comparison:
H33's all-catalogue collar can already suppress the very withheld faults being scored.
The entire baseline construction must be repeated from visible faults per fold.

## Ranked prospective geological hypotheses — NOT IMPLEMENTED OR VALIDATED

These are conditional research proposals using layer types already described by this
repo, not a claim of novelty across every sibling repository. Ranking is qualitative
potential versus cost, not a projected score. No new external source is required in the
design, but full feature-cache restoration/provenance checks remain prerequisites.
Only validation inputs were restored in this session. The universal duplicate blocker
stops all candidates before field construction; do not interpret this table as viability
or authorization to spend a slot.

| Priority | Proposed test and exact layer types | Physical signature / missing-fault rationale | Difference to inspected implementations | Non-fault mimic | Cost / expected evidence value |
|---|---|---|---|---|---|
| A | Conditional magnetic-edge survival: GeoDAWN `rtp`, `tmi_hg`, `tmi_vg`; `iso_grav_anom_vg`; `det_elev` | Trace magnetic derivative zero-crossings through scale, testing persistence specifically across a low-relief gravity-defined basin margin. Seek buried structure without requiring a scarp or catalogue proximity. | MRR tests orientation/coherence and PHASE tests cross-gradient disagreement; this proposal tests conditional survival across a terrain boundary, rather than their scalar fusion. Exact novelty still needs a fleet audit. | Buried volcanic contact | Medium; highest qualitative priority for falsifying the surface-topography bias hypothesis, improvement unknown |
| B | Within-lithology radiometric discontinuity: cached K/Th radiometric indices plus RTP texture and elevation | First stratify by label-blind magnetic texture, then test local radiometric residual jumps within strata. Could reduce lithologic-contact confounding in buried alteration corridors. | KTH uses antisymmetric ratio steps; this explicitly conditions residuals on host texture. Quantized indices cannot be treated as measured elemental concentrations. | Pedogenic redistribution and transported alluvium | Medium; uncertain, given negative KTH evidence |
| C | Drainage-polarity replication: cached DEM-derived chi/ksn, slope, LiDAR scarp orientation | Require multiple adjacent catchments to show consistent signed knickzone offsets across a shared axis, with terrain-matched negative controls. Could capture subtle offset traces missed by coarse catalogue mapping. | Existing chi/scarp features are local scores; the proposed unit is agreement among separate catchments. Must check feature resolution permits a catchment-level test. | Lake Lahontan shorelines or a resistant bed | High; lower priority because drainage reorganization is strongly confounded |

Before any implementation: clarify the lane and resolve the literal registry policy,
freeze one hypothesis, use the existing cached feature stack, test every feature alone
on held-out segments, and stop on suspicious symmetric AUC. Rebuild all catalogue-based
features from visible faults. Use the shared whole-segment buffered evaluator, pooled DTI,
paired segment-level uncertainty and a same-split current best. No best-of-many tuning on
the final holdout; reserve a fresh spatial audit split after accumulated experiments.

## Evidence and access inventory

| Source | Role | Status this session |
|---|---|---|
| [Official reference repository, pinned README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | Organizer baseline setup and hardware guidance | Retrieved through GitHub API; archived in `knowledge/official-reference-README-20261024.md`. It explicitly supports CPU-only operation: a GPU is faster, not universally required. |
| [Official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Target, metric and submission requirements | Manual reference link; not freshly verified here. Network allowlist excludes this host. |
| [Official data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Authoritative competition downloads | Not accessed; no DrivenData session. Restored owner mirrors are hash-pinned, not a new organizer download or a licensing verification. |
| [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Eligibility, deadline and slot policy | Not fetched: host outside network allowlist. Do not infer current weekly balance. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Potential-field/radiometric provenance | Reference only; not freshly retrieved. No new external dataset declared obtainable. |
| [GDR 1391](https://gdr.openei.org/submissions/1391) | Geothermal context | Reference only; not freshly retrieved or used as new training data. |
| [INGENIOUS](https://gbcge.org/current-projects/ingenious/) | Regional geological context | Reference only; not freshly retrieved. |

No official receipt, live leaderboard, external paper, or portal rule was invented.
Outbound hosts are limited to GitHub and package registries. The provided Dropbox and
other official-source hosts cannot be fetched from this environment. Contrary to the
old prompt, data placement is not the single remaining blocker: literal uniqueness,
scientific validation, current rules/slot evidence and source-use permissions also matter.

## Three review passes and continuation

1. **Implement/verify:** restore hash-pinned validation inputs; prove the universal
   blocker; reopen TIFF and ZIP using the shared format validator; correct current claims.
2. **Review/fix:** repair the shared v3 policy exception; test dense and sparse duplicates,
   empty/error/nonfinite measurements and exact thresholds; bind MDPS validation to
   pinned inputs instead of trusting a mutable `ok_to_submit` field.
3. **Recheck:** run the unified tests, site-link audit and expected-negative CLIs; include
   both audit and MDPS validation in CI and Pages deployment. Test counts and remote
   outcomes are recorded in the PR/final report, not asserted in advance here.

Next session: read README/PROMPT first. Do not silently alter the registry policy. If a
revised policy is explicitly authorized, amend the shared protocol and rerun all gates;
then select one lane and fairly retrain the incumbent on identical splits. Keep the
current research download and negative run card accessible. Promotion and actual portal
submission remain separate steps. **Maximize P(Win): reject unsupported candidates.
Own the Outcome: fix misleading safety claims rather than manufacture another TIFF.**

Final local verification: unified suite **306 passed, 23 skipped** (data-dependent
legacy tests; not full retraining), with rasterio deprecation warnings. All five
`--require-submit` commands for the new audit, MDPS, PHASE, canonical current release,
and historical release return the expected blocked exit code. Site links pass.
Final replay exposed a stale `docs/status.json`: regenerated it from the canonical
PHASE producer; the latest MDPS panel uses its own named validation file. Historical
root run cards containing promote/receipt claims remain archival and must not be used
as current slot authorization. This review did not verify those old receipt claims.
