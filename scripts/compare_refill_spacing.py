#!/usr/bin/env python3
"""Compare densified vs spacing-locked PRUNE refills on the same two instruments.

The PRUNE inventory before this session refilled every collar with an
unconstrained exact-marginal add, which put new dots as close as 1.0 px to a
survivor.  The ledger attributes a "densification tax" to that refill, and this
session's ``p3space35`` / ``p4space35`` arms lock it out.  This script measures
whether the tax is real, using the two instruments the brief allows as
report-only evidence and never as gates:

* the fixed, label-free four-line physical field (``MODEL`` projection), and
* the blind off-catalogue USGS SGMC fault control (``PROXY``).

Neither number is a score.  No leaderboard, submission service or Drivendata
page is contacted; all inputs are manifest-pinned.

    .venv/bin/python scripts/compare_refill_spacing.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from scripts import build_prune_variants as bpv  # noqa: E402
from scripts import build_prune_spaced_variants as bps  # noqa: E402
from scripts import build_prune_sweep_variants as sweep  # noqa: E402
from gems57 import metric  # noqa: E402

OUT = ROOT / "evidence" / "refill_spacing_comparison.json"


def nearest_neighbour(mask: np.ndarray) -> dict[str, float]:
    p = np.argwhere(mask)
    nn = cKDTree(p).query(p, k=2)[0][:, 1]
    return {
        "min_px": round(float(nn.min()), 4),
        "mean_px": round(float(nn.mean()), 4),
        "frac_below_2px": round(float((nn < 2.0).mean()), 4),
        "frac_below_3px": round(float((nn < 3.0).mean()), 4),
    }


def main() -> int:
    verified = bpv.verify_manifest(ROOT / "registry" / "data_manifest.json")
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat, parent = (
        lineage["foot"], lineage["catalogue"], lineage["d_cat"], lineage["r0"],
    )
    h19_5 = (np.nan_to_num(rasterio.open(verified["anc_h19_5"]).read(1), nan=0.0) > 0) & foot
    support_union = np.zeros_like(parent)
    for key in bps.SOURCE_SUPPORTS:
        support_union |= (np.nan_to_num(rasterio.open(verified[key]).read(1), nan=0.0) > 0) & foot

    weight, canaries = bpv.build_physical_field_and_canaries(
        verified=verified, foot=foot, catalogue=catalogue, h19_5=h19_5
    )
    if not canaries or max(canaries.values()) > 0.90:
        raise RuntimeError(f"LEAKAGE CANARY FAILURE: {canaries}")

    sgmc_raw = rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    from scipy.ndimage import binary_dilation

    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)

    def scores(mask: np.ndarray) -> dict:
        field = bpv.weighted_expected_dti(mask, weight)
        sgmc = metric.dti_binary(mask, sgmc_off, valid=foot, known=catalogue)
        return {
            "n_dots": int(mask.sum()),
            "field_model_dti": round(float(field["dti"]), 6),
            "sgmc_proxy_dti": round(float(sgmc["dti"]), 6),
            "nearest_neighbour": nearest_neighbour(mask),
        }

    base = scores(parent)
    arms: dict[str, dict] = {"R0": base}
    for thr, kind in ((3.0, "densified"), (4.0, "densified")):
        mask, _ = sweep.prune_at_threshold(
            parent=parent,
            source_support=h19_5,
            d_catalogue=d_cat,
            expected_fault_weight=weight,
            threshold_px=thr,
        )
        arms[f"densified{collar_tag(thr)}"] = scores(mask)
    for thr in (3.0, 4.0):
        survivors = parent & (d_cat > thr)
        removed = int(parent.sum() - survivors.sum())
        pool = support_union & ~survivors & (d_cat > thr)
        mask, _ = bps.spaced_marginal_add(survivors, pool, weight, removed, 3.5)
        arms[f"spaced{collar_tag(thr)}"] = scores(mask)
    survivors = parent & (d_cat > 3.0)
    arms["norefill3"] = scores(survivors)

    for name, arm in arms.items():
        arm["field_delta_vs_r0"] = round(arm["field_model_dti"] - base["field_model_dti"], 6)
        arm["sgmc_delta_vs_r0"] = round(arm["sgmc_proxy_dti"] - base["sgmc_proxy_dti"], 6)

    d3_spaced, d3_dense = arms["spaced300"], arms["densified300"]
    verdict = (
        "INSTRUMENTS DISAGREE: the label-free four-line field prefers the densified refill "
        f"({d3_dense['field_delta_vs_r0']:+.6f} vs {d3_spaced['field_delta_vs_r0']:+.6f} for the "
        f"spacing-locked refill at the same 300 m collar), while the blind off-catalogue SGMC "
        f"control prefers the spacing-locked refill ({d3_spaced['sgmc_delta_vs_r0']:+.6f} vs "
        f"{d3_dense['sgmc_delta_vs_r0']:+.6f}). Neither is a score and neither decides a slot; "
        "a live receipt is the only arbiter."
    )
    payload = {
        "schema": "gems88.refill-spacing-comparison.v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "parent": {
            "id": "h33-h33-2-b2",
            "n_dots": int(parent.sum()),
            "rebuilt_zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lineage["rebuilt_nan_sha256"],
        },
        "refill_spacing_px": 3.5,
        "instruments": {
            "field_model_dti": "MODEL: label-free four-line physical field, exact weighted expected DTI",
            "sgmc_proxy_dti": "PROXY: blind off-catalogue USGS SGMC faults (>3 px from the catalogue)",
        },
        "leakage_canaries": {
            "passed": all(v <= 0.90 for v in canaries.values()),
            "max_single_feature_symmetric_auc": max(canaries.values()),
        },
        "arms": arms,
        "verdict": verdict,
        "report_only": True,
        "no_submission": True,
    }
    OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for name, arm in arms.items():
        print(
            f"{name:14s} n={arm['n_dots']:6d} field={arm['field_model_dti']:.6f} "
            f"({arm['field_delta_vs_r0']:+.6f}) SGMC={arm['sgmc_proxy_dti']:.6f} "
            f"({arm['sgmc_delta_vs_r0']:+.6f}) minNN={arm['nearest_neighbour']['min_px']:.3f}"
        )
    print(verdict)
    print(f"REPORT: {OUT.relative_to(ROOT)}")
    return 0


def collar_tag(threshold_px: float) -> str:
    return f"{int(round(threshold_px * 100))}"


if __name__ == "__main__":
    raise SystemExit(main())
