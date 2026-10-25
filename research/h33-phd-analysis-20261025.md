# PhD-Level Analysis: Why H33 (0.2778) Led and Whether It Can Be Beaten

**Repository:** GEMSDOE88 · Branch `arena/7c0c1d12-gemsdoe88` · Date: 2026-10-25
**Status:** USER-REPORTED claim — not ORGANIZER-CONFIRMED

---

## 1. The Claim Under Scrutiny

`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` was reported by the site owner at
**0.2778** on `https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html`.

**Evidence class:** USER-REPORTED. No submission-page receipt, no organizer
confirmation, no portal hash match exists in this repository. It must not be
labelled ORGANIZER-CONFIRMED or treated as a measurable score.

For context, the live public leaderboard top (snapshot 2026-10-25) is **0.4413**
(participant `xiaofanhu`, rank #1), and the stale `0.3195` figure dates to
2026-10-04 (DARD, now #9 at ~0.3358). Public top-50 range on 2026-10-25:
0.4413 down to 0.2818. So even accepting 0.2778 at face value, it is **not**
the competition leader — it is the highest *reported* figure among the listed
GEMSDOE sibling sites.

---

## 2. Why H33 Likely Rose — Geometry, Not New Physics

The restored H33 lineage (fresh geometry audit, 2026-10-25) supports a narrow,
mechanism-specific conclusion:

1. **H33 is a 37,654-dot subset of H19-5 / D2.8.** Kernel-matched thinning
   removed clustered predictions. A two-pixel catalogue collar then removed
   6,436 near-catalogue dots **without adding new geography**.

2. **Under a 300 m triangular kernel with α=0.2, β=0.8:** Removing redundant
   dots (multiple dots within 3 px of the same truth cell) reduces weighted
   false positives (FP_w) more than it reduces weighted true positives (TP_w),
   because TP_w saturates at 1.0 per truth cell while FP_w accumulates per dot.
   Thinning therefore improves the precision–coverage trade-off.

3. **The catalogue collar (≥2 px from mapped faults) removes near-catalogue
   dots.** Under organiser thread 11516, a dot near a known trace but far from
   any new-fault pixel is fully penalised. Removing those dots reduces FP_w
   without proportionally reducing TP_w.

**Net effect:** sparsity + collar → lower FP_w → higher DTI *if* the removed
dots were mostly false positives. This is a **refinement of an existing
candidate**, not a discovery of new faults. It cannot be shown to beat 0.2778,
0.3195, or 0.4413 without hidden-label evidence.

---

## 3. Can We Beat 0.2778?

**Honest answer: not demonstrably, and not from local evidence alone.**

| Factor | Assessment |
|--------|-----------|
| Hidden labels | Required to prove any score. HOLDOUT-DTI is a proxy, not a leaderboard forecast. |
| H33 mechanism | Subset thinning + collar — reproducible but score-unverifiable. |
| Our best local HOLDOUT-DTI | H88-BPWD 0.205991 [0.188105, 0.223344] — below even the user-reported 0.2778. |
| Leaderboard top | 0.4413 (public snapshot, not organizer-confirmed for our account). |
| Binding literal stop | Dense 17GEMSDOE witness covers all 5,106,385 allowed cells; every nonempty candidate overlaps it at 1.0 > 0.70. No submission-eligible TIFF can be generated under the current rule. |

**Conclusion:** We cannot honestly claim to beat 0.2778, 0.3195, or 0.4413.
The path to a higher score requires:
1. Resolving the dense-witness duplicate stop (protocol/policy change, not a code tweak),
2. A candidate whose buffered holdout DTI *provably* exceeds the incumbent bar
   with a paired CI that excludes zero,
3. A separate weekly-slot selector authorization,
4. An actual organizer submission receipt (ORGANIZER-CONFIRMED).

---

## 4. The Unique TIFF Generated in This Session

A **new, previously unseen** research GeoTIFF was generated:

- **File:** `docs/downloads/gems88-uniq-20261025-DO-NOT-SUBMIT.tif`
- **SHA-256:** `8acaca3050056ae823a2da47fe450aa4a271a287edd8b9bcabfa93d775e96a73`
- **ZIP SHA-256:** `9267b249d9104f5f5866f8daa5b9a671ba6b13bd05ad0555fc57008e3082b620`
- **Dots:** 23,991 binary {0,1} dots (19,991 proximal halo 3–25 px + 4,000 blind >26 px)
- **Grid:** EPSG:32611, 3730×3292, 100 m, exact sample transform
- **Values:** all finite in [0,1], zero outside footprint, zero on catalogue faults
- **OK to download (research/education):** **YES**
- **OK to submit to DrivenData:** **NO — DO NOT SUBMIT**

**Why it is unique:** It is not a copy or rename of any file in the listed
GEMSDOE sites (1–92). It uses a distinct multi-physics conjunction
(K/Th anomaly × demagnetization trough × topographic lineament) with a
proximal-halo + blind-zone dot allocation that no prior lane implements.

**Why it cannot be submitted:** The binding literal all-registry duplicate
stop fires against the dense 17GEMSDOE witness (overlap 1.0000 > 0.70). This
rule blocks **every** nonempty candidate, not just this one. The filename
carries `-DO-NOT-SUBMIT` and the run card records `ok_to_submit: false` so
the download/submit decision is unambiguous.

---

## 5. Validation Summary (Automated, No Human Inspection)

| Gate | Threshold | Measured | Status |
|------|-----------|----------|--------|
| Portal GeoTIFF format | float32, [0,1], 0 NaN/Inf, nodata=None | PASS | PASS |
| Exact sample grid | EPSG:32611, 3730×3292, exact transform | PASS | PASS |
| Single-band, one-TIFF ZIP | 1 band, ZIP contains identical TIFF | PASS | PASS |
| Leakage canary | max symmetric AUC ≤ 0.90 | 0.5431 | PASS |
| Holdout DTI | gems57-pooled-hide-v2 | 0.0000 | Local instrument only |
| Sparse uniqueness (dot fields) | \|ρ\| ≤ 0.90, overlap ≤ 0.70 | 0.0000 / 0.0000 | PASS |
| Literal all-registry witness | overlap ≤ 0.70 vs every raster | 1.0000 vs 17GEMSDOE | **FAIL — blocked** |
| Weekly slot | 0 used | 0 | — |
| Organizer receipt | None | None | — |

---

## 6. Limitations

- **No organizer access:** Cannot authenticate against DrivenData, cannot verify
  current leaderboard, cannot obtain a submission receipt.
- **HOLDOUT-DTI ≠ leaderboard score:** The holdout instrument recovers withheld
  catalogue faults; hidden test labels are different. A projection is never a
  score.
- **Dense-witness stop:** The literal overlap rule is unsatisfiable for every
  nonempty candidate under the current shared protocol. No code change inside
  this repo can override it.
- **Untuned conjunction:** The K/Th × mag × topo surface has not been
  coefficient-tuned against held-out truth; HOLDOUT-DTI of 0.0000 reflects
  that, not geological impossibility.

---

## 7. Next Steps (Separate from This Session)

1. **Resolve the dense-witness duplicate stop** via an explicit shared-protocol
   revision (representation-aware dot definition for continuous surfaces), not
   a silent exemption.
2. **Rank and validate hypotheses** from `registry/hypothesis_queue.json`
   (H88-SPR, H88-AWA, H88-CBC) on buffered holdout before any slot.
3. **Obtain organizer access** to verify current quota, leaderboard, and
   submission terms.
4. **Only after all gates pass**, upload the approved TIFF with its unique
   name and ≤140-character note, and archive the receipt as ORGANIZER-CONFIRMED.

---

**Sources (official, publicly verifiable):**
- [DrivenData GEMS Prize competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Competition overview p967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About page p968](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [NLR Official Rules FY26 PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project (GBCGE)](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)