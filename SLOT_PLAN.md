# SLOT_PLAN — one entity; <=3 scored uploads per rolling week

**`2026-10-24` · twelve sessions merged: three `PRUNE` sessions this week — spaced-v2 collar×spacing (`#51`, IR-88-54), spacing-lock ladder + order control + slot-2 artifact recovery (`#52`, IR-88-55), and the interior-annulus bracket on `R0` (this PR, IR-88-56, latest).** All `15` manifest pins verified; `R0 = h33-h33-2-b2` rebuilt byte-exactly (`zeros c55bafc4…`, NaN `baeae321…`, `37,654` dots; `1,611` strictly `<3 px` per IR-88-47's corrected count); gate-clean `R1 = PRUNEp3px-6f7ae705` (`min d_cat 3.1623 px`) re-derived and SHA-asserted before editing. Ledger: **`64`** built rows across all 7 brief axes, **`0`** portal receipts, zero `(parent, axis, value)` and zero SHA-256 collisions. Nothing below is a score: `R0 0.2778` is a **CLAIM**; every variant number is `PROXY`/`MODEL`.

**Human must supply before any upload:** current `TOP_PUBLIC` + date (blank in both recent briefs; the repo's `0.4413` of `2026-10-22` is stale and `UNVERIFIED`, IR-88-49), the real rolling-week/total slot balance, permission to use/redistribute the owner's public mirrors, and confirmation of the `2026-12-03` deadline. No automated page access, no submission, no credentials.

## The `PRUNE` spaced-refill family is the only live lever — and it is now priced in two directions
Why `PRUNE` at all: `R0` keeps `2,171` dots at `2 < d <= 3 px`, so every non-`PRUNE` child inherits a sub-`3 px` collar (brief §4.4, IR-88-47); `MASS`, `CONCENTRATION`, `SNAP`, `RELIEF`, `SPACING` and `TRACKB` are all closed as slot axes on this lineage. Both sessions varied the same two knobs of one recipe (collar purge → spacing-locked refill, `N = 37,654`, union H19-5/H19-4/H16-1 pool), with predictions frozen before any proxy (`registry/prune_v2_preregistration.json`, `registry/prune_spacing_dose_preregistration.json`).

| Arm | Collar | Lock | Edit | blind `SGMC` `PROXY` vs `R0 0.096060` | field `w` |
|---|---|---|---:|---:|---:|
| `p3norefill fb308615` | 300 m | — | −2,171, no refill | `0.093643` (−0.00242) | −0.0157 |
| `p3space28 91d221ad` | 300 m | 2.8 px | +2,171 | `0.099446` (+0.00339) | −0.0094 |
| `p3.5space35 44be814e` | 350 m | 3.5 px | +2,702 | `0.101339` (+0.00528) | −0.0150 |
| `p3space35 49fff49b` | 300 m | 3.5 px | +2,171 | `0.101042` (+0.00498) | −0.0112 |
| `p3space35rand 8b3d0a40` | 300 m | 3.5 px, **random order** | +2,171 | `0.101146` (+0.00509) | −0.0135 |
| `p3space45 7a281bde` | 300 m | 4.5 px | +2,171 | `0.101629` (+0.00557) | −0.0126 |
| `p4space28 475fce4d` | 400 m | 2.8 px | +3,825 | `0.100907` (+0.00485) | −0.0210 |
| **`p4space35 07bd8182`** | 400 m | 3.5 px | +3,825 | **`0.102454` (+0.00639)** | −0.0228 |
| `R1 = PRUNEp3px 6f7ae705` | densified refill | — | +2,171 | `0.096083` (+0.00002) | — |

**What the joint grid says.** (1) **Spacing pays, then saturates:** at a fixed 300 m collar `2.8 → 3.5 → 4.5 px` gives `+0.0034 → +0.0050 → +0.0056`; the second half of the ladder buys `0.00059`, a tenth of the `0.01` floor. (2) **Collar width is non-monotone but the best cell is the widest pair:** `+0.0064` at `400 m × 3.5 px` vs `+0.0053` at `350 m × 3.5 px` and `+0.0049` at `400 m × 2.8 px` — consistent with both knobs acting on one latent variable. (3) **That variable is distance from the surviving mass, not mutual refill spacing:** refill-pair nearest neighbours average `17-19 px` (the lock almost never binds), while the distance to the nearest surviving `R0` dot rises `5.9 → 7.2 → 8.7 px` and the share of additions still on the saturated H19-5 support falls `20.9% → 6.5% → 8.6%` (`evidence/prune_spacing_dose_geometry.json`). (4) **The label-free field is worthless here:** `p3space35rand` — identical donors, collar, count, pool and lock, seeded random refill order — lands `0.000104` from the ranked `p3space35`, replicating the MASS random-donor control (`±0.0018`). Stop ranking refills with `w`; a random or maximin order is equivalent and cheaper. (5) Both sessions still see `w` and blind `SGMC` disagree in sign, and every arm is **inside the `0.01` no-evidence band**, so **`PRUNE` spacing is closed as a build axis**: no further lock or collar dose is worth a slot.

**Duplicate reconciliation (IR-88-55):** the two sessions independently built `p3space28` and emitted **byte-identical rasters** (`91d221ad…`/`47b49e84…`, blind `0.099446` in both). This PR withdraws its own row/receipt/card for that arm, keeping the merged `20261023` row — the same move IR-88-53 made for the duplicated MASS arms — so the ledger stays free of repeated `(parent, axis, value)` pairs and duplicate hashes.

**Artifacts:** `scripts/rebuild_prune_spaced_artifacts.py` rebuilds the two ledgered spaced arms that were **absent from the checkout** and reproduces their recorded hashes byte-exactly (`p3space35 49fff49b…`/zeros `e0b9d59b…`, `p4space35 07bd8182…`/zeros `fb7ee110…`), hardened PASS on disk (`evidence/prune_spaced_artifact_rebuild.json`). The whole family is therefore upload-ready in this clone; nothing is left to reconstruct.

## This session: `PRUNE` interior-annulus bracket on `R0` — built, gate-validated, closed (IR-88-56)
The collar curve had no points between `R0` (2 px) and `R1` (3 px). Pixel-centre Euclidean distances inside that annulus take only three values, so the `2,171` annulus dots split exactly into bands of `941` (sqrt5 = 2.236 px / 224 m), `670` (sqrt8 = 2.828 px / 283 m) and `560` (3.0 px / 300 m). Three fixed-count (`N=37,654`) exact-marginal-DTI refill arms were preregistered (`registry/prune_interior_preregistration.json`, MODEL frozen before any proxy) and built from byte-exact `R0` with the shared four-line field (canary max `0.56925`, identical to the prior sweep):

| Arm | Edit (moved %) | min `d_cat` | blind SGMC `PROXY` vs `R0 0.096060` | hide-recover `PROXY` | CV 12 km | MODEL |
|---|---:|---:|---:|---:|---:|---:|
| `p2.236px` `93b15124` | `941` removed (2.50%) | 2.8284 px | `0.096219` (**+0.00016**) | `0.000773` (CI `0.000641–0.000907`) | 0.5610 | +0.002 |
| `p2.828px` `b1ddf491` | `1,611` removed (4.28%) | 3.0000 px | `0.095977` (**−0.00008**) | `0.000000` (structurally, IR-88-20) | 0.5648 | +0.004 |
| `p5px` `2a5469c0` | `5,637` removed (14.97%) | 5.0990 px | `0.089464` (**−0.00660**) | `0.000000` | 0.6195 | −0.020 |

**Verdict: the 2–3 px annulus is proxy-neutral, and the outer descent is monotone.** (1) Both interior arms move blind SGMC by less than the `~0.0003` instrument noise yardstick (IR-88-51); `p2.236px` matches `R1`'s `+0.00023` while purging `43%` as many dots — no sharp 300 m boundary is visible to the control, so a future `R1` receipt prices the refill/spacing lineage, not a special kernel-radius edge. (2) Hide-and-recover credit survives only while sub-`2.828 px` dots remain (`p2.236px`), then collapses to the structurally-zero value every gate-clean arm shows. (3) `p5px` deepens the outer-collar descent already measured at `p3.7/p4.3` (`-0.00119 → -0.00350 → -0.00660` SGMC), sign-correct against its preregistered `MODEL -0.020`, and pushes `CV_12km` to `0.6195`, outside the reported `0.51–0.59` best-file band. Hardened validator 6/6 PASS on disk bytes (`registry/prune_interior_validation.json`); independent from-scratch rerun reproduces all three masks bit-for-bit; report `evidence/prune_interior_report.json`. **No arm enters the queue** — the largest delta is below the `0.01` no-evidence floor; the queue below is unchanged and the interior-collar question is closed.

## Next three slots
| Order | File | What the receipt changes |
|---|---|---|
| 1 | `PRUNEp3px 6f7ae705` (`R1` anchor) | Parents 27 ledgered children. `>= +0.01` supports the collar+refill lineage; `<= -0.01` closes it and demotes every `R1` child; `|Δ| < 0.01` is inconclusive and slot 2 disambiguates by pair. |
| 2 | **`PRUNEp4space35 07bd8182`** (peak `+0.0064`, rebuilt this session, upload-ready) — or `PRUNEp3.5space35 44be814e` (`+0.0053`, built by #51) if the human prefers the smaller 350 m collar edit | `>= +0.01` over `p3px` means the spaced refill pays and the final file should be the widest-collar spaced arm; `<= -0.01` closes the family outright. |
| 3 | conditional on a slot-2 win: the other collar arm (`3.5` vs `4.0 px`) | Pairs with slot 2 to price collar width, the only unmeasured knob left in this family; otherwise conserve — every other axis is closed. |

## HOLD / off-queue (this PR, IR-88-56; earlier closures per their IR entries)
The interior bracket `p2.236px 93b15124` / `p2.828px b1ddf491` / `p5px 2a5469c0` is `HOLD`: the `2–3 px` annulus is blind-proxy-neutral (both interior deltas inside the `~0.0003` noise yardstick) and every `|delta|` is below the `0.01` floor, so no interior arm is queued. All previously closed axes remain off-queue: `MASS` both parents (IR-88-52), `CONCENTRATION` (IR-88-52), `SNAP` dose negative and fixpoint/control (IR-88-51), `TRACKB` Phase-2 only, `SPACING` diagnostics, plus the `p3norefill`/`ridge2px` diagnostics.

## Weeks to `2026-12-03` (~6 weeks)
`wk1 (now)`: run slots 1–2 — the ledger is still entirely unpriced, which is the largest single risk. `wk2–3`: slot 3 by receipt; if a spaced arm wins, spend the next slot on the collar pair, not on a new field. `wk4–5`: combine two axes only after each has an independent `>= 0.01` receipt on a gate-clean parent, naming the true parent. `wk6`: confirm the leader twice, choose ONE blind final + a fallback twin, re-validate both from disk with the hardened validator. `TRACKB` remains Phase-2 geologist review only.

## Better axes — proposals only, none built here
**NOVELTY_RADIUS** (successor to this family): set the *distance from every surviving dot* directly (`6/8/10 px`) with a random or maximin order, since the two knob sweep is really one radius. Confounder: displacement itself, not novelty of ground, may be what the blind instrument rewards (IR-88-51). Falsifier: no `>= 0.01` live gain over `p4space35` and no monotone ordering across the three radii. **INSTRUMENT_AUDIT** (cheapest unknown): one seeded `1 px` random-jitter twin of a gate-clean parent beside a receipted crest arm — until a receipt lands, no proxy here can be ordered at all. **RE-MAP GAP**: refill into the largest empty 1 km blocks instead of by ridge support (post-`CONCENTRATION` mirror result). Falsifier: no gain over a random-receiver control at matched CV. **LIVE_COLLAR_PAIR** (IR-88-56): if the `R1` anchor receipt is inconclusive (`|delta|<0.01`), spend a later slot on `p2.236px 93b15124` as its paired read — blind SGMC cannot separate a partial (`941` purged) from a full (`2,171` purged) collar (`+0.00016` vs `+0.00023`); falsifier: both receipts within `0.01` of each other and of `R0`, closing the collar question privately too.

**Evidence discipline:** RECEIPT > CLAIM > PROXY > MODEL; `|live delta| < 0.01` is no evidence; dedupe on exact hash and `(parent, axis, value)` only; the human uploads at most one file per slot.
