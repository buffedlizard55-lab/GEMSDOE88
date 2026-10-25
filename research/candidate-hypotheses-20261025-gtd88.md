# H33 forensics, ranked untried hypotheses, and the H88-GTD lane — session `bc757d13`, 2026-10-25

**Status at writing:** hypotheses ranked and lane preregistered
([registry/preregistration_gtd88.json](../registry/preregistration_gtd88.json), `PREREG-20261025-GTD88`)
*before* any GTD feature construction, canary, holdout fit or placement in this session.
Every performance number below is labelled `HOLDOUT-DTI` (evaluator, withheld count, CI),
`USER-REPORTED` (owner ledger, no organizer receipt in this repo), `REGISTRY-MEASUREMENT`
(recomputed from saved rasters), or `MODEL-PROJECTION` (never a score).

---

## 1. Why did `h33-h33-2-b2-…-zeros` reach 0.2778? (PhD-level answer, evidence-bounded)

### 1.1 What is verified (not inferred)

- **Identity.** Pinned raster `data/registry/h33_education.tif`, SHA-256
  `c55bafc47005…f7ab6fa9`, 37,654 binary `{0,1}` float32 dots, `nodata=None`, all finite
  (re-measured this session with rasterio; [evidence/h33_forensics_20261024.json](../evidence/h33_forensics_20261024.json)).
- **Score status.** `0.2778` is **USER-REPORTED**. No DrivenData submission-page receipt for it
  exists in this repository, so it cannot be labelled `ORGANIZER-CONFIRMED`. The same applies to
  every fleet figure in the session prompt. The public-leaderboard values `0.4413` (rank 1, a
  non-GEMSDOE participant in the stored 2026-10-25 snapshot) and `0.3195` (stale 2026-10-04
  snapshot) are **not GEMSDOE scores** — see IR-88-120 and
  [docs/data/leaderboard_official_snapshot_20261025.json](../docs/data/leaderboard_official_snapshot_20261025.json).
- **Lineage (strict pixel-subset chain, `REGISTRY-MEASUREMENT`).**
  H19-5 (121,131 dots, USER-REPORTED 0.1922) ⊃ D2.8 (44,090 dots, 0.2600) ⊃ SOLO-D2.8 B=1
  (40,199 dots, 0.2708) ⊃ H33-B2 (37,654 dots, 0.2778). Each step **only deletes** dots
  (0 added). The final step removes the last 2,545 dots at distance ≤ 2 px (200 m) from the
  mapped catalogue, leaving `min d_cat = 2.236 px`, `share ≤2 px = 0.0`, median `d_cat = 19.65 px`,
  `share >25 px ≈ 0.42` (footprint baseline ≈ 0.47 — H33 is *not* far-biased, it avoids hugging).

### 1.2 The metric arithmetic that makes deletion profitable

Distance-weighted Tversky (official page 967; shared code `vendor/gems57/metric.py`):
triangular kernel `k(d)=max(1−d/3px,0)` (300 m), `α=0.2, β=0.8`,

```
TP_w = Σ_truth g  max_dot k(d)        (max-pooled: saturates at 1 per truth cell)
FP_w = Σ_dots x   (1 − max_truth k(d)) (summed: every redundant dot pays again)
DTI  = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w),  FN_w = |G| − TP_w
```

Removing one dot with marginal truth credit `ΔT` and self-credit `q` changes the denominator by
`−0.2(ΔT + 1 − q)` and the numerator by `−ΔT`; removal **raises** DTI iff
`ΔT < 0.2·DTI·(ΔT + 1 − q)` (exact form, metric docstring). For a pure false positive
(`ΔT = q = 0`) removal always helps. Break-even self-credit for a non-redundant dot at
DTI = 0.2778 is only `k = 0.2 × 0.2778 = 0.0556` — but *redundant* dots (ΔT ≈ 0 because a
neighbour already max-pools the same truth cells) almost never clear it. Three consequences,
each visible in the lineage:

