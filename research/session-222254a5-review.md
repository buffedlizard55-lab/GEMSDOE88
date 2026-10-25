# Session 222254a5 — three-pass review, H33 forensics, and the one decision that unblocks a submission (2026-10-25)

Evidence classes: **[MEASURED]** recomputed this session with repo code (script named) ·
**[CARD]** copied from a stored run card · **[USER]** user-reported, no organizer receipt ·
**[INFERENCE]** judgement. No number below is a projection written as a score.

## Pass 1 — Implement/verify

- Restored SHA-pinned validation inputs (`scripts/restore_inputs.py --validation`, 17/17 + registry
  groups) and installed the pinned CPU environment (`requirements.txt`, rasterio 1.4.4).
- Recomputed format and uniqueness for the only gates-cleared candidate in the repo,
  H88-CON88 (`evidence/session_222254a5_measurements.json`, repo-exact
  `vendor/gems57/uniqueness.py` functions):
  - Format **[MEASURED]**: 1-band float32, EPSG:32611, 3730×3292, transform exact vs sample,
    finite everywhere, values ⊆ {0,1}, 37,654 dots, 0 outside footprint, 0 on catalogue,
    SHA-256 `e830b58e…8d68`. This is the class of file that fixes the user's
    "Predicted values must be in range [0, 1]" rejection (no NaN, `-zeros` encoding).
  - Uniqueness **[MEASURED]**: vs H33 (GEMSDOE32) 3-px dot overlap **0.487** (limit 0.70);
    vs dense 17GEMSDOE equal-support (top-37,654) overlap **0.053**, Spearman **0.048** (limit 0.90).
    Worst stored equal-support row is GEMSDOE49 at 0.6936 **[CARD]** — passes, thin margin, flagged.
  - Generation guard **[MEASURED]**: `scripts/generation_guard.py` exits **2**, `DUPLICATE_STOP`
    (dense witness covers 5,106,385/5,106,385 allowed pixels).

### Why H33 scored 0.2778 [USER], and whether it can be beaten

H33 is a pure *subtraction* chain (H19-5 → D2.8 → SOLO → H33): it only deleted dots ≤2 px from the
catalogue (pure false positives under the DTI max-vs-sum algebra in `vendor/gems57/metric.py`),
kept a 2.83–3 px kernel-spaced lattice, and kept a non-hugging distance profile (41.7% of dots
>25 px from any mapped fault; fleet Spearman +0.90 between share->25px and user-reported score)
— full line-by-line derivation in `research/h33-forensics-20261024.md` and
`research/session-con88-20261025.md`. Arithmetically 0.2778 is beatable (+27–29% credit ⇒ 0.3539);
no local instrument can certify that in advance, and any claim of >0.2778 before an organizer
receipt would be a hallucination. CON88 was built exactly on that diagnosis (consensus + label-blind
ridge + stricter >3 px collar, H33 geometry preserved) and is the only candidate whose dots are
demonstrably not a copy (0.487 vs H33, 0.053 equal-support vs the dense prior).

### The critical calibration fact [MEASURED]

**H33 itself has literal 3-px overlap 1.0 against the dense 17GEMSDOE raster** — identically to
CON88. The literal `>0`-support rule therefore rejects the known 0.2778-scoring submission and
every other nonempty candidate; it carries zero discriminating information about duplication.
A dense continuous probability field (5,167,373 positive pixels = 100% of the footprint) has no
emitted "dots"; the like-for-like comparison is equal-support top-N (already implemented in the
shared template, `equal_support_dots`). This is flagged as **IR-88-222254A5-01** for the selector:
the binding `DUPLICATE_STOP` is a definition bug, not a scientific finding. Under the corrected
definition CON88 passes every automated gate; under the literal definition nothing ever can,
including the current fleet-best file.

### Holdout honesty [CARD]

CON88 does **not** beat the repo holdout record: per-fold re-emission HOLDOUT-DTI
(`gems57-pooled-hide-v2`, n=60,988) = **0.0017 [0.0013, 0.0021]**, vs trained-model record
H88-BPWD **0.2060 [0.1881, 0.2233]** (n=22,893). The same instrument scores the fixed H33 TIF at
0.0067 despite its user-reported 0.2778 — hide-and-recover of *catalogued* faults structurally
penalises blind-fault seekers, so it cannot rank this candidate class. Both facts are disclosed;
neither is hidden. Per the prompt's own gate ("do not spend a slot on an idea that hasn't beaten
the current holdout best") and the separate-selector rule, this session does **not** flip
`ok_to_submit`. The selector decision required is explicit: adopt equal-support uniqueness for
dense priors (IR-88-222254A5-01) and decide whether the H33-calibration argument exempts
blind-seeker emissions from the catalogue-recovery holdout bar. Until then the honest site label
remains **⛔ DO NOT SUBMIT** and P(win) is bounded by that governance choice, not by file quality.

