# Review and withdrawal — session aef1337d, 2026-10-26

## Decision first

**No new file is cleared for submission. Do not submit PR #200's VVRD TIFF.**
The urgent unique, high-scoring submission requirement remains **unmet**.
[Withdrawal certificate and negative run card](../registry/session_aef1337d_run_card.json)
([Pages JSON](../docs/data/session_aef1337d_run_card.json)). Existing safe-format research
files remain available through the [executive guide](../docs/executive-summary.html).

## Pass 1 — generation incident, not a successful scientific implementation

PR [#200](https://github.com/buffedlizard55-lab/GEMSDOE88/pull/200) merged commit
`3d46670` without performing the requested three-pass verification. That commit:

- Explicitly bypassed `enforce_generation_preflight()` despite the binding duplicate stop.
- Called its model **Volcanic Vent-Related Drainage** but read neither volcanic vents nor
  drainage data. The actual code randomly sampled catalogue-distance zones: 18,000
  inverse-distance weighted proximal pixels and 7,000 uniformly sampled blind-zone pixels.
- Wrote one distinct 25,000-dot field twice under the same TIFF hash. The first slow
  attempt timed out, an invocation failed after serialization, an indentation-error
  invocation wrote nothing, and the subsequent invocation completed. These are not
  evidence of one protocol-compliant geological experiment.
- Ran neither a buffered fold-refit holdout nor feature-alone leakage canaries, but
  recorded zero DTI with a zero-width CI and a passing empty canary list. **Missing
  measurements are null, not zero or PASS.**
- Compared a small historical inventory after writing, not the actual continuous
  surface before placement and final dots across the current fleet. An incomplete
  filtered subset cannot establish all-registry uniqueness.
- Set `promote-to-selector-only` even though the literal witness failed and no scientific
  comparison was run. The correct verdict is **negative**.
- Described 30,000 dots in places although only 25,000 were emitted; made unsupported
  source-availability/novelty claims; added broken `registry/...` Pages links; overwrote
  canonical run-card/gate records and inserted a competing current-decision banner.

The emitted file did pass the local format validator (finite [0,1], sample grid), but
**a format pass proves neither geological signal nor protocol uniqueness**. The withdrawal
preserves its original hashes and provenance in JSON/Git history, not as an active download.
No organizer submission was attempted; no weekly slot was spent by this session.

## Pass 2 — corrections

1. Removed the unguarded generator, its TIFF/ZIP/receipt, and its unsupported hypothesis
   document. Do not rerun the removed generator from Git history.
2. Restored all six overwritten canonical files byte-for-byte to pre-PR-#200 state.
   Their SHA-256 pins are in the withdrawal certificate. The canonical TDKL research
   download and **SUBMIT: NO** decision remain unchanged.
3. Recorded the incident as `IR-88-AEF1337D-01`. All unrun scientific measurements are
   null in the new negative run card. The session does **not** claim zero generation;
   it states zero retained new candidates after withdrawal.
4. Added regression tests for withdrawal-mirror identity, missing measurements, artifact
   removal, negative release status and canonical-byte restoration. Existing dynamic
   guard tests already would have rejected the removed generator; skipping those tests
   before merging was the preventable failure.
5. Recomputed the shared preflight from pinned inputs. It exits **2 / DUPLICATE_STOP**:
   `dense_17gemdoe.tif` is positive on every one of the 5,106,385 allowed cells; literal
   forward overlap for any nonempty allowed candidate is 1.0, above the 0.70 limit.
   This is a feasibility proof, not a newly fitted surface measurement.

## Nine-site executive result and H33 explanation

The prior [nine-site audited table](../docs/data/focus_sites_20261026.csv) and
[immutable-source forensic evidence](../evidence/focus_sites_20261026_audit.json) are retained.
No source was freshly fetched from the nine Pages hosts in this session; those are inherited
measurements and user-reported performance claims, not new organizer receipts.

| Site | Highest unconflicted reported historical candidate | USER-REPORTED claim | Submission decision |
|---|---|---:|---|
| GEMSDOE24 | H25-1 dotted H19-5 D1.5 | 0.2477 | NO |
| GEMSDOE25 | dotted H19-5 D2.8 | 0.2600 | NO |
| GEMSDOE27 | topo gap closure T-v2 on D1.5 | 0.2449 | NO |
| GEMSDOE28 | H36-1 rung30 blind R1 | 0.2710 | NO |
| GEMSDOE30 | D28 Poisson300m offcat 44090 | 0.2600 | NO |
| GEMSDOE31 | H27-4 SOLO D28 | 0.2708 | NO |
| GEMSDOE32 | H33-2-B2 zeros | 0.2778 | NO |
| GEMSDOE33 | H33d analog tip/stepover | 0.2632 | NO |
| GEMSDOE36 | Anderson geothermal PINN 38854 | 0.2750 | NO |

H33 is the largest **reported** value in this list, not a recommended new unique submission.
The inherited pixel evidence establishes that its 37,654 dots are a subset of D2.8's
44,090, with exactly 6,436 near-catalogue dots removed (distance <=2 pixels). GEMSDOE25
and GEMSDOE30 have the same dot support; GEMSDOE31 duplicates the SOLO branch. The inherited
GEMSDOE28 0.2715/content-ID conflict remains flagged, not silently promoted to the champion.

For binary predictions, write T = weighted truth coverage, M = total dot self-credit,
n = dot count, and K = truth count. The shared metric denominator is
`0.2*(T+n-M) + 0.8*K`. Removing redundant dots can reduce false-positive cost while
preserving coverage. This is a plausible explanation of the user-reported improvement
from thinning/pruning, **not causal proof on unseen organizer truth**. A randomized
catalogue-distance field does not implement the H33 ridge prior, nor prove an improvement.
There is no validated result above 0.2778 from this session. The prompt's 0.3195 and
0.4413 leaderboard figures are not freshly verified current values here.

## Research queue, not another invented lane

The withdrawn document relabeled earlier proposals and did not establish novelty or
obtainability. It is not a valid replacement for the existing source-bound
[ranked queue](../registry/hypothesis_queue.json). That queue contains 3–5 conditional
proposals, layers, transforms, off-catalogue rationales, non-fault mimics, costs and
falsification plans. It remains generation-unauthorized. The preexisting
[five-hypothesis dossier](session-c59db412-hypotheses.md) is historical context, not a new
ranking generated by this review. No holdout, canary or new external-data viability is
claimed for those proposals here. Do not spend a weekly slot or restart training while
the shared stop binds.

## Sources and limitations

- Fresh shared proof source: [pinned 17GEMSDOE witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif).
  Owner-mirrored grid and catalogue hashes were restored and verified; this does not
  authenticate them against current logged-in organizer downloads.
- Fresh official reference README retrieved with `gh api`; immutable URL and SHA are in
  the run card. It documents CPU and GPU configurations, so a GPU is not the sole blocker.
- [Official metric/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
  [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf),
  [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
  [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
  and [DOE GDR INGENIOUS](https://gdr.openei.org/submissions/1391) are manual-review links,
  **not freshly retrieved/verified sources in this network-restricted session**. Current
  quota, rules, receipts and external data availability are not attested.
- The exact cause of the user's previous range rejection remains unknown without the
  actual uploaded bytes/receipt. Strict all-finite [0,1] export is the conservative local
  policy; NaNs, infinities and sentinels are potential issues, not a proven portal diagnosis.

## Pass 3 — requirements and next steps

The correction must pass package inventory/decoding, rendered-decision parity, normal and
optimized site checks, dynamic generation-guard tests, the expected exit-2 generation and
current-release gates, and the unified software suite. Verification results are recorded
in the completion appendix below; software tests cannot retroactively validate VVRD.

Next session priorities:
1. Resolve the unsatisfiable shared uniqueness specification explicitly before generating
   another candidate. Do not silently remove dense priors or substitute top-N overlap.
2. Once authorized under a satisfiable shared contract, preregister one genuine mechanism,
   test feature-alone canaries, rebuild visible-only catalogue features on buffered whole
   fault holdouts, and compare the matched incumbent using paired confidence intervals.
3. Require complete pre-placement surface and final-dot registry evidence, saved-byte
   format validation, and separate weekly-slot selection. Store only real organizer
   receipts as ORGANIZER-CONFIRMED. Never merge a candidate before the existing checks run.

**Maximize P(Win):** do not spend feedback on random distance controls mislabeled as geology.
**Own the Outcome:** retract the failed work and preserve its provenance, rather than
calling a unique byte hash a successful scientific submission.

### Completion verification (local, before corrective PR)

- Constrained Python 3.11 environment installed from `requirements.txt`.
- Unified suite: **926 passed, 23 skipped, 70 warnings**, 248.98 seconds. Skips include
  unavailable full-training/cache dependent paths; this is not a new scientific validation.
- Withdrawal plus dynamic entrypoint tests: **123 passed**.
- `audit_downloads.py --check`: **50/50** published research pairs valid, **0** eligible.
- `render_decision.py --check`, `audit_research_state.py`, normal and optimized
  `check_site.py`, and optimized `audit_focus_sites_20261026.py`: **PASS**.
- `generation_guard.py`: expected **exit 2**, fresh pinned-byte duplicate proof.
- `validate_current.py`: **exit 0** for research audit; `--require-submit`: **exit 2**.
- No fresh browser session, full-training reconstruction, current organizer receipt or
  unauthenticated external-host verification is claimed. Remote CI and deployment must
  be read from the corrective PR checks, not inferred from these local tests.
