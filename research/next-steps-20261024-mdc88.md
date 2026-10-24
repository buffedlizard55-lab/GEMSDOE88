# Remaining work, blockers and access needed — after MDC-88 (2026-10-24)

> **Supersession note (2026-10-24 multipass review):** The proposed H-QTS work below is a historical next-step handoff, not authorization to switch the current method lane. The prompt does not include the promised single-method paragraph; the full feature stack is absent in a clean checkout; and the literal no-dense-exemption uniqueness rule blocks every nonempty candidate at 1.0 overlap with `dense_17gemdoe.tif`. The earlier statement that `registry/kdmc_gate.json` is `ok_to_submit: true` is specific to a different gate interpretation and is not sufficient for current submission clearance. Do not promote MDC-88 or start H-QTS until the lane/data contract and uniqueness policy are explicitly resolved. See [`repo-review-20261024-multipass.md`](repo-review-20261024-multipass.md).

## Immediate next steps (in order)

1. **Run H-QTS** (`research/candidate-hypotheses-20261024-mdc88.md`, rank 1): decoupled
   cover-thickness gradient `|∇z_base|·(1 − cos∠(∇z_base, ∇z_surface))` at σ = 1/3/6 px, added to
   `gems88.kdmc.build_feature_stack`, re-fit, re-score with `scripts/run_kdmc_experiment.py
   --seeds 20 21 --separations 2.8284271247461903 --budgets 0.0073 0.01 0.015`. Everything needed is
   already restored and cached; this is a one-command experiment once the columns are added.
2. **Promote or reject** `gemsdoe88-mdc88-pu-concentration-2p83px-20261024T0740Z-zeros-DO-NOT-SUBMIT.tif`
   through the weekly-slot selector (protocol rule 6 keeps that decision outside the run).
   `registry/kdmc_gate.json` already says `ok_to_submit: true`.
3. **Paste the first organizer receipt** into `ledger/submissions.csv`. The ledger has 66 rows and
   **0** receipts; without one, no number in this repository can be calibrated to the leaderboard.
4. **Reconstruct the two missing external rasters** (IR-88-75) or delete the code paths that need
   them: `acquisition_block_id_100m.tif` (from USGS GeoDAWN survey block polygons) and
   `tiger_road_distance_m.tif` (from US Census TIGER/Line roads). Until then
   `src/gems88/features.py` is dead code and every `H88-ADHR` number is unreproducible.
5. **Fix `scripts/restore_inputs.py --validation`** so it either validates the external group or
   refuses to report `PIN OK` for a manifest it did not check.

## Blockers that this environment cannot clear

| Blocker | Why it blocks | What access would clear it |
|---|---|---|
| `drivendata.org` unreachable | `TOP_PUBLIC`, the rolling-week slot balance, the Round 1/2 deadlines and forum thread 11516 (the catalogue-masking claim in `metric.py`) are all unverifiable from here | network access to `drivendata.org`, or a human pasting the leaderboard row and a submission receipt |
| 0 organizer receipts | every figure is `HOLDOUT-DTI` / `PROXY` / `MODEL`; the mapping from holdout to public score is unknown, so "will this beat 0.2778 / 0.3195 / 0.4413" is unanswerable | one scored submission |
| `acquisition_block_id_100m.tif`, `tiger_road_distance_m.tif` absent from every pinned source | the documented 67-feature stack cannot be rebuilt | the original producing script, or official GeoDAWN block polygons + TIGER/Line |
| 2 cores / 3 GB RAM, no `lightgbm`, no GPU | model capacity and the number of hide draws are compute-limited; a U-Net like the official reference solution is out of reach | more compute, or `segmentation_models_pytorch` + a GPU |
| Competition labels for the hidden set | by design | none — this is the task |

## Known limitations of what was delivered

* **The holdout is not the task.** It hides whole *mapped* fault components; the competition scores
  *unmapped* faults. It is unbiased for what it measures and is the best instrument available, but
  the transfer coefficient to the public score is unknown and unmeasured.
* **The collar decision rests on a proxy.** The blocked holdout returns exactly `0.00000` for every
  collar arm by construction, so it cannot rank them. The off-catalogue SGMC proxy can, and prefers
  collar 0 by `0.0497`, but 65 % of the naive proxy margin was shown to be circular
  (`sgmc_logdist` is a feature and the proxy truth is SGMC-derived); only the SGMC-free control
  (`+0.0243` over `h33`) is quoted. A conservative 3 px-collar file is published alongside.
* **The uniqueness inventory is the public, accessible one.** Private or unlinked organizer
  submissions cannot be observed, so "unique" means unique against 23 hash-pinned public rasters.
* **The leakage canary bounds single-feature leakage only.** It cannot exclude a leak that exists
  only in a feature *interaction*; the mitigation here is structural — zero catalogue-derived
  features — rather than statistical.

## Reconciliation with gate v3 (added after merging `origin/main`)

`main` merged a slot policy (`src/gems88/gate.py`, `gems88-gate-v3`) while this branch was in
review. The MDC-88 candidate is now judged by that shared module rather than by a second private
policy, and the verdict is split into **three** machine fields instead of one:

| field | value | meaning |
|---|---|---|
| `ok_to_download` | **true** | the saved bytes re-open as a valid single-band GeoTIFF on the pinned grid (writer 15/15 + an independent 19/19 re-read + gate v3's portal-parity validator) |
| `ok_to_submit` | **true** | the portal will accept it **and** it is unique like-for-like against all 33 registry rasters |
| `recommended_for_weekly_slot` | **false** | gate v3's stricter slot policy: `HOLDOUT-DTI 0.14885` is under the stored `0.18789` H88-ADHR bar, and the fleet fingerprint screen fails at `share_gt25 = 0.222 < 0.35` |

Conflating the last two is what kept every candidate in this repository marked DO NOT SUBMIT.

Two consequences for the next session:

1. **The slot bar itself is unverifiable.** `0.18789` is H88-ADHR's stored number, and IR-88-75 shows
   that stack cannot be rebuilt on a clean checkout. It is applied as written rather than silently
   relaxed, but it should be re-derived from a reproducible lane as soon as one exists. H-QTS on top
   of MDC-88 is the cheapest route to that.
2. **The fingerprint screen is the second thing to design for, not against.** `share_le2 == 0` is
   free (set `--collar-px 2`); `share_gt25 >= 0.35` is the real constraint and the primary reaches
   only `0.222`. That is a statement about where the density model puts its mass, so it is a model
   problem — again H-QTS, whose whole premise is buried structure far from mapped traces.

### Why the MDC-88 raster is NOT added to `registry/inventory.json`

`scripts/validate_release.py` asserts that the inventory's hash set is byte-identical to a frozen
pre-placement surface audit, so appending to it invalidates that audit
(`test_project.py::test_real_card_stays_blocked`). It is unnecessary anyway:
`src/gems88/registry_paths.py::registry_list` globs `docs/downloads/*.tif`, so the published
candidate is already visible to every future gate-v3 uniqueness check (it was counted among the 33
rasters in this session's own run). The collar-3 research variant stays out of both, by design.
