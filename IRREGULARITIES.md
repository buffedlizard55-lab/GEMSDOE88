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
