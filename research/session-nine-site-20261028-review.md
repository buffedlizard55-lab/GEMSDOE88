# Nine-site executive review — GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 (2026-10-28)

**Result: no file is cleared for download-and-submit. No new TIFF was generated.** The duplicate gate
(`DUPLICATE_STOP`) was reproduced from pinned bytes. Every pinned winner file overlaps the other eight
sites and the dense 17GEMSDOE witness above the protocol's 0.70 limit. The page is
[`docs/nine-sites/index.html`](https://buffedlizard55-lab.github.io/GEMSDOE88/docs/nine-sites/); the machine
record is [`docs/data/nine_sites_20261028.json`](../docs/data/nine_sites_20261028.json).

## 1. What was asked, and the status of each request

| Request | Status | Where |
|---|---|---|
| Executive summary per site, best file to download | Done, one page covering all nine sites (we do not own the eight sibling repos) | [page](../docs/nine-sites/index.html) |
| Estimated score per file | **Not estimable** from repo evidence. Only USER-REPORTED values exist. A fixed-file holdout is not possible under hide-and-recover. | JSON `estimated_score` |
| Unique versus the other GEMSDOE sites | **No.** Pairwise forward overlap 0.867–1.000 across all 72 ordered pairs | JSON `pairwise_forward_overlap` |
| Unique TIF generated for submission | **Blocked.** The guard stops before construction. No raster was produced. | Section 4 |
| Why H33 (GEMSDOE32, 0.2778) scored highest | Mechanism partly explained; the advantage itself is **unexplained** by available holdout evidence | Section 3 |
| Can we beat 0.2778 | Not demonstrated. No validated candidate exists under the current gate. | Section 5 |
| Leaderboard facts | Checked against the official page; several user figures are stale or wrong | Section 6 |
| 3–5 new hypotheses | Not added. Existing untested queue reviewed (section 5). | `registry/hypothesis_queue.json` |

## 2. Three review passes

**Pass 1 — implement and verify.** Installed the pinned CPU environment (`requirements.txt`, Rasterio 1.4.4).
Restored the validation tier (`scripts/download_competition_data.sh --validation`, exit 0). Re-ran the guard:
`DUPLICATE_STOP`, exit 2, with witness SHA-256 `ab0a0a62…` covering 5,106,385 of 5,106,385 allowed cells.
Fetched the nine pinned winner files by partial git clone at their historical commits; all nine SHA-256 values match
the source JSON. Wrote `scripts/nine_site_executive_summary.py`, which computes format checks and the pairwise overlap
with the shared `gems57.uniqueness.dot_overlap`.

**Pass 2 — review for bugs and incorrect assumptions.** Three problems found and fixed:
1. *Wrong break-even in my draft.* I first wrote that removing dots helps only when the FP/TP ratio exceeds 4×.
   Deriving the metric properly gives `f/d > (0.8·TP + 0.2·FP + 0.8·FN) / (0.2·TP)`, which at the official worked
   example (TP 3.00, FP 1.89, FN 2.00) is **7.3**. I checked this numerically; DTI is unchanged at the break-even
   point. The page carries the corrected form.
2. *Non-deterministic output.* A generation timestamp made `--check` fail on every run. Removed; `--check` now passes.
3. *Guard conflict.* The new page at `docs/` root broke `tests/test_site_links.py`, which requires exactly five root
   HTML pages. Moved the page to `docs/nine-sites/index.html`, matching the existing `docs/mdc88/` pattern.
   The guard was not edited.

**Pass 3 — re-check against the request.** Every number on the page is read from
`docs/data/nine_sites_20261028.json`, which the script writes. Every label is one of the four evidence classes
(USER-REPORTED, ORGANIZER-CONFIRMED, REGISTRY-MEASUREMENT, HOLDOUT-DTI). `ok_to_submit_any` is `false` and
`organizer_confirmed_scores` is `0`. Ten tests in `tests/test_nine_site_summary.py` pass. The regeneration check
(`--check`) passes. Remaining items are listed in section 7.

## 3. H33 / GEMSDOE32 (0.2778) — why it scored highest, and what is not known

**Facts (REGISTRY-MEASUREMENT, recomputed here from pinned bytes):**
- H33 has 37,654 dots. D2.8 (GEMSDOE25, and GEMSDOE30 with an identical dot set) has 44,090.
- H33 is a **strict subset** of D2.8. The 6,436 removed dots are all within 2 px of the known catalogue:
  3,891 within 1 px and 2,545 between 1 and 2 px. None lie beyond 2 px.
- H33's nearest dot to the catalogue is 2.24 px away. This is the distance-transform minimum, measured here.
  An older record in the repo gives 2.83 px for a quantity whose definition it does not state. That
  discrepancy is flagged, not resolved.

**What follows from the metric (official definition; derivation checked numerically):**
- Subset implies `TP_w(H33) ≤ TP_w(D2.8)` and `FN_w(H33) ≥ FN_w(D2.8)`. H33 cannot recover any fault D2.8 misses.
- Its score can therefore exceed D2.8 only if the removed dots' false-positive weight is large relative to their
  true-positive weight. The break-even ratio is `(0.8·TP + 0.2·FP + 0.8·FN) / (0.2·TP)`; at the worked example it is 7.3.
- The user-reported gap is 0.2778 − 0.2600 = **0.0178** on the public split. No receipt exists. The public label
  count is not published here, so the gap's noise cannot be bounded.

**What the repo's holdout says:** `registry/con88_collar_holdout.json` (HOLDOUT-DTI, `gems57-pooled-hide-v2`,
60,988 withheld positives) gives a collar-minus-control paired delta of **+1.0e-6**, 95% CI
**[−7.9e-9, +3.2e-6]**. That is negligible. Collar removal is therefore **not established** as the mechanism. The
test was a different construction, so this does not disprove H33's file either.

