"""Regression tests for session e8a09926 site-link hardening, CON88 withdrawal, and review mirrors."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import posixpath

from html.parser import HTMLParser


ROOT = Path(__file__).resolve().parents[1]


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        ref = attr_map.get("href") or attr_map.get("src")
        if ref:
            self.refs.append(ref)


def test_con88_package_is_withdrawn_and_marked_do_not_submit() -> None:
    tif = ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif"
    zip_path = ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.zip"
    sidecar_path = ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.json"
    assert tif.is_file()
    assert zip_path.is_file()
    assert sidecar_path.is_file()
    assert not (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.tif").exists()
    assert not (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.zip").exists()
    assert not (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.json").exists()

    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["ok_to_submit"] is False
    assert sidecar["verdict"] == "negative"
    assert sidecar["decision"] == "DUPLICATE_STOP"

    rc = json.loads((ROOT / "run_card_con88.json").read_text(encoding="utf-8"))
    assert rc["ok_to_submit"] is False
    assert rc["verdict"] == "negative"
    assert rc["decision"] == "DUPLICATE_STOP"
    assert rc["organizer_confirmed_score"] is None

    gates = json.loads((ROOT / "registry/con88_gates.json").read_text(encoding="utf-8"))
    assert gates["ok_to_submit"] is False
    assert gates["G2_ok"] is False
    assert gates["verdict"] == "negative"
    assert gates["decision"] == "DUPLICATE_STOP"


def test_docs_con88_html_stays_inside_docs_and_states_do_not_submit() -> None:
    docs = ROOT / "docs"
    con88_html = docs / "con88.html"
    text = con88_html.read_text(encoding="utf-8")
    assert "DO NOT SUBMIT" in text
    assert "OK TO DOWNLOAD AND SUBMIT" not in text
    assert "executive-summary.html" in text
    parser = _HrefParser()
    parser.feed(text)
    for ref in parser.refs:
        url = urlsplit(ref)
        if url.scheme or url.netloc or not url.path:
            continue
        norm_ref = posixpath.normpath(unquote(url.path))
        assert not norm_ref.startswith("../") and norm_ref != "..", ref
        assert (docs / norm_ref).is_file(), ref


def test_session_e8a09926_run_card_and_review_mirrors_match() -> None:
    rc_reg = ROOT / "registry/session_e8a09926_run_card.json"
    rc_docs = ROOT / "docs/data/session_e8a09926_run_card.json"
    rc_ev = ROOT / "evidence/session_e8a09926_run_card.json"
    assert rc_reg.read_bytes() == rc_docs.read_bytes() == rc_ev.read_bytes()
    rc = json.loads(rc_reg.read_text(encoding="utf-8"))
    assert rc["verdict"] == "negative"
    assert rc["ok_to_submit"] is False
    assert rc["decision"] == "DUPLICATE_STOP"
    assert rc["new_rasters_generated"] == 0
    assert rc["experiments_run"] == 0
    assert len(rc["ranked_untried_hypotheses"]) == 5

    rev_root = ROOT / "research/session-e8a09926-review.md"
    rev_docs = ROOT / "docs/research/session-e8a09926-review.md"
    assert rev_root.read_bytes() == rev_docs.read_bytes()
