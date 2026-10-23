# IRREGULARITIES — Decision-Changing Items Only

## IR-88-14 — Parent `R0` Retains `2,171` Dots Inside `2–3 px` Kernel Halo & Byte-Exact Rebuild Profile
- **Observed:** Rebuilding `R0` (`h33-h33-2-b2`) across all 5 lineage steps reproduces the `37,654` pixel mask AND reproduces **both** SHA-256 hashes bit-for-bit (`zeros` `c55bafc4...` with `nodata=None`; `nan` `baeae321...` with `nodata=nan`, `DEFLATE`, `predictor=3`, `zlevel=9`, `256×256` tiles — resolving prior GDAL re-emission mismatch). `R0` has `0` dots at `<= 2.0 px` (`min d_cat = 2.236 px`) but **`2,171` dots (`5.77%`) in `2 < d_cat <= 3.0 px`**, and prior historical steps conflated collar cuts with count reductions (`44,090 -> 40,199 -> 37,654`).
- **Decision Impact:** Built **`AXIS = PRUNE` at strictly held count `N = 37,654`** (`p1px`, `p3px`, `p4px`) so `p3px` (`6f7ae705`) achieves `min d_cat = 3.162 px > 3.0 px` with zero mass confounding, while non-`PRUNE` `CONCENTRATION` variants inheriting `R0`'s `2 px` collar remain marked `HOLD` until applied atop `PRUNEp3px`.

## IR-88-17 — Public Sibling GitHub Mirrors & Automated Portal Scraping Disabled
- **Observed:** Sibling public repos (`buffedlizard55-lab/GEMSDOE`, `GEMSDOE24`, `60GEMSDOE`) host login-walled competition rasters with redistribution terms unchecked; `.github/workflows/pages.yml` and `scripts/update_leaderboard.py` previously ran scheduled `drivendata.org` scraping.
- **Decision Impact:** Flagged `FLAGGED_DATA_USE_UNCHECKED` in `registry/data_manifest.json`, kept `data/` and `releases/*.{tif,zip}` gitignored (committing SHA-256 JSON receipts only), and disabled automated `drivendata.org` scraping.

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

## IR-88-22 — Parent rebuild paths produced different container-byte results
- **Observed:** The concurrent five-lineage `scripts/verify_parent_r0.py` path previously re-derived the exact 37,654-pixel mask but did not reproduce container SHA under its writer. This session’s simpler pinned D2.8-ancestor prune (`distance > 2`) plus the original DEFLATE/predictor/tile profile produced **exact SHA-256 `c55bafc4…` and 0 pixel differences**.
- **Decision Impact:** The session start gate passes using the exact direct reconstruction recorded in `ledger/concentration_build_receipt.json`. The pinned parent remains authoritative; no variant depends on accepting an approximate parent.

## IR-88-23 — Unspaced SNAP (`w2E1`, `w2S2`, `w2E2`) Returns Negative PROXY Due to Along-Strike Bunching
- **Observed:** Unspaced `<= 2 px` window-argmax `SNAP` arms (`w2E1`, `w2S2`, `w2E2`, `min_sep = 1.0 px`) moved blind off-catalogue SGMC DTI **down** (`-0.00796`, `-0.00396`, `-0.00795`) while also perturbing `R0`'s `2–3 px` collar (`579–1,565` dots remaining vs `2,171` in `R0`).
- **Decision Impact:** Kept `SNAPw2E1/S2/E2` in `ledger/submissions.csv` as `HOLD` negative-control records and diagnosed the root cause in `IR-88-25`.

## IR-88-24 — Block-density CV depends on the declared block population
- **Observed:** At 1 km, exact R0 CV is `1.874001` over density in all 50,984 complete-footprint blocks and `0.618596` when zero-density blocks are excluded. The historical `0.51–0.59` report used 12 km blocks elsewhere and cannot be compared to an undefined 1 km calculation. The retained 15% variant moves all-complete-block CV to `1.641677`.
- **Decision Impact:** Every CV now states block size and inclusion rule. No candidate is tuned to the historical range, and CV remains diagnostic rather than a gate.

## IR-88-25 — `AXIS = SNAP` Along-Strike Bunching Collapse vs `d_nn >= 2.8 px` Spacing Lock & $60^\circ$ Hanging-Wall Potential-Field Drift
- **Observed:** Unspaced `<= 2 px` window-argmax snapping (`w2E1/S2/E2`) lowers blind off-catalogue USGS `SGMC` DTI from `R0 = 0.096060` to `0.088098–0.092105` because adjacent `R0` dots along the same fault strand slide onto adjacent pixels (`d_nn = 1.0 px`), opening `4–6 px` (`400–600 m > R = 300 m`) kernel coverage gaps along strike. Conversely, enforcing `R0`'s `d_nn >= 2.8 px` (`sqrt(8) = 2.8284 px`) inter-dot spacing during `<= 2.0 px` snapping restricts moves to across-strike crest centering and raises `SGMC` to **`0.096806 (+0.00075)`** on `SNAPscarp2px` (`fae77ff4`) and **`0.096439 (+0.00038)`** on `SNAPridge2px` (`83d2d231`). In contrast, pure subsurface potential-field snapping even with spacing lock (`SNAPpot2px` `fc2548e7`, `Bands 3 & 18`) drops `SGMC` to `0.095178 (-0.00088)` because $60^\circ$ dipping normal faults place maximum horizontal gravity/magnetic gradients `200–600 m` down-dip in the hanging wall relative to the surface trace.
- **Decision Impact:** Enforced `min_sep = 2.8 px` (`min d_nn = 2.8284 px`), strictly provided `training_features.tif` bands (`Bands 3, 12, 18, 19`, zero un-supplied external LiDAR), and exact collar preservation (`2,171` `2–3 px` dots untouched; `100%` of moved dots at `d_cat > 3.0 px`) across `SNAPridge2px`, `SNAPpot2px`, and `SNAPscarp2px` (`scripts/build_snap_variants.py`, `tests/test_snap_axis.py`). Promoted `SNAPscarp2px` (`fae77ff4`) as the primary `SNAP` candidate (`Slot 2`) and `SNAPpot2px` (`fc2548e7`) as a negative-control diagnostic.
