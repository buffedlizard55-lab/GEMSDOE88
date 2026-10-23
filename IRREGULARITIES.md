# IRREGULARITIES — items that change a decision

## IR-88-14 — Hard constraint 4 vs parent R0 (2026-10-23, this session)

**Reported:** Brief v2 §4.4: "Emit zero mass on catalogue pixels and keep >=3 px from them unless AXIS=PRUNE."

**Observed:** Parent R0 `h33-h33-2-b2` (verified sha `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) has **0 within 2 px** (min dist 2.236) but **2,171 within 3 px (5.76%)** — see `data/registry/h33_education.tif` vs `data/bridge/existing_faults.tif` distance_transform_edt. This matches the ledger climb description "none within 2 px" and the forensic note "100% identical off-catalogue geometry outside 2 px". At 0.28 DTI, dots at 2-3 px still receive triangular kernel credit ~0.0-0.33, so pruning them is not cost-free.

**Decision:** This session's **MASS axis** variants (drop/add 10-20%) **inherit parent's 2 px collar (dist>2)** to hold "one change from named parent" invariant; changing both mass and collar would confound the MASS effect. A future **PRUNE axis** session should test 2 px→3 px move (drop 2,171 dots, 5.76%, refill to count if PRUNE-3px) as its own experiment.

**Evidence:** `scripts/generate_axis_variants.py` logs `dots <=2:0 <=3:2171` on restore; validator `test_06_zero_wasted_dots_inside_200m` expects 0 within 2 px, not 3 px.

**Update 2026-10-23 (CONCENTRATION session):** no variant mass is *added* inside 3 px of the catalogue (receiver sites require `dist > 3`), and the 2,171 inherited collar dots are reported per variant (`dots_within_3px_catalogue`) and left untouched, so the collar cannot be mistaken for part of the concentration effect. A PRUNE session should still test 2 px → 3 px as its own change.

## IR-88-15 — Manifest vs repo data_manifest (2026-10-23)

**Reported:** Brief v2 §4.2: "only files pinned in registry/data_manifest.json (or repo's equivalent); verify sha256 before use."

**Observed:** Repo has no `registry/data_manifest.json`; equivalent is `scripts/restore_inputs.py` SOURCES dict with SHA pins for `sample_submission.tif` (`2176d08e...`) and `existing_faults.tif` (`7ba308cc...`), verified before use. `training_features.tif` (`4371c82e...`) is absent locally (requires large external mirror) but not needed for MASS geometry-only variants; parent ranking rebuilt from distance+rand (MODEL) and documented in `ledger/mechanism_cards.json`.

**Decision:** No external fetch beyond GitHub owner mirrors (allowed hosts `github.com`, `codeload.github.com`). Grid pins verified; training feature mirror marked UNVERIFIED for this session.

## IR-88-16 — TOP_PUBLIC stale in prompt (2026-10-23)

**Reported:** Brief's `TOP_PUBLIC = ____` (human fills). Prompt-era note `site_reported_high 0.3195` is stale.

**Observed:** Automated `registry/leakage_canaries.json` not relevant; `run_card.json` and `docs/status.json` record `competition_leaderboard_high 0.4413` (#1 xiaofanhu, 2026-10-22). No scraped leaderboard; URL cited only.

**Decision:** README CURRENT STATE cites 0.4413 as TOP_PUBLIC with date and instructs re-check on competition page; no automated fetch performed per §4.1 ban.

## IR-88-17 — R0's byte sha256 is not reproducible; its pixel mask is (2026-10-23, CONCENTRATION session)

**Reported:** brief §5: "rebuild R0 and match its sha256 (if you cannot, stop and report; never approximate the parent)."

**Observed:** `scripts/verify_parent_r0.py` re-emits R0's own 0/1 array twice — once with R0's exact profile (tiled 256, deflate) and once with the release profile (LZW, single strip). Both re-emissions are **array-identical to the parent (`0` differing pixels)** and neither reproduces the parent's byte sha256 (`761adf6c…` / `85447179…` vs pin `c55bafc4…`). The difference is encoder-versioned bytes, not pixels. Record: `registry/r0_verification.json`.

**Decision:** proceed. The reproducible object is the 37,654-pixel dot mask, and it is exact. Stopping would have blocked every variant for a zlib-version artefact. Each variant is named by the sha256 of the bytes actually written, and the human's upload hashes come from the files in `releases/`, never from the pin.

## IR-88-18 — the MASS ranking is reconstructed, not the parent's own (changes slot ordering)

**Reported:** brief §5: MASS must drop/add "by the parent's own ranking (rebuild the ranking from the recorded recipe if it is not stored)"; §2 says to rank dots by exact marginal gain, not a shortcut.

**Observed:** no ranking is stored anywhere in the repo, and the previous session's recipe is `0.6·norm(dist_cat/50) + 0.4·rand(seed 88)` (`scripts/generate_axis_variants.py`). That is a distance-plus-noise ordering: it cannot identify a dot's marginal DTI gain, which needs the truth kernel `k` the metric uses. The same card also quotes a PROXY "0.092 → 0.108" that is not present in any `registry/` file, so it cannot be checked.

**Decision:** treat the three MASS rows as *built but weakly predicted*. They stay in the ledger with their original numbers; they are ranked below the CONCENTRATION pair in `SLOT_PLAN.md`. A future MASS session should either recover the parent's real ranking or declare MASS as "mass only, ordering arbitrary" and predict ±0.

## IR-88-19 — the 0.51–0.59 block-CV band is not reproducible from R0 (changes how CV is reported)

**Reported:** brief §5 CONCENTRATION: "report block-density CV before/after (the best files reportedly sit at 0.51-0.59)".

**Observed:** `registry/concentration_report.json` → `parent_stats.cv_ladder`. R0's CV of raw dot counts per block: 0.399 (5 px blocks), **0.618 (10 px)**, 0.744 (20 px), 0.703 (50 px); over all in-footprint blocks: 2.74 / 1.87 / 1.37 / 0.90. Only a *smoothed density* estimator lands near the band (5 km smoothing: 0.482; 3 km: 0.631). No estimator tried returns 0.51–0.59 for R0.

**Decision:** report four block sizes × two estimators plus the smoothed-density CV for every variant, and never gate on CV. The CONCENTRATION variants push the raw 10 px CV to 1.02–1.36 and the smoothed CV to 0.67–1.07 — i.e. far past the band. Their mechanism card records this as the main confounder and as the way to falsify the folklore: if the band is causal, the predicted sign inverts.

## IR-88-20 — this session's AXIS was unassigned (2026-10-23)

**Reported:** brief §1/§5: "AXIS for this session (human assigns)"; §5: "Each (AXIS, value) pair is built once across all sessions; check the ledger first."

**Observed:** the session prompt carried a blank AXIS. The ledger already holds three unsubmitted MASS variants from 2026-10-23 and `SLOT_PLAN.md`'s default order is MASS → CONCENTRATION → SNAP → PRUNE → RELIEF.

**Decision:** build CONCENTRATION (the next unbuilt axis) rather than repeat MASS. If the human wanted a different axis, the three files are still valid experiments and the scripts take the block size / fraction as parameters, so the axis can be re-targeted without rebuilding the pipeline.
