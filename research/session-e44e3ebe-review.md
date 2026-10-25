# Session e44e3ebe — review, claim correction, and unique-TIF status (2026-10-25)

**Bottom line.** No new unique TIFF can be cleared under the current literal protocol. The shared preflight returns `DUPLICATE_STOP` (exit 2) on SHA-pinned inputs, and `audit_downloads.py` reports `protocol_eligible_count: 0`. This session also found and corrected a false "OK to download and submit" claim for H88-CON88 on three pages. The claim was contradicted by the canonical gate. **Current answer for every file in this repo: download for research only, do not submit.**

Evidence labels: `REGISTRY-MEASUREMENT` = computed locally on the pinned rasters; `ORGANIZER-CONFIRMED` = none exists in this session; `PUBLIC-LEADERBOARD` = read from the official public page; `USER-REPORTED` = supplied in the request, not verified.

## Pass 1 — implement and verify

1. Read `README.md`, `PROMPT.md`, `AGENTS.md`, `USER_PROMPT_20261025.md`. Confirmed the branch matched `main` at `3017fe7` with a clean tree.
2. Installed the pinned CPU environment: `.venv` from `requirements.txt` with `requirements-constraints.txt` (Rasterio 1.4.4 / GDAL 3.10.3). `.venv/` is git-ignored.
3. Restored SHA-pinned owner-mirror inputs with `bash scripts/download_competition_data.sh --registry` (all groups restored, `prepare_data.py` checksums OK: `sample_submission.tif` `2176d08e…`, `existing_faults.tif` `7ba308cc…`, `training_features.tif` `4371c82e…`; grid EPSG:32611, 3730×3292). These are owner mirrors, not organizer downloads.
4. Ran `scripts/generation_guard.py` → **exit 2, `DUPLICATE_STOP`**. Witness `data/registry/dense_17gemdoe.tif` (`ab0a0a62…3872be`): 5,167,373 positive pixels, covers **100%** of the 5,106,385 allowed pixels. Under the inherited literal support rule (`finite prediction > 0`) every nonempty candidate overlaps it fully, so no candidate can pass the 0.70 gate.
5. Ran `render_decision.py --check` → PASS; `check_site.py` → PASS (after restoring two timestamp-only files that `audit_downloads.py` rewrote); `audit_downloads.py` → 48 published TIFF/ZIP pairs checked, `protocol_eligible_count: 0`.

## Pass 2 — bugs, missing requirements, wrong assumptions

- **Wrong assumption corrected:** the README banner, `docs/con88.html` and `docs/SUBMIT.md` said H88-CON88 was OK to download and submit. Its clearance relied on IR-88-CON88-01 (equal-support rule), which IR-88-B4DFA10C-08 withdrew, and `AGENTS.md` names the literal shared preflight as governing. All three surfaces now say NOT cleared. Logged as **IR-88-CON88-02**.
- **Filename rule:** `AGENTS.md` rule 6 requires the `DO-NOT-SUBMIT` marker on published research TIFFs. The CON88 TIFF and ZIP lack it. Not renamed: renaming breaks its audit chain and cross-links; flagged for review (IR-88-CON88-02).
- **Pre-existing test failures:** three tests fail identically on the untouched base commit (IR-88-CON88-03). Not weakened or edited to pass.
- **Test run:** 872 passed, 22 skipped, 3 failed (the three pre-existing failures above).

## Pass 3 — re-check against the original request

| Requirement | Status | Note |
|---|---|---|
| Unique TIF that is OK to download and submit | **NOT MET** | Blocked by the literal dense-witness gate. No new TIFF generated, to avoid evading the stop. |
| Obvious whether it is OK to submit | **MET (corrected)** | README, `con88.html`, `SUBMIT.md` now say NOT cleared. |
| No human inspection in the gate | **MET** | Gates are automated in `scripts/`; no clearance rests on visual review. |
| Explain why H33 (`0.2778`) scored high | **PARTIAL** | See below. No organizer receipt; the score is USER-REPORTED. |
| Beat 0.2778 / 0.3195 | **NOT ESTABLISHED** | No holdout was run for any new candidate. |
| 3–5 new hypotheses, ranked | **NOT DONE THIS SESSION** | Existing queue (`registry/hypothesis_queue.json`: SPR, AWA, CBC) is unauthorized to run. I did not generate new ones. |
| PR created and merged to `main` | see PR | Requested by user; executed after this review. |

### Leaderboard check (PUBLIC-LEADERBOARD)

Fetched `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/` on 2026-10-25. Rank #1: `xiaofanhu`, **0.4413**. Rank #2: `cfld__`, **0.3916**. Rank #3: `Batik Shirt Brothers`, **0.3904**. The page lists participant names, not GEMSDOE site IDs, so I cannot verify whether any GEMSDOE site maps to 0.4413. The request's label "GEMSDOE high score" for 0.4413 is therefore unverified; the repo's earlier review (`session-fd5f1d8b-review.md`) records the same concern. This fetch covered only the first chunk of the page (about 23 rows), so the rest of the table was not checked.

### H33 (`0.2778`) — what can and cannot be said

- The number is USER-REPORTED. Its own source page says no organizer score exists for its artifacts, and no receipt is in this repo. Prior analysis is in `research/session-fd5f1d8b-review.md` §2 (geometry, kernel spacing, non-hugging profile).
- It is not on the first 50 public rows (lowest visible row 0.2818, per the repo's 50-row snapshot).
- Whether anything can beat it is **not established**. The repo's catalogue holdout (`HOLDOUT-DTI 0.205991`, `gems57-pooled-hide-v2`, n=22,893) uses the public catalogue as truth and is not comparable to the public DTI, so it cannot rank blind-fault seekers.

## Decision needed (rule owner)

Should a dense continuous probability raster (here `17GEMSDOE` E-proba, 100% coverage) count as a "registry dot set" under the 70% / 3 px overlap rule?

- **If yes (literal, current):** no candidate can clear; the project should pivot to a sparse-catalogue-free comparison or stop generation.
- **If no:** write the revised protocol, then CON88 can be evaluated against the sparse registry (worst overlap 0.6936 vs `gems49_gate_ortho`, worst |ρ| 0.3762, both under limits). Clearance would still require the `DO-NOT-SUBMIT` marker to be handled and a fresh run card.

Until one of these is written and approved, no TIFF in this repo is cleared for submission.

## Limitations

- No DrivenData login; the competition data page is not accessible here, and the restored inputs are owner mirrors.
- No organizer receipt; weekly slot state is not visible from this sandbox.
- The browser-receipt tests need a real browser rerun to refresh their pinned digests; not run this session.

## Sources (official, fetched or cited)

- DrivenData competition 306 leaderboard — https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (fetched 2026-10-25)
- DrivenData competition page — https://www.drivendata.org/competitions/306/competition-doe-gems/
- NLR FY26 submission rules PDF — https://docs.nlr.gov/docs/fy26osti/96647.pdf (cited in the repo; not re-fetched this session)
- Reference solution — https://github.com/drivendataorg/gems-prize-reference-solution (cited; not re-fetched this session)
- EPSG:32611 — https://epsg.io/32611
- Run card: `evidence/session_e44e3ebe_run_card.json`
