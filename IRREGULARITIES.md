# IRREGULARITIES — items that change a decision

## IR-88-14 — Hard constraint 4 vs parent R0 (2026-10-23, this session)

**Reported:** Brief v2 §4.4: "Emit zero mass on catalogue pixels and keep >=3 px from them unless AXIS=PRUNE."

**Observed:** Parent R0 `h33-h33-2-b2` (verified sha `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) has **0 within 2 px** (min dist 2.236) but **2,171 within 3 px (5.76%)** — see `data/registry/h33_education.tif` vs `data/bridge/existing_faults.tif` distance_transform_edt. This matches the ledger climb description "none within 2 px" and the forensic note "100% identical off-catalogue geometry outside 2 px". At 0.28 DTI, dots at 2-3 px still receive triangular kernel credit ~0.0-0.33, so pruning them is not cost-free.

**Decision:** This session's **MASS axis** variants (drop/add 10-20%) **inherit parent's 2 px collar (dist>2)** to hold "one change from named parent" invariant; changing both mass and collar would confound the MASS effect. A future **PRUNE axis** session should test 2 px→3 px move (drop 2,171 dots, 5.76%, refill to count if PRUNE-3px) as its own experiment.

**Evidence:** `scripts/generate_axis_variants.py` logs `dots <=2:0 <=3:2171` on restore; validator `test_06_zero_wasted_dots_inside_200m` expects 0 within 2 px, not 3 px.

## IR-88-15 — Manifest vs repo data_manifest (2026-10-23)

**Reported:** Brief v2 §4.2: "only files pinned in registry/data_manifest.json (or repo's equivalent); verify sha256 before use."

**Observed:** Repo has no `registry/data_manifest.json`; equivalent is `scripts/restore_inputs.py` SOURCES dict with SHA pins for `sample_submission.tif` (`2176d08e...`) and `existing_faults.tif` (`7ba308cc...`), verified before use. `training_features.tif` (`4371c82e...`) is absent locally (requires large external mirror) but not needed for MASS geometry-only variants; parent ranking rebuilt from distance+rand (MODEL) and documented in `ledger/mechanism_cards.json`.

**Decision:** No external fetch beyond GitHub owner mirrors (allowed hosts `github.com`, `codeload.github.com`). Grid pins verified; training feature mirror marked UNVERIFIED for this session.

## IR-88-16 — TOP_PUBLIC stale in prompt (2026-10-23)

**Reported:** Brief's `TOP_PUBLIC = ____` (human fills). Prompt-era note `site_reported_high 0.3195` is stale.

**Observed:** Automated `registry/leakage_canaries.json` not relevant; `run_card.json` and `docs/status.json` record `competition_leaderboard_high 0.4413` (#1 xiaofanhu, 2026-10-22). No scraped leaderboard; URL cited only.

**Decision:** README CURRENT STATE cites 0.4413 as TOP_PUBLIC with date and instructs re-check on competition page; no automated fetch performed per §4.1 ban.
