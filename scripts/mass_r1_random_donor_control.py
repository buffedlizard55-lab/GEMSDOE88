#!/usr/bin/env python3
"""Report-only controls for the merged AXIS=MASS bracket on gate-clean ``R1``.

The three ``MASS`` arms on ``R1`` (PR #46: ``MASSr1m10minus/plus/swap``) are
already built and ledgered; this script adds the control that family is missing
and that decides how the ``+10%`` arm should be read:

* ``random``  — 3,765 uniformly random cells from the same candidate pool
  (``H19-5 & ~R1 & d_cat > 3 px``, seed ``20261023``). An ADD arm raises the
  kernel credit ``T`` and the mass ``S`` together, so some of any add-arm gain is
  a pure count effect. Whatever ``random`` recovers is *not* evidence of ranking.
* ``static_bottom`` / ``static_top`` — the 3,765 worst / best pool cells by the
  one-step marginal expected-DTI gain against the frozen ``R1`` coverage (the
  static analogue of the greedy ranking the arms use). The gap between these two
  and the random draw is the part of the ranking that actually carries
  information; ``static_top`` also re-derives the greedy arm's mask independently.

Nothing here is released, ledgered or gated (Brief §6: the SGMC control, the
holdout proxy and the canaries are report-only). No competition page, leaderboard,
dropbox or credential is touched, and nothing is submitted.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_prune_variants as bpv  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402
from gems57 import metric  # noqa: E402

REPORT = ROOT / "evidence" / "mass_r1_random_donor_control.json"
MERGED = ROOT / "evidence" / "mass_r1_axis_report.json"
SEED = 20261023
N_DOSE = 3_765
R1_ID = bsv.R1_ID


def static_marginal_gain(base_mask: np.ndarray, cand_mask: np.ndarray, w: np.ndarray) -> np.ndarray:
    """One-step dT for every candidate against the FROZEN coverage of ``base_mask``."""
    H, W = base_mask.shape
    w64 = np.asarray(w, dtype=np.float64)
    cov = np.zeros((H, W), dtype=np.float64)
    by, bx = np.nonzero(base_mask)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = by + int(dy), bx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        np.maximum.at(cov, (ny[ok], nx[ok]), kw)
    cy, cx = np.nonzero(cand_mask)
    dT = np.zeros(len(cy), dtype=np.float64)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = cy + int(dy), cx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        dT[ok] += w64[ny[ok], nx[ok]] * np.maximum(0.0, kw - cov[ny[ok], nx[ok]])
    return dT


def main() -> int:
    t0 = time.time()
    print("[1/4] Verifying pins, rebuilding R0 byte-exactly and the label-free field w ...")
    verified = bpv.verify_manifest()
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5 = lin["h19_5"]
    w_field, canaries = bpv.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    max_auc = max(canaries.values())
    if max_auc > 0.90:
        raise RuntimeError(f"Leakage canary tripped: symmetric AUC {max_auc:.4f} > 0.90")

    print("[2/4] Reconstructing parent R1 and asserting both published SHA-256 ...")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)
    assert int(r1.sum()) == 37_654
    assert float(d_cat[r1].min()) > 3.0
    pool = h19_5 & ~r1 & (d_cat > 3.0)
    print(f"      R1 OK | candidate pool {int(pool.sum()):,} px")

    print("[3/4] Building the three report-only controls ...")
    py, px = np.nonzero(pool)
    dT = static_marginal_gain(r1, pool, w_field)
    order = np.argsort(-dT, kind="stable")
    top = order[:N_DOSE]
    bottom = order[-N_DOSE:]
    rng = np.random.default_rng(SEED)
    rand = rng.choice(py.size, size=N_DOSE, replace=False)

    masks = {}
    means = {}
    for name, sel in (("static_top", top), ("random", rand), ("static_bottom", bottom)):
        m = r1.copy()
        m[py[sel], px[sel]] = True
        means[name] = float(dT[sel].mean())
        assert int(m.sum()) == 37_654 + N_DOSE
        assert float(d_cat[m].min()) > 3.0
        assert not (m & catalogue).any()
        masks[name] = m

    sgmc_raw = rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    r1_terms = bpv.weighted_expected_dti(r1, w_field)
    r1_sgmc = metric.dti_binary(r1, sgmc_off, valid=foot, known=catalogue)["dti"]

    controls = {}
    for name, m in masks.items():
        terms = bpv.weighted_expected_dti(m, w_field)
        sgmc = metric.dti_binary(m, sgmc_off, valid=foot, known=catalogue)["dti"]
        controls[name] = {
            "evidence_label": "PROXY",
            "n_dots": int(m.sum()),
            "n_added": N_DOSE,
            "sgmc_off_catalogue_dti": round(float(sgmc), 6),
            "sgmc_delta_vs_r1": round(float(sgmc) - float(r1_sgmc), 6),
            "w_model_delta_vs_r1": round(terms["dti"] - r1_terms["dti"], 6),
            "mean_static_dT_per_added_dot": round(means[name], 6),
            "cv_12km": round(bpv.compute_block_cv(m, foot, 120), 4),
        }

    merged = json.loads(MERGED.read_text()) if MERGED.is_file() else {}
    arm_sgmc = {
        k.split("-MASS")[-1].split("-2026")[0]: (
            v.get("sgmc_control", {}).get("dti", v.get("sgmc_off_catalogue_dti"))
        )
        for k, v in (merged.get("report_only") or {}).items()
        if "MASS" in k
    }
    arm_sgmc = {k.split("-MASS")[-1].split("-2026")[0]: v for k, v in arm_sgmc.items()}

    payload = {
        "schema": "gems88.mass-r1-controls.v1",
        "role": (
            "REPORT-ONLY controls for the merged (R1, MASS, r1m10*) family (PR #46). "
            "Never a gate; no raster is released, ledgered or submitted."
        ),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": bpv.git_sha(),
        "seed": SEED,
        "dose": {"fraction": 0.10, "n_dots": N_DOSE},
        "parent": {
            "id": R1_ID,
            "n_dots": int(r1.sum()),
            "sgmc_off_catalogue_dti": round(float(r1_sgmc), 6),
            "w_model_dti": round(r1_terms["dti"], 6),
        },
        "candidate_pool_px": int(pool.sum()),
        "controls": controls,
        "merged_family_arms": arm_sgmc,
        "leakage_canaries": {"passed": True, "max_symmetric_auc": max_auc, "channels": canaries},
        "reading": (
            "Compare sgmc_delta_vs_r1 across static_bottom < random < static_top. "
            "The random control is the pure count effect of adding 3,765 admissible dots; "
            "static_top minus random is the information in the ranking. The greedy arm's "
            "own value is quoted from evidence/mass_r1_axis_report.json, not recomputed here."
        ),
    }
    REPORT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    print("[4/4] Controls written to", REPORT.relative_to(ROOT))
    for name, c in controls.items():
        print(f"      {name:14s} SGMC {c['sgmc_off_catalogue_dti']:.6f} "
              f"({c['sgmc_delta_vs_r1']:+.6f}) | w-model {c['w_model_delta_vs_r1']:+.6f} | "
              f"mean static dT {c['mean_static_dT_per_added_dot']:.6f}")
    print(f"      parent R1      SGMC {r1_sgmc:.6f}")
    print(f"      merged arm     {json.dumps(arm_sgmc)}")
    print(f"      elapsed {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
