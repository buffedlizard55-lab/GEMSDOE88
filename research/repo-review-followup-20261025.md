# GEMSDOE88 repository review follow-up — 2026-10-25

## Executive decision

**No new competition TIFF was generated or cleared. Do not upload any archived download.** The local, hash-pinned registry audit records that `data/registry/dense_17gemdoe.tif` is positive on every allowed prediction cell. Under the repository's literal forward 3-pixel overlap definition, any nonempty candidate therefore has overlap 1.0, above the 0.70 stop threshold. Constructing or renaming a raster would not resolve that contradiction. The current negative decision is recorded in [`evidence/repo_review_20261025.json`](../evidence/repo_review_20261025.json) and mirrored for Pages at [`docs/data/repo_review_20261025.json`](../docs/data/repo_review_20261025.json).

The repo does contain downloadable GeoTIFF/ZIP artifacts marked as research-only. Their local format checks are not evidence of uniqueness, organizer acceptance, submission eligibility, or a competition score. The homepage and executive submission guide correctly say **DO NOT SUBMIT**. No weekly slot was used.

## Pass 1 — inspect, reproduce, fix

- Reviewed the current branch, README operating prompt, Pages decision, local audit scripts, candidate run cards, registry inputs, and test layout.
- Initial checkout omitted ignored `data/` inputs. The first full test run exposed three test defects rather than a scientific result:
  1. `tests/test_qts88.py` reached `pytest.skip(...)` without importing `pytest` when the optional grid was absent.
  2. `tests/test_tdkl88.py` had the same missing import on its data-dependent skip path.
  3. `tests/test_vhgd88_lane.py` unconditionally ran a validator that requires the sample grid, catalogue raster, and dense witness; when those optional files were absent, the test failed on the validator's explicit missing-input assertion.
- Fixed the two missing imports and made the VHGD release-validator integration test skip only when its three required local inputs are absent. When the inputs exist, the full validator assertions still run.
- Restored the validation-tier files with `scripts/restore_inputs.py --validation`; the script verifies the pinned bytes. The 19-band training feature raster and unrelated full external-data tier were not restored because the pre-placement duplicate stop makes model fitting impermissible and unnecessary.

## Pass 2 — run full checks with validation inputs present

Commands and observed results:

- `.venv/bin/python -m pytest -q` — **630 passed, 23 skipped**. The skips are the suite's explicitly optional/environment-dependent tests; 61 upstream rasterio deprecation warnings remain.
- `.venv/bin/python scripts/audit_downloads.py --check` — **43/43** archived TIFF/ZIP packages pass local research-download checks; **0** are protocol-eligible. This is not organizer validation.
- `.venv/bin/python scripts/render_decision.py --check` — PASS; machine evidence and canonical decision panels agree.
- `.venv/bin/python scripts/check_site.py` — PASS; site guard and links pass.
- `.venv/bin/python scripts/review_repo_20261025.py` — completed with `DUPLICATE_STOP`, no audit errors; no model or TIFF was produced.
- `git diff --check` — PASS.

The output is reproducible from pinned public GitHub mirrors, but these are not authenticated downloads from the DrivenData account. The official competition data page requires login. No account credentials or portal receipt were available here.

## Pass 3 — requirement and evidence re-check

- The readme still starts with the unmistakable download/submission decision. The current research TIFF is labeled **download for research: yes; submit: no**.
- No user-reported leaderboard value is relabeled as `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED`. H33's reported `0.2778` is an owner/user claim; archived geometry and lineage are measured separately. No official receipt for that file is present in this repository.
- The repo's previously recorded public leaderboard snapshot (`0.4413`) and the prompt's `0.3195` are not freshly checked in this review. Neither establishes the score of a GEMSDOE88 artifact.
- The hypothesis queue and source links are preserved in the repo review run card. The top-ranked cached-layer proposal is not fit: the mandatory pre-placement uniqueness proof fails first. Consequently no new holdout result, per-feature leakage canary, new TIFF hash, or new score exists for this review. Treating a historical lane's holdout as the new proposal's evidence would be invalid.
- The external official sources listed in the repo remain useful manual references: [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), and [DOE GDR INGENIOUS collection](https://gdr.openei.org/submissions/1391). These pages were **not re-fetched in this review** because this environment's outbound host allowlist does not include their domains. Prior recorded source audits are not represented as fresh verification.

## H33 (`h33-h33-2-b2`) — what is and is not supported

The archived forensic analysis (`research/h33-forensics-20261024.md`; calculations in `scripts/forensics_h33.py` and `evidence/h33_forensics_20261024.json`) describes H33 as a label-blind, multi-modal ridge product with a sparser support than its named ancestors. Disk-level lineage shows H33 is a subset, not an addition, of the D2.8 → SOLO-D2.8 → H33 chain. It removes near-catalogue dots, its nearest-neighbor spacing is approximately one 300 m kernel radius on the 100 m grid, and its broad distance-from-catalogue profile is less trace-hugging than several poor reported siblings.

A plausible explanation is metric alignment: in this asymmetric distance-weighted Tversky objective (`alpha=0.2`, `beta=0.8`), redundant or low-credit predictions can increase the false-positive penalty without adding much new truth coverage. Pruning a subset of low-marginal-credit pixels can thus improve the score. H33 geometry is **consistent** with that mechanism; it does not prove that the removed points were false positives, establish causality, or explain its whole reported score. Its `0.2778` remains **USER-REPORTED**, not organizer-confirmed. The audit cannot establish whether a new, scientifically distinct raster would exceed it.

## Findings and remaining work

1. **Protocol contradiction (blocking):** under the current literal registry rule, the full-positive `17GEMSDOE` raster is a universal overlap witness. Resolve this through a documented, shared protocol/template decision before any candidate construction. Do not create a one-off exemption or compare only against selected sparse priors.
2. **No trained/model-ready data in this review:** only the validation tier was restored. If a future protocol version clears the pre-placement gate, restore authenticated competition data, verify its provenance and license, then use the pinned shared feature stack/evaluator/writer and buffered component holdout.
3. **No current portal evidence:** current leaderboard state, submission quota, active deadline, organizer file acceptance, and receipts require account/page access. Static GitHub Pages cannot replace this.
4. **No empirical promotion basis:** after the protocol blocker is resolved, preregister 3–5 genuinely distinct hypotheses, check external data licensing/availability before use, test each feature alone for leakage, run paired spatial holdout against the current best, then do pre-placement and final-dot uniqueness checks. Spend no slot unless the evidence passes; slot selection remains separate.
5. **Source freshness:** automate dated checks only for sources available under approved access. Store retrieved page/PDF snapshots, timestamps, hashes, and claim provenance rather than claiming the feed is live when pages were not reachable.

### Small code change in this review

The only code changes are test resilience fixes in `tests/test_qts88.py`, `tests/test_tdkl88.py`, and `tests/test_vhgd88_lane.py`. They do not alter candidate generation, shared metrics, prediction files, or submission gates.
