# IRREGULARITIES — items that change a decision

## IR-88-17 — The MASS ranking is not the parent's ranking (2026-10-23)

**Reported:** Brief v2 §5: MASS variants drop/add "by the parent's own ranking (rebuild the ranking from the recorded recipe if it is not stored)".

**Observed:** R0's model score is not recoverable. Every raster in the H33 lineage is binary — `19GEMSDOE__h19-5-*`, `dotted_d2_8_02600` (44,090), `dotted_d2_8_02708` (40,199), `GEMSDOE32__h33-2-b2` (37,654) — and the files nest strictly (R0 ⊂ 0.2708 ⊂ 0.2600). The lineage therefore encodes only a partial order over dots that were *already dropped*, and cannot rank the 37,654 that remain. `scripts/generate_axis_variants.py` substituted a synthetic score, `0.6*clip(d_catalogue_px/50) + 0.4*uniform(seed)`, which `AI_USE.md` disclosed but `SLOT_PLAN.md` and `ledger/mechanism_cards.json` then described as "the parent ranking" with low-rank dots attributed to "low p_oof and low q_oof".

**Decision:** The three files stand (they are gated, reproducible and bit-exactly reconstructible), but their mechanism cards, predicted signs and slot recommendations are rewritten from measurement. `scripts/audit_mass_ranking.py` reproduces each shipped array bit-for-bit from the formula (`identical_to_on_disk: true` for all three), so the artifacts are sound even though the interpretation was not. No new MASS rasters were emitted this session: (AXIS, value) pairs are built once, and rebuilding the same values would burn the dedupe rule for no new information.

**Evidence:** `registry/mass_ranking_audit.json` — 89.4% of m10minus's dropped dots lie within 10 px of the catalogue vs a 30.2% baseline; Jaccard 0.167 against a seed swap, so the drop set is majority noise; dropped dots have a *higher* independent prior (0.561) than the parent mean (0.400).

## IR-88-18 — m10minus is a PRUNE experiment wearing a MASS label (2026-10-23)

**Reported:** The MASS axis was assigned to measure mass elasticity, holding everything else fixed.

**Observed:** Because the ranking is 60% distance-to-catalogue, the "lowest-ranked 10%" is a near-catalogue deletion: mean 5.69 px dropped vs 31.59 px kept, 2.96x enrichment inside 10 px. It changes mass *and* collar position together. m20minus is the same ranking cut deeper, so the pair is nested rather than independent.

**Decision:** m10minus is reclassified in the ledger as a collar-extension probe and is the only one of the three recommended for a slot, on the strength of the one measured live gain in the ledger (0.2708 → 0.2778 after deleting dots within 2 px of the catalogue, CLAIM). m20minus is held: it is not an independent read. m10plus is withdrawn from slot contention (see IR-88-19). A clean PRUNE axis session should own 3/4/5 px values and must not be confused with these.

**Evidence:** `ledger/submissions.csv` (`ranking_basis`, `recommendation` columns); audit Q2.

## IR-88-19 — m10plus adds isolated, lowest-prior dots and is predicted to lose (2026-10-23)

**Reported:** m10plus was recorded as "+0.004, tests whether parent under-calls near high-prior tip zones".

**Observed:** The 3,765 added dots have mean catalogue distance 74.2 px, mean distance to the nearest parent dot 20.6 px, 85.2% beyond the 3 px kernel from any parent dot, and mean independent prior 0.119 against 0.400 for the parent. They are not in tip or relay zones; they are the most isolated, lowest-prior positions in the pool. Under the exact algebra an addition pays only if its credit exceeds 0.2·DTI = 0.0556, i.e. unseen truth within 2.83 px.

**Decision:** predicted change corrected from +0.004 to -0.010 (MODEL, range [-0.014, +0.002]) and the file is marked DO NOT SPEND A SLOT. The stated mechanism was never implemented, so submitting it would spend a slot to re-learn that random mass costs score — which the ledger already establishes across files scoring 0.00-0.19.

**Evidence:** audit Q4 and `sensitivity.MASSm10plus` in `registry/mass_ranking_audit.json`.

## IR-88-20 — The brief's NaN-outside file fails this repository's own gate; the -zeros twin passes both (2026-10-23)

**Reported:** Brief v2 §5/§7 require NaN outside the footprint in `releases/<id>.tif`, with `-zeros.tif` as a fallback.

