# SLOT_PLAN — one entity; at most 3 scored files per rolling week

**2026-10-23 · AXIS=SNAP on gate-clean `R1` · 3 new variants, all above parent on the blind control.**
All 15 manifest pins verified; `R0 = h33-h33-2-b2` rebuilt byte-exactly (zeros `c55bafc4…`, NaN `baeae321…`,
37,654 dots) and `R1 = PRUNEp3px` (`6f7ae705…`/`dc6f090d…`) re-derived and SHA-asserted before any edit.
Ledger: **35** built rows, **0** portal receipts. `origin/main` re-checked immediately before building (IR-88-39).

**Budget/target:** TOP_PUBLIC **not supplied in the current brief** (repository's older `0.4413` of 2026-10-22 is
stale and UNVERIFIED — human must re-read the leaderboard). Slots left this rolling week / total: **unknown**;
deadline **2026-12-03 human-confirmation pending**. Human checks the competition page and rules; no automated
access. One blind final file; primary and zeros twin are alternatives, never two slots.

## Session findings (AXIS=SNAP, parent R1, preregistered in `registry/preregistration_snap_r1_scarp.json`)

The spacing-locked scarp re-centering of R0 (`SNAPscarp2px-fae77ff4`) was the only built candidate above R0 on
the blind off-catalogue USGS SGMC control — but every R0-parented non-PRUNE arm is HOLD under the literal ≥3 px
rule (IR-88-43). Transplanting the **same field** (`edge_scarp_pot` = 0.42·b19 slope + 0.23·b12 Hessian ridge +
0.20·b18 iso-grav HG + 0.15·b3 TMI HG, provided bands only, zero external LiDAR) and the **same deterministic
spacing-locked allocator** onto `R1` (all dots ≥3.1623 px) yields the first fully gate-clean family that beats
its parent on the blind control. The R0 winner itself was rebuilt in-run and reproduced exactly (30,889
displaced; SGMC 0.096806 = published).

| Arm (parent R1) | Moved | Mean disp. | Blind SGMC `PROXY` (R1 = 0.096083, R0-scarp = 0.096806) | 12 km CV | Pre-reg `MODEL` | w-field Δ `MODEL` |
|---|---:|---:|---:|---:|---:|---:|
| `SNAPscarp1px-1944aaf5` | 26,323 (69.91%) | 0.699 px | **0.097567** (+0.00148 vs R1) | 0.5710 | +0.003 | −0.035 |
| `SNAPscarp2px-c003d7d7` | 31,742 (84.30%) | 1.344 px | **0.097453** (+0.00137 vs R1) | 0.5715 | +0.006 | −0.077 |
| `SNAPridge2px-f4af84a3` | 6,567 (17.44%) | 0.211 px | **0.096548** (+0.00047 vs R1) | 0.5699 | +0.002 | −0.001 |

**Reading.** (1) All three arms beat R1 blind; the off-support crest arms beat the intra-support control,
replicating the R0 ordering (scarp > ridge) on a second parent — the gain is re-centering onto the physical
scarp emergence, not mere de-jittering inside the detector's ribbon. (2) `scarp1px` ≥ `scarp2px` by 0.000114 —
**a proxy-level tie**; the preregistered dose rule nominates the 1 px arm (lower overshoot risk, half the
displacement), receipts must arbitrate. (3) The in-house physics field w condemns exactly what the blind
control rewards (−0.03…−0.08 w-MODEL vs +0.0015 SGMC): w pays 0.045+ on H19-5 support and 0.015 off it, while
23k–30k snapped dots leave support for topographic crests — third confirmation that w must not judge geometry
edits (AUC 0.47 blind, IR-88-38/41). (4) Holdout proxy is structurally 0.0 for every >3 px file (IR-88-20);
SGMC/CV remain report-only, never gates.

## Next three slots — conditional sequence, not three automatic uploads

Prerequisites for EVERY upload (unchanged from the 2026-10-23 audit): human confirms quota/deadline/TOP_PUBLIC
on the competition pages; privately rebuilds the artifact (`python3 scripts/build_snap_r1_scarp_variants.py`,
deterministic) or restores it, matches the recorded SHA-256 / pixel content, and re-runs
`python3 scripts/validate_variant.py` on the actual bytes. A live |Δ| < 0.01 is **no evidence**.

