#!/usr/bin/env python3
"""Re-run ONLY the uniqueness gate for the existing headline TIFF against the current registry.

Needed after other sessions merge new rasters into main (e.g. PROVCREST, PR #53).  Does not refit, does not
change the TIFF/ZIP/name; refreshes registry/uniqueness_v3.json (+ docs copy).  Run ``make_run_card.py`` afterwards.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import grid as grid_mod  # noqa: E402
from gems88 import gate, registry_paths  # noqa: E402


def main():
    gv = json.loads((ROOT / "registry/gate_verdict.json").read_text())
    name = gv["name"]
    tif = ROOT / "docs/downloads" / f"{name}.tif"
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    reg = registry_paths.registry_list(exclude=(name,))
    rep = gate.uniqueness_report(tif, reg, g.footprint)
    old = json.loads((ROOT / "registry/uniqueness_v3.json").read_text())
    slim = {k: v for k, v in rep.items() if k != "rows"}
    slim["rows"] = [{k: r.get(k) for k in ("label", "dense", "registry_dots", "literal_overlap_3px", "like_for_like_overlap_3px",
                                            "rho_final", "rho_preplacement", "blocks_literal", "blocks_like_for_like", "duplicate_of", "error")}
                    for r in rep["rows"]]
    # the pre-placement surface is not stored (20 MB); keep the recorded pre-placement correlations of the first run
    old_pre = {r["label"]: r["rho_preplacement"] for r in old["rows"] if "rho_preplacement" in r}
    for r in slim["rows"]:
        if r["label"] in old_pre and old_pre[r["label"]] is not None:
            r["rho_preplacement"] = old_pre[r["label"]]
    pre_max = max((abs(r["rho_preplacement"]) for r in slim["rows"] if r.get("rho_preplacement") is not None), default=0.0)
    slim["worst_abs_rho"] = dict(label=max((r for r in slim["rows"] if r.get("rho_preplacement") is not None),
                                           key=lambda r: max(abs(r["rho_final"]), abs(r["rho_preplacement"])))["label"],
                                 value=max(max(abs(r["rho_final"]), abs(r["rho_preplacement"])) for r in slim["rows"] if r.get("rho_preplacement") is not None))
    slim["refreshed_after_merge_of"] = "PR #53 (PROVCREST) and other main changes; registry now includes docs/downloads of all sessions"
    text = json.dumps(slim, indent=1, default=float)
    (ROOT / "registry/uniqueness_v3.json").write_text(text)
    (ROOT / "docs/data/uniqueness_v3.json").write_text(text)
    print("registry", slim["registry_rasters"], "distinct", slim["distinct_dot_sets"], "unique_l4l", slim["unique_like_for_like"],
          "worst", slim["worst_like_for_like_overlap"], "rho", slim["worst_abs_rho"])


if __name__ == "__main__":
    main()