**Conclusion:** the H33 advantage is UNEXPLAINED by repo evidence. The most defensible statement is that it is a
geometry-only trim of D2.8 whose effect on the hidden labels is unmeasured, plus a public-split figure with no receipt.

## 4. Why no unique TIFF was generated

The shared generation guard (`scripts/generation_guard.py`) exits 2 before any feature or dot is built. This
session reproduced that exit. The reason is structural, not a bug:
- The 17GEMSDOE witness is a continuous probability map (5,167,373 finite cells; median 0.22; max 0.98). The
  protocol counts a witness "dot" wherever `p > 0`. That makes the witness cover the whole footprint.
- Any nonempty candidate therefore has forward overlap 1.0 with the witness, and the 0.70 limit cannot pass.
- The official rules contain **no uniqueness or duplicate clause** (see section 6). The 0.70 limit comes from the
  parallel-run protocol in the request, and its dense-prior reading is the owner's decision.

Producing a file anyway would violate the protocol the owner set. It would also repeat the failure already logged
as IR-88-12F18097-01..02. No file was created, and no existing file was relabelled.

## 5. Ideas that remain untested

- Existing queue (`registry/hypothesis_queue.json`, `selection_status: NOT STARTED — shared DUPLICATE_STOP takes precedence`,
  `generation_authorized: false`): the top three are **H88-SPR** (repeated scarp-profile restoration), **H88-AWA**
  (terrain-matched radiometric alteration-width asymmetry) and **H88-CBC** (basin-breach connectivity). None is run.
- **New question, not yet tested:** the official metric is defined on probabilities `p ∈ [0,1]`. Every repo
  submission is binary {0,1} dots. Whether a calibrated soft map beats hard dots under alpha 0.2 is an empirical
  question. It needs a holdout under the protocol, and the protocol is blocked.
- **Not supported by evidence now:** a higher score from collar trimming (section 3).

## 6. Official sources checked (retrieved 2026-10-28)

- Problem description, metric, format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  Confirms distance-weighted Tversky, α=0.2, β=0.8, R=300 m; float32, one layer, values in [0,1]; data outside the
  bounds "null or nan".
- Official rules (NLR PDF): https://docs.nlr.gov/docs/fy26osti/96647.pdf
  Confirms one final submission per entity (§3.4), three submissions per week (§3.2), original-work warranty (A.5),
  and no uniqueness or overlap clause. A.13 lists "technological or programmatic diversity" only as a judge-level
  program policy factor.
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
  Rank 1 = **0.4544**. Rank 26 = **0.3195**. Rank 50 = **0.2874**. The 0.4413 figure does not appear in the top 50.
  Snapshot: [`docs/data/leaderboard_public_snapshot_20261028.json`](../docs/data/leaderboard_public_snapshot_20261028.json).
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution

Not reachable from this sandbox: the NLR PDF is reachable only through the fetch tool, not through bash; the
DrivenData data download requires login. Organizer receipts are therefore not available.

