# GEMSDOE88

Auditable research for the DOE **Geothermal Exploration Machine-Learning Competition (GEMS)**. Project values:

- **Maximize P(Win):** scarce submissions belong to candidates that clear comparable offline evidence, not merely to valid files.
- **Own the Outcome:** preserve exact bytes, provenance, negative results, blockers, and evidence class.

## Current release — MRR-COH-88

> **DOWNLOAD FOR RESEARCH: YES · OK TO SUBMIT: NO · DO NOT SUBMIT**

MRR-COH-88 is a genuinely new magnetic residual-ribbon coherence candidate. The one preregistered experiment completed successfully, but its pooled buffered spatial holdout did **not** beat the same-split incumbent. The negative decision is binding even though format and expanded-registry uniqueness checks pass.

| Gate | Result | Decision |
|---|---:|---|
| Feature-alone leakage canaries | 8/8 pass; max symmetric AUC `0.540563` | pass (`≤ 0.90`) |
| Pre-placement surface similarity | max `|Spearman ρ| = 0.183582` | pass (`≤ 0.90`) |
| HOLDOUT-DTI | `0.07700055`, 95% CI `[0.06912859, 0.08486633]` | **fail** vs `0.18788764` |
| Withheld positives / evaluator | `22,893` / `gems57-pooled-hide-v2` | complete |
| Final dot-field overlap within 3 px | `0.45873578` | pass (`≤ 0.70`) |
| Final max excess overlap | `0.13015695` across 224 rasters | pass |
| Saved TIFF and one-TIFF ZIP | independent disk reopen passes | pass |
| Weekly slots / organizer receipt | `0` / none | not submitted |

The all-representation literal-overlap maximum is also disclosed as `1.0`: a dense positive-everywhere witness necessarily covers every sparse candidate dot. The binding representation-aware policy uses literal overlap for dot fields and chance-corrected excess overlap for dense rasters. No compared file has identical bytes or decoded predictions.

### Research artifact

- TIFF: [`docs/downloads/gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.tif`](docs/downloads/gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.tif)
- Single-member ZIP: [`docs/downloads/gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.zip`](docs/downloads/gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.zip)
- TIFF SHA-256: `98d8ecc539af4d1743b480c9fe1fc9165488076ba61fa82be4ee9fa2ccea0e24`
- ZIP SHA-256: `37959f896f95511a66241b0fe0a34c854bed203426be021bcd4624f0b7c02d7e`
- Positive pixels: `43,173`
- Canonical run card: [`registry/mrrcoh88_run_card.json`](registry/mrrcoh88_run_card.json)
- Frozen preregistration: [`registry/preregistration_mrrcoh88.json`](registry/preregistration_mrrcoh88.json)
- Ranked geology note: [`research/candidate-hypotheses-20261024-mrrcoh.md`](research/candidate-hypotheses-20261024-mrrcoh.md)
- Dated result and three-pass review: [`research/mrrcoh88-result-20261024.md`](research/mrrcoh88-result-20261024.md)
- Public decision and methodology: [`docs/index.html`](docs/index.html), [`docs/research.html`](docs/research.html)
- Submission safety guide: [`docs/SUBMIT.md`](docs/SUBMIT.md)

Archival identifier: `GEMSDOE88-MRRCOH-5FE6CDD8982F`<br>
Archival note (74/140): `MRR coherence OOF, 43173 dots; HOLDOUT-DTI 0.0770; UNSCORED; DO NOT SUBMIT`

Those strings identify a negative research file. They are **not** permission to upload it.

## Evidence classes

Do not merge unlike evidence into a single “score.”

- **HOLDOUT-DTI:** local evaluation with evaluator version, withheld-positive count, and confidence interval. MRR-COH-88 is `0.07700055` under `gems57-pooled-hide-v2`.
- **Owner-reported:** asserted without an organizer receipt. H33's `0.2778` remains owner-reported.
- **Model projection:** a forecast; never label it as observed DTI. No projection clears this release.
- **ORGANIZER-CONFIRMED:** copied from an immutable portal receipt or authenticated organizer record. There is none for MRR-COH-88.

Repository forensics make H33's report plausible: its raster is a strict thinning of an H19-5/D2.8 ridge family, preserving kernel-spaced off-catalogue support while deleting many likely low-yield/near-catalogue dots. With the false-positive-sensitive Tversky term (`α=0.2`, `β=0.8`) and 300 m triangular distance support, removing weak emitted mass can improve score. This is a mechanism, not causal proof. MRR-COH-88 is **not shown likely to beat H33**: even its holdout CI upper bound (`0.08487`) is below the same-split local incumbent (`0.18789`), before comparison with the unverified `0.2778` report.

## Method contract

MRR-COH-88 uses competition magnetic anomaly and vertical magnetic-gradient layers. It removes their broad local 10 km relationship, then derives negative residual trough, 200/400/600 m axial coherence, cross-scale persistence, and horizontal-gradient suppression channels. The intended signal is a narrow, persistent demagnetized damage corridor under cover. Named non-fault mimics are linear Tertiary dikes, reversed basalt-flow margins, and aeromagnetic flight-line leveling seams.

The evaluation contract is:

