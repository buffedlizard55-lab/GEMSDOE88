#!/usr/bin/env python3
"""Audit local Pages links and bind visible status to the current run card.

This is a fail-closed presentation check. It does not turn a format-valid file
into a weekly-slot decision and does not contact DrivenData.
"""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ("href", "src") and value)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root=ROOT):
    root = Path(root)
    card = json.loads((root / "registry/mrrcoh88_run_card.json").read_text())
    web_card = json.loads((root / "docs/data/mrrcoh88_run_card.json").read_text())
    current = json.loads((root / "docs/data/current_release.json").read_text())
    status = json.loads((root / "docs/status.json").read_text())
    evidence = json.loads((root / "evidence/mrrcoh88_final_uniqueness.json").read_text())

    assert card == web_card
    assert card["lane"] == "MRR-COH-88" and card["verdict"] == "negative"
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    assert card["organizer_confirmed"] is None and card["weekly_slots_used"] == 0
    assert len(card["submission_note"]) <= 140
    tif = (root / card["artifact"]).resolve()
    archive = (root / card["zip_artifact"]).resolve()
    downloads = (root / "docs/downloads").resolve()
    assert tif.is_relative_to(downloads) and archive.is_relative_to(downloads)
    assert tif.name.endswith("DO-NOT-SUBMIT.tif")
    assert tif.is_file() and archive.is_file()
    assert digest(tif) == card["raster_sha256"] == current["raster_sha256"]
    assert digest(archive) == card["zip_sha256"] == current["zip_sha256"]
    assert current["artifact"] == card["artifact"]
    assert current["candidate_id"] == "MRR-COH-88"
    assert current["unique"] is True and current["duplicate"] is False
    assert current["format_valid"] is True and current["research_download_ok"] is True
    assert current["ok_to_submit"] is False and current["verdict"] == "negative"
    assert current["holdout_dti"] < current["incumbent_best_dti"]
    assert evidence["candidate_sha256"] == card["raster_sha256"] and evidence["unique"] is True
    assert status["status"] == "BLOCKED" and status["ok_to_submit"] is False
    assert status["raster_sha256"] == card["raster_sha256"]

    # A non-DO-NOT-SUBMIT download may only be linked if one machine gate record
    # explicitly clears that exact filename. The current negative is never added.
    cleared_names = set()
    for record in sorted((root / "registry").glob("*gate*.json")):
        try:
            data = json.loads(record.read_text())
        except (ValueError, OSError):
            continue
        candidate = data.get("candidate") or {}
        name = Path(candidate.get("tif", "")).name
        if data.get("ok_to_submit") is True and name:
            cleared_names.update({name, name[:-4] + ".zip"})

    pages = [root / "index.html", *sorted((root / "docs").glob("*.html"))]
    assert len(pages) >= 5
    for page in pages:
        text = page.read_text(encoding="utf-8")
        if page.parent == root / "docs":
            upper = text.upper()
            assert "DO NOT SUBMIT" in upper, f"missing safety status: {page.name}"
            assert "OK TO SUBMIT: YES" not in upper, f"contradictory submit clearance: {page.name}"
            assert "SAFE TO SUBMIT: YES" not in upper, f"contradictory safety claim: {page.name}"
            assert "EXECUTIVE-SUMMARY.HTML" in upper, f"missing guide nav: {page.name}"
        parser = Links()
        parser.feed(text)
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = (page.parent / unquote(parsed.path)).resolve()
            assert path.is_relative_to(root), f"escaping link: {page.name}: {link}"
            assert path.is_file(), f"broken link: {page.name}: {link}"
            if path.suffix.lower() in (".tif", ".tiff", ".zip"):
                assert path.is_relative_to(downloads), link
                if "DO-NOT-SUBMIT" not in path.name:
                    assert path.name in cleared_names, f"unmarked research download: {link}"

    for page_name in ("index.html", "executive-summary.html"):
        text = (root / "docs" / page_name).read_text(encoding="utf-8")
        upper = text.upper()
        assert tif.name in text
        assert "DOWNLOAD FOR RESEARCH: YES" in upper
        assert "OK TO SUBMIT: NO" in upper or "DO NOT SUBMIT" in upper
        assert card["submission_name"] in text and card["submission_note"] in text
        assert "MAG-PSG" not in text and "KTH-88" not in text
    print("PASS: current MRR-COH bytes, evidence, site links, and negative decision agree")


if __name__ == "__main__":
    main()
