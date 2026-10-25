# Repository review — 2026-10-25, Arena 484fceed

## Outcome: research download YES; competition submission NO

**The requested new, unique competition TIFF remains unmet.** No previous TIFF was copied, renamed, or presented as a new candidate. No geological experiment or weekly submission slot was used. The existing overview and executive submission guide already expose direct negatively labeled TIFF/ZIP downloads and the automated decision; they remain unchanged.

The shared preflight freshly verified the pinned dense `17GEMSDOE` witness: all 5,106,385 allowed pixels have positive support. Under the existing literal support definition, every nonempty candidate has forward overlap 1.0, exceeding the requested 0.70 threshold. This is a registry measurement, **not a performance score**. A single counterexample suffices to stop; it is not full-registry uniqueness clearance. Surface correlation and final dots were not constructed. Neither deleting this witness nor silently substituting a sparse-only comparison is authorized. See [session run card](../registry/session_484fceed_run_card.json).

The request also refers to a single method paragraph without actually assigning one. No new lane was invented. The previously ranked, untested queue below is retained rather than relabeling an executed lane as new.

## Pass 1 — implementation and direct verification

- Restored the shared inputs using the repository downloader, then ran `prepare_data.py` separately. Core SHA pins, band counts and grid checks passed; nine shared feature planes loaded on CPU. These are **owner mirrors**, not authenticated organizer downloads or newly verified data-use permissions.
- Fixed stale preparation evidence: before any preparation work, `prepare_data()` atomically replaces old success with `preparing`. Errors, restoration `SystemExit`, and keyboard interruption publish `error` and propagate failure. An abrupt process termination leaves `preparing`, not a stale `ready`. Success is published only after checks finish. This is not a concurrency lock or a substitute for rehashing mutable inputs.
- Fixed the shell downloader silently ignoring extra arguments; invalid combinations now fail before restoration.
- Recomputed the shared generation stop and submission-review stop; both returned the expected exit 2. Did not change the shared evaluator, writer, overlap policy or selector.
- Reopened all 46 published research TIFF/ZIP pairs: 46 pass local research checks, zero are protocol eligible. Saved-byte validation checks range, finiteness, sample grid and single-raster packaging; passing these is not organizer acceptance.

## Pass 2 — defects and edge cases

New regression tests cover stale success on checksum/missing-file failures, failed subprocesses, `SystemExit`, keyboard interruption, failure to invalidate, nonfinite JSON, successful replacement and surplus CLI arguments.

The initial integrated run returned **802 passed, 23 skipped, 1 failed**. The failing historical parent reconstruction had exact matching pixel masks but different encoded TIFF bytes under Rasterio 1.4.3. Installing 1.4.4 made that exact-hash test pass without changing the raster, expected hash or test. `requirements.txt` now pins Rasterio 1.4.4. This constrains the tested wheel environment, not a promise of cross-platform byte identity with arbitrary GDAL builds. The focused safety/request/entrypoint suite passed **130 tests**.

Dependency acquisition irregularity: the first unconstrained pip attempt rejected a NumPy wheel hash; a subsequent attempt encountered a TLS error. A no-cache install of explicit versions succeeded with normal TLS and hash checks retained. No bad wheel was accepted and no verification was disabled. Final package versions are recorded in the session card.

## Why H33 appears stronger, and whether we can beat it

Fresh `audit_h33_lineage.py` measurements confirm H33 is nested inside D2.8, SOLO and H19-5. H33 has 37,654 positive pixels versus D2.8's 44,090; the 6,436 removed pixels are all within two pixels of the mapped catalogue. These are geometric measurements, not DTI scores.

The defensible explanation is **more economical placement plus catalogue-collar pruning**, not demonstrated superior geothermal physics. Spatial thinning can reduce redundant prediction mass while retaining nearby distance-kernel coverage. However, removing predictions can also lose true coverage; the sign of the net score change depends on hidden truth. Nested geometry and a user-supplied result list do not establish causality. The reported H33 value 0.2778 has no submission-page receipt here and is not labeled ORGANIZER-CONFIRMED. The conflicting supplied leaderboard figures are likewise not verified current targets. We cannot honestly promise to exceed any of them.

A proper experiment must rebuild catalogue-dependent features from visible segments only. Masking a fixed prediction using the full catalogue before hide-and-recover would suppress withheld positives and is not a valid comparison. Promotion requires matched folds, a reproduced incumbent and positive paired uncertainty evidence, not a numeric leaderboard projection.

## Ranked, still-untested geological queue

