# IRREGULARITIES — Decision-Changing Items Only

## IR-88-14 — Parent `R0` Retains `2,171` Dots Inside `2–3 px` Kernel Halo & Confounded Historical Climb
- **Reported:** Agent Brief v2 §4.4 requires `>= 3 px` from catalogue unless `AXIS=PRUNE`; prior notes attributed `H19-5 (0.1922) -> D2.8 (0.2600) -> SOLO (0.2708) -> R0 (0.2778)` `CLAIM` to near-catalogue pruning alone.
- **Observed:** Rebuilding `R0` (`h33-h33-2-b2`, `c55bafc4...`) bit-for-bit shows `0` dots at `<= 2.0 px` (`min d_cat = 2.236 px`), **`2,171` dots (`5.77%`) inside `2 < d_cat <= 3.0 px`**, and simultaneous mass drops across prior steps (`44,090 -> 40,199 -> 37,654`).
- **Decision Impact:** Selected **`AXIS = PRUNE` at strictly held count `N = 37,654`** (`p1px`, `p3px`, `p4px`) so `p3px` cleanly achieves `0` dots within `3.0 px` (`min d_cat = 3.162 px`) while separating true collar effect from dot-count elasticity.

## IR-88-17 — Public Sibling GitHub Mirrors & Automated Portal Scraping Disabled
- **Reported:** DrivenData #306 competition inputs are login-walled; automated portal scraping violates Terms of Use.
- **Observed:** Sibling public repos (`buffedlizard55-lab/GEMSDOE`, `GEMSDOE24`, `60GEMSDOE`) publicly mirror competition rasters (`training_features.tif`, `existing_faults.tif`, `sample_submission.tif`) with redistribution terms unchecked, AND `.github/workflows/pages.yml` + `scripts/update_leaderboard.py` previously contained a scheduled cron job scraping `drivendata.org`.
- **Decision Impact:** Flagged `FLAGGED_DATA_USE_UNCHECKED` in `registry/data_manifest.json` (`data/` stays gitignored and excluded from commits/releases); disabled scheduled `drivendata.org` scraping in `.github/workflows/pages.yml` and `scripts/update_leaderboard.py`.

## IR-88-18 — PR #14 `MASS` Variants Ranked by `rng.random()` (Deprecated)
- **Reported:** `ledger/mechanism_cards.json` on merged PR #14 claimed `MASS` variants dropped/added dots using physics + tip-relay ranking.
- **Observed:** Inspection of `scripts/generate_axis_variants.py` showed `training_features.tif` was never loaded and dot ranking was `0.6 * norm(dist_to_catalogue) + 0.4 * rng.random()`.
- **Decision Impact:** Marked all three PR #14 `MASS` rows `DEPRECATED` in `ledger/submissions.csv` (keeping hashes registered against accidental re-upload) and built deterministic `scripts/build_prune_variants.py` on verified 19-band + LiDAR + GeoDAWN + GDR physics.

## IR-88-19 — Band 16 Identity (`ieq_n100a15` Seismicity, Not Heat Flow), GDR Leakage Column & Canary Catch
- **Reported:** Prior repo summaries labeled `Band 16` of `training_features.tif` as heat flow.
- **Observed:** Reading `data/training_features.tif` (`4371c82e...`) band tags directly shows **`Band 16 = ieq_n100a15` (earthquake density)**, plus `-3.4e38` float32 nodata sentinels; `gdr_wellspring_in_footprint.csv` contains a catalogue-derived `dist_known_fault_px` column; AND applying `~catalogue` zeroing before canary evaluation tripped our live canary (`sym_auc = 1.0000 > 0.90`).
- **Decision Impact:** Sanitized `-3.4e38` sentinels, mapped `Band 16` strictly as seismic kinematics, excluded `dist_known_fault_px` from GDR geothermometry IDW, and evaluated all 15 physical channels unmasked prior to `known=catalogue` scoring (`max sym_auc = 0.56925 <= 0.90`).

## IR-88-20 — Triangle-Inequality Collapse of Post-Prune Catalogue Holdouts (`> 3 px => Holdout-DTI = 0`)
- **Reported:** Prior teams treated `buffered_component_draw` Holdout-DTI on emitted rasters as monotonous with live DTI.
- **Observed:** Every withheld pixel $g \in H$ satisfies $g \in \text{existing\_faults}$, so any raster with $d(x, C) > 3\text{ px}$ obeys $d(x, g) > 3\text{ px} \Rightarrow \ker(x, g) \equiv 0$, forcing post-prune Holdout-DTI to `0.03015 (p1px) -> 0.00401 (R0) -> 0.00000 (p3px, p4px)` (`PROXY`) — opposite to historical live `0.2600 -> 0.2708 -> 0.2778` (`CLAIM`). Conversely, blind off-catalogue USGS `SGMC` faults (`62,703` px, `d_cat > 3 px`) peak at **`p3px = 0.096083`** (`0.090926 -> 0.096060 -> 0.096083 -> 0.094465`).
- **Decision Impact:** Kept Holdout-DTI strictly `REPORT-ONLY` alongside blind `SGMC` control and `12 km` block-density CV (`0.5590 -> 0.5700` inside `0.51–0.59`, rising to `0.5937` at `p4px`).
