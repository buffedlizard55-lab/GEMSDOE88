# MRR-COH-88 — pre-experiment hypothesis ranking (frozen 2026-10-24)

## Lane decision and evidence boundary

The request says that a single method paragraph defines this parallel lane, but no such paragraph is present. Rather than attribute an invented instruction to the user, this session autonomously selects one lane from the required pre-implementation ranking: **MRR-COH-88**, persistent curvilinear coherence of a locally detrended magnetic-demagnetization residual. The machine-readable preregistration is [`registry/preregistration_mrrcoh88.json`](../registry/preregistration_mrrcoh88.json). It was written before feature implementation, canaries, holdout fitting, or production placement.

Expected improvement is qualitative—not a score. No candidate below has an `ORGANIZER-CONFIRMED` result. The selected experiment will use only the restored, hash-pinned 19-band competition feature stack. It requires no new external dataset, so source-host restrictions do not prevent the test.

## Ranked 5-candidate list before implementation

| Rank | Hypothesis; exact layers | Target transform / physical signature | Why it may find an off-catalogue fault | Named non-fault mimic | Difference from completed repo work | Expected improvement / cost |
|---:|---|---|---|---|---|---|
| **1** | **MRR-COH-88** — bands 1 `mag_anom`, 2 `rtp`, 3 `tmi_hg`, 9 `tmi_vg`, 14 `tmi`, 15 `depth_to_base_surf` | Remove the local 10 km affine `tmi_vg ~ 1 + tmi + mag_anom` relation; calculate a negative residual trough, 200–600 m structure-tensor axial coherence, cross-scale persistence, and a horizontal-gradient suppression term. | A strike-persistent demagnetized damage corridor can remain beneath volcanic/alluvial cover after its scarp is buried or erased. | Linear Tertiary dike, reversed basalt-flow edge, aeromagnetic flight-line leveling seam. | MRR-BPR used residual amplitude/trough/depth/cross-gradient but no residual orientation persistence; STR-88/fabric-dislocation used orientation on raw fields. This lane uses only eight label-blind MRR channels—not ADHR catalogue anatomy. | Small-to-medium qualitative potential; **medium** CPU cost. |
| 2 | **RTP-GRAV-ADMITTANCE-88** — bands 2, 13, 15, 18 | Robust local magnetic-to-gravity gradient admittance/phase jump from 300 m to 1.2 km, depth-conditioned. | Concealed basement throw can perturb both potential fields without a mapped trace. | Unfaulted intrusive/lithologic contact. | Existing co-edge features use magnitude/alignment, not spatially varying cross-scale admittance. | Medium but uncertain; **medium** cost. |
| 3 | **STRAIN-SEISMIC-AXIAL-RIDGE-88** — bands 4, 7, 8, 10, 16 | Keep anisotropic seismic-density ridges only where strike is compatible with local extensional strain. | An active blind fault can organize diffuse microseismicity/strain before making a preserved scarp. | Induced seismicity or a supplied-density smoothing boundary. | Existing models use raw strain and seismic covariates, not a strain-resolved axial seismic ridge. | Small; **low–medium** cost. |
| 4 | **CHI-DIVIDE-ANTISYMMETRY-88** — USGS 3DEP 10 m DEM, D8 chi/ksn, divide geometry | Paired cross-divide chi sign reversal plus aligned knickpoint trains. | Buried range-front displacement can reorganize opposite catchments outside mapped scarp geometry. | Lithologic knickzone or regional base-level fall. | Existing chi channels are local maxima/wavefronts, not paired opposite-catchment evidence. | Unknown; **high** cost and **blocked** until exact official AOI bytes/divide derivation are authenticated. Free official source: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). |
| 5 | **RADIOMETRIC-ILR-ALTERATION-88** — calibrated GeoDAWN K/U/Th | Regional-detrended three-part isometric log-ratio curvature and U–Th vs K–Th discordance. | Fluid-rock alteration may survive where geomorphic evidence does not. | Felsic pluton, soil-moisture contrast, atmospheric-radon/leveling residual. | A calibrated compositional transform, unlike separately quantized u8 ratios used by the failed KTH proxy. | Unknown; low compute but **blocked** until official raw scales/bytes are authenticated. Free official source: [USGS GeoDAWN, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). |

## Frozen selected test

1. Build exactly eight catalogue-blind MRR/MRR-COH channels and test **each alone** on Seed-20 hidden whole components. Symmetric AUC above 0.90 is a leakage stop.
2. Train a physics-only dual-expectation model on three spatial quadrants and predict the fourth; repeat for seeds 20 and 21. Features never see the catalogue. Catalogue use is limited to fold-visible training labels and exact scoring masks.
3. Score pooled `HOLDOUT-DTI` with unmodified `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`; alpha 0.2, beta 0.8, 300 m triangle; 1,000 paired 20 km block draws; expected 22,893 withheld positive pixels).
4. The bar is the stored same-split H88-ADHR **HOLDOUT-DTI** 0.187887642, 95% CI [0.171697649, 0.203260122], 22,893 withheld positives. A point estimate above it would trigger paired incumbent recomputation before promotion; otherwise verdict is negative.
5. Production inference is strict four-quadrant out-of-fold prediction. Before placing dots, compare the continuous surface against every accessible SHA-pinned registry raster and stop at `|Spearman rho| > 0.90`.
6. Write with shared `submission_writer.py`, reopen TIFF and one-TIFF ZIP independently, then compare final dots to the complete accessible registry. Use the shared IR-88-76 chance-corrected gate while also reporting literal overlap for every prior. A genuinely discriminating prior with excess overlap above 0.70 is a duplicate stop.
7. One experiment is planned; no competition slot or portal action is authorized by this research run.

## Sources and verification limits

- [Organizer reference solution, pinned commit](https://github.com/drivendataorg/gems-prize-reference-solution/commit/aebe92f7c8a990f0e3443451b7a825d9afd6336b) — public organizer-controlled code used to cross-check stack conventions.
- [Competition metric/submission description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official link retained for manual review; this sandbox cannot authenticate the private data/submission pages.
- [`registry/data_manifest.json`](../registry/data_manifest.json) — exact hashes and owner-mirror provenance. Owner-mirrored bytes are not claimed to be organizer-authenticated.
- External hypotheses 4–5 are explicitly not viable in this run. Listing an official free source does not assert that exact AOI files or redistribution permission were verified here.
