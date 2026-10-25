#!/usr/bin/env python3
"""Fresh, fail-closed submission review; never train, emit or submit a raster.

Exit 0 = completed research audit only; --require-submit exits 2 when blocked.
Exit 1 = audit error. Outputs replace stale approvals even after input failure.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_protocol_integrity import review  # noqa: E402

OUTPUTS = ("evidence/submission_review_latest.json", "docs/data/submission_review_latest.json")


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    root = Path(root)
    try:
        card = review(root)
        # A stop is the result of this audit, not an invitation to tune around it.
        if card.get("decision") != "DUPLICATE_STOP" or card.get("ok_to_submit") is not False:
            raise ValueError("Blocker changed: independent protocol review required")
        card.update(schema="gems88.submission-review.v1", date_utc=datetime.now(timezone.utc).date().isoformat(),
                    lane="protocol-integrity-only", new_rasters_generated=0,
                    fresh_geological_hypotheses_tested=0)
        card["submission_note"] = "Existing MDPS88 research artifact re-audited; literal registry duplicate; no new model; DO NOT SUBMIT"
        card["freshness"] = {"format_and_literal_overlap": "REMEASURED_FROM_PINNED_BYTES",
                             "holdout": "HISTORICAL_NOT_RERUN",
                             "leaderboard_and_receipts": "NOT_VERIFIED"}
        card["unmet_requirement"] = "No new protocol-unique competition TIFF: literal registry saturation forbids every nonempty allowed dot set."
    except Exception as exc:  # CLI boundary must invalidate stale readiness
        card = {"schema": "gems88.submission-review.v1", "date_utc": datetime.now(timezone.utc).date().isoformat(),
                "decision": "AUDIT_ERROR", "error": str(exc), "verdict": "negative",
                "ok_to_submit": False, "approved_for_weekly_slot": False,
                "ok_to_download_for_research": False}
    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    for relative in OUTPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    print(text, end="")
    return 1 if card["decision"] == "AUDIT_ERROR" else (2 if args.require_submit else 0)


if __name__ == "__main__":
    raise SystemExit(main())
