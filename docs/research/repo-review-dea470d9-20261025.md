# Independent repository review — session `dea470d9` (2026-10-25)

**Current decision: NEGATIVE / `DUPLICATE_STOP`. No submission-ready GeoTIFF exists.** No candidate, model, holdout, new feature canary, TIFF, or weekly-slot selection was produced in this review. The unique-file requirement remains unmet; no prior artifact was copied, renamed, or passed off as new.

- [Machine-readable review card](../data/repo_review_20261025.json) · [evidence copy](../../evidence/repo_review_20261025.json) · [public status](../status.json) · [submission decision](../SUBMIT.md) · [source/provenance audit](../sources.html)
- [Preserved operating prompt](../../PROMPT.md) · [complete user request](../../USER_PROMPT_20261025.md) · [README session-start guidance](../../README.md)

## 1. Decision and protocol stop

The shared preflight (`scripts/preflight_mtas88.py --gate-generation`) exits **2**, as expected, with `DUPLICATE_STOP`. Hash-pinned witness `data/registry/dense_17gemdoe.tif`, SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, has positive support on all **5,106,385** allowed cells. Under the repository's current literal-support interpretation, each nonempty candidate in the allowed domain has a 3-pixel forward-overlap lower bound of **1.0**, above the **0.70** stop threshold.

This is a `REGISTRY-MEASUREMENT`, not a prediction or performance result. The dense witness is a continuous probability surface, not a sparse dot set. Its positive-support interpretation makes the rule unsatisfiable for every nonempty candidate. That surface-versus-dot-set mismatch is a policy irregularity to resolve explicitly through the shared protocol. **This review preserves the existing stop; it does not grant an exemption or try to evade the rule by changing the TIFF, name, representation, or candidate.**

The latest request does not contain a separate single-method paragraph. The review therefore **does not assign or invent a method lane**. No slot was chosen or spent. The experiment budget used here is **0 experiments / 0 hours**, within the 3-experiment / 2-hour ceiling.

<a id="h33"></a>

## 2. H33 result: plausible de-redundancy, unverified score causality

The reported H33 value **0.2778** is **USER-REPORTED**, not `HOLDOUT-DTI` and not `ORGANIZER-CONFIRMED`; the repository contains no DrivenData submission-page receipt for it. The current on-disk H33 forensic record (`evidence/h33_forensics_20261024.json`) establishes geometry, not hidden-label performance:

- H33 has **37,654** dots and is a strict subset of H19-5 (**121,131**), D2.8 (**44,090**) and SOLO-D2.8 (**40,199**).
- It removes **6,436** D2.8 dots; every removed dot is **1–2 px** from the mapped catalogue. H33 itself has no dot within 2 px, minimum catalogue distance **2.236 px**, and median catalogue distance **19.647 px**.
- H33's minimum inter-dot nearest-neighbour distance is **2.828 px**. This is spacing geometry; it is not the same quantity as distance to the catalogue.

The local metric implementation in `vendor/gems57/metric.py` uses a 300 m triangular kernel and

`DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)`.

Removing redundant dots can reduce false-positive cost after truth-cell credit saturates, which is a plausible explanation for a higher reported score. But pruning can also remove credit for a genuine nearby hidden fault. The pixel geometry does not establish which occurred, does not show that pruning caused the reported 0.2778, and does not prove H33 beats any official live leaderboard result. No score projection is made.

<a id="hypotheses"></a>

## 3. Four method-level research candidates — novelty is conditional

The following shortlist satisfies the requested 3–5 **only at the exact-formulation level**. The searched code/research tree contained no exact implementation of these proposed statistics, but each uses a geological family or input channel already present in prior work. This review **cannot honestly certify them as globally or fleet-wide “genuinely untried” hypotheses**; the names below are research descriptions, not assigned lanes or preregistrations. They are not selected or tested.

Qualitative gain/cost are planning judgments only—not measured results, probabilities, or predicted `HOLDOUT-DTI`.

