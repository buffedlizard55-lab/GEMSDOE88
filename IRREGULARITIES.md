# IRREGULARITIES — Decision-Changing Items Only

## IR-88-14 — Parent `R0` Retains `2,171` Dots Inside `2–3 px` Kernel Halo & Byte-Exact Rebuild Profile
- **Observed:** Rebuilding `R0` (`h33-h33-2-b2`) across all 5 lineage steps reproduces the `37,654` pixel mask AND reproduces **both** SHA-256 hashes bit-for-bit (`zeros` `c55bafc4...` with `nodata=None`; `nan` `baeae321...` with `nodata=nan`, `DEFLATE`, `predictor=3`, `zlevel=9`, `256×256` tiles — resolving prior GDAL re-emission mismatch). `R0` has `0` dots at `<= 2.0 px` (`min d_cat = 2.236 px`) but **`2,171` dots (`5.77%`) in `2 < d_cat <= 3.0 px`**, and prior historical steps conflated collar cuts with count reductions (`44,090 -> 40,199 -> 37,654`).
- **Decision Impact:** Built **`AXIS = PRUNE` at strictly held count `N = 37,654`** (`p1px`, `p3px`, `p4px`) so `p3px` (`6f7ae705`) achieves `min d_cat = 3.162 px > 3.0 px` with zero mass confounding, while non-`PRUNE` `CONCENTRATION` variants inheriting `R0`'s `2 px` collar remain marked `HOLD` until applied atop `PRUNEp3px`.

## IR-88-17 — Public Sibling GitHub Mirrors & Automated Portal Scraping Disabled
- **Observed:** Sibling public repos (`buffedlizard55-lab/GEMSDOE`, `GEMSDOE24`, `60GEMSDOE`) host login-walled competition rasters with redistribution terms unchecked; `.github/workflows/pages.yml` and `scripts/update_leaderboard.py` previously ran scheduled `drivendata.org` scraping.
- **Decision Impact:** Flagged `FLAGGED_DATA_USE_UNCHECKED` in `registry/data_manifest.json`, kept new `data/` and `releases/*.{tif,zip}` artifacts gitignored (committing SHA-256 JSON receipts only), documented pre-existing tracked rasters in IR-88-26, and disabled automated `drivendata.org` scraping.

## IR-88-18 — PR #14 `MASS` Variants Ranked by `0.6*dist + 0.4*uniform` (`HOLD`)
- **Observed:** Direct audit (`registry/mass_ranking_audit.json`, `scripts/generate_axis_variants.py`) proved shipped `MASS` variants used `0.6 * clip(d_cat/50) + 0.4 * rng.random()` rather than parent physics (`89.4%` of `m10minus` drops fell within `10 px` of catalogue; `Jaccard = 0.167` across seeds).
- **Decision Impact:** Retained `MASS` hashes in `ledger/submissions.csv` with `HOLD` status to block accidental upload; replaced score-blind selection in `scripts/build_prune_variants.py` with unmasked 4-line physics + exact marginal-DTI solvers.

## IR-88-19 — Band 16 Identity (`ieq_n100a15` Seismicity, Not Heat Flow), GDR Leakage Column & Live Canary Catch
- **Observed:** `data/training_features.tif` (`4371c82e...`) band metadata proves **`Band 16 = ieq_n100a15` (earthquake density, not heat flow)** and carries `-3.4e38` float32 sentinels; `gdr_wellspring_in_footprint.csv` contains a catalogue-derived `dist_known_fault_px` column; AND zeroing `w_field` on `catalogue` before canary testing tripped our built-in canary (`sym_auc = 1.0000 > 0.90`).
- **Decision Impact:** Sanitized `-3.4e38` sentinels, assigned `Band 16` strictly to kinematic seismicity, excluded `dist_known_fault_px`, and verified all `15/15` unmasked channels pass (`max sym_auc = 0.56925 <= 0.90`) before applying `known=catalogue` scoring.

## IR-88-20 — Triangle-Inequality Collapse of Post-Prune Catalogue Holdouts (`> 3 px => Holdout-DTI = 0`)
- **Observed:** Every withheld pixel $g \in H \subset C$ lies on `existing_faults`, so any raster with $d(x, C) > 3\text{ px}$ obeys $d(x, g) > 3\text{ px} \Rightarrow \ker(x, g) \equiv 0$, forcing post-prune Holdout-DTI to `0.03015 (p1px) -> 0.00401 (R0) -> 0.00000 (p3px, p4px)` (`PROXY`) — opposite to historical live `0.2600 -> 0.2708 -> 0.2778` (`CLAIM`). Conversely, blind off-catalogue USGS `SGMC` faults (`62,703` px, `d_cat > 3 px`) peak at **`p3px = 0.096083`** (`0.090926 -> 0.096060 -> 0.096083 -> 0.094465`).
- **Decision Impact:** Kept Holdout-DTI strictly `REPORT-ONLY` alongside blind `SGMC` control and `12 km` block-density CV (`0.5590 -> 0.5700` inside `0.51–0.59`, rising to `0.5937` at `p4px`).