**Observed:** `vendor/gems57/gates.py` enforces a stricter all-finite export policy and reports `ok: False` for the NaN primaries ("7111787 NaN/infinite pixels"; "nodata tag outside all-finite [0,1] policy"), while the same content as `-zeros` passes `gates.format_report` and `validate.validate` with `all_checks_passed: true`. The gate text itself concedes "public spec permits outside-footprint NaN". The two twins are bit-identical inside the footprint, and the ledger records that NaN-outside and zeros-outside twins score identically live.

**Decision:** `docs/SUBMIT.md` now directs the human to upload the **`-zeros`** file. It satisfies the organiser spec, this repository's preflight, and the ledger's observation that the twin scores the same. Keeping the NaN primary as the named artifact would mean the only file a preflight accepts is the one labelled "fallback".

**Evidence:** `gates.format_report` on both twins; `scripts/validate_release.py` semantics.

## IR-88-21 — The gap to TOP_PUBLIC is 16x larger than any measured effect (2026-10-23)

**Reported:** Objective is to raise the live score of the incumbent (CLAIM 0.2778).

**Observed:** TOP_PUBLIC is 0.4413 (#1 xiaofanhu, 2026-10-22, per `registry/run_card.json`), a gap of 0.1635. The largest live improvement anywhere in the ledger is +0.007 (the 2 px prune). Brief §5 says to treat a live change under 0.01 as no evidence. Every controlled dot edit in the ledger — prune, thin, solo, the 76-81 lanes — is below that floor, and the three MASS variants are predicted at |Δ| ≤ 0.010.

**Decision:** `SLOT_PLAN.md` states plainly that dot-level edits cannot close a 0.1635 gap, caps MASS at one slot this week, and puts the remaining slots on the two structural questions that could move the score by more than the floor. It also records the option of not spending slots at all, which is a legitimate use of a scarce quota.

**Evidence:** `ledger/submissions.csv`; `registry/run_card.json`; brief §5 evidence rule.

## IR-88-14 — Hard constraint 4 vs parent R0 (2026-10-23, this session)

**Reported:** Brief v2 §4.4: "Emit zero mass on catalogue pixels and keep >=3 px from them unless AXIS=PRUNE."

**Observed:** Parent R0 `h33-h33-2-b2` (verified sha `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) has **0 within 2 px** (min dist 2.236) but **2,171 within 3 px (5.76%)** — see `data/registry/h33_education.tif` vs `data/bridge/existing_faults.tif` distance_transform_edt. This matches the ledger climb description "none within 2 px". At 0.28 DTI, dots at 2-3 px still receive triangular kernel credit ~0.0-0.33.

**Decision:** This session's **MASS axis** variants **inherit parent's 2 px collar (dist>2)** to hold "one change from named parent" invariant; changing both mass and collar would confound the MASS effect. A future **PRUNE axis** session should test 2 px→3 px (drop 2,171 dots, 5.76%) as its own experiment. Note IR-88-18: m10minus has already partly done this by accident.

**Evidence:** `scripts/generate_axis_variants.py` logs `dots <=2:0 <=3:2171` on restore.

## IR-88-15 — Manifest vs repo data_manifest (2026-10-23)

**Reported:** Brief v2 §4.2: "only files pinned in registry/data_manifest.json (or repo's equivalent); verify sha256 before use."

**Observed:** Repo has no `registry/data_manifest.json`; equivalent is `scripts/restore_inputs.py` SOURCES dict with SHA pins. All six mirror groups verified this session (`RESTORED/PIN OK` for grid, features, witness, h33, external, registry_60 = 62 rasters), including `training_features.tif` (`4371c82e...`), which the previous revision of this file marked UNVERIFIED. R0 was rebuilt and matched `c55bafc4...` exactly (37,654 dots).

**Decision:** No external fetch beyond GitHub owner mirrors. All pins verified; the UNVERIFIED note is withdrawn.

## IR-88-16 — TOP_PUBLIC stale in prompt (2026-10-23)

**Reported:** Brief's `TOP_PUBLIC = ____` (human fills). Prompt-era note `site_reported_high 0.3195` is stale.

**Observed:** `run_card.json` and `docs/status.json` record `competition_leaderboard_high 0.4413` (#1 xiaofanhu, 2026-10-22). No scraped leaderboard; URL cited only.

**Decision:** README CURRENT STATE cites 0.4413 as TOP_PUBLIC with date and instructs re-check on competition page; no automated fetch performed per §4.1 ban.