| Rank | Exact method-level test and cached inputs | Geological target / named mimic | Prior-method overlap and novelty limit | Potential / cost |
|---:|---|---|---|---|
| **1** | **Magnetic-marker restoration:** whiten paired RTP/TMI patches across a candidate boundary; estimate translation by phase correlation; require a stable offset that restores magnetic texture continuity across adjacent independent swaths. Context bands: `training_features.tif` B02 RTP, B14 TMI, B13 isostatic gravity, B12 detrended elevation, B15 cover depth. | A buried rupture may offset a magnetic marker without a surface scarp. Mimics: depositional facies pinch-out, intrusive contact, and GeoDAWN leveling seam. | `fabric_dislocation.py` measures axial gradient-orientation change; PHASE/XGCE compare gradient geometry. They do not implement this exact matched-patch translation/restoration statistic. The magnetic-dislocation family is already related; novelty is the displacement-restoration test only. | Moderate, uncertain / medium-high |
| **2** | **Drainage-vetoed scarp-profile restoration:** compare a shared smooth-landform-plus-signed-step model with a smooth no-step null on held-out flank profiles; require along-strike replication and veto drainage-aligned corridors. Inputs: B12/B19, cached 10 m terrain and LiDAR scarp grids. | Repeated low-amplitude cover-softened piedmont offsets. Mimics: fluvial terrace risers, fan toes, and pluvial shorelines. | TDKL/VESS/LSC/SHORE already use scarp and knickpoint evidence. The exact held-out profile-restoration likelihood plus preregistered drainage veto was not found; the scarp family is heavily tested. | Moderate-low, uncertain / medium |
| **3** | **Terrain-matched alteration-width asymmetry:** fit a terrain/parent-background radiometric null on training blocks; compare opposite-flank K:Th residual decay widths, requiring a localized magnetic-amplitude depression. Inputs: GeoDAWN K/Th/U, B02 RTP, B19 slope and B15 cover depth. | One permeable fault wall may show a wider alteration halo under cover. Mimics: differential weathering, transported K-rich alluvium and soil-moisture effects. | KTH-88 tests a signed opposite-flank K:Th step; MVRD and related lanes use radiometric/redox features. The proposed statistic is residual decay-width asymmetry—not generic K:Th enrichment. | Low-moderate, uncertain / medium |
| **4** | **Conductive basin-breach continuity:** test a narrow conductance path crossing an independently estimated basin-boundary saddle, concordant with a basement/gravity discontinuity; compare with smooth-fill and drainage-aligned nulls. Inputs: B17 conductance, B13 gravity, B15 cover depth, B12 detrended elevation. | A covered permeable connection across a structural basin boundary. Mimics: alluvial paleochannel and saline groundwater plume. | CTRA/DHTC and other thermal/conductivity lanes already use related conductance curvature or multi-sensor co-occurrence. No exact topology-preserving saddle-crossing test with a drainage null was identified; the sensor family is not new. | Low, uncertain / medium-high |

No candidate requires a new external dataset as currently stated. However, `data/training_features.tif` and the full training-feature stack are absent in this checkout, and owner-mirror files do not establish authenticated organizer provenance or current derivative-use rights. The exact inputs must be restored and their provenance rechecked before any feature construction.

### Queue reconciliation and screened-out “untested” labels

The earlier static five-item queue was not reliable as a list of untried hypotheses:

| Earlier label | Reconciliation |
|---|---|
| `H88-MTAS` | **Historically tested.** See Section 4 and `evidence/mtas88_experiment_20261025.json`; it must not remain labeled `UNTESTED`. |
| `H88-PRAN` | KTH/MVRD and shared feature code already use K/Th, terrain-conditioned radiometry and related alteration evidence. Do not claim the broad family untried. |
| `H88-FARC` | `features.py` and QTSK already include cross-catchment chi/knickpoint features. A new candidate needs a distinct statistic/control beyond that family. |
| `H88-TCONS` | DHTC/HGVC and prior lanes use thermal, conductance and basin-depth relationships. Generic thermal/conductivity co-location is not untried here. |
| `H88-FLAC` | KDMC/MTAS and other potential-field lanes already include seam controls. A separate flight-line veto does not by itself establish a new geological mechanism. |

Other close overlaps found in the repository: the old `H88-CURIE` reserve is represented by `psgv_curie_spectral_shallow` in BPWD/`src/gems88/bpwd.py`; `geodesic_relay.py` already contains Pollard–Segall-style wing-crack/splay features, so the old LEFM queue item is not a cleanly new family; and magnetic-fabric dislocation is implemented and preregistered in `src/gems88/fabric_dislocation.py`. Broader fleet-wide novelty remains unverified.

## 4. Historical H88-MTAS experiment (not this review's experiment)

The prior experiment card records one historical result:

- **`HOLDOUT-DTI 0.049577 [0.044659, 0.054417]`**
- Evaluator: `gems57-pooled-hide-v2`; **22,893** withheld positives; **8 folds**; seeds 20 and 21; 3 px buffer / 12 px boundary.
- Historical feature canaries passed with maximum symmetric AUC **0.567804**. The card reports one experiment and no weekly slot used.
- No organizer receipt exists; the card's `organizer_confirmed_score` is null and `ok_to_submit` is false. The saved MTAS TIFF is a research-only, negative archive.

The later `preflight_mtas88.py --gate-generation` rejection is separate. It blocked new feature construction and did **not** rerun, erase, or contradict the historical MTAS holdout. The old `H88-MTAS` “UNTESTED” queue entry and old research-page sentence “no new MTAS HOLDOUT-DTI” are corrected by the current queue and current research-page wording.

<a id="sources-and-provenance"></a>

## 5. Inputs, download status, and official-source provenance