## IR-88-21 — Concurrent CONCENTRATION work required ledger reconciliation
- **Observed:** Earlier concurrent work built 10% and 20% / 1 km parent-density CONCENTRATION arms before this branch merged. In this session the human explicitly selected CONCENTRATION and a distinct official-gradient prior (TMI-HG, gravity slope, gravity-HG) initially produced 10/15/20% arms.
- **Decision Impact:** Removed the semantically duplicate new 10% and 20% outputs during merge; retained only the unique **15%** official-gradient dose (`4dfb83f6`). It is `HOLD` because it inherits R0’s 2–3 px collar. This avoids repeating an `(axis,value)` experiment while preserving the human-assigned treatment at a new dose.

## IR-88-22 — Parent Rebuild Paths Differed; Current Full-Lineage Gate Is Byte-Exact
- **Observed:** An earlier generic five-lineage `scripts/verify_parent_r0.py` writer re-derived the exact 37,654-pixel mask but missed the container SHA; the human-assigned CONCENTRATION session's direct pinned-D2.8 reconstruction matched `c55bafc4…`. This PR then corrected the full-lineage path: `scripts/verify_parent_r0.py` now verifies all 15 pins and reproduces both `c55bafc4…` (zeros) and `baeae321…` (NaN) byte-exactly, as recorded in `registry/r0_verification.json`.
- **Decision Impact:** Use the current full-lineage byte-exact gate before rebuilding variants. Earlier nonmatching writer results remain historical only; no approximate parent is accepted.

## IR-88-23 — AXIS Unassigned Again; SNAP Built by Agent Judgment and Returns a Negative PROXY
- **Observed:** the brief's §1 slot `AXIS for this session (human assigns)` was empty and the human skipped the clarifying prompt, so the agent selected `SNAP` — the last unbuilt axis of the default order (MASS, CONCENTRATION, PRUNE already in the ledger). All three SNAP arms moved blind off-catalogue SGMC DTI **down** (`-0.00796`, `-0.00396`, `-0.00795`) while raising the mean potential-field edge percentile (`+0.07…0.09`).
- **Decision Impact:** SNAP is recorded as built and `HOLD`; it is retired from live consideration and removed from the slot queue (`SLOT_PLAN.md`). The three arms also leave `579–1,565` dots in the `2–3 px` collar, so they inherit the same non-PRUNE `>=3 px` gate conflict as MASS/CONCENTRATION. A-priori predictions were positive (`+0.004`); the shipped `MODEL` prediction was corrected to `-0.002`-ish **after** the PROXY measurement, and both values are recorded in the mechanism cards so the correction is auditable.

## IR-88-24 — Block-density CV depends on the declared block population
- **Observed:** At 1 km, exact R0 CV is `1.874001` over density in all 50,984 complete-footprint blocks and `0.618596` when zero-density blocks are excluded. The historical `0.51–0.59` report used 12 km blocks elsewhere and cannot be compared to an undefined 1 km calculation. The retained 15% variant moves all-complete-block CV to `1.641677`.
- **Decision Impact:** Every CV now states block size and inclusion rule. No candidate is tuned to the historical range, and CV remains diagnostic rather than a gate.

## IR-88-25 — Stale Multipart Feature-Raster Paths in Restore Helper
- **Observed:** the initial `restore_features()` helper requested `data/bridge/training_features.tif.part00`–`part04`, which do not exist at the manifest-pinned commit. The manifest points to `gems-geodawn-numerical-features.tif.part-000` and the pinned commit contains ordered `part-000`–`part-004` files. The failed attempt left only a zero-byte temporary target; it was removed. The fixed helpers now restore and verify the manifest's multipart entry; all 15 inputs pass SHA-256 and byte-length checks.
- **Decision Impact:** a clean checkout could not reproduce PRUNE ranking from its documented restore path. `scripts/restore_r0_prune_inputs.py` now restores/verifies multipart inputs, and `scripts/verify_parent_r0.py` enforces manifest pins plus byte-exact lineage before rebuilding.

## IR-88-26 — Existing Candidate TIFFs Are Already Tracked in This Public Repository
- **Observed:** `git ls-files` shows candidate `.tif`/`.zip` files under `docs/downloads/` and `submissions/`, plus three MASS variant TIFF/fallback/ZIP sets under `releases/`. Redistribution terms for owner-mirrored inputs and these generated rasters are not confirmed.
- **Decision Impact:** regenerated PRUNE TIFFs/ZIPs remain gitignored and are not added by this PR. Existing tracked artifacts were not removed. The human repository owner must decide how to handle them before further publication; no data-use permission is inferred.

