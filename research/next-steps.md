# Next Steps & Handoff (`GEMSDOE88` · updated `2026-10-24`)

Read `README.md`, `registry/run_card.json`, and `IRREGULARITIES.md` first. The current run is complete; do not rerun MRR-BPR-88 blindly.

## Current verified state

- **Candidate:** `GEMSDOE88-MRR-BPR-20261024-DO-NOT-SUBMIT`.
- **Artifact:** `docs/downloads/gems88-mrr-bpr-blockresid-dinkelbach-20261024-v1-DO-NOT-SUBMIT.tif`.
- **TIFF SHA-256:** `b9cb36519c2ee91c08f587d3c9c006623d8e2505ece0416fdf263b50e42deb7e`.
- **Format:** independent writer and format-audit PASS; single-band float32, exact competition grid, all finite, `[0,1]`, 36,033 binary dots, no positives outside footprint or on catalogue pixels.
- **Leakage:** 4/4 MRR channels PASS; max symmetric AUC `0.532607 <= 0.90`.
- **Candidate HOLDOUT-DTI:** `0.1852558211`, 95% CI `[0.1715190223,0.1999647712]`, `n=22,893`, `gems57-pooled-hide-v2`.
- **Recomputed paired H88 incumbent HOLDOUT-DTI:** `0.1896338558`, 95% CI `[0.1749708832,0.2054805938]`.
- **Paired delta:** `-0.0043780347`, 95% CI `[-0.0079022116,-0.0006230905]` — a conclusive negative result under the preregistered rule.
- **Blind-basin `d_vis>25 px`:** MRR `0.059095` vs incumbent `0.065263`, `n=3,117` withheld positives.
- **Uniqueness:** pre-placement max `|rho|=0.468709`; final sparse-raster max 3-px overlap `0.684178`; H33 overlap `0.402187`; byte- and pixel-unique across 21 accessible rasters. Literal 17GEMSDOE overlap is `1.0`, so the binding any-raster gate fails.
- **Decision:** `negative`; OK to download for research, **DO NOT SUBMIT**. Zero portal slots used and no ORGANIZER-CONFIRMED score exists.

## Scientific conclusion

Blockwise removal of the local vertical-to-regional magnetic relation did not add recoverable whole-fault signal beyond H88-ADHR. The failure is unlikely to be simple catalogue leakage because every new channel's feature-alone canary is near chance. The feature family also loses on the intended far-blind-basin subset. Retire `MRR-BPR-88` rather than retuning it after seeing these folds.

## Next actions—separate future session

1. **No weekly slot for MRR-BPR-88.** Its paired CI is entirely negative even before the universal literal witness is considered.
2. **Do not silently change the registry rule.** The SHA-pinned 17GEMSDOE surface is positive everywhere, making literal forward overlap `1.0` for every nonempty candidate. Only an explicit human protocol amendment can change that; current authorization has not.
3. **Authenticate organizer bytes before any future upload.** Compare a portal-downloaded `sample_submission.tif` with the pinned owner mirror. This session had no DrivenData authentication.
4. **If new work is authorized, preregister a genuinely different method lane.** Do not continue with connected MRR ridges or tune block size on these results; that would be post-hoc reuse of the same failed lane. Re-rank fresh hypotheses against the current 21-raster registry and preserve whole-component blocked evaluation.
5. **Keep scores epistemically separated.** H33 `0.2778` remains a user report/CLAIM. Local values are HOLDOUT-DTI only. ORGANIZER-CONFIRMED requires a real receipt.
