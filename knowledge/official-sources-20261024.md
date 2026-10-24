# Official-source knowledge, verified 2026-10-24 (LBCAL session)

Every item below was read directly from the source. No item is inferred.

## Competition pages (DrivenData #306)

- **Problem description** (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
  - The test set is expert-identified NEW faults, split into public and private chunks.
  - **Metric:**
    - TP_w = Σ_g max p·k
    - FP_w = Σ_{p>0} p·(1 − max_g k)
    - k(d) = max(1 − d/300 m, 0)
    - DTI = TP/(TP + 0.2·FP + 0.8·FN)
    - Worked example: 3.00 / 1.89 / 2.00 → 0.60.
  - **Format:** single-band float32, EPSG:32611, 100 m, values in [0, 1].
- **Leaderboard** (https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/, read 2026-10-24)
  - #1 xiaofanhu 0.4413, #2 cfld__ 0.3916, #3 Batik Shirt Brothers 0.3904, #4 0.3724, #5 No Fault of Our Own 0.3539.
  - #21 0.3262, #30 0.3004, #40 0.2898, #50 0.2818.
- **Submissions** (https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/)
  - Upload a .tif, or a .zip holding exactly one GeoTIFF, on the matching grid. The Note is optional.

## Forum (staff answers, community.drivendata.org)

| Thread | What staff said |
|---|---|
| 11516 | The known-fault mask is PIXEL-EXACT and identical to the training labels. New ground truth CAN lie within 300 m of known traces. |
| 11536 | A "new fault" is any fault pixel not already in USGS/INGENIOUS, including continuations and splays. |
| 11550 | The public score is pooled over all public pixels. Chunking is not disclosed. The final round uses the whole area. |
| 11556 | Phase-2 labels may be added, removed or changed. The mask stays the same and the metric is unchanged. |
| 11527 | No details on test-fault sources. Phase-2 labels are revised by expert review of all Phase-1 submissions. |
| 11553 / 11524 | 3 submissions per rolling 7 days. |
| 11557 | deq/ieq are INGENIOUS earthquake-density layers (GDR 1391). deq carries fill-like values up to 4.96e6. |
| 11531 | Team #5 uses 20 m LiDAR-derivative U-Net ensembles. |

## Official rules (NLR, https://docs.nlr.gov/docs/fy26osti/96647.pdf, chunks 0–3 of 7 read)

- **Prizes:** Phase 1 pays $50K split among the top 5. Phase 2 pays $250K (100/70/40/25/15).
- **Data:**
  - GeoDAWN includes LiDAR.
  - The features include the 1 m USGS DEM.
  - The labels come from INGENIOUS (doi:10.15121/1881483).
- **Final pick:** one submission must be chosen without knowledge of its private score.
- **Disclosure:** generative-AI use must be disclosed. Finalists must provide code and documentation.
- **Not read:** chunks 4–6 of the rules were not read this session. No statement is made about their content.

## How LBCAL uses these facts

- **Pixel-exact mask (11516):** catalogue pixels are excluded from both the prediction and the truth domain.
- **Pooled public score (11550):** together with random chunking, the public fraction cancels out of the expected-DTI ratio. That is why a whole-region density q can be fitted to public receipts.
- **Final pick without private knowledge:** LBCAL is coordinate-free. It learns physical-feature effects, not the public chunk layout, so it does not tune to public chunks.
