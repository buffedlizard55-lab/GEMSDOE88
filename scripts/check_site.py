#!/usr/bin/env python3
"""Fail-closed integrity guard for the GitHub Pages decision surface."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
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
        self.open_archives = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "details" and "archive-lanes" in values.get("class", "").split() and "open" in values:
            self.open_archives += 1
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
            "con88.html",
            "mdc88/index.html",
            "mdc88/executive-summary.html",
        )
    ]
    card = json.loads((root / "registry/mvrd_run_card.json").read_text())
    web_card = json.loads((docs / "data/mvrd_run_card.json").read_text())
    gate = json.loads((root / "registry/mvrd_gate_v3.json").read_text())
    web_gate = json.loads((docs / "data/mvrd-gate-v3.json").read_text())
    current = json.loads((docs / "data/current_release.json").read_text())
    status = json.loads((docs / "status.json").read_text())
    con88 = json.loads((docs / "data/run_card_con88.json").read_text())
    con88_gate = json.loads((root / "registry/con88_gates.json").read_text())
    con88_gate_web = json.loads((docs / "data/con88_gates.json").read_text())
    con88_correction = json.loads((root / "evidence/con88_clearance_withdrawal_20261025.json").read_text())
    con88_correction_web = json.loads((docs / "data/con88_clearance_withdrawal_20261025.json").read_text())
    require(con88_gate == con88_gate_web and con88_correction == con88_correction_web,
            "Pages CON88 evidence differs from canonical negative records")
    require(con88["verdict"] == "negative" and con88["ok_to_submit"] is False
            and con88["approved_for_weekly_slot"] is False
            and con88_gate["ok_to_submit"] is False
            and con88_gate["verdict"] == "negative"
            and con88_correction["ok_to_submit"] is False
            and con88_correction["verdict"] == "negative",
            "CON88 withdrawal records must fail closed")
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
        require(parser.open_archives == 0, "Historical lane archive must remain closed by default")
        for ref in parser.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc or not url.path:
                continue
            target = page.parent / unquote(url.path)
            require(target.is_file(), f"broken local link: {page.name}: {ref}")

    # Every published binary must carry the negative decision in its filename.
    # Pre-existing CTRA is allowed ONLY for the exact hash-pinned negative bytes
    # checked above.  IR-88-F55AFF34-01 removed CON88's unsafe exception.
    sys.path.insert(0, str(ROOT))
    from scripts.audit_downloads import PUBLICATION_DIRECTORIES, check_package_inventory
    legacy_negative = {ctra_tif.resolve(), ctra_zip.resolve()}
    _con88 = docs / "downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif"
    _gates = json.loads((ROOT / "registry/con88_gates.json").read_text())
    require(_gates.get("ok_to_submit") is False and _gates.get("candidate") == _con88.name
            and hashlib.sha256(_con88.read_bytes()).hexdigest() == _gates.get("sha256"),
            "CON88 negative bytes disagree with corrected gates record")
    for published in sorted(docs.rglob("*")):
        if published.is_file() and published.suffix.lower() in {
            ".tif", ".tiff", ".zip",
        }:
            require(
                "DO-NOT-SUBMIT" in published.name or published.resolve() in legacy_negative,
                f"unmarked published research artifact: {published}",
            )
            require(
                published.parent in {docs / name for name in PUBLICATION_DIRECTORIES},
                f"published artifact outside the declared audited directories: {published}",
            )
    # A negative filename is necessary but does not make an unrecorded ZIP or
    # a newly added TIFF/ZIP pair part of the saved, two-decoder file audit.
    check_package_inventory(root)
    download_audit = json.loads((docs / "data/download_audit.json").read_text())
    all_rows = download_audit["artifacts"] + download_audit.get("additional_research_artifacts", [])
    recorded_files = {(row.get("publication_directory", "downloads"), name) for row in all_rows
                      for name in (row["file"], row["zip_file"])}
    actual_files = {(directory, p.name) for directory in PUBLICATION_DIRECTORIES
                    for p in (docs / directory).glob("*")
                    if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"}}
    require(actual_files == recorded_files and len(recorded_files) == 2 * len(all_rows),
            "Published TIFF/ZIP inventory differs from the saved download audit")
    require(download_audit["schema"] == "gems88.download-audit.v2"
            and download_audit["tiff_count"] == len(download_audit["artifacts"])
            and download_audit["research_download_pass_count"] == len(download_audit["artifacts"])
            and download_audit["additional_research_tiff_count"] == len(download_audit["additional_research_artifacts"])
            and download_audit["total_published_tiff_count"] == len(all_rows)
            and download_audit["total_research_download_pass_count"] == len(all_rows)
            and download_audit["protocol_eligible_count"] == 0,
            "Saved download audit must cover both publication directories without granting submission clearance")
    for row in all_rows:
        directory = docs / row.get("publication_directory", "downloads")
        require(row["format_valid"] is True and row["research_download_ok"] is True
                and row["ok_to_submit"] is False
                and row.get("cleared_by_con88_gates") is False
                and sha256(directory / row["file"]) == row["sha256"]
                and sha256(directory / row["zip_file"]) == row["zip_sha256"],
                f"Published research bytes or negative audit changed: {directory.name}/{row['file']}")

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
        and "fetch('data/download_audit.json'" in js
        and "fetch('status.json'" in js
        and "PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT" in js,
        "Dynamic decision banner must fail closed on absent canonical audit/proof",
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

    vhgd_card = json.loads((root / "registry/vhgd88_run_card.json").read_text())
    vhgd_web = json.loads((docs / "data/vhgd88_run_card.json").read_text())
    vhgd_gv = json.loads((root / "registry/vhgd88_gate_verdict.json").read_text())
    vhgd_gv_web = json.loads((docs / "data/vhgd88_gate_verdict.json").read_text())
    require(vhgd_card == vhgd_web, "Pages VHGD card differs from canonical registry card")
    require(vhgd_gv == vhgd_gv_web, "Pages VHGD gate v3 differs from canonical registry gate")
    require(
        vhgd_card["verdict"] == "negative"
        and vhgd_card["ok_to_download"] is True
        and vhgd_card["ok_to_submit"] is False
        and vhgd_gv["ok_to_submit"] is False
        and vhgd_card["correlation_overlap_vs_registry"]["unique_like_for_like"] is True
        and vhgd_card["correlation_overlap_vs_registry"]["final_worst_like_for_like_overlap_3px"]["value"] <= 0.70,
        "VHGD run card verdict/gate flags inconsistent",
    )
    require(
        0 < len(vhgd_card["submission"]["submission_name"]) <= 140
        and 0 < len(vhgd_card["submission"]["submission_note"]) <= 140,
        "VHGD submission name/note must satisfy <=140 character cap",
    )
    vhgd_tif = root / vhgd_card["submission"]["file"]
    vhgd_zip = root / vhgd_card["submission"]["zip_file"]
    require(vhgd_tif.is_file() and vhgd_zip.is_file(), "VHGD tif/zip files exist")
    require(
        sha256(vhgd_tif) == vhgd_card["raster_sha256"] == vhgd_gv["sha256"],
        "VHGD TIFF SHA-256 mismatch across file, card, and gate",
    )
    require(
        sha256(vhgd_zip) == vhgd_card["zip_sha256"] == vhgd_gv["zip_sha256"],
        "VHGD ZIP SHA-256 mismatch across file, card, and gate",
    )
    require(vhgd_tif.name in index and vhgd_tif.name in executive, "VHGD tif in pages")
    require(
        vhgd_card["submission"]["submission_name"] in index
        and vhgd_card["submission"]["submission_name"] in executive,
        "VHGD name in pages",
    )
    require(
        vhgd_card["raster_sha256"] in index and vhgd_card["raster_sha256"] in executive,
        "VHGD SHA-256 in pages",
    )
    # The primary panels must be generated from the same canonical evidence.
    # A new lane cannot prepend a contradictory banner and still pass because
    # the expected negative words happen to appear much further down the page.
    sys.path.insert(0, str(ROOT))
    from scripts import render_decision
    for page, kind in ((docs / "mdc88/index.html", "overview"),
                       (docs / "mdc88/executive-summary.html", "guide")):
        require(page.read_text() == render_decision.legacy_notice(kind),
                "Legacy page must withdraw unsupported upload clearance and link the canonical decision")
    legacy_status = json.loads((docs / "mdc88/status.json").read_text())
    require(legacy_status["ok_to_submit"] is False
            and legacy_status["status"] == "BLOCKED_HISTORICAL_RESEARCH"
            and legacy_status["recommended_for_weekly_slot"] is False,
            "Legacy status must not advertise a ready-to-submit file")
    for page, kind in ((pages[0], "overview"), (pages[1], "guide")):
        text = page.read_text()
        require(
            text.split('<main id="main">', 1)[1].split(render_decision.START, 1)[0].strip() == "",
            "Primary decision must precede every lane banner and download",
        )
        require(text.count('<h1') == 1, "Only one primary page heading is allowed")
        expected = render_decision.replace_block(text, render_decision.render(root, kind))
        require(expected == text, "Canonical decision panel is stale or altered; render from machine evidence")
    bgcd = json.loads((root / "registry/bgcd88_run_card.json").read_text())
    bgcd_web = json.loads((docs / "data/bgcd88_run_card.json").read_text())
    bgcd_gate = json.loads((root / "registry/bgcd88_gate_verdict.json").read_text())
    bgcd_gate_web = json.loads((docs / "data/bgcd88_gate_verdict.json").read_text())
    require(bgcd == bgcd_web, "Pages BGCD card differs from canonical registry card")
    require(bgcd_gate == bgcd_gate_web, "Pages BGCD gate verdict differs from registry")
    require(
        bgcd["verdict"] == "negative"
        and bgcd["ok_to_download"] is True
        and bgcd["ok_to_submit"] is False
        and bgcd_gate["ok_to_submit"] is False,
        "BGCD fail-closed status invariant failed",
    )
    bgcd_tif = root / bgcd["submission"]["file"]
    bgcd_zip = root / bgcd["submission"]["zip_file"]
    require(sha256(bgcd_tif) == bgcd["raster_sha256"], "BGCD TIFF SHA256 mismatch")
    require(sha256(bgcd_zip) == bgcd["zip_sha256"], "BGCD ZIP SHA256 mismatch")
    with zipfile.ZipFile(bgcd_zip) as zf:
        require(
            zf.namelist() == [bgcd_tif.name] and zf.read(bgcd_tif.name) == bgcd_tif.read_bytes(),
            "BGCD ZIP does not contain byte-identical single TIFF",
        )
    bgcd_doc_md = docs / "research/bgcd88-forensics-and-phd-synthesis-20261025.md"
    require(bgcd_doc_md.is_file(), "BGCD PhD synthesis markdown missing under docs/research")
    bgcd_root_md = root / "research/bgcd88-forensics-and-phd-synthesis-20261025.md"
    if bgcd_root_md.is_file():
        require(
            bgcd_root_md.read_bytes() == bgcd_doc_md.read_bytes(),
            "BGCD PhD synthesis markdown differs between research/ and docs/research/",
        )
    sources = (docs / "sources.html").read_text()
    for page_name, page_txt in (
        ("index.html", index),
        ("executive-summary.html", executive),
        ("research.html", research),
        ("sources.html", sources),
    ):
        require(bgcd_tif.name in page_txt, f"BGCD tif missing in {page_name}")
        require(bgcd["submission"]["submission_name"] in page_txt, f"BGCD submission_name missing in {page_name}")
        require(bgcd["raster_sha256"] in page_txt, f"BGCD raster_sha256 missing in {page_name}")
    require(
        bgcd["zip_sha256"] in index and bgcd["zip_sha256"] in executive,
        "BGCD zip_sha256 missing in index/executive",
    )
    # Concurrent SEPA is archived; the unauthorized HGVC v4 approval is revoked.
    sepa = json.loads((root / "registry/sepa88_run_card.json").read_text())
    require(sepa == json.loads((docs / "data/sepa88_run_card.json").read_text()), "SEPA card mirrors differ")
    require(sepa["ok_to_submit"] is False and sepa["verdict"] == "negative", "SEPA must stay negative")
    sepa_tif = root / sepa["download"]
    require(sha256(sepa_tif) == sepa["raster_sha256"], "SEPA TIFF differs from record")
    for page in (index, executive):
        require(sepa_tif.name in page and sepa["raster_sha256"] in page, "SEPA archival identity missing")
        require("Unsupported HGVC submission clearance revoked" in page, "v4 correction must be disclosed")
    reaudit = json.loads((root / "registry/hgvc88_gate_v4_reaudit_20261025.json").read_text())
    require(reaudit == json.loads((docs / "data/hgvc88_gate_v4_reaudit_20261025.json").read_text()), "HGVC correction mirrors differ")
    require(reaudit["policy"] == "gems88-gate-v3" and reaudit["ok_to_submit"] is False
            and reaudit["eligible_for_selector"] is False and reaudit["approved_for_weekly_slot"] is False
            and reaudit["subject"]["sha256"] == hgvc_card["raster_sha256"]
            and reaudit["uniqueness_recomputed"]["unique_literal"] is False
            and reaudit["uniqueness_recomputed"]["worst_literal_overlap"]["value"] == 1.0
            and reaudit["correction"]["reason_id"] == "IR-88-D0C3ADEB-08",
            "Unsupported v4 dense-prior/selector clearance must remain revoked")
    addendum = json.loads((root / "registry/hgvc88_gate_v4_addendum_psgv_20261025.json").read_text())
    require(addendum == json.loads((docs / "data/hgvc88_gate_v4_addendum_psgv_20261025.json").read_text())
            and addendum["ok_to_submit"] is False, "Creation-order exemption must not clear HGVC")

    bpwd_card = json.loads((root / "registry/bpwd88_run_card.json").read_text())
    bpwd_web = json.loads((docs / "data/bpwd88_run_card.json").read_text())
    bpwd_ev = json.loads((root / "evidence/bpwd88_run_card.json").read_text())
    bpwd_gv = json.loads((root / "registry/bpwd88_gate_v3.json").read_text())
    bpwd_gv_web = json.loads((docs / "data/bpwd88_gate_v3.json").read_text())
    require(bpwd_card == bpwd_web == bpwd_ev, "BPWD card mirrors differ")
    require(bpwd_gv == bpwd_gv_web, "BPWD gate v3 mirrors differ")
    require(
        bpwd_card["verdict"] == "negative"
        and bpwd_card["ok_to_download"] is True
        and bpwd_card["ok_to_submit"] is False
        and bpwd_card["all_5_discriminating_gates_pass"] is True
        and bpwd_card["beats_hgvc_holdout_best"] is True
        and bpwd_card["holdout_dti"]["candidate_exp03"]["dti"] > bpwd_card["holdout_dti"]["control_h88_hgvc_incumbent"]["dti"]
        and bpwd_gv["ok_to_submit"] is False,
        "BPWD run card verdict/gate flags inconsistent",
    )
    require(
        0 < len(bpwd_card["submission_name"]) <= 140
        and 0 < len(bpwd_card["submission_note"]) <= 140,
        "BPWD submission name/note must satisfy <=140 character cap",
    )
    bpwd_tif = root / bpwd_card["download"]
    bpwd_zip = root / bpwd_card["zip_download"]
    require(bpwd_tif.is_file() and bpwd_zip.is_file(), "BPWD tif/zip files exist")
    require(
        sha256(bpwd_tif) == bpwd_card["raster_sha256"] == bpwd_gv["sha256"],
        "BPWD TIFF SHA-256 mismatch across file, card, and gate",
    )
    require(
        sha256(bpwd_zip) == bpwd_card["zip_sha256"] == bpwd_gv["zip_sha256"],
        "BPWD ZIP SHA-256 mismatch across file, card, and gate",
    )
    with zipfile.ZipFile(bpwd_zip) as zf:
        require(
            zf.namelist() == [bpwd_tif.name] and zf.read(bpwd_tif.name) == bpwd_tif.read_bytes(),
            "BPWD ZIP does not contain byte-identical single TIFF",
        )
    bpwd_doc_md = docs / "research/candidate-hypotheses-20261025-bpwd88.md"
    bpwd_root_md = root / "research/candidate-hypotheses-20261025-bpwd88.md"
    require(
        bpwd_doc_md.is_file() and bpwd_root_md.is_file() and bpwd_doc_md.read_bytes() == bpwd_root_md.read_bytes(),
        "BPWD PhD hypotheses markdown missing or mismatched",
    )
    for page_name, page_txt in (
        ("index.html", index),
        ("executive-summary.html", executive),
        ("research.html", research),
        ("sources.html", sources),
    ):
        require(bpwd_tif.name in page_txt, f"BPWD tif missing in {page_name}")
        require(bpwd_card["submission_name"] in page_txt, f"BPWD submission_name missing in {page_name}")
        require(bpwd_card["raster_sha256"] in page_txt, f"BPWD raster_sha256 missing in {page_name}")
    require(
        index.index('id="mtas-review"') < index.index('id="bpwd-hero"') < index.index('class="archive-lanes"')
        and executive.index('id="mtas-review"') < executive.index('id="bpwd-hero"') < executive.index('class="archive-lanes"'),
        "BPWD hero must appear between canonical decision and archive-lanes",
    )

    vcaz_card = json.loads((root / "registry/vcaz88_run_card.json").read_text())
    vcaz_web = json.loads((docs / "data/vcaz88_run_card.json").read_text())
    vcaz_gv = json.loads((root / "registry/vcaz88_gate_v3.json").read_text())
    vcaz_gv_web = json.loads((docs / "data/vcaz88_gate_v3.json").read_text())
    require(vcaz_card == vcaz_web, "Pages VCAZ card differs from canonical registry card")
    require(vcaz_gv == vcaz_gv_web, "Pages VCAZ gate v3 differs from canonical registry gate")
    require(
        vcaz_card["verdict"] == "negative"
        and vcaz_card["ok_to_download"] is True
        and vcaz_card["ok_to_submit"] is False
        and vcaz_gv["decision"]["ok_to_submit"] is False
        and vcaz_card["correlation_overlap_vs_registry"]["unique_like_for_like"] is True
        and vcaz_card["correlation_overlap_vs_registry"]["final_worst_like_for_like_overlap_3px"]["value"] <= 0.70,
        "VCAZ run card verdict/gate flags inconsistent",
    )
    require(
        0 < len(vcaz_card["submission_name"]) <= 140
        and 0 < len(vcaz_card["submission_note"]) <= 140,
        "VCAZ submission name/note must satisfy <=140 character cap",
    )
    vcaz_tif = root / vcaz_card["download"]
    vcaz_zip = root / vcaz_card["zip_download"]
    require(vcaz_tif.is_file() and vcaz_zip.is_file(), "VCAZ tif/zip files exist")
    require(
        sha256(vcaz_tif) == vcaz_card["raster_sha256"] == vcaz_gv["sha256"],
        "VCAZ TIFF SHA-256 mismatch across file, card, and gate",
    )
    require(
        sha256(vcaz_zip) == vcaz_card["zip_sha256"] == vcaz_gv["zip_sha256"],
        "VCAZ ZIP SHA-256 mismatch across file, card, and gate",
    )
    with zipfile.ZipFile(vcaz_zip) as archive:
        require(
            archive.namelist() == [vcaz_tif.name]
            and archive.read(vcaz_tif.name) == vcaz_tif.read_bytes(),
            "VCAZ ZIP must contain the exact research TIFF",
        )
    require(vcaz_tif.name in index and vcaz_tif.name in executive, "VCAZ tif in pages")
    require(
        vcaz_card["submission_name"] in index and vcaz_card["submission_name"] in executive,
        "VCAZ name in pages",
    )
    require(
        vcaz_card["raster_sha256"] in index and vcaz_card["raster_sha256"] in executive,
        "VCAZ SHA-256 in pages",
    )
    require("fetch('data/vcaz88_run_card.json'" in js, "site.js must verify vcaz88_run_card.json")

    if (docs / "data/mmrx88_run_card.json").is_file():
        mmrx_card = json.loads((root / "registry/mmrx88_run_card.json").read_text())
        mmrx_web = json.loads((docs / "data/mmrx88_run_card.json").read_text())
        require(mmrx_card == mmrx_web, "Pages MMRX card differs from canonical registry card")
        require(
            mmrx_card["verdict"] == "negative"
            and mmrx_card["ok_to_submit"] is False
            and mmrx_card["ok_to_download"] is False
            and mmrx_card["download"] is None
            and mmrx_card["zip_download"] is None,
            "MMRX card must stay negative and must not advertise nonexistent docs/downloads paths",
        )

    submit_top = (docs / "SUBMIT.md").read_text().split("<details>", 1)[0]
    inventory_fraction = f"**{download_audit['total_research_download_pass_count']}/{download_audit['total_published_tiff_count']}**"
    require(inventory_fraction in submit_top,
            "Submission guide inventory count is stale against saved-byte audit")

    # Every JSON file served under docs/ must be strict RFC-8259 JSON (no NaN/Infinity that breaks browser JSON.parse).
    for docs_json in sorted(docs.rglob("*.json")):
        bad_constants: list[str] = []
        json.loads(docs_json.read_text(encoding="utf-8"), parse_constant=bad_constants.append)
        require(
            not bad_constants,
            f"{docs_json.relative_to(docs)} contains non-RFC-8259 JSON constants: {bad_constants[:3]}",
        )

    # Guard local links in Markdown files served under docs/ (e.g., docs/research/*.md).
    md_link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    inline_code_re = re.compile(r"`[^`]*`")
    for md_path in sorted(docs.rglob("*.md")):
        rel_md = md_path.relative_to(docs)
        in_fence = False
        for line_no, raw_line in enumerate(md_path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = raw_line.lstrip()
            if stripped.startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            cleaned = inline_code_re.sub("", raw_line)
            for match in md_link_re.finditer(cleaned):
                ref = match.group(1).strip().split()[0]
                parsed_url = urlsplit(ref)
                if parsed_url.scheme or parsed_url.netloc or not parsed_url.path:
                    continue
                rel_parent = rel_md.parent.as_posix()
                joined = posixpath.join("" if rel_parent == "." else rel_parent, unquote(parsed_url.path))
                norm = posixpath.normpath(joined)
                require(
                    norm != ".." and not norm.startswith("../") and not norm.startswith("/"),
                    f"{rel_md}:{line_no} escapes docs/ Pages root: {ref}",
                )
                require(
                    (docs / norm).exists(),
                    f"{rel_md}:{line_no} has broken local Markdown link: {ref}",
                )

    sub_dir = root / "submissions"
    if sub_dir.is_dir() and not sub_dir.is_symlink():
        sub_tifs = sorted(p for p in sub_dir.iterdir() if p.is_file() and p.suffix.lower() in {".tif", ".tiff"})
        sub_zips = {p.name for p in sub_dir.iterdir() if p.is_file() and p.suffix.lower() == ".zip"}
        require(
            not any(p.is_symlink() for p in sub_dir.iterdir()),
            "Symlinks are forbidden inside submissions/",
        )
        require(
            {t.with_suffix(".zip").name for t in sub_tifs} == sub_zips,
            "submissions/ TIFF and ZIP archives must be paired 1-for-1",
        )
        for sub_tif in sub_tifs:
            sub_zip = sub_tif.with_suffix(".zip")
            require(
                "DO-NOT-SUBMIT" in sub_tif.name and "DO-NOT-SUBMIT" in sub_zip.name,
                f"submissions/ archive lacks DO-NOT-SUBMIT marker: {sub_tif.name}",
            )
            with zipfile.ZipFile(sub_zip) as zf:
                require(
                    zf.namelist() == [sub_tif.name] and zf.read(sub_tif.name) == sub_tif.read_bytes(),
                    f"submissions/ ZIP member mismatch or missing DO-NOT-SUBMIT inside {sub_zip.name}",
                )

    print(
        "PASS: canonical decision first, H88-BPWD record, H88-VCAZ, research bytes, archived records, Pages links and negative gates agree"
    )


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"SITE GUARD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
