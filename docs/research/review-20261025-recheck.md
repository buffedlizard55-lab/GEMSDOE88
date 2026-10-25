# Independent repository recheck — 2026-10-25

## Decision: no new TIFF; do not submit an archived file

**Research downloads exist. No new unique competition submission was produced.** This review cannot honestly satisfy the demand for an eligible new TIFF while also obeying the mandatory duplicate-stop rule. No competition slot was used. This is a negative result, not a claim of completing model development.

The prompt does not actually supply the referenced single method paragraph. This review does not invent an assigned lane, replace the incumbent, or start another model experiment. It reuses the existing shared preflight, validator and negative run card rather than a private evaluator.

## Pass 1 — restore and reproduce

- Read README, PROMPT, current Pages decision, prior research and machine cards.
- Installed the repository requirements in an ignored virtual environment.
- Ran `scripts/restore_inputs.py --validation`: restored all validation groups successfully. This is **not** the full feature stack or authenticated organizer download.
- Ran `scripts/preflight_mtas88.py --gate-generation`: expected exit **2**, `DUPLICATE_STOP`. Its three tracked reports reproduced without changes.
- The independent hash-pinned witness has positive support on all **5,106,385 allowed cells**. Any nonempty allowed candidate has literal forward overlap **1.0**, exceeding **0.70**. This is a registry measurement, not a predictive score. Its sufficiency makes training and dot generation inadmissible under the supplied rule. It is not an inventory-wide uniqueness pass.
- The separate archived TDKL download passed the saved-byte local format validator: finite footprint, range [0,1], single band, CRS/shape/transform match, identical TIFF in its ZIP. This does not make it a new file or approve upload.
- Baseline full suite: **432 passed, 23 skipped**, with 47 deprecation warnings. Skips mean unavailable optional/historical inputs, not all scientific results verified.

## Pass 2 — evidence defects corrected

1. `PROMPT.md` called the archived GZZC lane a current precedence instruction, despite the pre-placement stop. It now labels it historical and explicitly preserves the stop. No historical raster or machine result was rewritten.
2. The public SGMC cards displayed a nonzero HOLDOUT-DTI point estimate with `[0,0]` as a confidence interval. That cannot be a valid reported interval for that point estimate. The website now says **95% CI unavailable** and identifies the archived placeholder. No fabricated bootstrap replaces it. The archival JSON is retained for audit, not endorsed as a valid CI.
3. The XGCE card said “Live Portal Status” despite no organizer receipt. It now says archived local artifact status, not portal-verified. Rasterio directly reports DEFLATE compression and 256-by-256 tiles; the contradictory “LZW deflate” label is corrected.
4. Added regression tests for these three evidence defects. The dated source ledger's earlier fetch claims were not reverified here; they must not be treated as this session's live fetches.

## H33: plausible mechanism, not demonstrated causality

The [owner H33 build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/registry/submission_build.json), retrieved through the GitHub API in this review, describes pruning catalogue-adjacent dots from a base and retaining 37,654 dots. It explicitly calls its projected result a model, not a score. It is **not an organizer receipt**. The prompt's **0.2778 remains user-reported**, not ORGANIZER-CONFIRMED.

Under the repository's DTI implementation, pruning dots that are redundant or spend predictions on masked mapped faults can reduce false-positive burden while retaining truth coverage. This is a plausible explanation of the reported ordering, not proof about unavailable hidden labels. Removing a dot near a mapped fault can also remove credit for a real hidden adjacent fault. Better local geometry alone does not establish a higher secret-test result. This review has no evidence proving a candidate will beat 0.2778, 0.3195, or 0.4413. Those differently dated claims must not be used as interchangeable current leaderboard measurements.

## Hypothesis queue: retain the preregistration, do not claim novelty twice

The repository already ranked five specific candidates before this review. Repeating them as “new hypotheses we have not tried” would be misleading. See [the five-hypothesis machine record](../data/repo_review_20261025.json) and [prior research](review-20261025-autonomous.md).

| Prior rank / candidate | Cached layers and physical signature | Missing-fault mechanism / non-fault mimic | Expected gain / cost (qualitative, not a score) |
|---|---|---|---|
| 1 MTAS | Gravity and RTP gradients at 200/800 m, cover, slope, transtension; cross-scale admittance residual | Buried density edge without surface scarp / unfaulted intrusive contact | Highest prior expectation / low–medium |
| 2 PRAN | K:Th, terrain slope, profile curvature, basement depth; terrain-matched radiometric residual | Alteration beneath weak scarps / transported K-rich alluvium | Medium / low–medium |
| 3 FARC | Chi steps, normalized ksn jumps, lineaments, scarp coherence; replicated cross-channel offsets | Blind deformation crossing separate channels / inherited drainage capture | Medium / medium |
| 4 TCONS | Shallow/deep temperature anomalies, conductivity edge, basement depth; conditional thermal residual | Focused blind fluid pathway / saline groundwater circulation | Medium / medium |
| 5 FLAC | RTP, gravity, conductivity edges, geodetic shear/dilation; acquisition-direction veto | Independent sensor persistence / leveling seam or lithologic contact | Low–medium / low |

These are **existing, untested proposals**, not new or scientifically validated findings. Differences from earlier implementations are recorded in the existing preregistration; novelty across the entire parallel fleet is not established. No new external layer is proposed as obtainable or licensed. No new feature canaries, buffered holdout scores, CIs, final dots, or raster hash are invented. A new shortlist should only be funded after the infeasible gate is resolved through an explicit policy decision; this review does not change that policy.

## Sources and limitations — what was actually verified here

| Source | Verification and scope |
|---|---|
| [Official DrivenData reference README, pinned commit](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | GitHub API retrieval; SHA-256 `cfa4d55559c9128313beb9417eae7e0a94c31677132afb1120f9e86222804239`. Explicitly provides CPU-only and GPU options and directs data download from the challenge website. GPU is not universally mandatory. |
| [Pinned registry witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) | Owner mirror, not official geological truth; restored and hash-checked by shared preflight. SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`. |
| [Official competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) / [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) / [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Review links only in this session: outbound host restriction, no DrivenData account access, no current quota or receipt verification. |
| [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Review link only; not fetched in this session. No claim of current rules verification. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) / [DOE GDR INGENIOUS](https://gdr.openei.org/submissions/1391) | Official reference URLs, not newly fetched data. Access, provenance and derivative redistribution terms are not independently established here. |

## Pass 3 — release verification and next steps

Regression tests, the complete suite, and the site guard in normal and optimized Python are rerun after corrections; exact results are in the companion [review card](../data/recheck_20261025.json). The expected preflight exit 2 is a successful rejection, not a build failure or permission to submit. No new binary artifact is added.

**Next session:** resolve the dense-continuous-surface versus dot-set protocol contradiction explicitly without silently granting an exemption; authenticate organizer input provenance and redistribution rights; identify comparable incumbent folds; then test feature-alone leakage canaries and a preregistered candidate on whole-segment buffered holdouts before any promotion. Use spatial bootstrap CIs rather than placeholders. Keep slot selection separate. An authenticated receipt is necessary for any ORGANIZER-CONFIRMED score. A merged Pages workflow is not proof of live site deployment until its check completes.
