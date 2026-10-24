# H88-VESS — results dossier (2026-10-24)

**Verdict: negative (science promote-worthy, emission duplicate).**
`ok_to_download = true`, `ok_to_submit = false`, 0 weekly slots spent.
No ORGANIZER-CONFIRMED score exists for this or any GEMSDOE88 file.

## Answer to the standing question

- **Why did `h33-h33-2-b2-…-zeros` (CLAIM 0.2778) lead the owner's fleet?**
  Kernel de-redundancy (nearest-dot spacing → 3 px so each dot owns a private
  300 m kernel) plus moving emission mass away from mapped faults (median
  distance-to-catalogue 19.7 px, 42% beyond 25 px). Full forensic audit:
  `research/session-20261024-audit-why-0.2778.md`. Public leaderboard snapshot
  2026-10-24 (`docs/data/leaderboard.json`): #1 = 0.4413, #50 = 0.2818 — the
  CLAIM would not place in the Round-1 top 5 (cutoff 0.3539).
- **Can we generate a submission shown to score higher than 0.2778?**
  No — not demonstrably. HOLDOUT-DTI (below) scores withheld *catalogue*
  pixels under hide-and-recover; the live score is on hidden positives tuned
  partly through prior live receipts. Only a portal receipt could settle it,
  and this candidate is not cleared to spend a slot (uniqueness, below).

## HOLDOUT-DTI (`gems57-pooled-hide-v2`, seeds 20+21, 8 folds, 20 km block bootstrap, 2000 draws)

| Arm | Overall (n=22,893) | Far >10 px (n=10,791) | Blind >25 px (n=3,117) |
|---|---:|---:|---:|
| phys44 zero-catalogue control | 0.104163 [0.090747, 0.117718] | 0.085531 | 0.059648 |
| H88-ADHR incumbent (recomputed, B12 scarp) | 0.194876 [0.177933, 0.210764] | 0.123481 | 0.074122 |
| Exp1 vessel+TDKL physics-only PoE | 0.103545 [0.090014, 0.117009] | 0.086910 | 0.060569 |
| Exp2 single combined (90 ch) | 0.199672 [0.181757, 0.216638] | 0.130269 | 0.082847 |
| **Exp3 H88-VESS PoE (candidate)** | **0.200941 [0.183602, 0.217576]** | **0.131922 [0.112350, 0.152638]** | **0.090449 [0.058939, 0.129341]** |

Paired Δ Exp3 − ADHR: overall **+0.006065 [+0.001619, +0.010692]**, far
+0.008441 [+0.002173, +0.015440], blind +0.016327 [+0.001792, +0.031171]
(all exclude 0; 7/8 folds won). Point estimate exceeds stored TDKL
0.196237 — cross-run only (TDKL derived scarp fields from B14, IR-88-110;
this lane uses B12), so it is not a paired claim. Exp1 shows vesselness
alone adds ≈0 over physics: the gain requires the visible-structure head.

Leakage canary: 68/68 features ≤ 0.90 (max 0.59299, a TDKL channel;
VESS channels 0.503–0.551). VESS channels are weak alone, useful jointly —
consistent with a line-likeness prior, not leakage.

## Uniqueness (Protocol Rule 1) — duplicate, stop

- Pre-placement surface: max |Spearman ρ| = 0.413621 ≤ 0.90 (PASS).
- Final dots (25,000): 3 px forward overlap **0.84548 vs H88-TDKL**,
  0.7695 vs GTHC-88, 0.7639 vs QTSK-88 (all > 0.70); literal 1.0 vs the
  17GEMSDOE dense witness. Exact-pixel shares are small (TDKL 20.22%,
  H33 3.40%), so the file is byte/pixel-unique but geometrically in the
  TDKL lane (same PoE base + same two-stratum allocator). Per protocol:
  logged as duplicate, frozen without retuning. Any de-duplicated refill
  would be an unevaluated raster and could not carry this holdout number.

## Format (portal range-error guard)

Single band float32, EPSG:32611, 3730×3292, sample transform, nodata=None,
all 12,279,160 cells finite and in {0,1}, 0 outside footprint and on
catalogue. Independent re-reads (rasterio, tifffile, vendor validator,
gate portal parity) agree; ZIP has exactly one byte-identical TIFF.
`scripts/validate_vess88.py` exits 0 (research); `--require-submit` exits 2.

## Limitations / next steps

1. Selector decision needed on the shared protocol: the literal dense
   witness makes submission mathematically impossible for any candidate;
   a like-for-like-only rule still blocks this file vs TDKL/GTHC/QTSK.
2. A genuinely distinct emission would need a new allocator/head evaluated
   as its own holdout arm (new session, new preregistration) — e.g. rank 2
   (geothermometer discordance) in
   `research/candidate-hypotheses-20261024-vess88.md`.
3. Inputs are owner-mirrored, SHA-pinned, not organizer-authenticated
   (see `registry/data_manifest.json` flag). DrivenData login still
   required to authenticate bytes.
4. IR-88-110/111 (TDKL B14 scarp input; nondeterministic CSV glob) should
   be fixed in the shared TDKL script by its owner lane, not forked here.
