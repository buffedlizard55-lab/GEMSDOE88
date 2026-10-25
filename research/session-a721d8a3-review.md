# Session a721d8a3 — three-pass review (2026-10-25)

## Verdict: negative. No new TIFF. No slot used. Requirement UNMET, stated plainly.

The highest-urgency request (generate a unique, download-and-submit TIFF) conflicts
with the binding parallel-run protocol stored in this repo (`AGENTS.md` §2,
`scripts/generation_guard.py`). That protocol was followed; it stops generation.

## Pass 1 — fresh measurement, not stored claims
- Installed pinned deps (`numpy 2.4.6`, `rasterio 1.4.4`) and restored the
  validation tier: `bash scripts/download_competition_data.sh --validation`
  (SHA-verified owner mirrors; organizer provenance is separate and unverified here).
- `scripts/preflight_mtas88.py --gate-generation` → exit 2, `DUPLICATE_STOP`.
- `scripts/generation_guard.py` → exit 2, `DUPLICATE_STOP`.
- Measured reason: pinned witness `data/registry/dense_17gemdoe.tif`
  (sha256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`)
  has finite >0 values on **5,106,385 / 5,106,385 allowed pixels (1.0000)**.
  Under the literal support rule, every nonempty candidate's forward 3-px
  overlap is therefore 1.0 > 0.70, and surface rank-correlation vs this dense
  raster cannot be cleared either. Protocol step 1 says: log as duplicate and stop.
- No lane paragraph was supplied in the request ("the single method paragraph
  below" — none follows), so no lane was invented.

## Pass 2 — why H33 scored 0.2778 (USER-REPORTED, not ORGANIZER-CONFIRMED)
Fetched 2026-10-25: https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
- H33-2-B2 = 37,654 binary dots pruned from the 0.2708-scoring dotted base,
  deleting every dot within 2 px of the catalogue.
- Mechanism (grid-site's own metric theory, consistent with the published
  Tversky/DTI formula, alpha=0.2, beta=0.8): each emitted pixel not covering a
  new truth pixel costs 0.2 mass; thinning a thick surface to sparse dots at
  ~the break-even credit bar (0.2 × DTI ≈ 0.052–0.055/dot) raises credit per dot.
- IRREGULARITY FLAGGED: the GEMSDOE32 site itself states "NO ORGANISER SCORE
  EXISTS for this or any artifact in this repository", while the prompt lists
  0.2778 as its score. Per protocol §3, 0.2778 is labelled **USER-REPORTED**,
  never ORGANIZER-CONFIRMED. Likewise 0.4413 / 0.3195 have no receipt in-repo;
  a prior session recorded 0.4413 as a non-GEMSDOE participant's public score.
- Beating it requires higher credit density at equal mass — a better off-catalogue
  detector, not a re-emission of H33 geometry (which would also fail uniqueness).

## Pass 3 — re-check against the full request
- "[0,1] portal error": already explained/fixed in-repo — all-finite float32,
  `nodata=None`, values in [0,1]; archived research TIFF revalidated this session
  by the preflight (`ok: true`, sha256 `db9d1867…aaadf`). It remains
  **DO-NOT-SUBMIT**: format validity ≠ uniqueness ≠ slot approval.
- Automated inspection without humans: the preflight + `validate_artifact`
  pipeline does this; it returned a negative, which is a deliverable (protocol §5).
- Hypotheses: the four ranked, untried candidates in `NEW_HYPOTHESES.md`
  (H88-GTD gradient-tensor dimensionality; H88-SPR scarp restoration;
  H88-AWA alteration-width asymmetry; H88-CBBC basin-breach continuity) each name
  layers, transforms, off-catalogue rationale and non-fault mimics. None may be
  executed until the duplicate rule is revised — executing them now would
  produce TIFFs that fail the literal gate by construction.
- Tests: `.venv/bin/python -m pytest tests -q` → **805 passed, 23 skipped**.

## The one decision that unblocks everything (owner action, not a code fix)
Define "dots/support" for dense continuous registry rasters in the shared
protocol (e.g. threshold a probability raster before support is computed), or
exempt dense priors explicitly — in `vendor/gems57/uniqueness.py` + AGENTS.md,
applied to all lanes. Until then any "unique" TIFF produced here would be a
protocol violation dressed as a deliverable, and claiming it could beat
0.2778 would be an unlabelled projection.
