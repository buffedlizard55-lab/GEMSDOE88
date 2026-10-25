#!/usr/bin/env python3
"""Publish step: ledger rows + mechanism cards for the CONCENTRATION variants.

Reads the builder's report (``registry/concentration_report.json``) and the
MODEL projection (``registry/concentration_projection.json``), and writes

* ``ledger/submissions.csv`` -- one row per built variant, with the receipt
  columns left empty for the human, and the projection's point estimate as
  ``predicted_change``;
* ``ledger/mechanism_cards.json`` -- one card per variant (hypothesis,
  mechanism, non-fault mimic, predicted sign and size, falsifier).

Rows already in the ledger (the MASS axis from the previous session) are kept
verbatim; the schema is extended with ``receipt_score`` and ``receipt_date`` on
every row so the human fills one format.
"""

from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
FIELDS = ["id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256",
          "sha256_zeros", "status", "predicted_change", "receipt_score",
          "receipt_date", "description"]


def load_existing() -> list[dict]:
    if not LEDGER.is_file():
        return []
    with LEDGER.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.setdefault("receipt_score", "")
        r.setdefault("receipt_date", "")
        # the pre-existing rows were written with a "%_changed" header
        if not r.get("pct_changed") and r.get("%_changed"):
            r["pct_changed"] = r["%_changed"]
        if r.get("id", "").endswith(".tif"):
            r["id"] = r["id"][:-4]
    return rows


def main() -> int:
    report = json.loads((ROOT / "registry" / "concentration_report.json").read_text())
    proj = json.loads((ROOT / "registry" / "concentration_projection.json").read_text())
    rows = load_existing()
    have = {r["id"] for r in rows}
    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}

    for vid, v in report["variants"].items():
        d = v["diff_stats"]
        p = proj["variants"][vid]
        predicted = f"{p['point_estimate']:+.3f}"
        tag = vid.split("-CONC")[1].split("-2026")[0]
        block = 50 if tag.startswith("b50px") else 10
        desc = (f"Move {d['n_moved']} dots ({d['pct_of_parent_dots_moved']:.0f}%) from the coldest to the "
                f"hottest {block}px ({block / 10:g} km) blocks; prior = 2-block smoothed parent density; "
                f"count fixed at {d['n_dots']}; CV_occ {d['block_stats_before']['cv_occupied_blocks']:.3f}->"
                f"{d['block_stats_after']['cv_occupied_blocks']:.3f}; receivers welded <=1.42 px to a "
                f"surviving host dot; donors keep one dot per block.")
        row = {
            "id": vid[:-4] if vid.endswith(".tif") else vid, "parent": "h33-h33-2-b2", "axis": "CONCENTRATION", "value": tag,
            "n_dots": d["n_dots"], "pct_changed": f"{d['pct_of_parent_dots_moved']:.2f}",
            "sha256": v["nan"]["sha256"], "sha256_zeros": v["zeros"]["sha256"],
            "status": "BUILT", "predicted_change": predicted,
            "receipt_score": "", "receipt_date": "", "description": desc,
        }
        if row["id"] in have:
            rows = [row if r["id"] == row["id"] else r for r in rows]
        else:
            rows.append(row)

        cards[row["id"]] = {
            "axis": "CONCENTRATION",
            "value": tag,
            "block_px": block,
            "moved_fraction": round(d["pct_of_parent_dots_moved"] / 100.0, 4),
            "hypothesis": (
                "At a fixed dot count, raising local dot density on the parent's most confident km-scale "
                "clusters raises the metric more than the relocation costs, because the metric's false-positive "
                "term is sum_x p(x)(1 - max_g k): a dot welded next to an already-covering dot pays almost no "
                "penalty (0.2(1 - k) ~ 0.07 at 1 px) while a dot in an empty km block pays the full 0.2. "
                "Mass moved out of the coldest blocks therefore relieves denominator weight that the parent was "
                "still paying."),
            "mechanism": (
                f"DTI = T / (0.2T + 0.2(n - M) + 0.8|G|) with n fixed at {d['n_dots']}. Each move changes "
                "the denominator by 0.2(t_add - t_rm + m_rm - m_add). Donors are drawn from the coldest 1 km "
                "blocks (mean block prior "
                f"{d['removed_block_prior_mean']:.2f} dots/km2) where m_rm ~ 0; receivers land in blocks with "
                f"mean prior {d['added_block_prior_mean']:.2f} dots/km2 at {d['added_distance_to_host_px_mean']:.2f} px "
                "from a surviving host, so m_add is inherited from the host's proximity to truth. "
                "No new pixels enter the catalogue collar and no block is emptied."),
            "non_fault_mimic": (
                "Pleistocene Lake Lahontan benches and GeoDAWN E-W flight-line corrugation both survive "
                "edge filters and pack into km-scale bands; welding dots onto them raises M only if the "
                "host is actually near truth, so a mimic shows up as a null (m_add ~ 0), not a false gain. "
                "Conversely, alluvial geothermal outflow along range fronts forms km-scale clusters with no "
                "fault slip, which would produce a real m_add but nothing in T."),
            "predicted_sign_size": (
                f"MODEL {predicted} live, scenario range [{p['range_scenarios'][0]:+.3f}, "
                f"{p['range_scenarios'][1]:+.3f}]. Point scenario: m_add 0.30, t_rm 0.02, m_rm 0.02, "
                "t_add = 0.2 m_add, calibrated on the two CLAIM pairs (0.2778 / 0.2600). The sign is not "
                "guaranteed: at m_add <= 0.15 and t_rm >= 0.02 the recall lost from the donors dominates."),
            "confounder": (
                "CV excursion. Under every estimator tried, R0 sits at 0.62 (raw 1 km counts, occupied "
                "blocks) / 0.48 (5 km-smoothed density); these variants push it to 1.02-1.36 / 0.67-1.07, "
                "far outside the 0.51-0.59 band the brief quotes for the best files. If that band is "
                "causal and not an artefact of the estimator, the live change should be negative even "
                "though the algebra predicts positive. That is the cleanest way to falsify the folklore."),
            "falsifier": (
                "Live change <= -0.010: concentration past the parent costs real recall, the cold-tail "
                "donors were catching isolated blind faults, and the axis is closed. "
                "Live change in (-0.010, +0.010): the metric's redundancy credit is too small to matter at "
                "10-20 % and the axis is closed as sub-noise at this dose. "
                "Live change >= +0.010 with the 20 % move > 10 % move: mechanism confirmed, scale the dose "
                "and combine with the best MASS setting next session."),
        }

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")
    print(f"ledger rows: {len(rows)}; cards: {len(cards)}")
    for r in rows:
        print(f"  {r['axis']:14s} {r['value']:12s} {r['n_dots']:>6} {r['predicted_change']:>7}  {r['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
