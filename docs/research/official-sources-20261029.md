# Source audit — 2026-10-29 (bounded GitHub refresh)

A source link is not a verified score, an authenticated organizer download, a submission receipt, or proof of license terms. This file records what was actually fetched or read in this review and what remains unverified.

## Freshly retrieved official GitHub source

- **DrivenData official reference solution:** `drivendataorg/gems-prize-reference-solution`, `main` at commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b` (`README.md` fetched through the GitHub API on 2026-10-29). The README identifies the repository as a reference solution for the GEMS Prize Challenge, says to download data from the competition website, and documents both CPU-only and GPU-capable setup paths. This verifies the reference-repository identity/content at that commit; it does not authenticate local owner-mirror bytes, verify hidden labels, establish current contest rules or standings, or provide a receipt for any GEMSDOE submission.
  - Pinned source: <https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md>

## Current-but-unverified owner repository observations

- **GEMSDOE36 README**, current sampled HEAD `e280188adbbe762e6b7ac6f3b8e105e8e7915026`, states that the public leaderboard showed `0.4544` on 2026-10-28. This is a report in a participant repository, not a fresh fetch of the official leaderboard and not a receipt for a focus-site file.
  - Pinned source: <https://github.com/buffedlizard55-lab/GEMSDOE36/blob/e280188adbbe762e6b7ac6f3b8e105e8e7915026/README.md>
- Other stored/requested observations include `0.3195`, `0.4413`, and `0.4437`, with differing dates and provenance. These conflict with the participant README's `0.4544` statement. None is treated here as a live current score, a GEMSDOE candidate score, or a submission receipt.
- The fresh bounded focus feed records current GitHub HEADs and a single README-cited raster path per site; it does not discover/rank every current raster or verify scores. See `docs/data/focus-freshness.json`, `docs/data/focus-current-samples.json`, and their session-dated mirrors.

## Official sources not refreshed in this review

The following primary-source links are retained for manual or authorized review. The current sandbox session did not retrieve these non-GitHub hosts, so their present contents, current rules, access requirements, leaderboard values, quota, and data-use terms are **not freshly verified** here:

- DrivenData GEMS competition/problem, data and submission pages: <https://www.drivendata.org/competitions/306/competition-doe-gems/>; <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>; <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>; <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>.
- NLR official rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>.
- USGS GeoDAWN primary dataset page: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>.
- DOE GDR INGENIOUS record: <https://gdr.openei.org/submissions/1391>.
- EPSG:32611 reference: <https://epsg.io/32611>.

The historical source audit `knowledge/official-sources-20261025.md` records prior page-fetch claims, including retrieval dates and limits. Those older observations are historical evidence, not a new verification in this session.

## Data provenance and license boundary

The validation-tier files restored for the preflight were read from SHA-pinned owner GitHub mirrors and verified against local pins. They are not authenticated downloads from the organizer account. The full 19-band feature raster, external feature caches, and sibling corpus were not restored. Current redistribution terms were not rechecked. No training, candidate fitting, holdout, TIFF creation, or slot selection followed the duplicate stop.