## IR-88-27 — Legacy H88 Witness Gate Is Not a PRUNE Candidate Gate
- **Observed:** the old `validate_release.py`/README status evaluates an H88 research raster against a continuous full-footprint witness and reports 100% forward overlap. The current brief excludes rank-correlation/dot-overlap thresholds as PRUNE gates and specifies exact-hash/repeated `(parent, axis, value)` deduplication.
- **Decision Impact:** the legacy H88 status remains attached only to that unrelated raster. It was not used to gate PRUNE variants; format, zero-catalogue, exact-hash, parent-diff, and on-disk re-read checks were used.

## IR-88-28 — Competition Deadline Not Portal-Verified
- **Observed:** the latest human-confirmed planning values recorded on 2026-10-23 are TOP_PUBLIC `0.4413` dated `2026-10-22`, `3/3` rolling-week slots remaining, and approximately `21` total. The agent did not access `drivendata.org`, as prohibited by the brief, so the repository-listed `2026-12-03` deadline remains unverified.
- **Decision Impact:** the human must re-confirm the deadline and current planning counts on the competition page before live submissions; no portal fact was inferred.

## IR-88-29 — The Same Axis Was Built Twice Concurrently; the Compliant Arm Needed a Different Parent
- **Observed:** SNAP was built twice in parallel on `2026-10-23`: `main` shipped an `R0`-based family (`w2E1`/`w2S2`/`w2E2`, values `≤2 px` windows, `52–95%` of dots moved, `579–1,565` dots left in the `2–3 px` collar) while this branch built an `R1`-based family (`g2f35`/`d2f35`/`d1f35`, `34–35%` moved, strict `> 3 px`). Neither session saw the other's ledger at build time; `(AXIS, value)` pairs do not collide, but the *hypothesis* does.
- **Decision Impact:** Both families are kept and reconciled into one 17-row ledger, each row naming its own parent, and each build script now replaces **only its own family's** rows on a re-run. Because the `R0` family cannot satisfy Brief §4.4, the `R1` family is the one that can be spent — but IR-88-31 shows it should not be. Future sessions must re-check `origin/main` (not just the local ledger) immediately before building a new axis.

## IR-88-30 — Two Manifest Ancestors Were Never Restored at All
- **Observed:** Beyond the multipart path bug in IR-88-25, `scripts/restore_inputs.py --validation` never restored `anc_h19_4` (`data/registry/family_60gemsdoe/calib_h194_01894.tif`) or `anc_h16_1` (`calib_h161_01855.tif`), although both are declared in `registry/data_manifest.json`. `build_prune_variants.verify_manifest()` therefore aborted with "Missing pinned input anc_h19_4" even on a clean `--validation` restore, which blocks every variant build.
- **Decision Impact:** Both pins added to the restore list; the SNAP build now starts with `Verified 15/15 pinned inputs`. `tests/test_data_manifest_restore.py` covers the multipart entry only, so the ancestor pins remain a manual check until a test covers every manifest id.

## IR-88-31 — SNAP Loses Blind Off-Catalogue Alignment on a Gate-Clean Parent; Geometry Is Not the Lever
- **Observed:** With the collar confound removed (parent `R1`, `min d_cat 3.162 px`), all three `R1` SNAP variants still score **below** their own parent on the blind USGS `SGMC` off-catalogue fault control (`PROXY`, `n = 62,703 px`, nothing fit to any leaderboard): `R1 = 0.09608` vs `g2f35 0.09198`, `d2f35 0.09246`, `d1f35 0.09505`. The loss scales with mean displacement (`1.92 → 0.09505` at `1.00 px`) and the `12 km` block CV is unchanged (`0.5705–0.5708` vs `0.5700`), so this is localisation, not dispersion. The supplied edge bands localise catalogue pixels only weakly here (percentile rank `0.53–0.56` vs `0.50` background), consistent with the brief's `~0.57` single-band AUC and with the independent `R0`-based family (`-0.0040 … -0.0080`, IR-88-23).
- **Decision Impact:** The SNAP axis is **retired** (both families). Slot 1 stays `R1`; slot 2 becomes `CONCENTRATION` re-based on `R1`; no slot is spent measuring SNAP live unless the human wants the axis closed with a receipt. Positive claim: the lineage's dot *positions* are already at the noise floor of the supplied potential-field and elevation-edge bands, so remaining headroom is in *where mass is spent*, not in nudging dots. Falsifier: a live `RECEIPT >= R1 + 0.01` on any SNAP variant.