1. **Collar pruning (≤2 px deletion).** Organizer scoring masks only the exact rasterised
   catalogue trace; dots 100–200 m away sit on scarp shoulders/digitisation jitter of *already
   mapped* faults. They are near-certain FPs against *hidden off-catalogue* truth, so deleting
   6,436 of them (D2.8→H33) buys ≈0.2 denominator units each while forfeiting ≈0 numerator.
   (Conditional algebra, not proof: a hidden fault *could* run within 200 m of a mapped one;
   the reported monotone gains 0.1922→0.2600→0.2708→0.2778 are consistent with, but do not
   prove, that the deleted mass was pure clutter. No causal hidden-truth measurement exists.)
2. **Kernel-spaced dotting (spacing ≈ 2.8 px).** Because `TP_w` max-pools within 3 px, two dots
   closer than ~300 m mostly duplicate credit while both pay FP risk. A spaced binary lattice
   maximises independent 300 m kernel disks per dot; dense continuous fields and tight clusters
   waste budget. This is why the fleet's dense/clustered files (e.g. USER-REPORTED 0.0041–0.09)
   collapse while dotted files dominate the top of the owner table.
3. **Non-hugging distance profile.** Hidden truth is, by construction, faults *missing* from the
   catalogue. Across 20 fleet rasters with owner-reported scores, `share_gt25` correlates with
   reported score at Spearman +0.90 (`evidence/fleet_distance_prior_20261024.json`); catalogue-
   hugging files (median `d_cat` 2–8 px) score 0.004–0.09. H33's median 19.65 px with 0% inside
   2 px is the geometric signature of the winning regime. It is a *screen*, not a selector:
   files passing it still range 0.11–0.28 USER-REPORTED.

### 1.3 Why local holdout cannot certify "better than 0.2778"

Hide-and-recover withholds *catalogue* segments and rewards recovering them from visible-fault
context — the exact behaviour the portal punishes. The fixed H33 raster scores **HOLDOUT-DTI
0.0039** (`gems57-pooled-hide-v2`; stored literal-protocol audit) because its collar deletes
precisely the near-catalogue dots that recover hidden segments. Conversely catalogue-adjacent
lanes reach HOLDOUT-DTI ≈ 0.19–0.21. **Holdout rank ≠ portal rank in the top regime**
(IR-88-125). Therefore: no method in this repo can be *shown* to beat 0.2778 without an
organizer receipt; anyone claiming otherwise is projecting. The rational, P(Win)-maximising
play is to (a) hard-enforce H33's three proven geometric properties (spaced dots, >2 px collar,
non-hugging profile with ≥35% beyond 25 px), (b) add a physically independent off-catalogue
measurement that raises per-dot credit in covered basins, (c) require it to beat the repo
holdout record (H88-BPWD, HOLDOUT-DTI 0.205991 [0.188105, 0.223344], `gems57-pooled-hide-v2`,
22,893 withheld) on identical folds as a leakage/regression discipline, and (d) let only the
portal receipt decide the 0.2778 question. At fixed dot count, reaching 0.3539 needs roughly
+27–29% more truth credit and 0.4413 roughly +59–63% (same DTI algebra; INFERENCE) — collar
tweaks alone cannot plausibly deliver that; only genuinely better off-catalogue placement can.

---

## 2. Five ranked, previously untried geological hypotheses

