import hashlib
import json
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if "id" in a:
            self.ids.add(a["id"])
        if tag in ("script", "link"):
            u = a.get("src") if tag == "script" else a.get("href")
            if u:
                self.scripts.append(u)


def test_pages_have_local_links_assets_and_clear_status():
    docs = ROOT / "docs"
    pages = {p.name: p for p in docs.glob("*.html")}
    assert set(pages) == {
        "index.html",
        "executive-summary.html",
        "research.html",
        "sources.html",
    }
    all_pages = sorted(docs.rglob("*.html"))
    assert set(all_pages) >= set(pages.values())
    for page in all_pages:
        text = page.read_text()
        assert "DO NOT SUBMIT" in text and "executive-summary.html" in text
        html = HTMLLinks()
        html.feed(text)
        for href in [*html.links, *html.scripts]:
            u = urlsplit(href)
            if u.scheme or u.netloc:
                continue
            target = page.parent / unquote(u.path) if u.path else page
            assert target.is_file(), (page, href)
            if u.fragment and target.suffix == ".html":
                linked = HTMLLinks()
                linked.feed(target.read_text())
                assert u.fragment in linked.ids, (page, href)
    assert (
        docs / "downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif"
    ).is_file()


def test_current_pages_bind_to_negative_current_release():
    docs = ROOT / "docs"
    current = json.loads((docs / "data/current_release.json").read_text())
    assert current["candidate_id"] == "KTH-88"
    assert current["release_date_utc"] == "2026-10-24"
    assert current["decision_label"] == "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT"
    assert current["ok_to_download"] is True and current["ok_to_submit"] is False
    assert current["organizer_confirmed"] is None and current["duplicate"] is True
    for name in ("index.html", "executive-summary.html"):
        text = (docs / name).read_text()
        upper = text.upper()
        assert "OK TO SUBMIT: NO" in upper
        assert "DO NOT SUBMIT" in upper
        assert "OK TO SUBMIT: YES" not in upper
        assert current["file"].split("/")[-1] in text
        assert "HOLDOUT-DTI" in upper


def test_mdc88_literal_reassessment_withdraws_public_download_and_retires_publisher():
    docs = ROOT / "docs"
    status = json.loads((docs / "mdc88/status.json").read_text())
    canonical = json.loads((ROOT / "registry/kdmc_gate_literal_reassessment.json").read_text())
    assert status == canonical
    assert status["ok_to_download_for_research"] is True
    assert status["public_pages_offer_download"] is False
    assert status["ok_to_submit"] is False
    assert status["organizer_confirmed"] is None
    assert status["weekly_slot_selected_or_spent"] is False
    assert status["decision"]["ok_to_download_for_research"] is True
    assert status["decision"]["ok_to_submit"] is False
    literal = status["binding_uniqueness_rule"]
    assert literal["policy"] == "literal-all-rasters; no chance-corrected exemption"
    assert literal["final_dot_overlap_3px"] == 1.0 > literal["overlap_threshold"]
    assert literal["duplicate"] is True
    assert literal["preplacement_surface_screen_documented"] is False

    candidate = status["candidate"]
    tif = ROOT / candidate["raster_archive_path"]
    archive = ROOT / candidate["zip_archive_path"]
    meta = ROOT / candidate["metadata_archive_path"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == candidate["raster_sha256"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == candidate["zip_sha256"]
    assert meta.is_file()
    with zipfile.ZipFile(archive) as zf:
        assert zf.namelist() == [tif.name]
        assert zf.read(tif.name) == tif.read_bytes()
    for suffix in (".tif", ".zip", ".json"):
        assert not (docs / "downloads" / (candidate["name"] + suffix)).exists()

    old_gate = json.loads((ROOT / "registry/kdmc_gate.json").read_text())
    assert old_gate["ok_to_submit"] is True  # historical v3 field is preserved, not current
    assert old_gate["uniqueness_literal"]["duplicate"] is True
    assert old_gate["uniqueness_literal"]["stop_required"] is True
    for name in ("index.html", "executive-summary.html"):
        page = docs / "mdc88" / name
        text = page.read_text()
        upper = text.upper()
        assert "OK TO DOWNLOAD FOR RESEARCH: YES" in upper
        assert "OK TO SUBMIT: NO" in upper and "DO NOT SUBMIT" in upper
        assert "OK TO SUBMIT: YES" not in upper
        html = HTMLLinks()
        html.feed(text)
        assert not any(candidate["name"] in link for link in html.links)

    publisher = ROOT / "scripts/publish_kdmc_site.py"
    result = subprocess.run([sys.executable, str(publisher)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert "retired" in result.stderr.lower() and "refusing to generate" in result.stderr.lower()
    assert not any((docs / "downloads" / (candidate["name"] + suffix)).exists()
                   for suffix in (".tif", ".zip", ".json"))


def test_synthetic_psg_demo_is_quarantined_and_not_a_site_download():
    docs = ROOT / "docs"
    old_public_path = docs / "downloads/gems88-hyp-psg-submission.tif"
    archived = ROOT / "evidence/simulated/mag-psg-synthetic-mock-20261024.tif"
    manifest = json.loads((ROOT / "evidence/simulated/manifest.json").read_text())
    generator = (ROOT / "scripts/build_synthetic_psg_demo.py").read_text()
    assert not old_public_path.exists()
    assert archived.is_file()
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == manifest["sha256"]
    assert manifest["classification"] == "SIMULATED_NOT_SCIENTIFIC_CANDIDATE"
    assert manifest["submission_allowed"] is False
    assert "submission_writer" not in generator and "docs/downloads" not in generator
    for name in ("index.html", "executive-summary.html"):
        html = HTMLLinks()
        html.feed((docs / name).read_text())
        assert not any("gems88-hyp-psg-submission.tif" in link.lower() for link in html.links)
