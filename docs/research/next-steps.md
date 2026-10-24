# Next Steps & Handoff Brief (`GEMSDOE88` · updated `2026-10-24`, supersedes the 2026-10-22 ADHR brief)

Read `README.md` (banner + permanent prompt) and `registry/session_20261024_run_card.json` first. Then run
`python scripts/submission_gate.py --require-submit` — exit 0 means the promoted file is OK to upload.

## 1. Verified state
- **Upload file (unscored):** `docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros.tif`, sha256 `13b4155c41a8cfe56c5ca9a8079eb3b48d5c3e987cd71beb7ff7c9dc675d1b5f`, name `GEMSDOE88-PROVCREST-RANK-04559A2C`, note (113/140) in `docs/data/submission_gate.json`.
- Gate: 29 checks pass; worst dot-field 3-px overlap 0.4076; max |ρ| 0.0302; canary max AUC 0.575; bit-for-bit reproduction; beats random and lattice nulls (paired CI > 0, ALL and FAR). HOLDOUT-DTI 0.076277 [0.067653, 0.084607] (22,663 withheld; `gems57-pooled-hide-v2`). ORGANIZER-CONFIRMED: none. Slots used by any agent: 0.
- The archived ADHR file (`…adhr…DO-NOT-SUBMIT`) stays blocked: the continuous 17GEMSDOE prior overlaps every non-empty raster at 1.0. The earlier "human portfolio-selector decision on IR-88-01" is **superseded**: PROVCREST was built after classifying dense vs sparse rasters (IR-88-58) and the gate reports the literal reading rather than hiding it.
- Public leaderboard (one manual read, 2026-10-24): #1 0.4413, #50 0.2818. The CLAIMED 0.2778 would be below #50.

## 2. What to do next (in order)
1. **Human, outside the repo:** confirm weekly quota/deadline on the portal, upload the single file with the note, paste the verbatim receipt into `ledger/submissions.csv`. This is the only instrument that can say whether geometry-independent crest ranking beats the tuned lineage.
2. After a receipt exists: choose between the N ladder (holdout says 50k > 37.6k; live lineage says thinning helped — the two disagree) and the **geometry-null probe** (far-from-catalogue spaced random dots) to measure the geometry-only floor.
3. Hypotheses to test (TILTZERO from PR #59 was tried and is negative, 0.0551 < 0.0763; the rest untried, see `research/session-20261024-audit-why-0.2778.md` §5): crest-junction/termination prior (Faulds & Hinz 2015); dilation-tendency-weighted crests (Morris 1996 / Ferrill 1999); crest scale-persistence; RDC-88 K/Th. First measure overlap with the sibling lanes (GEMSDOE42/67/69 rasters are not in the restored registry).
4. Cross-check the sample/catalogue mirror against an authenticated DrivenData download (IR-88-02). Reproduce the reference U-Net MC-CV ([reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)) as an external benchmark.
5. Decide whether automated leaderboard refresh is permitted by DrivenData's terms; until then refresh `docs/data/leaderboard.json` by hand and run `python scripts/render_site.py`.

## 3. Do not
- Re-run `scripts/build_provcrest_submission.py` main() (raises FileExistsError, appends to ledgers).
- Treat HOLDOUT-DTI as a leaderboard prediction; fit a score model to the 13 claimed lineage points; claim a score without a receipt.
- Edit a generated page by hand: change the gate/run card/leaderboard JSON and run `python scripts/render_site.py`.
