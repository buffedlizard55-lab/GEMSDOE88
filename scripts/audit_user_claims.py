#!/usr/bin/env python3
"""Extract the prompt's full result list without laundering claims into scores.

No web scraping and no inferred result for a blank site. Repeated exact entries
are counted once and their number of occurrences is retained. Outputs are
traceable to the checked-in request, not to any organizer receipt.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LABEL = "USER-REPORTED CLAIM — NOT HOLDOUT-DTI OR ORGANIZER-CONFIRMED"


def extract(text: str) -> dict:
    sites = {}
    claims = {}
    site = None
    for number, line in enumerate(text.splitlines(), start=1):
        source = re.fullmatch(r"https://buffedlizard55-lab\.github\.io/([^/]+)/(.*)", line.strip())
        if source:
            site = source[1]
            sites.setdefault(site, {"site": site, "source_url": line.strip(), "reported_entries": 0})
            continue
        result = re.fullmatch(r"([^\s].*?):\s*(0\.\d+)\s*", line)
        if result and site:
            name, value = result.groups()
            key = (site, name, value)
            if key not in claims:
                claims[key] = {
                    "site": site, "source_url": sites[site]["source_url"],
                    "submission_name": name, "user_reported_value": value,
                    "evidence_class": LABEL, "organizer_receipt": None,
                    "request_line_numbers": [],
                }
                sites[site]["reported_entries"] += 1
            claims[key]["request_line_numbers"].append(number)
    return {"schema": "gems88.user-claims-inventory.v1", "evidence_class": LABEL,
            "not_a_live_leaderboard": True, "not_used_as_promotion_evidence": True,
            "sites": list(sites.values()), "claims": list(claims.values()),
            "site_count": len(sites), "distinct_claim_count": len(claims),
            "sites_without_a_reported_result": [s for s, r in sites.items() if not r["reported_entries"]]}


def main(root: Path = ROOT) -> None:
    source = root / "USER_PROMPT_20261026.md"
    report = extract(source.read_text())
    report["request_file"] = source.name
    report["request_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    target = root / "docs/data/user_reported_results.json"
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["site", "source_url", "submission_name", "user_reported_value", "evidence_class", "organizer_receipt", "request_line_numbers"])
    writer.writeheader()
    for row in report["claims"]:
        writer.writerow({**row, "request_line_numbers": ";".join(map(str, row["request_line_numbers"]))})
    (root / "docs/data/user_reported_results.csv").write_text(out.getvalue())
    print(json.dumps({k: report[k] for k in ("site_count", "distinct_claim_count", "sites_without_a_reported_result")}))


if __name__ == "__main__":
    main()
