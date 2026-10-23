#!/usr/bin/env python3
"""Write the tracked receipts for the CONCENTRATION releases.

The competition rasters themselves stay out of the public repository (data-use
terms unchecked, `.gitignore` -> `/releases/*.tif`). What is tracked is a small
JSON per candidate: identity, hashes, the human form fields (name + <=140-char
note), the gate evidence pointer, the MODEL prediction and the exact command
that rebuilds the file byte-for-byte.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "releases"

NOTES = {
    "b10px-m20": "h33-2-b2 CONC 1km 20% coldest->hottest blocks; 37654 dots CV .62->1.26; pred +0.020 MODEL; R0 0.2778 CLAIM",
    "b10px-m10": "h33-2-b2 CONC 1km 10% coldest->hottest blocks; 37654 dots CV .62->1.02; pred +0.011 MODEL; R0 0.2778 CLAIM",
    "b50px-m20": "h33-2-b2 CONC 5km 20% coldest->hottest blocks; 37654 dots CV .70->1.36; pred +0.006 MODEL; R0 0.2778 CLAIM",
}
ORDER = {"b10px-m20": 1, "b10px-m10": 2, "b50px-m20": 3}


def main() -> int:
    report = json.loads((ROOT / "registry" / "concentration_report.json").read_text())
    proj = json.loads((ROOT / "registry" / "concentration_projection.json").read_text())
    validation = json.loads((ROOT / "registry" / "variant_validation.json").read_text())
    gates = {r["sha256"]: r["gates_pass"] for r in validation["results"]}

    written = []
    for vid, v in sorted(report["variants"].items(),
                         key=lambda kv: ORDER.get(kv[0].split("-CONC")[1].split("-2026")[0], 9)):
        tag = vid.split("-CONC")[1].split("-2026")[0]
        base = vid[:-4] if vid.endswith(".tif") else vid
        note = NOTES[tag]
        assert len(note) <= 140, (tag, len(note))
        d = v["diff_stats"]
        p = proj["variants"][vid]
        receipt = {
            "schema_version": 1,
            "candidate": base,
            "axis": "CONCENTRATION",
            "parent": {"id": "h33-h33-2-b2", "sha256": report["parent"]["sha256"],
                       "n_dots": report["parent"]["n_dots"]},
            "file": {
                "primary": f"releases/{base}.tif",
                "zeros": f"releases/{base}-zeros.tif",
                "sha256": v["nan"]["sha256"],
                "sha256_zeros": v["zeros"]["sha256"],
                "zip": f"releases/{base}.zip",
                "zip_sha256": v["nan"]["zip_sha256"],
                "zip_zeros": f"releases/{base}-zeros.zip",
                "zip_zeros_sha256": v["zeros"]["zip_sha256"],
                "tracked_in_git": False,
                "why_local": "competition raster; public-repository data-use terms unchecked",
            },
            "submission": {
                "name": base,
                "note": note,
                "note_chars": len(note),
                "upload_one_twin_only": True,
            },
            "built": {
                "n_dots": d["n_dots"],
                "n_moved": d["n_moved"],
                "pct_of_parent_dots_moved": round(d["pct_of_parent_dots_moved"], 4),
                "block_px": 50 if tag.startswith("b50px") else 10,
                "blocks_emptied": d["blocks_emptied"],
                "added_distance_to_host_px_mean": round(d["added_distance_to_host_px_mean"], 4),
                "dots_within_2px_catalogue": d["dots_within_2px_catalogue"],
                "dots_within_3px_catalogue": d["dots_within_3px_catalogue"],
                "cv_occupied_before": round(d["block_stats_before"]["cv_occupied_blocks"], 4),
                "cv_occupied_after": round(d["block_stats_after"]["cv_occupied_blocks"], 4),
                "cv_smoothed_5blocks_before": round(
                    report["parent_stats"]["smoothed_density_cv"]["cv_density_smoothed_5blocks"], 4),
                "cv_smoothed_5blocks_after": round(
                    d["smoothed_density_cv_after"]["cv_density_smoothed_5blocks"], 4),
            },
            "prediction": {
                "label": "MODEL",
                "delta": round(p["point_estimate"], 4),
                "range": [round(p["range_scenarios"][0], 4), round(p["range_scenarios"][1], 4)],
                "source": "registry/concentration_projection.json",
            },
            "gates": {
                "validator": "scripts/validate_variant.py",
                "evidence": "registry/variant_validation.json",
                "primary_all_pass": gates.get(v["nan"]["sha256"]),
                "zeros_all_pass": gates.get(v["zeros"]["sha256"]),
                "note": "checks were run against the bytes on disk before the files were untracked",
            },
            "report_only": {
                "proxy": "registry/concentration_proxy.json",
                "proxy_delta_vs_parent": 0.0,
                "proxy_power": "none: R0's 2 px collar already excluded the withheld strands",
                "leakage_canary": "not applicable: no feature channel used",
                "sgmc_control": "not applicable",
            },
            "disposition": (
                "HOLD: inherits R0's 2 px collar, so not eligible under the literal 3 px "
                "non-PRUNE gate. Predicted gain is the highest in the inventory if the human "
                "scopes that gate away from controlled R0 edits."
            ),
            "rebuild": "python scripts/make_concentration_variants.py && "
                       "python scripts/project_concentration.py && "
                       "python scripts/finalize_concentration.py && "
                       "python scripts/write_concentration_receipts.py",
            "provenance": {"git_sha": report["provenance"]["git_sha"],
                           "generated_utc": report["provenance"]["generated_utc"],
                           "builder": "scripts/make_concentration_variants.py"},
        }
        out = RELEASES / f"{base}-receipt.json"
        out.write_text(json.dumps(receipt, indent=2) + "\n")
        written.append(out.name)
        print("wrote", out.relative_to(ROOT), "gates",
              receipt["gates"]["primary_all_pass"], receipt["gates"]["zeros_all_pass"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
