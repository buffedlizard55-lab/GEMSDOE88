# IRREGULARITIES — items that change a decision

## IR-88-14 — Hard constraint 4 vs parent R0 (2026-10-23, this session)

**Reported:** Brief v2 §4.4: "Emit zero mass on catalogue pixels and keep >=3 px from them unless AXIS=PRUNE."

**Observed:** Parent R0 `h33-h33-2-b2` (verified sha `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) has **0 within 2 px** (min dist 2.236) but **2,171 within 3 px (5.76%)** — see `data/registry/h33_education.tif` vs `data/bridge/existing_faults.tif` distance_transform_edt. This matches the ledger climb description "none within 2 px" and the forensic note "100% identical off-catalogue geometry outside 2 px". At 0.28 DTI, dots at 2-3 px still receive triangular kernel credit ~0.0-0.33, so pruning them is not cost-free.

**Decision:** This session's **MASS axis** variants (drop/add 10-20%) **inherit parent's 2 px collar (dist>2)** to hold "one change from named parent" invariant; changing both mass and collar would confound the MASS effect. A future **PRUNE axis** session should test 2 px→3 px move (drop 2,171 dots, 5.76%, refill to count if PRUNE-3px) as its own experiment.

**Evidence:** `scripts/generate_axis_variants.py` logs `dots <=2:0 <=3:2171` on restore; validator `test_06_zero_wasted_dots_inside_200m` expects 0 within 2 px, not 3 px.

## IR-88-15 — Manifest vs repo data_manifest (2026-10-23)

**Reported:** Brief v2 §4.2: "only files pinned in registry/data_manifest.json (or repo's equivalent); verify sha256 before use."

**Observed:** Repo has no `registry/data_manifest.json`; the checked-in equivalent is `docs/evidence/GEMSDOE32__registry__data_manifest.json` plus `scripts/restore_inputs.py`. For this CONCENTRATION session the grid, R0 mirror, D2.8 ancestor, and official 19-band feature raster were restored only from immutable GitHub owner-mirror refs and matched pins `2176d08e…`, `7ba308cc…`, `c55bafc…`, `91eae1ca…`, and `4371c82e…`.

**Decision:** Added the pinned D2.8 ancestor to `restore_inputs.py` so R0 is rebuilt, not merely copied. The parent rebuild matched SHA-256 exactly. No external source or unpinned byte was used.

## IR-88-16 — TOP_PUBLIC stale in prompt (2026-10-23)

**Reported:** Brief's `TOP_PUBLIC = ____` (human fills). Prompt-era note `site_reported_high 0.3195` is stale.

**Observed:** Automated `registry/leakage_canaries.json` not relevant; `run_card.json` and `docs/status.json` record `competition_leaderboard_high 0.4413` (#1 xiaofanhu, 2026-10-22). No scraped leaderboard; URL cited only.

**Decision:** README CURRENT STATE cites 0.4413 as TOP_PUBLIC with date and instructs re-check on competition page; no automated fetch performed per §4.1 ban.

## IR-88-17 — Reported block-density CV lacked a definition (2026-10-23)

**Reported:** The inherited slot plan said the best files “reportedly sit at 0.51–0.59” and called H33 CV ~0.55, without naming whether zero-density blocks, partial footprint blocks, or occupied blocks were included.

**Observed:** For exact R0 at 1 km (10×10 pixel) blocks, CV is **1.874001** over dot density in all 50,984 complete-footprint blocks and **0.618596** when zero-density blocks are excluded. Neither reproduces ~0.55. CONCENTRATION 10/15/20% changes the all-block CV to 1.724230/1.641677/1.557219.

**Decision:** Use the standard, reproducible all-complete-block definition as the primary report and retain occupied-block CV as a secondary diagnostic. Do not tune candidates to an undefined historical range.
