# Official sources retrieved 2026-10-28 (focus-site review)

All links below were retrieved by the agent in this session. "Read" means the chunks listed were read in full. Unread parts are listed under *Not verified*.

| # | Source | URL | What was verified | Method |
|---|---|---|---|---|
| 1 | DrivenData competition, problem description | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Submission format (EPSG:32611, 100 m, float32, one layer, values 0-1, NaN/null outside bounds); distance-weighted Tversky with alpha 0.2, beta 0.8, R = 300 m; worked example TI_w = 0.60; "portions of the existing fault data may be misaligned" | fetch_page, chunks 0-1 (complete) |
| 2 | DrivenData public leaderboard | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | Top 50 "Best public DW-Tversky"; rank 1 = 0.4544; rank 26 = 0.3195; rank 50 = 0.2874 (`evidence/leaderboard_snapshot_20261028.json`) | fetch_page, chunks 0-2 (complete) |
| 3 | Official Rules, NLR PDF (September 2026) | https://docs.nlr.gov/docs/fy26osti/96647.pdf | Three submissions per week (section 3.2); two-round scoring (Initial and Final Prize Rounds); the GeoTIFF format requirement in section 3.2 | fetch_page, chunks 0 and 2 read; chunks 1 and 3-6 not read |
| 4 | Reference solution repository | https://github.com/drivendataorg/gems-prize-reference-solution | Single commit `aebe92f` (June 2026); notebook baseline; README setup steps | fetch_page of the GitHub page (README only) |
| 5 | Owner repositories (nine focus sites) | https://github.com/buffedlizard55-lab/GEMSDOE{24,25,27,28,30,31,32,33,36} | Live `docs/downloads` filenames, SHA-256, dot counts, encodings (`evidence/focus_top_files_20261028.json`) | api.github.com contents and git blobs |

## Not verified

- Whether the organiser masks mapped catalogue faults from scoring. The repo's `vendor/gems57/metric.py` docstring cites "organiser thread 11516". That thread was not retrieved. Status: UNVERIFIED (IR-F9-08).
- The reported portal error "Predicted values must be in range [0, 1]". Its cause is unknown (IR-F9-05).
- The reference notebook's metric code. It was not diffed against `vendor/gems57/metric.py` (open item).
- Rules text after section 3.2 of the NLR PDF (chunks not read).
- The Pages sites (`*.github.io`) were not fetched; the sandbox allowlist does not include them. Live content was taken from the GitHub repositories.
