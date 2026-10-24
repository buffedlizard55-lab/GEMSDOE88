"""The published pages are generated from the gate report and must agree with it (IR-88-59)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _gate():
    return json.loads((ROOT / "docs" / "data" / "submission_gate.json").read_text())


def test_rendering_is_idempotent_and_committed(tmp_path):
    import render_site
    before = {p: (ROOT / p).read_text() for p in ("index.html", "docs/index.html", "docs/executive-summary.html", "docs/research.html", "docs/sources.html", "README.md")}
    try:
        render_site.render_root(); render_site.render_index(); render_site.render_exec(); render_site.render_strips(); render_site.render_readme()
        after = {p: (ROOT / p).read_text() for p in before}
    finally:
        for p, t in before.items():
            (ROOT / p).write_text(t)
    assert before == after, "pages are stale: run python scripts/render_site.py"


def test_every_page_shows_the_gate_verdict_and_one_submit_file():
    g = _gate()
    c = g["candidate"]
    for rel in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        t = (ROOT / rel).read_text()
        assert f'data-gate-verdict="{g["verdict"]}"' in t
    for rel in ("docs/index.html", "docs/executive-summary.html"):
        t = (ROOT / rel).read_text()
        assert c["file_name"] in t and c["sha256"] in t
        assert "Note" in t and str(c["note_chars"]) + "/140" in t
        # exactly one non-archived tif is offered for download on each page
        tifs = set(re.findall(r'href="downloads/([^"]+\.tif)"', t))
        assert {x for x in tifs if "DO-NOT-SUBMIT" not in x} <= {c["file_name"]}


def test_exec_summary_has_no_contradictory_verdict_text():
    t = (ROOT / "docs" / "executive-summary.html").read_text()
    assert "OK to Submit Automatically" not in t
    assert "NO — DO NOT SUBMIT" not in t


def test_site_js_reads_the_unified_gate_and_the_real_leaderboard_keys():
    js = (ROOT / "docs" / "assets" / "site.js").read_text()
    assert "data/submission_gate.json" in js
    assert "data/run-card.json" not in js
    lb = json.loads((ROOT / "docs" / "data" / "leaderboard.json").read_text())
    assert ("observed_top10" in lb and "retrieved_at_utc" in lb)
    assert lb["observed_top10"][0]["rank"] == 1 and 0 < lb["observed_top10"][0]["public_dti"] <= 1
    assert lb["rows"][0]["public_dti"] == lb["observed_top10"][0]["public_dti"]


def test_check_site_passes():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_site.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