- `scripts/restore_inputs.py --validation` restored the validation tier from hash-pinned owner mirrors. It did **not** restore the full training feature stack, and it was not an authenticated organizer download.
- `data/training_features.tif` is absent. Feature canaries, new spatial holdout and candidate construction were therefore not run; independently, the pre-placement stop forbids continuing.
- The local research-download audit reports **43/43** TIFF/ZIP packages passing local format/package checks and **0 protocol-eligible** packages. Format validation is not scientific uniqueness or organizer acceptance. An older `docs/SUBMIT.md` revision said 41/41; the current wording and machine report now say 43/43.
- **One official page was freshly fetched:** the [pinned DrivenData reference README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) through GitHub HTML. It identifies the reference solution, directs competition-data downloads to the challenge website, and documents both CPU-only and GPU paths (including Apple Silicon MPS). This confirms environment options and download instructions only; it does not authenticate local data, licensing, current rules, or a score receipt.
- A separate GitHub API request for the same pinned commit returned HTTP **403 rate limit** at `2026-10-25 13:52:36 UTC`. That API attempt failed; the later HTML page fetch succeeded.
- Other official manual-review links were **not fetched or asserted current**: [DrivenData problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/), [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR INGENIOUS](https://gdr.openei.org/submissions/1391), and [USGS 3DEP](https://www.usgs.gov/3d-elevation-program).

## 6. Three-pass review and verification

### Pass 1 — evidence and gates

Read `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md`, `AGENTS.md`, preflight, shared evaluator/writer, hypothesis files, registered feature code, holdout records, H33 forensics, download/status cards, and site renderers. Reproduced the hash-pinned preflight witness. Identified the historical MTAS experiment separately from the later preflight.

### Pass 2 — independent consistency and novelty review

Compared the generic queue against MTAS, KTH/MVRD, H88-H4/QTSK, DHTC/HGVC, KDMC, BPWD and magnetic-fabric-dislocation records. Corrected the historical MTAS status, made global novelty limits explicit, and marked the old HGVC v4 “OK TO DOWNLOAD AND SUBMIT” and rename/upload advice revoked. Reconciled `43/43` vs `41/41`, current input availability, and the site's MTAS wording. Only the pinned official GitHub reference README was fetched; all other official links remain explicitly unverified.

### Pass 3 — post-change checks

Final local verification for this review:

- `pytest -q`: **654 passed, 23 skipped**; Rasterio/Affine pending-deprecation warnings remain. These are software tests, not performance evidence.
- `scripts/audit_downloads.py --check`: **43** local research-format packages pass, **0** protocol-eligible.
- `scripts/render_decision.py --check`, `scripts/check_site.py`, and `python -O scripts/check_site.py`: pass.
- `scripts/browser_check.cjs` in Chromium `153.0.8010.0`: **5/5** responsive page cases pass, with the failed-fetch path remaining fail-closed; saved receipt: [`evidence/session_d0c3adeb_browser_check.json`](../../evidence/session_d0c3adeb_browser_check.json).
- Current internal-link/anchor audit: 85 links in `docs/research.html`, 179 in `docs/sources.html`, 15 in the active README section, and 3 in the active submission decision section all resolve.
- `scripts/review_repo_20261025.py`: returns 0 for completing the negative audit; `--require-submit`: expected exit **2**.
- `scripts/preflight_mtas88.py --gate-generation`: expected exit **2**, `DUPLICATE_STOP`.

No candidate or experimental performance was evaluated in this pass. The exact machine card preserves the run scope, three review passes, historical MTAS result, protocol thresholds and zero slot count.

## 7. Remaining work and limitations

1. Obtain an explicit shared protocol decision on whether continuous-surface support counts as “dots.” Until then, preserve the current rule and stop; do not silently class-exempt the dense witness.
2. Restore and authenticate the full training stack and verify its official source, hash, license/derivative-use terms and applicable organizer rules. Validation-tier mirrors are not enough.
3. The user request does not assign a single method. Do not infer one. If a lane is explicitly assigned later, first preregister its statistic, control, mimic and kill criteria. Rank 1 above is a research priority only, not a selection.
4. Only after the shared prerequisite is resolved: use the existing feature cache, whole buffered fault segments, visible-only catalogue features, per-feature leakage canaries, shared `gems57-pooled-hide-v2` evaluator and submission writer. Label measured results `HOLDOUT-DTI` with evaluator, withheld-positive count and 95% CI. Stop at `|Spearman rho| > 0.90` or >70% of final dots within 3 px of any registry raster. Keep within 3 experiments or 2 hours.
5. Run the full registry and saved-byte format checks only after a candidate is permitted. Keep weekly-slot selection separate; no slot is selected or spent by this review. Label `ORGANIZER-CONFIRMED` only from a genuine submission-page receipt.

**Readiness remains: no eligible TIFF; do not submit.** The missing unique file and unrun leading hypothesis are explicit limitations, not successful completion claims.
