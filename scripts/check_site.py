#!/usr/bin/env python3
"""Fail-closed integrity guard for the GitHub Pages decision surface."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import zipfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MVRD_NAME = "gems88-mvrd-monoclinal-redox-strand-20261024-v1-DO-NOT-SUBMIT"


def require(condition: bool, message: object) -> None:
    """Enforce a release check even when Python optimization is enabled."""
    if not condition:
        raise ValueError(str(message))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("href", "src"):
            if key in values:
                self.refs.append(values[key])


def main(root: Path = ROOT) -> None:
    root = Path(root)
    docs = root / "docs"
    pages = [
        docs / name
        for name in (
            "index.html",
            "executive-summary.html",
            "research.html",
            "sources.html",
        )
    ]
    card = json.loads((root / "registry/mvrd_run_card.json").read_text())
    web_card = json.loads((docs / "data/mvrd_run_card.json").read_text())
    gate = json.loads((root / "registry/mvrd_gate_v3.json").read_text())
    web_gate = json.loads((docs / "data/mvrd-gate-v3.json").read_text())
    current = json.loads((docs / "data/current_release.json").read_text())
    status = json.loads((docs / "status.json").read_text())
    audit = json.loads(
        (docs / "downloads" / f"{MVRD_NAME}.format-audit.json").read_text()
    )
    literal = json.loads((docs / "data/literal_protocol_audit.json").read_text())
    ibl = json.loads((root / "registry/ibl88_run_card.json").read_text())
    ibl_web = json.loads((docs / "data/ibl88_run_card.json").read_text())
    qts = json.loads((root / "registry/qts88_run_card.json").read_text())
    qts_web = json.loads((docs / "data/qts88_run_card.json").read_text())
    qts_gate = json.loads((root / "registry/qts88_gate.json").read_text())
    tdkl = json.loads((root / "registry/tdkl88_run_card.json").read_text())
    tdkl_web = json.loads((docs / "data/tdkl88_run_card.json").read_text())
    require(tdkl == tdkl_web, "Pages TDKL card differs from canonical registry card")
    require(
        tdkl["verdict"] == "negative"
        and tdkl["ok_to_download"] is True
        and tdkl["ok_to_submit"] is False,
        'Site integrity check failed: tdkl["verdict"] == "negative" and tdkl["ok_to_download"] is True and tdkl["ok_to_submit"] is False',
    )
    require(
        0 < len(tdkl["submission_name"]) <= 140
        and 0 < len(tdkl["submission_note"]) <= 140,
        'Site integrity check failed: 0 < len(tdkl["submission_name"]) <= 140 and 0 < len(tdkl["submission_note"]) <= 140',
    )
    require(
        tdkl["verdict_summary"].startswith("NEGATIVE"),
        "TDKL summary contradicts negative verdict",
    )
    tdkl_tif = root / tdkl["raster"]["file"]
    tdkl_zip = root / tdkl["raster"]["zip_file"]
    require(
        sha256(tdkl_tif) == tdkl["raster_sha256"],
        'Site integrity check failed: sha256(tdkl_tif) == tdkl["raster_sha256"]',
    )
    require(
        sha256(tdkl_zip) == tdkl["raster"]["zip_sha256"],
        'Site integrity check failed: sha256(tdkl_zip) == tdkl["raster"]["zip_sha256"]',
    )

    require(
        literal["decision"] == "DUPLICATE_STOP",
        'Site integrity check failed: literal["decision"] == "DUPLICATE_STOP"',
    )
    require(
        literal["saturation_certificate"]["universal_overlap_blocker"] is True,
        'Site integrity check failed: literal["saturation_certificate"]["universal_overlap_blocker"] is True',
    )
    require(
        literal["saturation_certificate"]["uncovered_allowed_pixels"] == 0,
        'Site integrity check failed: literal["saturation_certificate"]["uncovered_allowed_pixels"] == 0',
    )
    require(
        literal["correlation_overlap_vs_registry"]["literal_duplicate"] is True,
        'Site integrity check failed: literal["correlation_overlap_vs_registry"]["literal_duplicate"] is True',
    )
    require(
        literal["correlation_overlap_vs_registry"][
            "final_literal_overlap_3px_remeasured"
        ]
        == 1.0,
        'Site integrity check failed: literal["correlation_overlap_vs_registry"]["final_literal_overlap_3px_remeasured"] == 1.0',
    )
    require(
        literal["ok_to_submit"] is False,
        'Site integrity check failed: literal["ok_to_submit"] is False',
    )
    require(ibl == ibl_web, "Pages IBL card differs from canonical registry card")
    require(
        ibl["verdict"] == "negative"
        and ibl["ok_to_download"] is True
        and ibl["ok_to_submit"] is False,
        'Site integrity check failed: ibl["verdict"] == "negative" and ibl["ok_to_download"] is True and ibl["ok_to_submit"] is False',
    )
    require(
        ibl["uniqueness"]["literal_worst_forward_overlap_3px"] == 1.0,
        'Site integrity check failed: ibl["uniqueness"]["literal_worst_forward_overlap_3px"] == 1.0',
    )
    require(
        ibl["uniqueness"]["unique"] is False
        and ibl["uniqueness"]["stop_required"] is True,
        'Site integrity check failed: ibl["uniqueness"]["unique"] is False and ibl["uniqueness"]["stop_required"] is True',
    )
    ibl_tif = root / ibl["submission"]["file"]
    ibl_zip = root / ibl["submission"]["zip_file"]
    require(
        sha256(ibl_tif) == ibl["submission"]["sha256"],
        'Site integrity check failed: sha256(ibl_tif) == ibl["submission"]["sha256"]',
    )
    require(
        sha256(ibl_zip) == ibl["submission"]["zip_sha256"],
        'Site integrity check failed: sha256(ibl_zip) == ibl["submission"]["zip_sha256"]',
    )
    require(qts == qts_web, "Pages QTS card differs from canonical registry card")
    require(
        qts_gate == json.loads((docs / "data/qts88_validation.json").read_text()),
        'Site integrity check failed: qts_gate == json.loads((docs / "data/qts88_validation.json").read_text())',
    )
    require(
        qts["verdict"] == "negative"
        and qts["ok_to_download"] is True
        and qts["ok_to_submit"] is False,
        'Site integrity check failed: qts["verdict"] == "negative" and qts["ok_to_download"] is True and qts["ok_to_submit"] is False',
    )
    qts_tif = root / qts["file"]
    qts_zip = root / qts["zip_file"]
    require(
        sha256(qts_tif) == qts["raster_sha256"],
        'Site integrity check failed: sha256(qts_tif) == qts["raster_sha256"]',
    )
    require(
        sha256(qts_zip) == qts["zip_sha256"],
        'Site integrity check failed: sha256(qts_zip) == qts["zip_sha256"]',
    )
    gthc = json.loads((root / "registry/gthc88_run_card.json").read_text())
    gthc_web = json.loads((docs / "data/gthc88_run_card.json").read_text())
    gthc_val = json.loads((docs / "data/gthc88_validation.json").read_text())
    require(gthc == gthc_web, "Pages GTHC card differs from canonical registry card")
    require(
        gthc["verdict"] == "negative"
        and gthc["ok_to_download"] is True
        and gthc["ok_to_submit"] is False,
        'Site integrity check failed: gthc["verdict"] == "negative" and gthc["ok_to_download"] is True and gthc["ok_to_submit"] is False',
    )
    gthc_tif = root / gthc["download"]
    gthc_zip = root / gthc["zip_download"]
    require(
        sha256(gthc_tif) == gthc["raster_sha256"] == gthc_val["tif_sha256"],
        'Site integrity check failed: sha256(gthc_tif) == gthc["raster_sha256"] == gthc_val["tif_sha256"]',
    )
    require(
        sha256(gthc_zip) == gthc["zip_sha256"] == gthc_val["zip_sha256"],
        'Site integrity check failed: sha256(gthc_zip) == gthc["zip_sha256"] == gthc_val["zip_sha256"]',
    )
    qtsk = json.loads((root / "registry/qtsk88_run_card.json").read_text())
    qtsk_web = json.loads((docs / "data/qtsk88_run_card.json").read_text())
    require(qtsk == qtsk_web, "Pages QTSK card differs from canonical registry card")
    require(
        qtsk["verdict"] == "negative"
        and qtsk["ok_to_download"] is True
        and qtsk["ok_to_submit"] is False,
        'Site integrity check failed: qtsk["verdict"] == "negative" and qtsk["ok_to_download"] is True and qtsk["ok_to_submit"] is False',
    )
    require(
        0 < len(qtsk["submission_name"]) <= 140
        and 0 < len(qtsk["submission_note"]) <= 140,
        'Site integrity check failed: 0 < len(qtsk["submission_name"]) <= 140 and 0 < len(qtsk["submission_note"]) <= 140',
    )
    qtsk_tif = root / qtsk["raster"]["tif_path"]
    qtsk_zip = root / qtsk["raster"]["zip_path"]
    require(
        sha256(qtsk_tif) == qtsk["raster"]["sha256"],
        'Site integrity check failed: sha256(qtsk_tif) == qtsk["raster"]["sha256"]',
    )
    require(
        sha256(qtsk_zip) == qtsk["raster"]["zip_sha256"],
        'Site integrity check failed: sha256(qtsk_zip) == qtsk["raster"]["zip_sha256"]',
    )

    require(card == web_card, "Pages MVRD card differs from canonical registry card")
    require(gate == web_gate, "Pages MVRD gate differs from canonical registry gate")
    require(
        card["submission_name"] == MVRD_NAME and card["verdict"] == "negative",
        'Site integrity check failed: card["submission_name"] == MVRD_NAME and card["verdict"] == "negative"',
    )
    require(
        card["ok_to_download"] is True and card["ok_to_submit"] is False,
        'Site integrity check failed: card["ok_to_download"] is True and card["ok_to_submit"] is False',
    )
    require(
        gate["ok_to_download"] is True and gate["ok_to_submit"] is False,
        'Site integrity check failed: gate["ok_to_download"] is True and gate["ok_to_submit"] is False',
    )
    require(
        gate["fingerprint_screen_pass"] is False,
        'Site integrity check failed: gate["fingerprint_screen_pass"] is False',
    )
    require(
        gate["holdout_cross_run"]["evidence_class"] == "HOLDOUT-DTI",
        'Site integrity check failed: gate["holdout_cross_run"]["evidence_class"] == "HOLDOUT-DTI"',
    )
    require(
        gate["holdout_cross_run"]["evaluator_version"] == "gems57-pooled-hide-v2",
        'Site integrity check failed: gate["holdout_cross_run"]["evaluator_version"] == "gems57-pooled-hide-v2"',
    )
    require(
        gate["holdout_cross_run"]["withheld_positives"] == 22_893,
        'Site integrity check failed: gate["holdout_cross_run"]["withheld_positives"] == 22_893',
    )
    require(
        gate["uniqueness"]["unique_like_for_like"] is True,
        'Site integrity check failed: gate["uniqueness"]["unique_like_for_like"] is True',
    )
    require(
        card["correlation_overlap_vs_registry"][
            "literal_all_positive_witness_overlap_3px"
        ]
        == 1.0,
        'Site integrity check failed: card["correlation_overlap_vs_registry"]["literal_all_positive_witness_overlap_3px"] == 1.0',
    )
    require(
        len(card["submission_name"]) <= 140,
        'Site integrity check failed: len(card["submission_name"]) <= 140',
    )
    require(
        len(card["submission_note"]) == card["submission_note_length"] <= 140,
        'Site integrity check failed: len(card["submission_note"]) == card["submission_note_length"] <= 140',
    )

    tif = root / card["artifact"]
    zipped = root / card["zip_artifact"]
    require(
        tif.is_file() and zipped.is_file(),
        "Site integrity check failed: tif.is_file() and zipped.is_file()",
    )
    require(
        sha256(tif)
        == card["raster_sha256"]
        == gate["sha256"]
        == audit["portal_tif"]["sha256"],
        'Site integrity check failed: sha256(tif) == card["raster_sha256"] == gate["sha256"] == audit["portal_tif"]["sha256"]',
    )
    require(
        sha256(zipped) == card["zip_sha256"] == gate["zip_sha256"],
        'Site integrity check failed: sha256(zipped) == card["zip_sha256"] == gate["zip_sha256"]',
    )
    with zipfile.ZipFile(zipped) as archive:
        require(
            archive.namelist() == [tif.name],
            "Site integrity check failed: archive.namelist() == [tif.name]",
        )
        require(
            archive.read(tif.name) == tif.read_bytes(),
            "Site integrity check failed: archive.read(tif.name) == tif.read_bytes()",
        )
    require(
        audit["portal_tif"]["ok"] is True and audit["portal_zip"]["ok"] is True,
        'Site integrity check failed: audit["portal_tif"]["ok"] is True and audit["portal_zip"]["ok"] is True',
    )
    require(
        audit["portal_tif"]["layout_parity_with_sample"] is True,
        'Site integrity check failed: audit["portal_tif"]["layout_parity_with_sample"] is True',
    )
    require(
        audit["shared_validate"]["all_checks_passed"] is True,
        'Site integrity check failed: audit["shared_validate"]["all_checks_passed"] is True',
    )
    require(
        all(audit["shared_validate"]["checks"].values()),
        'Site integrity check failed: all(audit["shared_validate"]["checks"].values())',
    )
    require(
        audit["shared_gates_format_report"]["ok"] is True,
        'Site integrity check failed: audit["shared_gates_format_report"]["ok"] is True',
    )

    require(
        current["candidate"] == "H88-MVRD",
        'Site integrity check failed: current["candidate"] == "H88-MVRD"',
    )
    require(
        current["file"] == card["artifact"],
        'Site integrity check failed: current["file"] == card["artifact"]',
    )
    require(
        current["file_sha256"] == card["raster_sha256"],
        'Site integrity check failed: current["file_sha256"] == card["raster_sha256"]',
    )
    require(
        current["ok_to_download"] is True and current["ok_to_submit"] is False,
        'Site integrity check failed: current["ok_to_download"] is True and current["ok_to_submit"] is False',
    )
    require(
        current["literal_duplicate"] is True
        and current["distance_fingerprint_ok"] is False,
        'Site integrity check failed: current["literal_duplicate"] is True and current["distance_fingerprint_ok"] is False',
    )
    require(
        status["status"] == "BLOCKED",
        'Site integrity check failed: status["status"] == "BLOCKED"',
    )
    require(
        status["raster_sha256"] == card["raster_sha256"],
        'Site integrity check failed: status["raster_sha256"] == card["raster_sha256"]',
    )
    require(
        status["ok_to_download_for_research"] is True
        and status["ok_to_submit"] is False,
        'Site integrity check failed: status["ok_to_download_for_research"] is True and status["ok_to_submit"] is False',
    )

    for page in pages:
        text = page.read_text()
        require("DO NOT SUBMIT" in text, page)
        require("executive-summary.html" in text, page)
        require("OK TO SUBMIT: YES" not in text, page)
        parser = Links()
        parser.feed(text)
        for ref in parser.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc or not url.path:
                continue
            target = page.parent / unquote(url.path)
            require(target.is_file(), f"broken local link: {page.name}: {ref}")

    # Every published binary under docs/ must carry its negative decision in the
    # filename. This includes unlinked research variants, not only downloads/.
    for published in sorted(docs.rglob("*")):
        if published.is_file() and published.suffix.lower() in {
            ".tif",
            ".tiff",
            ".zip",
        }:
            require(
                "DO-NOT-SUBMIT" in published.name,
                f"unmarked published research artifact: {published}",
            )

    index = pages[0].read_text()
    executive = pages[1].read_text()
    research = pages[2].read_text()
    require(
        MVRD_NAME in index and MVRD_NAME in executive,
        "Site integrity check failed: MVRD_NAME in index and MVRD_NAME in executive",
    )
    require(
        tdkl_tif.name in index and tdkl_tif.name in executive,
        "Site integrity check failed: tdkl_tif.name in index and tdkl_tif.name in executive",
    )
    require(
        tdkl["submission_name"] in index and tdkl["submission_name"] in executive,
        'Site integrity check failed: tdkl["submission_name"] in index and tdkl["submission_name"] in executive',
    )
    require(
        tdkl["raster_sha256"][:16] in index and tdkl["raster_sha256"][:16] in executive,
        'Site integrity check failed: tdkl["raster_sha256"][:16] in index and tdkl["raster_sha256"][:16] in executive',
    )
    require(
        ibl_tif.name in index and ibl_tif.name in executive,
        "Site integrity check failed: ibl_tif.name in index and ibl_tif.name in executive",
    )
    require(
        qts_tif.name in index and qts_tif.name in executive,
        "Site integrity check failed: qts_tif.name in index and qts_tif.name in executive",
    )
    require(
        qts["submission_name"] in index and qts["submission_name"] in executive,
        'Site integrity check failed: qts["submission_name"] in index and qts["submission_name"] in executive',
    )
    require(
        gthc_tif.name in index and gthc_tif.name in executive,
        "Site integrity check failed: gthc_tif.name in index and gthc_tif.name in executive",
    )
    require(
        gthc["submission_name"] in index and gthc["submission_name"] in executive,
        'Site integrity check failed: gthc["submission_name"] in index and gthc["submission_name"] in executive',
    )
    require(
        qtsk_tif.name in index and qtsk_tif.name in executive,
        "Site integrity check failed: qtsk_tif.name in index and qtsk_tif.name in executive",
    )
    require(
        qtsk["submission_name"] in index and qtsk["submission_name"] in executive,
        'Site integrity check failed: qtsk["submission_name"] in index and qtsk["submission_name"] in executive',
    )
    require(
        qtsk["raster"]["sha256"][:16] in index
        and qtsk["raster"]["sha256"][:16] in executive,
        'Site integrity check failed: qtsk["raster"]["sha256"][:16] in index and qtsk["raster"]["sha256"][:16] in executive',
    )
    require(
        "literal_protocol_audit.json" in index
        and "literal_protocol_audit.json" in executive,
        'Site integrity check failed: "literal_protocol_audit.json" in index and "literal_protocol_audit.json" in executive',
    )
    require(
        "DOWNLOAD FOR RESEARCH: YES" in index,
        'Site integrity check failed: "DOWNLOAD FOR RESEARCH: YES" in index',
    )
    require("SUBMIT: NO" in index, 'Site integrity check failed: "SUBMIT: NO" in index')
    require(
        card["raster_sha256"] in index and card["raster_sha256"] in executive,
        'Site integrity check failed: card["raster_sha256"] in index and card["raster_sha256"] in executive',
    )
    require(
        "0.197314" in index and "0.197314" in research,
        'Site integrity check failed: "0.197314" in index and "0.197314" in research',
    )
    require(
        "0.2778" in index and "0.2778" in research,
        'Site integrity check failed: "0.2778" in index and "0.2778" in research',
    )
    require(
        "hyp-psg" not in index and "hyp-psg" not in executive,
        'Site integrity check failed: "hyp-psg" not in index and "hyp-psg" not in executive',
    )

    print(
        "PASS: current MVRD/TDKL cards, bytes, hashes, Pages links, status feed, and explicit negative decision agree"
    )


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"SITE GUARD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
