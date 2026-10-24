# Remaining work, blockers and access needed — after MDC-88 (2026-10-24)

## Immediate next steps (in order)

1. **Run H-QTS** (`research/candidate-hypotheses-20261024-mdc88.md`, rank 1): decoupled
   cover-thickness gradient `|∇z_base|·(1 − cos∠(∇z_base, ∇z_surface))` at σ = 1/3/6 px, added to
   `gems88.kdmc.build_feature_stack`, re-fit, re-score with `scripts/run_kdmc_experiment.py
   --seeds 20 21 --separations 2.8284271247461903 --budgets 0.0073 0.01 0.015`. Everything needed is
   already restored and cached; this is a one-command experiment once the columns are added.
2. **Promote or reject** `gemsdoe88-mdc88-pu-concentration-2p83px-20261024T0740Z-zeros.tif`
   through the weekly-slot selector (protocol rule 6 keeps that decision outside the run).
   `registry/kdmc_gate.json` already says `ok_to_submit: true`.
3. **Paste the first organizer receipt** into `ledger/submissions.csv`. The ledger has 66 rows and
   **0** receipts; without one, no number in this repository can be calibrated to the leaderboard.
4. **Reconstruct the two missing external rasters** (IR-88-72) or delete the code paths that need
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