"Untried" = no implementation in `src/gems88/` or `vendor/gems57/` at session start (grep-verified
for the named transforms; local novelty only, not a worldwide claim). All five use only
SHA-pinned inputs already restorable in this sandbox (`scripts/download_competition_data.sh`);
none needs a new external download to be testable. Official sources for manual review:
[competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) ·
[problem/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) ·
[reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) ·
[DOE GDR #1391 INGENIOUS](https://gdr.openei.org/submissions/1391) ·
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
[EPSG:32611](https://epsg.io/32611) ·
[Tversky index](https://en.wikipedia.org/wiki/Tversky_index).

| Rank | Candidate | Specific layers (verified band tags) | Physical signature / transform | Why it catches a fault *missing* from USGS/INGENIOUS | Named non-fault mimic (+ handling) | Difference from everything implemented here | Expected DTI gain / cost |
|---|---|---|---|---|---|---|---|
| **1 (selected → H88-GTD)** | Potential-field gradient-tensor **source dimensionality** | `training_features.tif` B02 `rtp`, B13 `iso_grav_anom`, B15 `depth_to_base_surf`, B19 `det_elev_slope` | Structure-tensor + Hessian eigenvalues at σ=2,5 px; linearity `L=(λ1−λ2)/(λ1+λ2)`, step score `S=L·E`, cross-field `cos(2Δθ)`, σ5/σ2 persistence, cover-gated joint score | A buried normal fault offsets magnetic/density basement with **no surface scarp** for air-photo mappers to trace, but its potential-field source is an elongated quasi-2-D step persisting across scales and fields | Unfaulted lithologic contact/pinch-out, dike swarm (requires coincident B15 step); equant plutons/volcanic centres (explicit `(1−L)E` mimic channel); flight-line striping (persistence + multi-field agreement) | SSA-88 uses orientation *coherence* only; Frangi/Hessian-crest channels classify surface ridges; BPWD uses phase *dislocation*/worms. No code computes source-shape eigenvalues/dimensionality of the potential fields themselves (grep-clean) | Moderate (+0.002–0.005 HOLDOUT-DTI class, ordinal judgement not a projection) / **Low** (local bands, closed-form eigensystem) |
| 2 | **H88-SPR** — scarp-profile restoration with drainage veto | B12 `det_elev`, B19 slope, `dem10_chi_100m_*`, topo_10m derivatives | Cross-strike profile model comparison (smooth vs smooth+signed-step likelihood), along-strike repetition, veto on channel-aligned steps | Erosion-softened piedmont displacement survives as a repeated profile break below single-pixel ridge thresholds and catalogue mapping sensitivity | Fluvial terrace riser; Lake Lahontan shoreline bench (drainage + elevation-band vetoes) | TDKL/VESS/SHORE rank scarp *responses*; none fits a profile-restoration likelihood against an explicit drainage null | Moderate / Medium |
| 3 | **H88-LEFM** — elastic tip/step-over stress lobes | `trace_segments_utm11.csv` (fold-visible only), B07/B08 strain rates, B18 grav HG | Okada/LEFM Coulomb stress-change lobes at visible-fault tips and step-overs, gated by geodetic dilatation | Blind relay/ramp faults nucleate in predictable stress lobes between mapped segments yet are themselves unmapped under cover | Aseismic creep lobes and volcanic dike-intrusion stress shadows (strain-sign gating) | Relay lanes use geometric distance/strike heuristics, not an elastic stress kernel; zero lift expected in >25 px blind basins (disclosed) | Low–moderate (near-field only) / Medium |
| 4 | **H88-AWA** — alteration-width asymmetry | GeoDAWN radiometrics (`geodawn_rad_u8`, extensions K/Th/U), B02, B15, B19 | Terrain-matched cross-strike K/Th decay-width fit; asymmetric halo + magnetic-amplitude loss | A concealed permeable damage zone alters one upflow flank broadly with no surface trace | Differential weathering across a contact; transported alluvium (width-asymmetry vs level test) | KTH/MVRD use enrichment *levels*/concordance, not fitted decay-width asymmetry | Low–moderate / Medium |
| 5 | **H88-CBBC** — conductive basin-breach continuity | B17 `cond_surf`, B13, B15, cover proxies | Conductivity-curvature ridge continuity *across* a gravity-defined basin-margin step; suppress basin-axis-parallel ridges | A blind fault hydraulically connects basin aquifer to fractured basement across the margin | Permeable paleochannel; saline playa-margin sediment (continuity-through-margin test) | CTRA ranks conductivity curvature/conjunctions, not margin-crossing continuity vs a paleochannel null | Low / Medium |

**Blocked alternatives (named, not proposed as viable here):** 3-D MT conductor roots
([IRIS SPUD](https://ds.iris.edu/spud/emmodel), DOE GDR #1592) and InSAR/TIR
(NASA ASF OPERA, ECOSTRESS) require hosts outside this sandbox's allowlist
(github.com / pypi.org / npm only) — checked against the session network policy; they remain
future work for an unrestricted machine, exactly as recorded in earlier preregistrations.

## 3. Validation plan for the top candidate (frozen)

Shared stack, shared evaluator (`gems57-pooled-hide-v2`), shared writer — no private forks.
Buffered whole-component hide-and-recover (seeds 20+21, 8 folds, 22,893 withheld), visible-only
catalogue features, pixel-exact visible masking, per-feature canaries (AUC > 0.90 = leakage),
quadrant-scramble invariance, same-fold controls including recomputed H88-BPWD, surface +
final-dot uniqueness, fingerprint screen, saved-byte format audit. Promotion rule frozen in the
preregistration. Results are appended below after the run; nothing in §1–2 depends on them.

## Results appendix (2026-10-25, session bc757d13) — NEGATIVE

All values HOLDOUT-DTI (`gems57-pooled-hide-v2`, α=0.2, β=0.8, 300 m triangular kernel,
8 folds seeds 20+21, 22,893 withheld positives; far >10 px 10,791; blind >25 px 3,117;
20 km block bootstrap, 2,000 draws, seed 521088). Same-fold controls reproduced the stored
records exactly (BPWD 0.205991, HGVC 0.202947, ADHR 0.194876, PHYS-44 0.104163).

| Arm | Pooled DTI [CI95] | Paired Δ vs BPWD [CI95] | far | blind |
|---|---|---|---|---|
| exp01 GTD zero-cat | 0.119073 [0.105, 0.133] | — | — | — |
| exp02 GTD tri-PoE | 0.207624 [0.190, 0.226] | +0.001634 [−0.000687, +0.004007] | — | — |
| exp03 GTD tri-PoE + novelty (production) | 0.199773 [0.184, 0.216] | −0.006218 [−0.011079, −0.001153] (1/8 folds won) | 0.134865 | 0.081902 |
| H88-BPWD control | 0.205991 [0.188, 0.223] | 0 | 0.136782 | 0.072733 |

- Canary: 121/121 ≤ 0.90 (max 0.769268 `d2` seed=20; max zero-cat 0.590462; max GTD-14
  0.558728); zero-test-quadrant scramble invariance true.
- Uniqueness: v4 pre-placement cleared (234 rasters, worst effective halo 0.4426; literal
  witness 1.0). Final production **duplicate under v4**: 70.5025% of dots within 3.0 px of
  BPWD dots (limit 70%); max |Spearman ρ| 0.2156 (dense witness; passes).
- Production file: `gems88-gtd88-tensor-dim-37654-20261025-a49e9d38-zeros-DO-NOT-SUBMIT.tif`,
  37,654 dots, sha256 `a49e9d389f8bc823d53fc7becac159fd58ca1e9c8415e3d9c626e7d2713f1d45`;
  saved-byte format audit 29/29 (`scripts/validate_gtd88.py`); name `GEMSDOE88-GTD88-A49E9D38`,
  note 97/140. Verdict **negative**, `ok_to_download=true`, `ok_to_submit=false`, 0 slots.

Interpretation: (1) GTD-14 alone is a weak-but-real zero-catalogue signal (0.1191 vs BPWD's
zero-cat reference 0.1170), yet appended to the 107-channel stack it adds no proven lift
(Δ CI crosses 0) — the dimensionality split is largely redundant with PSGV/PHYS/HGVC.
(2) The soft incumbent-proximity discount (0.55 floor, 3 px ramp) trades near-catalogue
holdout credit for blind-stratum credit (blind 0.0819 vs BPWD 0.0727) and still fails
separation (70.5% > 70%): allocator crest-reselection is stronger than a multiplicative
discount. A successor needs a structurally different, newly preregistered separation
mechanism; lane budget (3 experiments) is consumed. Runtime 7,322 s (~2 h 02 m) exceeded
the 2 h lane wallclock under sandbox CPU contention; experiment count (3) was respected
and the overrun is recorded in the run card.
