# AI_USE — Generative-AI disclosure per NLR Rules §3.6

**Human:** `buffedlizard55-lab` (entity owner, submitter, approver). **AI:** Arena.ai Agent Mode (branch `arena/81f0028f-gemsdoe88`, commit `c2c9da2` → this PR). Disclosure must be copied into final technical narrative.

## What AI wrote (this session, 2026-10-23)
- `scripts/generate_axis_variants.py` (368 lines): loads pinned `h33_education.tif` (sha `c55b...`) and grid `sample_submission.tif` (`2176d08e...`)/`existing_faults.tif` (`7ba308cc...`), recomputes ranking as `0.6·norm(dist/50)+0.4·rand(seed88)` for parent and `seed90` for candidate pool on `allowed_2px` (dist>2), emits 3 MASS variants (drop10% 33,889, add10% 41,419, drop20% 30,123) with NaN-outside + -zeros fallback, verifies no NaN inside, [0,1], CRS/shape/transform, 0 catalogue, ≥2 px collar, logs sha256/sha8, writes `releases/*.tif` + `.zip`, re-reads from disk, writes `ledger/submissions.csv` + `ledger/mechanism_cards.json` with predicted deltas (-0.008, +0.004, -0.018 MODEL).
- `SLOT_PLAN.md` (≤1 page): next 3 slots wk1-2 MASS/CONCENTRATION/SNAP/PRUNE/RELIEF, wk3-4 fusion, wk5-6 final+fallback, deadline 2026-12-03.
- `README.md` CURRENT STATE block: parent, best receipt (none), TOP_PUBLIC 0.4413 (2026-10-22), slots 3/3, next 3 slots.
- `docs/SUBMIT.md`: file/name/note (≤140) / format receipt per variant.
- `IRREGULARITIES.md` IR-88-14/15/16: 2 px vs 3 px collar, manifest equivalence, TOP_PUBLIC staleness.

## What the human decided
- Selected AXIS=MASS for this session (per brief §5, human assigns; default plan wk1-2 lists MASS first).
- Reviewed mechanism cards (hypothesis, mechanism, non-fault mimic Lahontan/E-W corrugation vs tip-relay, predicted sign/size, falsifier Δ≥0.01 live) — approved as MODEL, not score.
- Will fill `ledger/submissions.csv` receipt_score/date after authenticated submission (never AI-fetched), and will choose ONE final file blind per §3.4.
- Authorizes `NO — DO NOT SUBMIT` to remain until selector scopes literal 3-px rule (4 space-covering witnesses block literal gate).

## Reproducibility
Inputs: `data/bridge/sample_submission.tif` `data/bridge/existing_faults.tif` `data/registry/h33_education.tif` pinned SHAs above, `data/registry/dense_17gemdoe.tif` witness `ab0a0a62...`. Seed 88/90 fixed, `git SHA` logged in `releases/*.zip` + `ledger`. No `dropbox.com`, no `drivendata.org` fetch, no credentials stored.
