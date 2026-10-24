#!/usr/bin/env python3
"""Fail-closed OFFLINE parser for manually verified official public snapshots.

No scheduled DrivenData requests or scraping: ``update`` requires HTML supplied
explicitly by a human reviewer (or a synthetic test fixture). It validates
ranked rows and atomically writes a dated snapshot compatible with site.js.
It cannot log in, provide a live score or authenticate a GEMSDOE88 submission.
On login/markup failure the previous snapshot remains untouched.
"""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re

URL = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.depth = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "table":
            if self.depth == 0:
                self.table = []
            self.depth += 1
        if self.depth == 1 and tag == "tr":
            self.row = []
        if self.depth == 1 and self.row is not None and tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data):
        if self.depth and not self.skip and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if self.depth == 1 and tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        if self.depth == 1 and tag == "tr" and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        if tag == "table" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.tables.append(self.table)
                self.table = None


def parse_leaderboard(html):
    parsed = Tables()
    parsed.feed(html)
    for table in parsed.tables:
        for header_index, row in enumerate(table):
            idx = next((i for i, v in enumerate(row) if "tversky" in v.lower()), None)
            if idx is None:
                continue
            results = []
            for cells in table[header_index + 1 :]:
                if not cells or not re.search(r"#\s*\d+", cells[0]):
                    continue
                rank = int(re.search(r"#\s*(\d+)", cells[0]).group(1))
                if idx >= len(cells):
                    continue
                candidates = re.findall(r"(?<!\d)0\.\d{4}(?!\d)", cells[idx])
                if len(candidates) != 1:
                    continue
                score = float(candidates[0])
                if not (0 < score <= 1):
                    continue
                participant = cells[idx - 1].strip() if idx > 0 else ""
                results.append(
                    dict(rank=rank, participant=participant, public_dti=score)
                )
            if (
                len(results) >= 3
                and [r["rank"] for r in results[:3]] == [1, 2, 3]
                and all(
                    results[i]["public_dti"] >= results[i + 1]["public_dti"]
                    for i in range(len(results) - 1)
                )
            ):
                return results[:10]
    raise ValueError(
        "no rank-ordered organizer DW-Tversky table; login/markup change? previous snapshot preserved"
    )


def update(path, html=None):
    if html is None:
        raise RuntimeError(
            "Automated drivendata.org fetching/scraping is disabled per "
            "https://www.drivendata.org/termsofuse/ and Agent Brief v2 §4.1. "
            "The human records TOP_PUBLIC manually with date; offline HTML "
            "fixtures may still be passed explicitly for unit tests."
        )
    rows = parse_leaderboard(html)
    snapshot = dict(
        schema='gems88.public-leaderboard-snapshot.v2',
        evidence_class='OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT (not an owner submission receipt)',
        source_url=URL,
        checked_utc=datetime.now(timezone.utc).isoformat(),
        retrieval='Manually supplied and reviewed offline HTML; not a live account feed',
        live=False,
        stale_after_hours=24,
        top_public_dti=rows[0]['public_dti'],
        rows=rows,
        observed_top10=rows,  # compatibility with earlier offline parser tests
        score_not_our_submission=True,
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/data/leaderboard.json'))
    parser.add_argument('--html-file', type=Path, required=True,
                        help='locally supplied reviewed HTML, never fetched by this script')
    parser.add_argument('--source-confirmed', action='store_true',
                        help='reviewer confirms HTML is the official public leaderboard')
    args = parser.parse_args()
    if not args.source_confirmed:
        parser.error('offline HTML must be manually source-confirmed before publishing')
    snap = update(args.output, args.html_file.read_text())
    print('Recorded dated public snapshot (NOT an account receipt):',
          snap['checked_utc'], snap['rows'][0])


if __name__ == "__main__":
    main()
