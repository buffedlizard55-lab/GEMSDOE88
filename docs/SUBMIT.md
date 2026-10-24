# Submission Checklist — Current Candidate

## Automated decision (`2026-10-24`)

- **Candidate:** `GEMSDOE88-MRR-BPR-20261024-DO-NOT-SUBMIT`
- **Research TIFF:** `docs/downloads/gems88-mrr-bpr-blockresid-dinkelbach-20261024-v1-DO-NOT-SUBMIT.tif`
- **TIFF SHA-256:** `b9cb36519c2ee91c08f587d3c9c006623d8e2505ece0416fdf263b50e42deb7e`
- **OK to download for research:** **YES**
- **OK to submit:** **NO — DO NOT SUBMIT**
- **Weekly slots used:** `0`
- **ORGANIZER-CONFIRMED score:** none

The file passes all format checks but fails two independent gates:

1. **Scientific:** candidate HOLDOUT-DTI `0.1852558211` (95% CI `[0.1715190223,0.1999647712]`, `n=22,893`, `gems57-pooled-hide-v2`) is below the recomputed paired H88 incumbent `0.1896338558`. Paired delta `-0.0043780347`, 95% CI `[-0.0079022116,-0.0006230905]`.
2. **Literal registry uniqueness:** 17GEMSDOE is positive over the entire allowed footprint, so the final forward 3-pixel overlap is `1.0000 > 0.70`. No exemption is authorized.

Do not upload the current TIFF or ZIP. The exact note below is archival identification, not upload authorization:

> `MRR88 block-VG residual+demag trough; 36033 dots; HOLDOUT-DTI 0.1853; literal registry overlap blocks submit`

## Reproduce the fail-closed decision

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/restore_inputs.py
.venv/bin/python scripts/run_mrr88_experiment.py
.venv/bin/python scripts/validate_release.py
.venv/bin/python scripts/validate_release.py --require-submit  # expected exit 2
```

The default validator exits zero because the research download is internally valid and its negative status is truthful. `--require-submit` must exit `2` for this candidate.

## Preconditions for any future candidate

A future file may be considered only when all are true:

- paired whole-component HOLDOUT-DTI improvement has a 95% CI above zero;
- every feature-alone symmetric AUC is `<=0.90`;
- pre-placement surface `|rho|<=0.90` and final 3-pixel forward overlap `<=0.70` under the currently authorized all-raster rule;
- the saved TIFF and one-member ZIP pass exact grid, all-finite, `[0,1]`, and hash checks;
- the authenticated organizer template bytes are verified;
- a human portfolio selector explicitly chooses to spend one weekly slot.

After an authorized manual upload, archive the portal receipt and label its score **ORGANIZER-CONFIRMED**. Never treat H33's user-reported `0.2778`, HOLDOUT-DTI, MODEL, or PROXY values as a receipt.

Historical PRUNE and prior H88 upload suggestions are superseded by this checklist and are not current slot authorizations.