## Pass 2 — Bug/irregularity hunt (fixed or flagged)

1. **[FIXED] `scripts/validate_con88.py` crashed with an unhandled `FileNotFoundError`** on a fresh
   checkout (canary surfaces live in uncommitted `.cache/`). Now fails closed: exit 1,
   `AUDIT_ERROR` JSON naming the missing prerequisite, stored gates file not overwritten.
   Regression tests: `tests/test_validate_con88_failclosed.py` (5 passed with the existing
   uniqueness tests).
2. **[FLAGGED IR-88-222254A5-02]** CON88's TIFF is the only published file *without* the
   `-DO-NOT-SUBMIT` filename marker, while the current decision blocks submission — a user could
   read the filename as clearance. Renaming would break stored hashes/links/tests, so it is
   flagged, not silently renamed; `docs/con88.html` already carries the blocked banner.
3. **[FLAGGED IR-88-222254A5-03]** `PROMPT.md`'s top handoff still says CON88 is "✅ OK TO SUBMIT",
   superseded by README/`docs/status.json`. Left untouched (historical handoff chain); README and
   `docs/status.json` are authoritative and agree: `ok_to_submit: false`.
4. `audit_downloads.py --check` (47+1 pass, **0 protocol-eligible**), `render_decision.py --check`,
   and `python -O scripts/check_site.py` all PASS unmodified — site, manifest and audit agree.
5. **[FLAGGED, pre-existing]** Full suite: **872 passed / 23 skipped, 4 failed** — and the identical
   4 failures reproduce on the clean tree (`git stash`, verified): publication-guard source-hash
   drift (`docs/data/hypothesis_queue.json`), README inventory counts, a docs-link guard, and a
   dated browser receipt. None is caused by this session; fixing the hash bindings requires
   reviewing the drifted sources, not blindly regenerating hashes (AGENTS.md).

## Pass 3 — Re-check against the full request

- **Unique TIF, easy download, obvious status:** the unique candidate exists and is downloadable
  from `docs/con88.html` / `docs/index.html`; the site's first screen states
  "Research download. Not cleared to submit." with a ⛔ pill. What this session adds is the
  measured proof that the blocker is a vacuous definition (H33 fails it too), so the selector can
  unblock with one explicit protocol decision instead of more candidate generation.
- **No new TIFF was generated this session** (guard exit 2 honoured; no internal-function evasion —
  the 4fd0d184 incident pattern). Generating another near-duplicate research raster would drift
  lanes (CON88 variants would exceed 0.70 overlap vs CON88 itself) and add zero information.
- **Ranked untried hypotheses** (grep-verified unimplemented in `src/gems88/` + candidate runners;
  full layers/falsification in `registry/hypothesis_queue.json`): 1) **H88-SPR** scarp-profile
  restoration vs drainage/shoreline null (medium cost, cached only); 2) **H88-AWA** radiometric
  alteration-width asymmetry (medium); 3) **H88-CBC** conductive basin-breach connectivity
  (medium-high). None may run until the preflight definition is revised; none needs new external
  data (GeoDAWN USGS / GDR 1391 already mirrored).
- **Limitations:** all fleet scores incl. 0.2778/0.4413 are [USER], zero organizer receipts in repo;
  DrivenData auth unavailable in this sandbox, so portal acceptance can only be proven by an actual
  submission receipt; inputs are SHA-pinned owner mirrors, not an authenticated organizer download.

## Run card (summary; machine-readable in `registry/session_222254a5_run_card.json`)

Hypothesis: like-for-like (equal-support) uniqueness, not literal dense support, is the operative
duplication test. Mechanism: dense fields have no dots; top-N comparison. Non-fault mimic: n/a
(measurement claim, falsified if H33's literal overlap were <1.0 — it is 1.0). HOLDOUT-DTI:
CON88 0.0017 [0.0013, 0.0021] (n=60,988) vs record 0.2060 — does not beat the bar.
Correlation/overlap vs registry: 0.487 vs H33, 0.053 equal-support vs dense17, |ρ| ≤ 0.376 [CARD].
Raster SHA-256 `e830b58e…8d68`. Validator: format PASS [MEASURED]; `validate_con88.py` now
fail-closed exit 1 on missing cache. Submission name/note (prepared, unused):
`gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros` /
"H88-CON88 consensus(49,70,BPWD)+label-blind ridge; 3px collar 2.83px spacing H33-profile; gates in run card" (107/140).
**Verdict: negative** (no slot; selector decision on IR-88-222254A5-01 is the next action).