These are the existing unexecuted proposals from the prior session, **not four experiments or newly discovered literature results**. Ranking is ordinal expected scientific usefulness; no numerical improvement is projected. The detailed [prior hypothesis specification](session-b4dfa10c-hypotheses.md) remains the starting point. None needs new external data beyond the restored cached stack; source licensing still needs confirmation.

| Rank / cost | Layers and physical signature | Missing-catalogue rationale; confounder; implementation difference |
|---|---|---|
| 1 / medium–high | RTP, TMI, gravity, elevation, basement depth: repeatable magnetic-marker displacement and restoration across independent neighboring swaths | Covered offset need not have a visible scarp. **Depositional facies pinch-out** can mimic it. Unlike axial fabric dislocation or amplitude residuals, require the same inferred displacement to restore an unseen swath. |
| 2 / medium | DEM, slope, cached LiDAR and drainage: out-of-profile predictive improvement from two compatible flanks plus signed step | A small piedmont offset could be below ridge thresholds. **Fluvial terrace risers** mimic it. Unlike step/knickpoint magnitude, test restoration likelihood against drainage-matched controls; 100 m summaries cannot recover raw 1 m profiles. |
| 3 / medium | Radiometric indices, RTP, slope, cover: terrain-matched alteration-width asymmetry with localized magnetic depression | A buried fluid pathway may alter one permeable wall. **Differential weathering** mimics it. Unlike radiometric step conjunctions, estimate width asymmetry; quantized indices are not physical elemental ratios. |
| 4 / medium–high | Conductivity, gravity, basement depth, elevation: narrow conductive connectivity across a basin-boundary saddle | A covered cross-boundary pathway may lack a mapped trace. **Saline alluvial paleochannels** mimic it. Unlike conductive curvature, test connectivity against a terrain-aligned drainage null. |

Top-proposal execution is blocked **before** feature construction. After an explicitly authorized shared-policy resolution, preregister one lane, run feature-alone leakage canaries, buffered whole-segment hide-and-recover using visible-only catalogue features, matched-incumbent pooled HOLDOUT-DTI and block-bootstrap CI, plus surface and final-dot registry gates. Keep an untouched spatial audit partition because repeated selection on the same holdout risks portfolio overfitting. These are tests for fault evidence, not confirmed geothermal vents.

## Source ledger and limits

| Source | What this session actually verified |
|---|---|
| [Official reference README, immutable commit](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | Retrieved through GitHub API. Documents separate competition-data download and CPU/GPU environments. A GPU is faster, not a hard prerequisite. Does not certify this project's triangular-distance evaluator or hidden performance. |
| [Pinned registry witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) | Downloaded via the shared git restore, SHA verified and support recomputed. Owner-authored evidence, not organizer science or a receipt. |
| [H33 local byte audit](../evidence/h33_lineage_recheck.json) | Freshly rerun on pinned mirror bytes. Explains nested geometry; cannot prove the cause of hidden-label improvement. |
| [Official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Manual-review authority links, not fetched here: domains outside allowed outbound hosts; no authenticated DrivenData account or receipt. Current slot quota and ranking unknown. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [GDR 1391](https://gdr.openei.org/submissions/1391), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Not retrieved in this session. No new availability, licensing or literature-verification claim. Dropbox owner links are not relabeled official. |
| [User-result inventory](../docs/data/user_reported_results.json) | Existing tested extraction preserves 92 sites and 115 distinct supplied claims; this session did not freshly browse all sites. Claims remain distinct from organizer receipts. |

The full recorded request remains embedded in README and checked by the request-evidence tests. It is not replaced by this shorter review.

## Pass 3 — final verification and next steps

Final integrated result: **803 passed, 23 skipped, zero failed**; the post-documentation focused checks also passed (24 tests). Exact commands and installed versions are recorded in the session card. The normal and optimized site guards, canonical renderer and saved-byte inventory are rerun; the public site must remain unequivocally **DO NOT SUBMIT**. No claim is made that every historical scientific statement or every external source has been verified line by line.

Priority next steps: resolve the contradictory dense-support protocol through the shared contract, then execute one preregistered untested proposal; establish organizer input identity, permitted redistribution, current rules and quota through authorized access; preserve automated fail-closed status and untouched spatial selection data. Static GitHub Pages can serve audited files and instructions but cannot train models or authenticate a competition upload. Do not mistake a format-valid research download for a unique submission.

**Maximize P(Win):** avoid duplicate slots and false performance promises. **Own the Outcome:** retain negative evidence, fix status bugs, and state the unique-TIFF requirement as unmet.
