# Source and evidence ledger — session d0c3adeb, 2026-10-25 UTC

This is a claim-level ledger, not a declaration that every external link was fetched. Only GitHub and package registries are reachable under this session's outbound-host policy. A page cited in an earlier session is not freshly verified here. No score in this session is ORGANIZER-CONFIRMED. No new HOLDOUT-DTI was measured.

## Freshly retrieved sources

| Source and immutable link | What the retrieved text actually supports | What it does not support |
|---|---|---|
| [DrivenData official reference README, commit aebe92f](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | Documents data download separately from the competition site; explicitly provides CPU-only and GPU setup. **A GPU is optional**, not an absolute training prerequisite. | Does not authenticate mirrored input bytes, grant data redistribution rights, establish a current quota, or supply a submission receipt. |
| [Official reference notebook, same commit](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb) | Intro cell describes geological fault detection and U-Net/Monte-Carlo validation. Code cell 16 assigns alpha=0.2 and beta=0.8 for **Tversky training loss**. | The notebook's patch validation/loss is **not** an independent validation of this repository's buffered pooled distance-weighted evaluator. Do not conflate the two. |
| [GEMSDOE32 submission-build record, commit 098f3af](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/098f3af9508a135277ef4d1bf2266e2e448be814/registry/submission_build.json) | Owner's record identifies H33-2-B2 as collar pruning of an existing base; its pinned zeros TIFF hash matches the restored H33 artifact. The record says no organizer score exists and distinguishes a model projection from a score. | Owner-authored evidence, **not an official organizer receipt**. Its projections and live-mirror surrogate do not establish this session's holdout or hidden score. |
| [GEMSDOE32 H33 module, same commit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/098f3af9508a135277ef4d1bf2266e2e448be814/src/gems32/h33.py) | Contains several physical-surface proposals. Confirms that a repository may contain many methods unrelated to the exact downloaded file. | The existence of magnetic/geological hypotheses in the repository does not mean they generated the H33-2-B2 artifact. |

Retrieval hashes (SHA-256, not performance scores):

- Official README: `cfa4d55559c9128313beb9417eae7e0a94c31677132afb1120f9e86222804239`
- Official notebook: `1a7622732ba00f67237058bc0efe79b45ba4e87c449fc9c1e5d6ea659de92ca0`
- GEMSDOE32 build record: `0d7c5c3fb0079410e0d519fac45a36b37dc6136f2e42d5c6b2468a29397c478a`
- GEMSDOE32 H33 module: `e478a6f4cb5beb6dd79f711cde43b77748010154d73d1e11b33cf3df47301516`

## Fresh local measurements

| Evidence | Checked scope | Limitation |
|---|---|---|
| `evidence/h33_lineage_recheck.json` | Reopens hash-pinned H19-5, D2.8, SOLO and H33; exact subset geometry, deleted support and spacing. | Geometry, not ground truth or causal score attribution. No outputs copied into a new submission. |
| `evidence/download_audit.json` | Every currently published research TIFF, two decoders, [0,1]/finite/grid/footprint, catalogue mask, ZIP parity, exact decoded-field duplicate groups. | No new holdout, no full-fleet uniqueness clearance, no organizer acceptance. |
| `registry/mtas88_run_card.json` | Existing shared saturation proof re-run against pinned sample, catalogue and dense witness. | One counterexample suffices to reject, but cannot establish completeness of every registry scan. |
| `evidence/archive_repairs_20261025.json` | Two old ZIP member names repaired to retain DO-NOT-SUBMIT after extraction. TIFF hashes unchanged. | Packaging correction only, not a novel raster or scientific improvement. |
| `evidence/session_d0c3adeb_input_receipt.json` | Core inputs restored and prepared; nine shared planes load on CPU; exact grids and band counts rechecked. | Mirrors are not authenticated DrivenData downloads; shared-tier readiness is not every historical lane's full training environment. |
| `docs/data/user_reported_results.json` / `.csv` | Complete supplied site/result list parsed from the recorded request, with source-line numbers and blank-site handling. | USER-REPORTED CLAIMS ONLY; no receipt-backed ranking or live leaderboard fetch. |

## Official review links not fetched in this session

| Official or reference source | Intended use | Current verification status |
|---|---|---|
| [DrivenData problem/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Task, exact submission contract, competition metric | Host outside allowlist; current text not fetched. Local format tests use the pinned sample and the supplied contract. |
| [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Current public standings | Not fetched; the prompt contains conflicting historical maxima. No current leaderboard claim is made. |
| [DrivenData data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Organizer-authenticated input identity | No logged-in access; local restoration uses disclosed owner mirrors. |
| [DrivenData submissions](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/) | Current weekly quota, submission acceptance and receipts | No logged-in access; no upload made and no slot selected. |
| [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Current eligibility, deadlines, data/AI disclosure and prize rules | Not fetched; no assertion that the competition is still accepting submissions or that a stated cap is current. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Official magnetic/radiometric data provenance | Official review link; no fresh availability/license check. Owner-mirrored derived inputs are hash-checked separately. |
| [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) | Elevation-source provenance | Not fetched; restored derivative manifests do not independently authenticate new downloads. |
| [DOE GDR 1391](https://gdr.openei.org/submissions/1391) | INGENIOUS regional/geothermal inputs | Not fetched; no new externally dependent proposal is called immediately viable. |
| [INGENIOUS](https://gbcge.org/current-projects/ingenious/) | Scientific project context | Not fetched; local geometric predictions are not observations of vents. |
| [EPSG:32611 reference](https://epsg.io/32611) | CRS reference | Not fetched; actual CRS equality is checked from both raster headers, not inferred from the link. |
| [Tversky overview](https://en.wikipedia.org/wiki/Tversky_index) | General mathematical background | Not an official competition specification; not fetched or used as authoritative validation. |

No credentials are requested, stored or invented. An authenticated organizer context with permitted network access would be needed for official input comparisons, current rules/allowance and eventual receipts, **after** the project gates become satisfiable.
