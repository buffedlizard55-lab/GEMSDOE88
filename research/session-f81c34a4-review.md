# Three-pass review — Arena f81c34a4, 2026-10-25

## Outcome

**New unique submission requirement: unmet. Download existing research: YES. Submit: NO.** No new prediction was generated, no old prediction was repackaged as new, and no weekly slot was used. The existing site and executive guide already expose the research TIFF/ZIP and automated negative decision. No human inspection is substituted for automated validation.

Read README, PROMPT, USER_PROMPT_20261025, AGENTS, and the preceding review at session start. The full recorded request remains embedded in README. This request does not supply its referenced single method paragraph; no new lane was assumed.

## Pass 1 — reproduce before changing anything

Installed requirements in an isolated virtual environment (system Python correctly refused an externally managed installation). Restored validation inputs, reran the shared generation preflight, then restored and prepared the full shared data tier. Ran prepare_data separately as requested. SHA checks, EPSG:32611, shape 3730 × 3292, 100 m transform, and nine shared robust-z feature planes passed on CPU. Inputs are **owner mirrors**, not independently organizer-authenticated downloads; GPU is not a prerequisite for these preparation steps.

The pinned 17GEMSDOE witness has positive support on all 5,106,385 allowed cells. Thus every nonempty allowed dot set has forward overlap 1.0, above the literal 0.70 threshold. These are registry measurements, not scores. A universal witness suffices to reject, not to certify inventory-wide uniqueness. Surface and dots were not constructed. The shared generation and slot commands both returned expected exit 2. No shared evaluator, writer, thresholds, or registry entries were changed.

## Pass 2 — fix a verified audit defect

`audit_h33_lineage.py` verified lineage raster hashes and reference grid geometry but did not verify reference sample/catalogue hashes before deriving footprint and catalogue distances. Same-grid modified reference values could therefore contaminate its conclusions. It now uses the existing shared `pinned` helper for both references before loading the grid. Three regression tests check each corruption path and both expected pins before derivation. No new evaluator or private writer was introduced.

Re-ran H33 audit on pinned inputs: measured geometry is unchanged; only its audit timestamp changed. H33 is a subset of H19-5, D2.8, and SOLO. Relative to D2.8, its 37,654 positive pixels exclude 6,436 pixels, all within two pixels of the catalogue. A plausible explanation is economical distance-kernel coverage with less redundant prediction mass and catalogue-collar pruning. This is **not proof of causal hidden-score improvement**, nor evidence of newly discovered vents. Removing predictions can also reduce true coverage. The supplied 0.2778 and conflicting leaderboard targets have no organizer receipt here. No verified basis exists to promise improvement over them.

## Ranked hypotheses before implementation

Retain the prior unexecuted queue rather than falsely claiming novel discoveries. The comparison is with existing implementations, not an exhaustive proof that nobody across all sites has tried them. Ranking is qualitative expected usefulness and cost, **not a projected DTI score**. All use already restored layers; none depends on claiming inaccessible external data is available.

| Rank; cost | Layers and transform | Why potentially off-catalogue; confounder; distinction |
|---|---|---|
| 1; medium–high | RTP/TMI magnetic-marker displacement; independent-swath restoration with gravity, elevation and basement context | A covered offset need not have a visible scarp. Depositional facies pinch-out or leveling seams mimic it. Require restoration of an unseen neighboring swath rather than existing fabric-dislocation/amplitude evidence. |
| 2; medium | DEM/slope/cached LiDAR/drainage; compatible-flank signed-step restoration likelihood | Small piedmont offsets can fall below ridge thresholds. Fluvial terrace risers mimic them. Test drainage-matched predictive restoration rather than step magnitude; cached 100 m summaries cannot recover raw 1 m profiles. |
| 3; medium | Radiometric indices/RTP/slope/cover; terrain-matched alteration-width asymmetry plus magnetic depression | A covered fluid pathway may preferentially alter one wall. Differential weathering mimics it. Estimate width asymmetry rather than existing radiometric step conjunctions; indices are not calibrated elemental ratios. |
| 4; medium–high | Conductivity/gravity/basement/elevation; conductive connectivity across a basin-boundary saddle | A concealed cross-boundary fault may lack a mapped trace. Saline alluvial paleochannels mimic it. Compare against drainage-aligned connectivity nulls rather than curvature alone. |

Top-candidate validation is stopped **before construction**, not treated as a failed or successful holdout experiment. No feature canary or HOLDOUT-DTI exists for this review. If legitimately unblocked by a shared contract, preregister one assigned lane; run each feature alone (AUC >0.90 treated as leakage); withhold whole segments with buffers; derive all catalogue features from visible faults; mask visible faults exactly; compare with an incumbent on identical folds using pooled DTI (alpha 0.2, beta 0.8, triangular 300 m) and a paired block-bootstrap confidence interval. Check surface and final dots against the registry. Preserve an untouched spatial audit partition against repeated-holdout selection bias. A local format pass never selects a weekly slot.

## Pass 3 — integrated verification

- Initial existing suite: 805 passed, 23 skipped. Final suite including the three new regressions: **808 passed, 23 skipped**, 68 warnings, 207.15 s. Skips are not claimed as tested behavior.
- `audit_downloads.py --check`: 46/46 published research packages pass local checks, zero protocol-eligible files.
- `render_decision.py --check`, `check_site.py`, and optimized `python -O scripts/check_site.py`: pass.
- Saved-byte checks cover finite values, [0,1], exact sample grid, one-band TIFF and byte-identical one-TIFF ZIP. They are local research-format validation, **not organizer acceptance**.
- Fresh generation guard and submission-review `--require-submit`: expected exit 2. Experiments: zero; slots: zero.

## Sources actually retrieved and limits

- [Official reference README at immutable commit](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md): freshly retrieved through GitHub API. Describes separate data download and CPU/GPU options, not this project's hidden score or evaluator certification.
- [Pinned owner registry witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif): freshly restored and hashed. Owner-authored registry evidence, not organizer receipt.
- [Fresh H33 geometric evidence](../evidence/h33_lineage_recheck.json): pinned owner bytes, not hidden truth. [User-reported results inventory](../docs/data/user_reported_results.json) is not an independently confirmed leaderboard.
- [Official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [GDR 1391](https://gdr.openei.org/submissions/1391): authority links for review, **not retrieved this session**, outside this environment's outbound allowlist. No claims of current quota, permission, current leaderboard, fresh literature verification, or source availability. Owner Dropbox links are not relabeled official.

## Next session priorities

1. Resolve the dense continuous-raster versus sparse-dot protocol contradiction explicitly in the shared policy; do not silently exempt a registry raster or adjust support thresholds. Under the unchanged rule a unique nonempty TIFF is mathematically unavailable.
2. Establish organizer input identity, redistribution permissions, current competition eligibility/quota and receipts using authorized access. No credentials should be pasted in chat.
3. Only after those gates, execute one preregistered hypothesis and matched-incumbent hide-and-recover experiment; promote only with defensible paired evidence. Investigate untouched-block generalization, not leaderboard projections.

The goal is fault discovery relevant to geothermal pathways, not confirmed vent localization. Static Pages serves audited downloads but cannot itself train or authenticate uploads. The highest-urgency request is **not fully satisfied**, and no claim of line-by-line verification of all historical scientific assertions is made. Maximize P(Win) by conserving slots; own the outcome by retaining negative evidence and repairing the audit rather than fabricating success.
