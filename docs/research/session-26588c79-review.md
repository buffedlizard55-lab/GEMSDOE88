# Follow-up repository review — 26588c79 — 2026-10-25

## Decision: research download YES; new competition file NO

**DO NOT SUBMIT. No new TIFF was generated, copied, renamed, or uploaded.** The urgent unique-submission requirement is **UNMET**, not silently waived. No new HOLDOUT-DTI was measured, no organizer receipt was obtained, and no weekly slot was used.

This review continues the previous session's next step: preserve the literal pre-placement stop and strengthen autonomous validation. It does not introduce a different geological lane or a private evaluator/writer. The supplied prompt contains no actual single-method paragraph. The inherited H88-MTAS preregistration is referenced only for preflight; its hypothesis was not fitted.

## Pass 1 — reproduce before building

Installed the existing requirements into an ignored environment and restored the validation tier with `bash scripts/download_competition_data.sh --validation`. These are SHA-pinned **owner-mirror** inputs, not newly authenticated organizer downloads. Full feature restoration/training was intentionally not repeated after a necessary-condition rejection.

`python scripts/generation_guard.py` exited **2**, `DUPLICATE_STOP`. The pinned witness SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`. Its positive support directly covers all **5,106,385** allowed cells; **0** are uncovered. Thus every nonempty allowed candidate has forward overlap **1.0**, above the binding **0.70** limit. These are **REGISTRY-MEASUREMENTS**, not performance scores. Surface/final-dot correlations for a nonexistent candidate remain null. A full registry clearance is not claimed: one rejecting counterexample suffices.

All **43** published TIFF/ZIP pairs passed the existing saved-byte research audit: finite [0,1], exact reference CRS/shape/transform, two decoders, footprint/catalogue support, identical single-TIFF ZIP payload, and negative filename labels. **Zero** are eligible under the literal uniqueness rule. A format pass is not a high-scoring-validation pass.

### Confirmed audit omission and fix

Previously the all-download audit enumerated TIFFs, then checked only their expected ZIP companions. An extra ZIP, including `orphan.ZIP`, was not enumerated and could remain downloadable without any payload audit. The test claiming to cover every TIFF and ZIP had the same blind spot.

The existing shared project audit now checks a **closed publication inventory** before raster preflight:

- Every top-level TIFF has exactly its expected lowercase `.zip` companion; extra ZIPs of any suffix case are rejected.
- Two TIFF suffixes cannot share an ambiguous archive stem.
- Nested TIFF/ZIP files cannot silently escape the flat published inventory.
- Symlinked payloads, directories, and the download directory itself are rejected.
- Fresh-audit failures overwrite old positive evidence with `AUDIT_ERROR`; `--check` remains read-only and exits nonzero.

No TIFF or ZIP bytes were changed. The successful audit schema and scientific policy were not changed. Existing CI already invokes this audit, so the stronger inventory gate runs without another workflow or private validation fork.

## Pass 2 — adversarial edge cases and wording

The first focused run passed **35** tests. A subsequent full run passed **646**, skipped **23**, with **61** warnings. Review then added the download-directory-itself symlink edge case. Synthetic tests also cover missing archives, uppercase aliases, orphan archives, nested payloads, shared stems, stale-evidence invalidation, and read-only check failure.

The executive guide previously said a human selector could update the dense-prior rule and flip `ok_to_submit`, and elsewhere suggested a selector's boolean flip sufficed. Those instructions contradicted the binding automated gates. They now explicitly state that human inspection or a stored boolean cannot override failed scientific or uniqueness checks. A separate selector is still required **after**, not instead of, valid automated evidence under an authorized shared protocol.

## Pass 3 — recheck rather than edit evidence to fit

The final check includes the complete test suite, unchanged canonical renderer, normal and optimized site guards, the negative slot gate, and all 43 saved-byte packages. A first final-suite run caught the now-stale browser receipt after the executive-guide edit (**647 passed, 1 failed, 23 skipped**). This was a valid failure: a receipt must bind the current page, not a previous screenshot. The hashes were **not** manually patched. The existing Playwright audit was rerun against the live static server; all five desktop/mobile cases and the failed-fetch denial passed. The current receipt at `evidence/session_d0c3adeb_browser_check.json` was refreshed, preserving its prior revision in Git history. The final complete suite passed: **650 passed, 23 skipped, 61 warnings** in **199.04 seconds**. Skipped historical local-only raster/optional registry checks are not clearance; the warnings are Rasterio/Affine pending deprecations.

The browser initially lacked `libnspr4.so`/NSS runtime libraries. The already-installed `@sparticuz/chromium` package contains them in `bin/al2023.tar.br`; these were locally decompressed into the ignored cache and supplied through `LD_LIBRARY_PATH`. No extra external host, committed browser binary, or weakened browser check was needed.

## H33: evidence versus causal interpretation

The **USER-REPORTED 0.2778** is not an ORGANIZER-CONFIRMED score available here. The prompt also supplies conflicting leaderboard maxima; none is adopted as the current official standing.

Freshly retrieved [GEMSDOE32 build record, pinned commit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) identifies H33-2-B2 as catalogue-collar pruning and explicitly distinguishes its projection from a score. It is owner-authored, not an organizer receipt. Its H33 TIFF SHA agrees with the independently restored artifact.

Fresh local geometry rechecks confirm the ancestry:

| Raster | Positive support, REGISTRY-MEASUREMENT |
|---|---:|
| H19-5 | 121,131 cells |
| D2.8 | 44,090 cells |
| SOLO-D2.8 | 40,199 cells |
| H33-2-B2 | 37,654 cells |

H33 is an exact subset of each upstream support. Relative to D2.8 it deletes **6,436** dots, all within **2 pixels** of the catalogue; it adds none. Its minimum dot spacing is **2.828427 pixels**. No upstream submission is reused as a new one.

**Plausible mechanism:** thinning and pruning can remove redundant predictions that incur false-positive cost without adding much truth coverage. In the shared binary distance-weighted Tversky evaluator, truth coverage and per-dot nearest-truth credit are different quantities. Removing a dot helps only when the lost truth coverage is sufficiently small relative to the reduced penalty. It is not valid to assume every removed near-catalogue dot was a false positive: an unmapped fault can lie near a mapped one. The code-level algebra and caveats are in the [prior review](session-d0c3adeb-review.md#h33-what-actually-changed-and-why-that-can-help).

**Can we exceed it?** Possibly, but no valid numerical forecast or demonstrated improvement follows from these records. There is no new model to compare in this stopped run. Picking the maximum of many historical hide-and-recover trials would also exaggerate confidence; future comparisons need frozen folds and a paired spatial-block uncertainty estimate, not only a point-estimate win.

## Geological research queue — retained, not advertised as new discoveries

The [four ranked, conditional hypotheses](session-d0c3adeb-hypotheses.md) remain the next scientific queue: (1) magnetic marker restoration, (2) drainage-vetoed scarp-profile restoration, (3) cross-boundary alteration-width asymmetry, and (4) conductive basin-breach continuity. That record names exact layers, transforms, off-catalogue rationale, non-fault mimics, implementation contrasts and qualitative benefit/cost rankings. They are existing **untested proposals**, not four newly executed experiments or globally novel methods. This follow-up does not claim a fresh novelty search across all sibling repositories.

No additional externally dependent hypothesis is called viable without a fresh source/availability/terms check. The universal stop takes precedence over fitting the top proposal. Single-feature canaries, whole-component buffered hide-and-recover, visible-only catalogue features, pre-placement correlations, final-dot registry comparisons, and the same-fold incumbent comparison must all run after legitimate unblocking. No weekly slot is selected by a local format validator.

## Source ledger and access limits

| Source | Freshly retrieved? | Supported scope |
|---|---|---|
| [Official DrivenData reference README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | Yes, GitHub API | CPU-only training is supported; GPU accelerates it. Organizer data download is separate. Does not certify mirrors or this project's evaluator. |
| [Pinned GEMSDOE32 build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) | Yes, GitHub API | Owner evidence for H33 ancestry and file identity; not hidden-label validation. |
| [Pinned 17GEMSDOE witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) | Bytes restored and SHA-checked | Local literal-support saturation proof. |
| [DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | No: host outside allowlist; no authenticated portal session | Links for review only. Current standings, quota and organizer receipts remain unverified. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR 1391](https://gdr.openei.org/submissions/1391), [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | No: hosts outside allowlist | No new scientific, availability, permission or rules assertions based on unfetched pages. |

Hashes for the freshly retrieved documents and lineage measurements are preserved in [the JSON run card](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_26588c79_run_card.json). The complete recorded request remains embedded in README and `USER_PROMPT_20261025.md`; user performance claims remain separately inventoried with request-line provenance. This follow-up does not claim all 92 sites were freshly scraped or every external statement verified.

## Next session, in order

1. Do not build around the stop. A separately authorized **shared** representation-aware protocol revision would be necessary to make another nonempty candidate possible. No such revision is authorized by this prompt.
2. Only if legitimately unblocked, freeze one method from the existing queue and validate it against the incumbent with matched folds, visible-only derived inputs, leakage canaries and paired uncertainty. Limit to three experiments/two hours.
3. Complete surface/final-dot registry checks and saved-byte format/package validation. Enforce the separate weekly selector using authenticated current quota evidence. Do not infer organizer acceptance from project validation.
4. Keep current official-source access, input provenance, external-data terms and organizer receipts explicit. An optional GPU is not the primary blocker; the protocol and evidence prerequisites are.

**Maximize P(Win):** avoid wasting feedback on inadmissible files. **Own the Outcome:** report the unmet unique-file requirement and fix genuine validation gaps instead of fabricating a successful submission.