## 7. Irregularities for review

1. **Leaderboard figures are stale.** Prompt figures 0.4413 (top) and 0.3195 ("highest") disagree with the official
   page: top is 0.4544; 0.3195 is rank 26. An earlier repo note (2026-10-25) recorded 0.4413 as rank 1. Either the
   public board changed since then or that note was wrong. The 2026-10-28 snapshot shows 0.4544.
2. **0.2778 is not in the public top 50** (minimum 0.2874). Participant handles are not GitHub site owners, and no
   mapping between them is established.
3. **All nine winner files are near-duplicates of each other**: pairwise forward overlap 0.867–1.000; every file is 1.000
   against the witness.
4. **GEMSDOE25 and GEMSDOE30 carry identical dot sets** (44,090 dots, overlap 1.000 both ways), and both report 0.2600.
   Two site names point to one submission content.
5. **Outside-footprint convention deviates from the rule text in one direction.** The official text says "null or nan".
   Five files use NaN; four (GEMSDOE30, 32, 33, 36) use zeros. The user reports these were scored, so the portal
   appears to accept both. The official text is still not followed literally by the zero-filled files.
6. **The portal error "Predicted values must be in range [0, 1]" is not explained by these bytes.** Every finite value
   in all nine files lies in [0, 1]. Cause unknown; needs the exact uploaded file and the portal's log.
7. **The project's local "full-grid finite" check is stricter than the official text.** It fails the current
   GEMSDOE30 HEAD file (7,111,787 NaN outside the footprint) even though the official text permits NaN outside.
8. **The 0.70 rule's dense-prior reading is contestable.** The witness is a probability map with `p > 0` everywhere.
   A top-N dot reading would give different overlaps. That choice belongs to the owner and was not made here.
9. **H33 distance discrepancy** (section 3): 2.24 px measured here versus 2.83 px in an older record with no definition.

## 8. Verification log

| Command (in `/home/user/GEMSDOE88`, venv `.venv`) | Result |
|---|---|
| `bash scripts/download_competition_data.sh --validation` | exit 0; 10 groups restored, all SHA-pinned |
| `python scripts/generation_guard.py` | exit 2, `DUPLICATE_STOP`, `new_rasters_generated: 0` (reproduced) |
| `python scripts/audit_downloads.py --check` | exit 0 (50 published TIFFs; 0 protocol-eligible) |
| `python scripts/audit_executive_metrics.py` | exit 0 |
| `python scripts/audit_research_state.py` | exit 0 (negative) |
| `python scripts/render_decision.py --check` | exit 0 |
| `python -O scripts/check_site.py` | exit 0 |
| `python scripts/review_repo_20261025.py` | exit 0 |
| `python scripts/review_submission_status.py` | exit 0 |
| `python scripts/audit_protocol_integrity.py` | exit 0 |
| `python scripts/focus_current_samples.py --check` | PASS (8 `DUPLICATE_STOP`, 1 `NOT_DISCOVERED`, 0 `ok_to_submit`) |
| `python scripts/nine_site_executive_summary.py` | writes 3 outputs; input hashes verified (3/3) |
| `python scripts/nine_site_executive_summary.py --check` | PASS |
| `pytest tests/test_nine_site_summary.py tests/test_site_links.py` | 11 passed |
| Full `pytest tests` | see the final session note; the earlier baseline stopped at the `test_site_links` conflict described in pass 2 |

Two guard runs regenerate `docs/data/submission_review_latest.json` and `evidence/submission_review_latest.json`
with only a date change (`2026-10-25` → `2026-10-28`). These are reverted, so this session's diff stays focused.

## 9. Limitations and what is needed from the owner

- **Decision needed (rule owner):** choose how the uniqueness rule applies to dense priors. The options are
  (A) keep the literal rule (no file can ever clear); (B) an authorized top-N dot representation for dense priors,
  followed by a full sibling check; (C) an exact-duplicate-only rule, which matches the wording "not an exact
  duplicate". Under (C), the nine sites would still be one family, and that should be weighed. Option (D) is to
  stop generating.
- No organizer receipt is available. Every score on this page is a claim.
- The full 190-sibling registry is not restored in this session (only the validation tier). The nine-site overlap
  is measured against the nine winners and the witness, not against the full sibling inventory.
- No holdout, leakage canary, or experiment was run. The budget (three experiments, two hours) was not spent.
