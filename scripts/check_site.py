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
# Historical XGCE pair renamed by main to carry DO-NOT-SUBMIT; pin exact bytes.
XGCE_TIF = "gems88-xgce-crossgradient-30000dots-20261025-zeros-DO-NOT-SUBMIT.tif"
XGCE_SHA = "199e6f30e2fc68bddae69e21ac5ea04823ec5d3f0b6239d3f32cb136c8a32c4c"
XGCE_ZIP_SHA = "eba566f9f960017f98d9502ee5026b3a48b2b3b59a0d6e320471f2ddd6e0fb5f"


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
    ctra = json.loads((root / "registry/ctra_run_card.json").read_text())
    ctra_web = json.loads((docs / "data/ctra_run_card.json").read_text())
    require(ctra == ctra_web, "Pages CTRA card differs from canonical registry card")
    ctra_tif = docs / "downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.tif"
    ctra_zip = docs / "downloads/gems88-ctra-conductivity-curvature-20261024-zeros-DO-NOT-SUBMIT.zip"
    require(sha256(ctra_tif) == ctra["sha256"], "CTRA TIFF hash differs from negative run card")
    require(sha256(ctra_zip) == ctra["zip_sha256"], "CTRA ZIP hash differs from negative run card")
    audit = json.loads(
        (docs / "downloads" / f"{MVRD_NAME}.format-audit.json").read_text()
    )
    literal = json.loads((docs / "data/literal_protocol_audit.json").read_text())
    mtas = json.loads((root / "registry/mtas88_run_card.json").read_text())
    mtas_web = json.loads((docs / "data/mtas88_run_card.json").read_text())
    mtas_evidence = json.loads((root / "evidence/mtas88_preflight_20261025.json").read_text())
    require(mtas == mtas_web == mtas_evidence, "MTAS mirrored negative run cards disagree")
    proof = mtas["preplacement_registry_proof"]
    require(
        mtas["decision"] == "DUPLICATE_STOP"
        and mtas["verdict"] == "negative"
        and mtas["ok_to_submit"] is False
        and mtas["new_rasters_generated"] == 0
        and mtas["raster_sha256"] is None
        and mtas["holdout"]["dti"] is None
        and mtas["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
        and proof["universal_overlap_blocker"] is True
        and proof["directly_saturated"] is True
        and proof["allowed_pixels"] == 5_106_385
        and proof["uncovered_allowed_pixels"] == 0
        and proof["overlap_limit"] == 0.7
        and proof["witness_sha256"] == literal["saturation_certificate"]["witness_sha256"],
        "MTAS negative stop missing, inconsistent or contradicted by literal audit",
    )
    require(
        mtas["archived_research_download"]["validator_output"]["ok"] is True
        and mtas["archived_research_download"]["ok_to_submit"] is False
        and mtas["archived_research_download"]["sha256"] == current["file_sha256"],
        "MTAS archived format-only download disagrees with canonical current release",
    )
    require(
        len(mtas["submission_note"]) == mtas["submission_note_length"] <= 140,
        "MTAS negative note exceeds 140 characters",
    )
    # A parallel research lane merged into main while this branch was reviewed.
    # Its names now carry DO-NOT-SUBMIT. The exact binary bytes and negative
    # card must still be bound to the literal witness failure.
    xgce = json.loads((root / "registry/xgce88_run_card.json").read_text())
    xgce_web = json.loads((docs / "data/xgce88_run_card.json").read_text())
    xgce_tif = docs / "downloads" / XGCE_TIF
    xgce_zip = xgce_tif.with_suffix(".zip")
    require(
        xgce == xgce_web and xgce["verdict"] == "negative"
        and xgce["ok_to_submit"] is False
        and xgce["uniqueness"]["literal_dense_witness_overlap"] == 1.0
        and xgce["uniqueness"]["literal_dense_witness_pass"] is False
        and sha256(xgce_tif) == XGCE_SHA == xgce["submission"]["raster_sha256"]
        and sha256(xgce_zip) == XGCE_ZIP_SHA == xgce["submission"]["zip_sha256"],
        "Pinned XGCE research pair must remain negative and DO NOT SUBMIT",
    )
    with zipfile.ZipFile(xgce_zip) as archive:
        require(
            archive.namelist() == [xgce_tif.name]
            and archive.read(xgce_tif.name) == xgce_tif.read_bytes(),
            "Inherited XGCE ZIP must contain the exact pinned research TIFF",
        )
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

    sarcsd = json.loads((root / "registry/sarcsd88_run_card.json").read_text())
    sarcsd_web = json.loads((docs / "data/sarcsd88_run_card.json").read_text())
    sarcsd_gv = json.loads((root / "registry/sarcsd88_gate_v3.json").read_text())
    sarcsd_gv_web = json.loads((docs / "data/sarcsd88_gate_v3.json").read_text())
    require(
        sarcsd == sarcsd_web,
        "Pages SAR-CSD card differs from canonical registry card",
    )
    require(
        sarcsd_gv == sarcsd_gv_web,
        "Pages SAR-CSD gate differs from canonical registry gate",
    )
    require(
        sarcsd["verdict"] == "negative"
        and sarcsd["gate_v3_ok_to_download"] is True
        and sarcsd["gate_v3_ok_to_submit"] is False,
        "SAR-CSD run card must enforce negative DO-NOT-SUBMIT verdict",
    )
    require(
        0 < len(sarcsd["submission_name"]) <= 140
        and 0 < len(sarcsd["submission_note"]) <= 140,
        "SAR-CSD submission name/note must satisfy <=140 character portal cap",
    )
    sarcsd_tif = root / sarcsd["download"]
    sarcsd_zip = root / sarcsd["zip_download"]
    require(
        sha256(sarcsd_tif) == sarcsd["raster_sha256"] == sarcsd_gv["sha256"],
        "SAR-CSD TIFF SHA-256 mismatch across file, card, and gate",
    )
    require(
        sha256(sarcsd_zip) == sarcsd["zip_sha256"] == sarcsd_gv["zip_sha256"],
        "SAR-CSD ZIP SHA-256 mismatch across file, card, and gate",
    )

    dhtc = json.loads((root / "registry/dhtc88_run_card.json").read_text())
    dhtc_web = json.loads((docs / "data/dhtc88_run_card.json").read_text())
    require(dhtc == dhtc_web, "Pages DHTC card differs from canonical registry card")
    require(
        dhtc["verdict"] == "negative"
        and dhtc["ok_to_download"] is True
        and dhtc["ok_to_submit"] is False,
        "DHTC run card must enforce negative DO-NOT-SUBMIT verdict",
    )
    require(
        0 < len(dhtc["submission"]["submission_name"]) <= 140
        and 0 < len(dhtc["submission"]["submission_note"]) <= 140,
        "DHTC submission name/note must satisfy <=140 character portal cap",
    )
    dhtc_tif = root / dhtc["submission"]["file"]
    dhtc_zip = root / dhtc["submission"]["zip_file"]
    require(
        sha256(dhtc_tif) == dhtc["raster_sha256"],
        "DHTC TIFF SHA-256 mismatch",
    )
    require(
        sha256(dhtc_zip) == dhtc["zip_sha256"],
        "DHTC ZIP SHA-256 mismatch",
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

    shore = json.loads((root / "registry/shore_hinge_run_card.json").read_text())
    shore_web = json.loads((docs / "data/shore_hinge_run_card.json").read_text())
    require(shore == shore_web, "Pages SHORE-HINGE card differs from canonical registry card")
    require(shore["verdict"] == "negative" and shore["ok_to_download"] is True and shore["ok_to_submit"] is False, "SHORE verdict")
    require(0 < len(shore["submission_name"]) <= 140 and 0 < len(shore["submission_note"]) <= 140, "SHORE name/note")
    shore_tif = root / shore["artifact"]
    shore_zip = root / shore["zip_artifact"]
    require(shore_tif.is_file() and shore_zip.is_file(), "SHORE files exist")
    require(sha256(shore_tif) == shore["validator"]["raster_sha256"] == shore["submission"]["sha256"], "SHORE tif hash")
    require(sha256(shore_zip) == shore["validator"]["zip_sha256"] == shore["submission"]["zip_sha256"], "SHORE zip hash")
    require(shore["holdout_dti"]["evaluator_version"] == "gems57-pooled-hide-v2", "SHORE evaluator")
    require(shore["holdout_dti"]["withheld_positive_pixels"] == 22_893, "SHORE withheld")
    require(shore["uniqueness"]["unique_like_for_like"] is True, "SHORE unique")
    require(shore["validator"]["fingerprint_pass"] is True, "SHORE fingerprint")

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
        current["candidate"] == "H88-TDKL",
        'Site integrity check failed: current["candidate"] == "H88-TDKL"',
    )
    require(
        current["file"] == tdkl["raster"]["file"],
        'Site integrity check failed: current file differs from TDKL run card',
    )
    require(
        current["file_sha256"] == tdkl["raster_sha256"],
        'Site integrity check failed: current hash differs from TDKL run card',
    )
    require(
        current["ok_to_download"] is True and current["ok_to_submit"] is False,
        'Site integrity check failed: current TDKL decision is not download-yes/submit-no',
    )
    require(
        current["literal_duplicate"] is True and current["duplicate"] is True,
        'Site integrity check failed: current TDKL literal duplicate stop is missing',
    )
    require(
        status["status"] == "BLOCKED",
        'Site integrity check failed: status["status"] == "BLOCKED"',
    )
    require(
        status["raster_sha256"] == tdkl["raster_sha256"]
        and status["run_card"] == "registry/tdkl88_run_card.json",
        'Site integrity check failed: status does not bind canonical TDKL bytes/card',
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

    # Every published binary must carry the negative decision in its filename.
    # Pre-existing CTRA is allowed ONLY for the exact hash-pinned negative bytes
    # checked above; XGCE was renamed on main and requires no such exception.
    legacy_negative = {ctra_tif.resolve(), ctra_zip.resolve()}
    for published in sorted(docs.rglob("*")):
        if published.is_file() and published.suffix.lower() in {
            ".tif", ".tiff", ".zip",
        }:
            require(
                "DO-NOT-SUBMIT" in published.name or published.resolve() in legacy_negative,
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
        sarcsd_tif.name in index and sarcsd_tif.name in executive,
        "Site integrity check failed: sarcsd_tif.name in index and sarcsd_tif.name in executive",
    )
    require(
        sarcsd["submission_name"] in index and sarcsd["submission_name"] in executive,
        'Site integrity check failed: sarcsd["submission_name"] in index and sarcsd["submission_name"] in executive',
    )
    require(
        sarcsd["raster_sha256"][:16] in index and sarcsd["raster_sha256"][:16] in executive,
        'Site integrity check failed: sarcsd["raster_sha256"][:16] in index and sarcsd["raster_sha256"][:16] in executive',
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
        "Current review · 2026-10-25" in index
        and "NO FILE APPROVED" in index
        and "every nonempty dot set fails the literal overlap limit" in index,
        "Overview must present the current fail-closed decision before archived candidates",
    )
    require(
        "genuinely unique" not in index.lower()
        and "not unique under the binding all-registry rule" in index,
        "Overview must not overstate sparse-screen uniqueness as global uniqueness",
    )
    require(
        card["raster_sha256"] in index,
        'Site integrity check failed: archived MVRD hash missing from overview',
    )
    require(
        tdkl["raster_sha256"] in index and tdkl["raster_sha256"] in executive,
        'Site integrity check failed: canonical TDKL hash missing from overview/guide',
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

    require(shore_tif.name in index and shore_tif.name in executive, "SHORE tif in pages")
    require(shore["submission_name"] in index and shore["submission_name"] in executive, "SHORE name in pages")
    require(shore["validator"]["raster_sha256"][:16] in index and shore["validator"]["raster_sha256"][:16] in executive, "SHORE hash in pages")

    require(dhtc_tif.name in index and dhtc_tif.name in executive, "DHTC tif in pages")
    require(dhtc["submission"]["submission_name"] in index and dhtc["submission"]["submission_name"] in executive, "DHTC name in pages")
    require(dhtc["raster_sha256"][:16] in index and dhtc["raster_sha256"][:16] in executive, "DHTC hash in pages")
    for page_text in (index, executive):
        require(
            page_text.index('id="mtas-review"') < page_text.index('class="archive-lanes"')
            and 'NO NEW TIFF: DUPLICATE — STOP' in page_text
            and 'data/mtas88_run_card.json' in page_text
            and mtas["archived_research_download"]["sha256"] in page_text,
            "Pages must lead with the MTAS no-new-file stop and a marked historical download",
        )
    js = (docs / "assets/site.js").read_text()
    require(
        "fetch('data/mtas88_run_card.json'" in js
        and "fetch('data/gzzc88_run_card.json'" in js
        and "PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT" in js,
        "Dynamic decision banner must fail closed on absent MTAS/GZZC proof",
    )

    gzzc_card = json.loads((root / "registry/gzzc88_run_card.json").read_text())
    gzzc_web = json.loads((docs / "data/gzzc88_run_card.json").read_text())
    require(gzzc_card == gzzc_web, "Pages GZZC card differs from canonical registry card")
    require(
        gzzc_card["verdict"] == "negative"
        and gzzc_card["ok_to_download"] is True
        and gzzc_card["ok_to_submit"] is False
        and gzzc_card["uniqueness"]["literal_dense_witness_overlap"] == 1.0
        and gzzc_card["uniqueness"]["literal_dense_witness_pass"] is False
        and gzzc_card["uniqueness"]["unique_like_for_like"] is True,
        "GZZC run card verdict/gate flags inconsistent",
    )
    require(
        0 < len(gzzc_card["submission_name"]) <= 140
        and 0 < len(gzzc_card["submission_note"]) <= 140,
        "GZZC submission name/note must satisfy <=140 character cap",
    )
    gzzc_tif = root / gzzc_card["download"]
    gzzc_zip = root / gzzc_card["zip_download"]
    require(gzzc_tif.is_file() and gzzc_zip.is_file(), "GZZC tif/zip files exist")
    require(
        sha256(gzzc_tif) == gzzc_card["raster_sha256"],
        "GZZC TIFF SHA-256 mismatch across file and card",
    )
    require(
        sha256(gzzc_zip) == gzzc_card["zip_sha256"],
        "GZZC ZIP SHA-256 mismatch across file and card",
    )
    require(gzzc_tif.name in index and gzzc_tif.name in executive, "GZZC tif in pages")
    require(
        gzzc_card["submission_name"] in index and gzzc_card["submission_name"] in executive,
        "GZZC name in pages",
    )
    require(
        gzzc_card["raster_sha256"] in index and gzzc_card["raster_sha256"] in executive,
        "GZZC SHA-256 in pages",
    )
    with zipfile.ZipFile(gzzc_zip) as archive:
        require(
            archive.namelist() == [gzzc_tif.name]
            and archive.read(gzzc_tif.name) == gzzc_tif.read_bytes(),
            "GZZC ZIP must contain the exact research TIFF",
        )

    hgvc_card = json.loads((root / "registry/hgvc88_run_card.json").read_text())
    hgvc_web = json.loads((docs / "data/hgvc88_run_card.json").read_text())
    hgvc_gv = json.loads((root / "registry/hgvc88_gate_v3.json").read_text())
    hgvc_gv_web = json.loads((docs / "data/hgvc88_gate_v3.json").read_text())
    require(hgvc_card == hgvc_web, "Pages HGVC card differs from canonical registry card")
    require(hgvc_gv == hgvc_gv_web, "Pages HGVC gate v3 differs from canonical registry gate")
    require(
        hgvc_card["verdict"] == "negative"
        and hgvc_card["ok_to_download"] is True
        and hgvc_card["ok_to_submit"] is False
        and hgvc_card["all_5_discriminating_gates_pass"] is True,
        "HGVC run card verdict/gate flags inconsistent",
    )
    require(
        0 < len(hgvc_card["submission_name"]) <= 140
        and 0 < len(hgvc_card["submission_note"]) <= 140,
        "HGVC submission name/note must satisfy <=140 character cap",
    )
    hgvc_tif = root / hgvc_card["download"]
    hgvc_zip = root / hgvc_card["zip_download"]
    require(hgvc_tif.is_file() and hgvc_zip.is_file(), "HGVC tif/zip files exist")
    require(
        sha256(hgvc_tif) == hgvc_card["raster_sha256"] == hgvc_gv["sha256"],
        "HGVC TIFF SHA-256 mismatch across file, card, and gate",
    )
    require(
        sha256(hgvc_zip) == hgvc_card["zip_sha256"] == hgvc_gv["zip_sha256"],
        "HGVC ZIP SHA-256 mismatch across file, card, and gate",
    )
    require(hgvc_tif.name in index and hgvc_tif.name in executive, "HGVC tif in pages")
    require(
        hgvc_card["submission_name"] in index and hgvc_card["submission_name"] in executive,
        "HGVC name in pages",
    )
    require(
        hgvc_card["raster_sha256"] in index and hgvc_card["raster_sha256"] in executive,
        "HGVC SHA-256 in pages",
    )

    gcsd_reg = json.loads((root / "registry/gcsd88_run_card.json").read_text())
    gcsd_web = json.loads((root / "docs/data/gcsd88_run_card.json").read_text())
    require(gcsd_reg == gcsd_web, "GCSD run card sync")
    gcsd_tif = root / gcsd_reg["submission"]["file"]
    gcsd_zip = root / gcsd_reg["submission"]["zip_file"]
    require(gcsd_tif.is_file() and gcsd_zip.is_file(), "GCSD tif/zip on disk")
    require(
        sha256(gcsd_tif) == gcsd_reg["raster_sha256"] and sha256(gcsd_zip) == gcsd_reg["zip_sha256"],
        "GCSD sha256 match",
    )
    require(
        gcsd_reg["ok_to_download"] is True and gcsd_reg["ok_to_submit"] is False and gcsd_reg["verdict"] == "negative",
        "GCSD fail-closed status",
    )
    readme = (root / "README.md").read_text()
    require(
        gcsd_tif.name in readme and gcsd_tif.name in index and gcsd_tif.name in executive and gcsd_tif.name in research,
        "GCSD tif linked across README and Pages",
    )
    require(
        gcsd_reg["raster_sha256"] in readme and gcsd_reg["raster_sha256"] in index and gcsd_reg["raster_sha256"] in executive,
        "GCSD hash present across README and Pages",
    )
    require(
        "0.201610" in readme and "0.201610" in index and "0.201610" in executive and "0.201610" in research,
        "GCSD HOLDOUT-DTI 0.201610 present across README and Pages",
    )
    print(
        "PASS: H88-GCSD, H88-GZZC, H88-HGVC, MTAS pre-placement stop, canonical archived bytes, Pages links, and negative decisions agree"
    )


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"SITE GUARD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
