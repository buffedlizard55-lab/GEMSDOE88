#!/usr/bin/env python3
"""Write H88-UNIQ-20261025 run card and gate verdict with unique names (no overlap with test fixtures)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

run_card = json.loads((ROOT / "registry" / "run_card_uniq25.json").read_text())
gate_verdict = json.loads((ROOT / "registry" / "gate_verdict_uniq25.json").read_text())

# Rewrite run_card paths from generic to uniq-specific
run_card["downloadable_file"] = "downloads/gems88-uniq-20261025-DO-NOT-SUBMIT.tif"
run_card["artifact"] = "docs/downloads/gems88-uniq-20261025-DO-NOT-SUBMIT.tif"
run_card["zip_artifact"] = "docs/downloads/gems88-uniq-20261025-DO-NOT-SUBMIT.zip"

# Write to unique names (no collision with test fixtures)
destinations = [
    "registry/run_card_uniq25.json",
    "docs/run_card_uniq25.json",
    "docs/data/run-card_uniq25.json",
    "evidence/run-card_uniq25.json",
]
for dest in destinations:
    p = ROOT / dest
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")

gate_destinations = ["registry/gate_verdict_uniq25.json"]
for dest in gate_destinations:
    p = ROOT / dest
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(gate_verdict, indent=2, allow_nan=False) + "\n")

print("Wrote run_card_uniq25.json to:", destinations)
print("Wrote gate_verdict_uniq25.json to:", gate_destinations)
print("Verdict:", gate_verdict["verdict"])
print("OK to download:", gate_verdict["ok_to_download"])
print("OK to submit:", gate_verdict["ok_to_submit"])
