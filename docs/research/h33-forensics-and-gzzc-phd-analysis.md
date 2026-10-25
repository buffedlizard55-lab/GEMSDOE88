# PhD forensic note: why H33’s user-reported 0.2778 led, and whether H88-GZZC can beat it

**Numbers.** `0.2778` is **USER-REPORTED** from GEMSDOE32 `h33-h33-2-b2-…-zeros` ([site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)). It is **not** `ORGANIZER-CONFIRMED`. Archived public `#1 = 0.4413` (2026-10-24 snapshot) is not this file’s score. Prompt `0.3195` is stale.

**Lineage (on-disk, nested).** `H19-5 (121,131) ⊃ D2.8 (44,090) ⊃ SOLO-D2.8 (40,199) ⊃ H33 (37,654)`. H33 deletes 6,436 near-catalogue (≤2 px) D2.8 dots. Under pooled Tversky DTI (α=0.2, β=0.8, 300 m triangular kernel; [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)), that thinning is the rational precision/coverage trade-off **if hidden truth is a subset of the same ridge family**. It is not a proof of geothermal discovery.

**Instrument mismatch.** Local `HOLDOUT-DTI` hides *mapped* catalogue segments. The portal scores *unmapped* geothermal-indicative faults ([problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). A 3 px catalogue collar makes withheld-on-trace recovery structurally near zero (this lane: **HOLDOUT-DTI 0.0000**, evaluator `gems57-pooled-hide-v2`, n=22,641 scored withheld positives). That does **not** imply a portal zero; it also does **not** imply a portal win.

**H88-GZZC mechanism.** Residual isostatic gravity zero-contours (Jachens & Moring 1990; Blakely 1995) locate buried density contacts. Low `det_elev_slope` rejects already-mapped scarps. Geodetic shear/dilation rejects static onlap. Placement is 32,000 binary dots, 3.2 px spacing, dual-regime 45% at >25 px from the catalogue (fingerprint pass). Like-for-like 3 px overlap vs accessible registry **0.343 ≤ 0.70**; Spearman **0.039 ≤ 0.90**. Literal overlap vs space-filling `17GEMSDOE` is **1.0 > 0.70** → **DO NOT SUBMIT**.

**Can we beat 0.2778?** Not shown. No organizer receipt. 0 weekly slots. Copying H33 would violate uniqueness and the “do not copy” rule. GZZC is a **contrarian buried-contact** prior, not a ridge-thinned H33 clone.

Official links: [DrivenData 306](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [NLR rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [EPSG:32611](https://epsg.io/32611) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).