| Order | File (MODEL vs parent) | What a receipt changes |
|---|---|---|
| 1 | `…-SNAPscarp1px-20261023-1944aaf5` (+0.003 pre-reg; blind SGMC top of inventory) | **≥ +0.01 vs the human's best live score:** scarp re-centering is live; slot 2 = `scarp2px-c003d7d7` to arbitrate dose and pick the final-file geometry. **\|Δ\| < 0.01:** slot 2 = `R1 (PRUNEp3px-6f7ae705)` for attribution (snap-neutral vs snap-blind public chunks). **≤ −0.01:** re-centering hurts live; slot 2 = `R1`, and SNAP closes on both parents (three families agree). |
| 2 | conditional: `…-SNAPscarp2px-20261023-c003d7d7` (+0.006) or `R1` (+0.005 vs R0) | `scarp2px` ≥ slot-1 receipt + 0.01 ⇒ 200 m reach beats 100 m; reverse ⇒ dose confirmed at 1 px; tie ⇒ keep the 1 px geometry (lower displacement risk). `R1` receipt ≥ slot-1 + 0.01 ⇒ the snap edit itself is the problem, keep the collar step. |
| 3 | reserve: `R1 = PRUNEp3px-6f7ae705` if not yet receipted, else `PRUNEp3.2px-f272cdae` (+0.002) | Completes the R0→R1→snap attribution chain on live chunks before any week-2 combination. `PRUNEp1px/p3.7px/p4.3px`, all RELIEF/CONC/MASS rows and both R0-parented SNAP families stay HOLD (negative MODEL, collar breach, or dominated on the blind control). |

## Weeks to the provisional deadline (2026-12-03, human-confirm)
- Oct 23–29: resolve receipts/quota/provenance; run the conditional sequence above (≤3 files).
- Oct 30–Nov 5: read receipts; if a snap arm confirmed ≥ +0.01, test one pre-registered extension
  (SNAP-FIXPOINT below) on that parent; do not mint parallel duplicates.
- Nov 6–19: combine two axes only after each has an independent ≥ +0.01 receipt; name the true parent.
- Nov 20–Dec 3: confirm the leading file twice, prepare Phase-2 TRACKB for geologist review, choose ONE blind
  final + fallback twin, re-validate both from disk.

## Better axes — proposed only, NOT built this session
- **SNAP-FIXPOINT:** iterate the 1 px spacing-locked scarp snap to a fixed point (2–3 passes). Mechanism:
  residual >100 m drift unreachable in one pass. Confounder: compounding percentile-field noise; each pass is
  a fresh chance to overshoot a thin truth strand. Falsifier: blind SGMC below single-pass `scarp1px`.
- **SUPPORT:** spaced H16-1/H19-4 ridge pixels as receivers instead of densified H19-5 adds. Mechanism: recover
  uncovered strand length (IR-88-41). Confounder: ancestor thresholds tuned on the same lineage. Note: today's
  result weakens the "never leave support" premise — off-support crest pixels beat on-support jitter fixes.
  Falsifier: no ≥ +0.01 live gain, count-matched and spacing-controlled.
- **RANKFIELD:** replace w in every drop/refill/ranking decision with a blind-neutral field (H19-5 component
  length or seeded uniform with a ≥2.8 px lock). Mechanism: w has blind AUC 0.47 and now anti-correlates with
  the winning geometry edit. Confounder: SGMC bedrock bias. Falsifier: no SGMC gain over R1 at equal count.
- **STRIKE_ALIGN:** move only dots whose structure-tensor strike matches the local ridge within ±22°.
  Confounder: drainage/flight-line lineaments. Falsifier: no gain vs a matched random-strike control.
- **TRACKB (Phase 2):** ≥1 km strike-consistent traces from top-ranked dots + one evidence paragraph per trace;
  not a weekly-slot candidate unless the human decides.

**Evidence discipline:** RECEIPT > CLAIM > PROXY > MODEL. Everything above is PROXY/MODEL except the R0 CLAIM
(0.2778, unreceipted); PROXY instruments are report-only and never gates; dedupe is exact-hash and
(parent, axis, value) only — no rank-correlation or overlap thresholds.
