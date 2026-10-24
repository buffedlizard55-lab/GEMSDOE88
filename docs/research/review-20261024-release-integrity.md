# Release-integrity review — 2026-10-24

## Decision and download

**Research download: YES. Competition submission: NO — DO NOT SUBMIT.**
Use the existing [executive submission guide](../executive-summary.html) for research TIFF/ZIP links, unique names, notes, hashes and gate results. This review generated **no new TIFF**, ran **no new model experiment**, and used **no competition slot**. It does not satisfy the request for a newly generated, submit-approved artifact; doing so would contradict the binding stop rule.

## Three passes

1. **Inspect and reproduce.** Read the README, stored prompt, existing review and release gates. Installed dependencies in an ignored virtual environment. Restored validation-tier reference and registry rasters with `scripts/restore_inputs.py --validation`. `scripts/check_site.py` passed. `scripts/audit_literal_protocol.py` independently reproduced overlap 1.0 against the pinned dense witness: zero allowed pixels escape its support. The baseline suite passed 337 tests with 23 skips. Skips are not passes and do not establish a full-data training rerun.
2. **Fix reliability defects.** The production site guard used `assert`, disabled by Python `-O`. Replaced these with explicit exceptions, preserving the existing checks. Added subprocess regression tests for both normal and optimized Python: corrupted upload permission and unmarked published artifacts must fail; the real site must pass. Also found the TDKL card's free-text summary still started “PROMOTE” despite `verdict=negative` and `ok_to_submit=false`. Preserved it under a historical field, made the current summary explicitly negative in both canonical and Pages copies, and added an enforced consistency check. No historical numerical measurements were changed.
3. **Recheck.** Run the complete test suite, both site-guard interpreter modes and the literal audit with `--require-submit`. Expected audit exit 2 means a completed rejection, not a successful submission. CI now checks optimized Python explicitly. Final execution counts are recorded in the PR and session run card.

## Scientific answer: H33

The [stored H33 forensic measurements](../../evidence/h33_forensics_20261024.json) show a sparse subset of the H19-5/D2.8 lineage. Thinning redundant predictions and removing near-catalogue dots can change the precision–coverage trade-off favorably. This is a plausible metric explanation, not an isolated causal experiment or evidence of discovery of geothermal vents. The attributed **0.2778 is USER-REPORTED**, not ORGANIZER-CONFIRMED. No new submission receipt was obtained. A higher leaderboard score cannot be guaranteed or inferred from local HOLDOUT-DTI.

There is no new geological lane in this review: the prompt's promised single-method paragraph is missing, and the dense witness proves every nonempty placement fails the literal gate before model fitting. Existing ranked proposals and tested negative outcomes are available in the [TDKL dossier](hypotheses-20261024-tdkl88.md) and [MVRD dossier](candidate-hypotheses-20261024.md). These are historical research, not fresh preregistration or evidence that their proposals remain novel. Do not spend another model experiment or slot to evade the witness with cosmetic filename changes or silently revised support rules.

## Verified access and limitations

- **Official repository inspected live:** [DrivenData reference README at commit aebe92f7c8a990f0e3443451b7a825d9afd6336b](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md), retrieved through GitHub API. It documents both CPU-only and GPU environments; the blanket claim that a GPU is required is not correct for that reference solution.
- **Locally reverified mirrored bytes, not organizer authenticity:** sample, catalogue and registry restored via pinned GitHub mirrors. Hash matching proves reproducibility against those pins, not independent organizer endorsement.
- **Not checked live in this session:** [competition instructions](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf). Direct access to these hosts is outside this sandbox's network allowlist. These links are review targets, not claims of live verification. The prompt's conflicting leaderboard figures cannot establish today's best score or weekly slot balance.
- No DrivenData portal interaction, new external geoscience dataset, full feature-stack restoration, retraining or fresh feature canary was performed. Historical holdout evidence remains explicitly historical. A static Pages site cannot itself authenticate and submit to DrivenData.

## Next session, in order

1. Resolve the shared protocol's dense-raster support ambiguity explicitly; until then keep the literal duplicate stop. No private evaluator or dense-prior exemption.
2. Supply the missing parallel-run method lane and reconcile the authoritative holdout incumbent on identical folds, not the highest number from differing instruments.
3. Then preregister genuinely new hypotheses against the integrated repository, run per-feature canaries, buffered whole-segment holdout and paired intervals, check the complete registry before/after placement, and validate saved TIFF/ZIP bytes automatically.
4. Only promote a candidate that passes every binding gate. Retrieve current rules, slot balance and any eventual organizer receipt through authorized access before using a real slot.