1. hide whole connected fault components with a buffer;
2. rebuild catalogue-derived geometry from visible faults only;
3. mask visible fault pixels exactly;
4. test every feature alone and stop if symmetric AUC exceeds `0.90`;
5. compute pooled DTI with `α=0.2`, `β=0.8`, and the 300 m triangular kernel;
6. stop before dot placement if surface `|Spearman ρ| > 0.90`;
7. after placement, stop if more than 70% of candidate dots fall within 3 pixels of a registry dot field;
8. reopen and validate the saved TIFF and ZIP independently;
9. separate scientific promotion from weekly-slot selection.

Production fitting is strict four-quadrant out-of-fold. Shared evaluator/writer code lives in `vendor/gems57`; no private evaluator fork is maintained.

## Ranked hypotheses and source status

Five hypotheses were frozen before the experiment. MRR-COH-88 ranked first on qualitative expected gain, implementation cost, and verified local availability. RTP-GRAV-ADMITTANCE-88, STRAIN-SEISMIC-AXIAL-RIDGE-88, CHI-DIVIDE-ANTISYMMETRY-88, and RADIOMETRIC-ILR-ALTERATION-88 remain unrun. Their exact layers, transforms, off-catalogue rationale, named mimics, novelty, cost, and official-source availability are recorded in [`research/candidate-hypotheses-20261024-mrrcoh.md`](research/candidate-hypotheses-20261024-mrrcoh.md) and [`docs/sources.html`](docs/sources.html). No numeric expected-gain values were invented where calibration evidence did not exist.

Competition inputs came from owner-hosted mirrors and are hash-pinned in [`registry/data_manifest.json`](registry/data_manifest.json). Exact bytes were verified; organizer authentication and redistribution terms were not. Restored competition inputs stay gitignored. Free official supplemental-source links and unresolved availability irregularities are listed line by line on the source page.

## Session-start operating prompt

**Reread [`PROMPT.md`](PROMPT.md) at the start of every work session.** It is the canonical operating prompt. Its non-negotiable session checklist is:

1. Work in one preregistered method lane; do not tune after seeing its holdout result.
2. Restore only authorized inputs and verify all SHA-256 pins.
3. Reuse the cached feature stack, `vendor/gems57/evaluate_holdout.py`, and `vendor/gems57/submission_writer.py`; repair shared defects once.
4. Use buffered whole-component spatial holdout and visible-only catalogue features.
5. Run feature-alone leakage, pre-placement correlation, post-placement overlap, and saved-byte format stops.
6. Label all quantitative evidence as HOLDOUT-DTI, owner-reported, projection, or ORGANIZER-CONFIRMED.
7. Stop after three experiments or two hours; weekly-slot promotion is a separate selector decision and never automatic.
8. End with one canonical JSON run card and make download/submit status conspicuous.
9. Perform three passes: implement/verify; review/fix; requirement recheck/fix.
10. Preserve **Maximize P(Win)** and **Own the Outcome**.

See also [`AGENTS.md`](AGENTS.md) for the short session-start checklist and repository conventions.

## Reproduce validation (not the 12-minute experiment)

Python 3.11 is used in CI. Restore ignored, hash-pinned inputs before full current-release checks:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_inputs.py --validation
.venv/bin/python scripts/restore_siblings.py
.venv/bin/python scripts/validate_current.py
.venv/bin/python scripts/readiness.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

The expected current decision is `BLOCKED` on HOLDOUT while research download and format/uniqueness validation remain green. This command must fail closed with exit code 2:

```bash
.venv/bin/python scripts/validate_current.py --require-submit
```

The completed experiment runner is [`scripts/run_mrrcoh88_experiment.py`](scripts/run_mrrcoh88_experiment.py). Do not rerun it simply to improve the result: the one preregistered experiment is complete and negative. A rerun also refuses to overwrite the existing artifact unless the explicit writer policy changes.

## Evidence and code map

- `src/gems88/mrr_coh.py` — catalogue-blind residual/coherence/persistence feature builder and cache
- `src/gems88/adhr.py` — strict clearance and quadrant OOF production helpers
- `src/gems88/registry_paths.py` — expanded accessible-registry indexing with hash pins
- `evidence/mrrcoh88_canaries.json` — eight feature-alone leakage tests
- `evidence/mrrcoh88_holdout.json` — fold and pooled HOLDOUT-DTI evidence
- `evidence/mrrcoh88_surface_uniqueness.json` — pre-placement surface stop
- `evidence/mrrcoh88_final_uniqueness.json` — 224-raster final comparison rows
- `scripts/validate_current.py` — independent current TIFF/ZIP/evidence validator
- `scripts/readiness.py` — fail-closed selector/readiness status generator
- `scripts/check_site.py` — site link and visible-decision consistency audit

Historical KTH, MRR, fabric, and UGFV records remain in the repository as archived evidence. They are not the current release.

## Limitations and next work

- Hidden true unmapped faults are unavailable; catalogue-only holdout cannot resolve all label incompleteness.
- Eight spatial folds do not span every geological domain shift.
- “Expanded registry” means all accessible SHA-pinned rasters, not unknown private submissions.
- Dense witnesses make literal all-raster overlap uninformative, hence the declared representation-aware policy.
- Owner-mirrored input authenticity and competition redistribution terms remain unresolved.
- No portal upload occurred; local checks do not prove organizer acceptance.

Do not tune MRR-COH-88. If research continues, freeze exact official inputs for the next ranked hypothesis, preregister one new lane, and apply the same canary/holdout/uniqueness/format gates. Promote only if it beats the same-split incumbent and a separate selector approves a slot.
