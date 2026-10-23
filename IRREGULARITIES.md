# Decision-changing irregularities — 2026-10-23

1. **No session AXIS was assigned; MASS was not scientifically implementable from the pinned parent.** The default-first MASS lane was investigated, but every R0 dot has H19-5 value 1.0 and the recorded D2.8/R0 operator is score-blind geodesic BFS. An arbitrary raster-order prune would not be a mechanism-backed MASS test. Decision: do not build MASS; use the only coherent fixed-count edit found, PRUNE3.

2. **The non-PRUNE 3 px exclusion conflicts with R0's `d_cat>2 px` construction.** R0 contains 1,611 dots at `2<d_cat<3`; 30 have no destination that is both within 2 px and at least 3 px from the catalogue. Decision: do not build SNAP or silently add a relocation/prune second axis. PRUNE1 and PRUNE2 were also skipped because their specified edits would repeat R0 exactly.

3. **Fixed-count PRUNE3 could not retain 2.8 px spacing.** Only 475 of the required 2,171 legal H19-5 refills fit with that inhibition. Before any candidate scoring, `registry/prune3_amendment.json` removed extra inhibition while retaining support, exclusions, BFS order, and count. Decision: report nearest-neighbour drift (minimum 2.828→1.000 px; mean 3.735→3.550 px) as a confounder.

4. **The first leakage diagnostic was structurally invalid and forced investigation.** Full-catalogue distance gave symmetric AUC 1.0; direct hide/recover gave the candidate zero credit because withheld catalogue geometry had already been used in the exclusion. Decision: invalidate that diagnostic, recompute distance from each fold's visible catalogue, and rebuild both arms per fold. Repaired canary max AUC is 0.7536; the fold-visible mechanism PROXY is reported separately and is not a direct file score or a gate.

5. **Historical ledger material is incomplete.** Neither `ledger/submissions.csv` nor `ledger/raw_paste.txt` existed, and a targeted GitHub filename search found no shared copy. Decision: start a new ledger with the built variant, refuse future repeated `(parent,axis,value)` rows, and run exact-hash dedupe against all accessible local family rasters. Cross-session pair history before this checkout is **UNVERIFIED**; the human must supply any external ledger before another axis/value is built.

6. **Competition rasters were already tracked in this public repository, but data-use terms are unchecked.** Decision: flag the pre-existing condition; keep the two new candidate GeoTIFFs local and Git-ignored under `releases/`, while tracking their hashes, validation receipts, mechanism card, and reproducible code. No GitHub release is created.

7. **Live planning inputs are missing and automated DrivenData access is prohibited.** `TOP_PUBLIC`, slots remaining, R0's submission receipt, and manual deadline confirmation were not supplied. Decision: leave them UNSUPPLIED/UNCONFIRMED, make no leaderboard or quota assumption, and submit nothing. The existing repository's older leaderboard statements were not used as this session's target.
