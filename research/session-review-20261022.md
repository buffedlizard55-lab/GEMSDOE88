# Session review — 2026-10-22 (3 passes, line-by-line re-verification)

## Pass 1 — implement/verify (reproduced from clean state)
- Created `.venv` from `requirements.txt` (pinned numpy/scipy/rasterio/scikit-learn/pytest).
- `python scripts/restore_inputs.py` → RESTORED/PIN OK for grid, features, dense witness, H33 (SHA-pinned owner mirrors; **not** organizer-authenticated — unchanged limitation).
- `pytest -q` → **53 passed** (initial failure was only missing `data/`, resolved by the restore step; no code defect).
- `scripts/validate_release.py` → format_ok=true, no NaN in footprint, values in [0,1], CRS/shape/transform match, ZIP = exactly one matching TIFF, sha256 `3af5d290…730b`.
- `scripts/validate_release.py --require-submit` → **exit 2, ok_to_submit=false**: forward 3px dot overlap = 1.0 vs hash-pinned dense prior (ab0a0a62…) > 0.70 gate. Automatic STOP, no human inspection involved.

## Pass 2 — bug/edge review
- Site checker PASS; readiness = BLOCKED with the single true problem stated.
- Hypotheses: 4 ranked candidates in `docs/research.html`, each naming layers, transform, off-catalogue rationale, named non-fault mimic; only rank-1 (MGC-88) tested. No external data required.
- H33 forensic claim re-read: exact subset relation (37,654 ⊂ 44,090; 6,436 dots ≤2px from catalogue removed) is a pixel measurement; 0.2778 remains user-reported, **not ORGANIZER-CONFIRMED** (no receipt). Leaderboard 0.4413 is a dated 2026-10-22 public snapshot, not this project's score.
- **Defect found & fixed:** `.github/workflows/ci.yml` push trigger listed the stale branch `arena/e650459f-gemsdoe88`; updated to the current session branch `arena/7faad4bb-gemsdoe88`.
- Edge cases already handled by validator/writer: NaN/inf, nodata sentinels, out-of-range (the user's reported "[0,1]" portal error — original file unavailable, cause unproven, flagged IR-88-05), ZIP byte-identity, SHA mismatch, note ≤140 chars.

## Pass 3 — recheck against original request
- Unique TIFF exists and is byte/pixel-distinct from H33 (406 exact shared pixels, surface ρ=0.025), **but** the literal registry rule is unsatisfiable: the pinned 17GEMSDOE prior is positive at all 5,167,373 footprint cells, so any nonempty raster has 100% 3px overlap. Granting a green light would require silently exempting that prior — prohibited. Verdict stays **negative**; 0 weekly slots used.
- Site top banner, executive summary, filenames (`-DO-NOT-SUBMIT`) and run card all state: download YES (research), submit NO.
- No claim anywhere labels a projection or HOLDOUT-DTI as an organizer score.

## Flagged for protocol owner (not fixable in-repo)
1. IR-88-01: literal overlap rule vs dense prior makes promotion mathematically impossible — needs an explicit protocol decision.
2. IR-88-02: mirrored "sample_submission.tif" semantics contradict organizer description; grid-only use.
3. Organizer-authenticated data/receipts require DrivenData login (never request credentials in chat).
