# Session fd5f1d8b — review, duplicate-stop verification, H33 analysis and leaderboard reconciliation (2026-10-25)

Branch `arena/fd5f1d8b-gemsdoe88` · Machine card: [`evidence/session_fd5f1d8b_run_card.json`](../evidence/session_fd5f1d8b_run_card.json) · Leaderboard snapshot: [`docs/data/leaderboard_official_snapshot_20261025.json`](../docs/data/leaderboard_official_snapshot_20261025.json)

**Evidence labels used below.** `ORGANIZER-CONFIRMED` = copied from a DrivenData submission-page receipt; **none exists** in this repository or session. `HOLDOUT-DTI` = the repo's own catalogue hide-and-recover evaluator; **no new holdout was run**. `OFFICIAL-PUBLIC` = read from an official page on 2026-10-25 (public split, not an organizer receipt). `USER-REPORTED` = supplied in the request, unverified. `REGISTRY-MEASUREMENT` = read-only raster arithmetic on hash-pinned owner-mirror bytes.

---

## Bottom line

1. **No unique competition TIFF was generated, and none is eligible to submit.** The binding literal duplicate stop returns `DUPLICATE_STOP` (exit 2). The pinned dense `17GEMSDOE` witness covers **100 %** of the allowed cells, so any nonempty candidate has overlap 1.0 against a 0.70 limit. Building one anyway would break `AGENTS.md` rule 2 and the user's own protocol. This is the honest state of the highest-urgency request, not a passed test.
2. **Every published file remains `DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO — DO NOT SUBMIT`.** `audit_downloads.py --check` passes for all 43 TIFF/ZIP pairs; `protocol_eligible_count = 0`.
3. **The 0.2778 H33 score is unverified.** Its geometry is reproducible and explained below, but there is no organizer receipt. Its own source page says no organiser score exists for its artifacts.
4. **Two leaderboard figures in the request are stale or misattributed.** `0.3195` is the 2026-10-04 snapshot value of DARD, not a current standing; `0.4413` is the rank-1 public score of a participant named `xiaofanhu`, not a GEMSDOE entry.
5. **GitHub:** `gh auth status` reports that `GH_TOKEN` is no longer valid, yet `gh pr create` succeeded: [PR #145](https://github.com/buffedlizard55-lab/GEMSDOE88/pull/145) is open from this branch into `main`. Its merge is pending: it was `CONFLICTING` with `main` (main advanced via PRs #141–#143), which I resolved by merging `origin/main` into the branch. CI checks were still pending when this section was written. See Section 8.

---

## 1. The unique-TIFF request — what the stop actually measures

Command: `.venv/bin/python scripts/generation_guard.py` → `DUPLICATE_STOP`, exit 2, `new_rasters_generated: 0`, `experiments_run: 0`, `weekly_slots_used: 0`.

| Quantity | Value | Label | Source |
|---|---:|---|---|
| Witness | `data/registry/dense_17gemdoe.tif`, sha256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be` | REGISTRY-MEASUREMENT | restored by `download_competition_data.sh --validation` |
| Witness grid | 3730 × 3292, float32, EPSG:32611, 100 m, no nodata | REGISTRY-MEASUREMENT | rasterio read |
| Witness finite footprint | 5,167,373 cells (42.08 % of grid), identical to the sample footprint | REGISTRY-MEASUREMENT | read-only comparison |
| Witness value range on footprint | min 0.00046, median 0.2187, max 0.9841 — **continuous probability** | REGISTRY-MEASUREMENT | read-only |
| Catalogue cells inside footprint | 60,988 | REGISTRY-MEASUREMENT | `data/bridge/existing_faults.tif` |
| Allowed cells (footprint minus catalogue) | 5,106,385 | REGISTRY-MEASUREMENT (matches preflight) | read-only |
| Share of allowed cells with witness `> 0` | **1.0000** | REGISTRY-MEASUREMENT | read-only |
| Literal overlap lower bound | 1.00 vs limit 0.70 | REGISTRY-MEASUREMENT | preflight `universal_overlap_blocker: true` |

The measured witness is a dense probability surface. Under the inherited literal support rule (`finite prediction > 0`), every allowed cell is a witness "dot". Any candidate's dots are therefore within 3 px of witness dots by construction. The official metric uses the same support: its false-positive term sums `p(x)·[1 − max_g k(d(x,g))]` over **all** `x` with `p(x) > 0` ([DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). The stop's support definition therefore mirrors the metric's own false-positive support. The effect is that the rule rejects every nonempty candidate, sparse or dense.

I did not compute Spearman correlation or a top-N dot overlap. Both are diagnostics, and neither can clear a stop that binds before construction.

**What would change this** is a decision by the rule owner, not a code change in this session: see Section 9, decision D1. Changing the threshold, exempting the dense prior, or renaming a file would be the evasion `AGENTS.md` forbids.

---

## 2. Why H33 (`0.2778`) may have scored high — and whether 0.2778 can be beaten

### 2a. What is verified about the file

Rerun of the existing read-only audit `scripts/audit_h33_lineage.py` (its timestamp-only diff was reverted):

| Raster | Positive cells | Relationship |
|---|---:|---|
| H19-5 (`GEMSDOE19`) | 121,131 | upstream |
| D2.8 (`GEMSDOE25`) | 44,090 | upstream |
| SOLO-D2.8 (`GEMSDOE28`) | 40,199 | upstream |
| H33-2-B2 (`GEMSDOE32`) | 37,654 | exact subset of all three; no added cells |

- H33 removes **6,436** D2.8 dots. Every removed dot lies within **2 px** of the public catalogue (`removed_pixels_all_within_2px_catalogue: true`).
- H33 keeps **0** positives within 2 px of the catalogue; nearest-neighbour minimum **2.828 px**; median catalogue distance **19.65 px**.
- `organizer_confirmed_score: null`.

H33's public source: [GEMSDOE32 index](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), which describes the file as "UNSCORED" with "NO ORGANISER SCORE EXISTS for this or any artifact".

### 2b. The official arithmetic (quoted from the DrivenData problem page)

- `TP_w = Σ_g max_x p(x)k(d(x,g))`
- `FP_w = Σ_{x: p(x)>0} p(x)[1 − max_g k(d(x,g))]`
- `FN_w = Σ_g [1 − max_x p(x)k(d(x,g))]`
- `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε)`, triangular kernel `k(d) = max(1 − d/R, 0)`, `R = 300 m` (3 px).

For a **binary** dot set (`p ∈ {0,1}`) with `n` dots, `T = TP_w`, `G` truth pixels and `M = Σ_x max_g k(d(x,g))`:

`TP_w + 0.2·FP_w + 0.8·FN_w = T + 0.2(n − M) + 0.8(G − T) = 0.8G + 0.2T + 0.2(n − M)`, so `DTI = T / (0.8G + 0.2T + 0.2(n − M))`.

This is the identity the repository already uses, and it is derived here from the official formulas. Each emitted dot costs `0.2·(1 − its own credit)`, and each truth pixel it covers earns credit. A dot earns almost nothing if it sits far from truth. Removing such a dot helps unless it was also covering truth.

### 2c. How this explains a high score — and where the explanation stops

- **Mechanism (arithmetic, verified):** H33 is a precision-improving prune. It deletes dots that the official text suggests are least likely to hit hidden truth. The competition's hidden faults are described as "not contained within the current public USGS database" ([problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). Dots within 2 px of the catalogue therefore carry false-positive cost with probably little hidden-truth credit.
- **What is NOT verified:** that those removed dots were pure false positives. The repository's own review records that some deleted dots may have covered hidden truth ([session-d0c3adeb review](session-d0c3adeb-review.md), H33 section). No hidden labels are accessible.
- **The score itself:** `USER-REPORTED 0.2778`. Not on the top-50 public rows (lowest visible row is 0.2818). No receipt.
- **Can 0.2778 be beaten?** Not demonstrated. The repository's catalogue holdout (e.g. `HOLDOUT-DTI 0.205991`, `gems57-pooled-hide-v2`, `n = 22,893`) uses the public catalogue as truth. It is **not comparable** to the public DTI and, per the repo's own note `IR-32-PROXY-01`, cannot reward a genuinely new fault. Any claim of "beats 0.2778" needs either an organizer receipt for a new file or an off-catalogue validation that does not exist in this repo.

---

## 3. Leaderboard reconciliation (`OFFICIAL-PUBLIC`, fetched 2026-10-25)

| Figure in the request | Where it appears | What the official source says | Status |
|---|---|---|---|
| "0.4413 — GEMSDOE high score" | request | [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) rank #1 = `xiaofanhu` 0.4413. No GEMSDOE/buffedlizard55 handle in rows 1–50. | Real public score; **not attributable to this project** |
| "0.3195 — highest right now" | request | Appears in the [GEMSDOE32 leaderboard page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/leaderboard.html) snapshot dated **2026-10-04** (DARD, rank 3). On 2026-10-25 DARD is **rank 9, 0.3358**. | **Stale** |
| "0.3262 — leader" | GEMSDOE32 snapshot | 2026-10-25: `nchuzhoy` rank 21, 0.3262. | Stale as a "leader" |
| "0.2778 — H33" | request | Not among rows 1–50 (lowest 0.2818). | **Unverified; no receipt** |
| Public top-50 range | official | 0.4413 (#1) … 0.2818 (#50) | Verified; stored in snapshot JSON (50 rows, monotone) |

Structural check of the stored snapshot: 50 rows, ranks 1–50 contiguous, scores monotone non-increasing, endpoints 0.4413 and 0.2818, and no row equal to 0.3195 or 0.2778. Labelled public split; not a private or organizer score.

---

## 4. Ranked hypotheses — status (no new experiment run)

The repository already holds four ranked, **untested** proposals in [`research/session-d0c3adeb-hypotheses.md`](session-d0c3adeb-hypotheses.md): (1) magnetic marker restoration across candidate boundaries; (2) scarp-profile restoration with a drainage veto; (3) cross-boundary alteration-width asymmetry; (4) conductive basin-breach continuity. Each names its layers, physical signature, non-fault mimic and contrast with existing code. I checked the `src/` and `scripts/` trees for implementations of their core operations. Phase-correlation marker restoration, profile restoration with a drainage veto, and breach topology: no match found, so these remain untested in this checkout. Proposal 3 is **partly overlapped**: `src/gems88/bgcd.py` already defines `bgcd_rad_redox_asymmetry` (a cross-strike U/Th + K/Th alteration step against a felsic background). That feature tests a radiometric step, not the fitted alteration-width asymmetry the proposal specifies, so proposal 3 is not a duplicate, but it is not fully novel either.

I did not add new hypotheses this session, because the four above already meet the request's requirements and cannot be validated while the stop binds. Validation would require the full 19-band stack (`scripts/restore_inputs.py`, about 419 MB, not run here), and it would require lifting the stop first.

Inconsistency for review: `evidence/repo_review_20261025.json` lists **H88-MTAS** at rank 1 of its hypothesis queue, but H88-MTAS was already executed and recorded as negative in an earlier session (README "H88-MTAS" record). The markdown queue puts MMR at rank 1. The machine queue is stale.

---

## 5. Irregularities flagged for review

| ID | Irregularity | Evidence | Who must act |
|---|---|---|---|
| I-1 | The literal overlap rule, with a dense continuous registry member, blocks **every** candidate, sparse or dense. | §1 table | Rule owner (D1) |
| I-2 | The owner-mirror `sample_submission.tif` (sha256 `2176d08e…`) has **60,988 cells equal to 1.0** at exactly the catalogue cells and zeros elsewhere in the footprint. The official page describes the sample as one that "predicts total fault absence". | REGISTRY-MEASUREMENT: ones == catalogue ones, True; [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | User, via organizer download (login required; see D3) |
| I-3 | "0.4413 GEMS high" belongs to a non-GEMSDOE participant. | §3 | User |
| I-4 | "0.3195 highest right now" is a 2026-10-04 snapshot value. | §3 | User |
| I-5 | H33 `0.2778` has no receipt; its own source page says no organiser score exists. | §2a | User |
| I-6 | Machine hypothesis queue (rank 1 = H88-MTAS, already run) disagrees with markdown queue (rank 1 = MMR). | §4 | Maintainers |
| I-7 | `AI_USE.md` cites rules §3.6 for the generative-AI disclosure; the NLR rules place that disclosure in §3.2 ("Process Overview"). `AI_USE.md` already notes the conflict. | [NLR Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), §3.2 | Maintainers |
| I-8 | `gh` token rejected; PR/merge blocked. | §8 | User (reconnect GitHub) |
| I-9 | Full 19-band training stack not restored in this session (validation tier only). | §6 | Maintainers if needed |

The competition rules themselves are consistent with the repo's gates on three points I checked: a single GeoTIFF, a single raster layer at 100 m, and a three-submissions-per-week limit ([NLR Official Rules §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf)). The rules also require the generative-AI disclosure in the narrative.

---

## 6. Verification log (commands run, outcomes)

| Command | Outcome |
|---|---|
| `python3 scripts/generation_guard.py` (no venv) | exit 1 `AUDIT_ERROR`: numpy missing. Expected; fail-closed. |
| `.venv/bin/pip install -r requirements.txt` | OK (numpy 2.4.6, rasterio 1.4.4, lightgbm 4.7.0). |
| `bash scripts/download_competition_data.sh --validation` | exit 0; 10 SHA-pinned owner-mirror groups restored. |
| `.venv/bin/python scripts/generation_guard.py` | exit 2 `DUPLICATE_STOP` (the expected stop). |
| `.venv/bin/python scripts/audit_downloads.py --check` | exit 0; 43 TIFF, 43 research-pass, 0 protocol-eligible, 0 duplicate groups. |
| `.venv/bin/python scripts/render_decision.py --check` | exit 0; canonical decision and executive summary agree with evidence. |
| `.venv/bin/python -O scripts/check_site.py` | exit 0. |
| `.venv/bin/python scripts/audit_literal_protocol.py --require-submit` | exit 2 (expected: no clearance). |
| `.venv/bin/python scripts/review_submission_status.py --require-submit` | exit 2 (expected). |
| `.venv/bin/python -m pytest tests -q` (before merging `origin/main`) | 651 passed, 23 skipped, 0 failed. |
| Same command after merging `origin/main` (final state) | **671 passed, 23 skipped, 0 failed** (198.4 s). |
| `.venv/bin/python scripts/audit_h33_lineage.py` | reproduces §2a numbers; timestamp-only diff, reverted. |
| Read-only witness/sample analysis (inline Python, no writes) | numbers in §1 and I-2. |
| Snapshot structural check (inline Python) | 50 rows, monotone, endpoints as stated. |
| `git push --dry-run origin arena/fd5f1d8b-gemsdoe88` | succeeds (git credentials OK). |
| `gh auth status` | **fails**: token no longer valid. |

Official sources fetched 2026-10-25 (`fetch_page`): [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (3 chunks, rows 1–50), [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) (2 chunks, full metric and format), [NLR Official Rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (chunks 0–2 of 7, §1–§3.2), [GEMSDOE32 index](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), [GEMSDOE32 leaderboard](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/leaderboard.html). Not fetched in full: NLR rules chunks 3–6 (appendix terms) and the DrivenData data page, which requires login.

---

## 7. Three-pass review

- **Pass 1 — implement and verify.** Set up the environment, restored the validation tier, reproduced the guard, ran every audit and the test suite, read the witness, checked H33 and the leaderboard, fetched the metric and rules.
- **Pass 2 — review for errors.** Found and corrected: (a) my first witness read used the wrong path (`data/official/`; the restore places it in `data/bridge/`); (b) the H33 audit rewrote two tracked receipts with new timestamps, reverted; (c) my first "not on the leaderboard" wording for 0.2778 overstated the evidence, since the page shows only the top 50, so the claim is now limited to rows 1–50; (d) the snapshot was checked programmatically rather than by eye.
- **Pass 3 — recheck against the request.** See Section 8.

---

## 8. Requirement matrix (the request, line by line)

| Requirement | Status | Note |
|---|---|---|
| Generate a **unique** TIFF submission | **NOT MET** | Blocked by `DUPLICATE_STOP` (§1). Not faked, renamed or copied. |
| Obvious whether it is OK to download/submit | **MET** | "DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO" on every file and on the site. |
| Submission validator without human inspection | **MET (local)** | Automated audit reopens every TIFF/ZIP; not organizer acceptance. |
| `Predicted values must be in range [0, 1]` | **MET for existing files** | `audit_downloads` checks finite [0,1]; no new raster. |
| Unique name + note ≤ 140 characters | **NOT MET for a new file** | No candidate exists, so no new name or note was written. |
| Executive summary subpage | **EXISTS** | [`docs/executive-summary.html`](../docs/executive-summary.html); `render_decision --check` passes. |
| Explain H33 0.2778 | **MET with limits** | §2; no receipt, so the score remains unverified. |
| Can we beat 0.2778? | **NOT ESTABLISHED** | §2c. |
| 3–5 hypotheses, ranked | **MET (existing)** | §4; four untested proposals, none validated. |
| Validate top candidate on holdout before a slot | **NOT RUN** | Blocked by the stop; no slot used. |
| Official, verifiable sources with links | **MET** | Section 6 list; snapshot JSON. |
| Flag irregularities | **MET** | §5. |
| Prompt stored in README and read each session | **MET (existing)** | `USER_PROMPT_20261025.md` and README contain the request text. |
| Pass 3 review, PR and merge to main | **PARTIAL** | PR #145 open; merge pending CI and conflict re-check (§8). |

**GitHub status.** `gh auth status` reports `github.com: authentication failed — the github.com token in GH_TOKEN is no longer valid`. That did not prevent `gh pr create` or `gh pr view`: [PR #145](https://github.com/buffedlizard55-lab/GEMSDOE88/pull/145) was created from `arena/fd5f1d8b-gemsdoe88` into `main`. The PR was first reported `CONFLICTING`, because `main` advanced to `f03883d` via PRs #141–#143. I merged `origin/main` into the branch and resolved the README conflict by keeping both sections. I did not attempt any credential workaround and did not request a token. The merge is performed only after CI checks pass and the PR is re-verified as mergeable. Decision D2 covers the auth warning.

---

## 9. Decisions needed from you

- **D1 — the duplicate rule (blocks the top-urgency request).** Choose one:
  - **A. Keep the literal rule.** No candidate can be generated while the dense witness is in the registry. The site stays negative. This is consistent with the protocol as written.
  - **B. Authorize a written revision for dense registry members.** For example: compare top-N dot sets, with N equal to the candidate's emitted count, keeping the 3 px ≤ 70 % limit. I would implement it once in the shared preflight with tests, then generate a `DO-NOT-SUBMIT` candidate with its run card. Still no slot without a separate selector step.
  - **C. Another rule you specify.** Recorded verbatim in the next session.
  My recommendation is B, because under A every continuous probability submission (which the official format asks for) is blocked by construction, and the rule was not written with a dense registry member in mind. The choice is yours; I have not changed the rule.
- **D2 — reconnect GitHub in Arena** if `gh` continues to report an invalid token, so later PR operations are not at risk. PR #145 is already open.
- **D3 — organizer sample.** Download `sample_submission.tif` from the logged-in DrivenData data page and send its SHA-256. If it is all-zero, the owner mirror (`2176d08e…`) is not the organizer file (I-2).

---

## 10. Limitations and access still needed

- No organizer receipts, leaderboard private split, weekly-slot state, or hidden labels are accessible. Every score here is labelled.
- DrivenData data pages require login. Owner mirrors are SHA-pinned but are not organizer provenance.
- `gh auth status` reports an invalid token although PR creation worked (D2). The merge of PR #145 is not yet done.
- No holdout, leakage canary or new raster was run, because the stop binds first.
- Only the validation tier is restored locally; the full 19-band stack and 15 external datasets need `scripts/restore_inputs.py` and `scripts/restore_siblings.py`, which were not run here.
- Nothing in this session changes the site's decision; `render_decision --check` still passes.
