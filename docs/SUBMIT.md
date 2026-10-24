# GEMSDOE88 — current submission decision (2026-10-24)

## DO NOT SUBMIT any GEMSDOE88 file yet

**Current new research artifact (not a copy of H33 or any previous raster):**
[`gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif`](downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif),
SHA-256 `1bbb20e60ce5633a979e2bea8e1216105325b78c4ca93ca4380ea3f533e774ae`.
Research download **YES**; competition upload **NO**. The adjacent `.zip` contains only the same TIFF.

- Shared writer and independent disk audit passed: single-band float32 EPSG:32611,
  3730×3292, exact mirrored sample transform, no nodata, all 12,279,160 values
  finite in {0,1}, 0 outside footprint and 0 on visible mapped faults. Thus the
  file does not contain the kind of out-of-range cells that produced the user's
  prior portal error; **portal acceptance itself is not proven**.
- HOLDOUT-DTI (`gems57-pooled-hide-v2`, 22,893 withheld positives, 95% CI):
  **0.062936 [0.054201, 0.072122]** versus prior best
  **0.187888 [0.171698, 0.203260]** on the same frozen split. No paired
  incumbent-bootstrap terms; this experiment is below even the incumbent CI.
- Uniqueness measured against 29 accessible hash-verified prior rasters:
  surface max |Spearman ρ| **0.062661** before placement; final max
  |ρ| **0.008450**. Final dot overlap with all-positive `17GEMSDOE` prior is
  **1.0000 > 0.70**. The *literal* template rule calls this a duplicate and
  stops promotion; there is no silent dense-raster exemption. Access to
  private/unlinked files cannot be certified.
- Name reserved for research bookkeeping: `GEMSDOE88-FABDIS-621B097B`.
  Note (97/140 characters; **DO NOT paste into the portal**):
  `FAB88 RTP fabric dislocation x gravity; 37654 dots; HOLDOUT-DTI 0.0629; no receipt; DO NOT SUBMIT`.
- ORGANIZER-CONFIRMED score for this file: **none**. Agent used **0** weekly
  submissions. Public leaderboard 0.4413 (2026-10-24 official snapshot) is
  somebody else's score, not ours. Prompt-supplied H33 0.2778 has no receipt.

**Machine decisions (no human format/uniqueness inspection needed):**
[`current_release.json`](data/current_release.json),
[`fabric_dislocation_run_card.json`](data/fabric_dislocation_run_card.json),
[`fabric_dislocation_uniqueness.json`](data/fabric_dislocation_uniqueness.json).
Run `.venv/bin/python scripts/validate_current.py --require-submit`: exit **2**
correctly rejects the current file. If the grid, zip, SHA, evidence or prior
rasters change, the ordinary validator exits nonzero instead of approving.

### Procedure ONLY after a different future candidate clears all gates

1. Freeze the proposed method and rerun label-blind feature canaries and the
   buffered whole-component spatial holdout; require a matched-fold paired
   95% CI improvement over the prior best. Evaluate surface before placement
   and final dots against the full accessible registry. The current literal
   dense-prior blockade must be addressed by an **explicit protocol decision**
   before changing the template, not by renaming a file.
2. Verify the sample grid against an authenticated DrivenData download, resolve
   the owner-mirror redistribution rights, and run the shared writer plus
   independent all-cell range/CRS/transform/ZIP validation.
3. Only after separate selector approval and a verified account quota, upload
   **one approved** single-band GeoTIFF (or a ZIP containing only that TIFF) at
   [DrivenData submissions](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/)
   and paste the *approved file's* ≤140-character note. NLR [official rules
   §3.2/3.4](https://docs.nlr.gov/docs/fy26osti/96647.pdf) allow at most three
   feedback submissions per week and one final selection.
4. Copy the submission-page receipt verbatim into the ledger before writing
   any **ORGANIZER-CONFIRMED** score. HOLDOUT-DTI, proxies and projections are
   not organizer scores.

Prior PROVCREST, ADHR and PRUNE "promote/upload-ready" notes elsewhere in the
historical record are **superseded** by this machine-negative current decision.
See the [executive summary](executive-summary.html) and [official sources](sources.html).
