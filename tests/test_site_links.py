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
    for page in pages.values():
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
