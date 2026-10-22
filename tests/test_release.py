import json
from pathlib import Path
import pytest
from validate_release import release_report

ROOT = Path(__file__).resolve().parents[1]


def test_published_card_and_tif_fail_closed():
    if not (ROOT / "data/bridge/sample_submission.tif").exists():
        pytest.skip(
            "restore grid and registry witness via scripts/restore_inputs.py --validation"
        )
    if not (ROOT / "data/registry/dense_17gemdoe.tif").exists():
        pytest.skip(
            "restore registry witness via scripts/restore_inputs.py --validation"
        )
    report = release_report()
    assert report["format_ok"]
    assert report["values_0_1"] and report["inside_no_nan"]
    assert report["literal_duplicate"] and report["registry_forward_overlap_3px"] == 1
    assert report["ok_to_download"] and not report["ok_to_submit"]
    card = json.loads((ROOT / "docs/data/run-card.json").read_text())
    assert (
        card["submission_note"]
        == json.loads((ROOT / "registry/run_card.json").read_text())["submission_note"]
    )
    assert len(card["submission_note"]) <= 140 and card["verdict"] == "negative"


def test_brief_and_site_are_not_missing():
    readme = (ROOT / "README.md").read_text()
    assert "Maximize P(Win)" in readme and "Own the Outcome" in readme
    assert "MUST GENERATE A UNIQUE TIF SUBMISSION" in readme
    site = (ROOT / "docs/index.html").read_text()
    assert "DO NOT SUBMIT" in site
    assert "executive-summary.html" in site
    assert "download" in site.lower()


def test_cgo88_and_band19_audit_receipt():
    reg_audit = json.loads(
        (ROOT / "registry/cgo88_holdout_and_band19_audit.json").read_text()
    )
    doc_audit = json.loads(
        (ROOT / "docs/evidence/cgo88_holdout_and_band19_audit.json").read_text()
    )
    holdout = json.loads((ROOT / "registry/holdout_result.json").read_text())
    meta = json.loads((ROOT / "evidence/input-metadata.json").read_text())
    assert reg_audit == doc_audit
    assert reg_audit["evaluator_version"] == "gems57-pooled-hide-v2"
    assert reg_audit["withheld_positive_pixels"] == 22893
    assert reg_audit["radiometric_k_th_u_in_19band_tiff"] is False
    assert (
        reg_audit["band_06_tc_is_magnetic_tilt_curvature_not_radiometric_total_count"]
        is True
    )
    bands = reg_audit["band_catalog_19"]
    assert len(bands) == 19
    for idx, (entry, desc) in enumerate(
        zip(bands, meta["training_features"]["descriptions"]), start=1
    ):
        assert entry["band_index"] == idx
        assert entry["description"] == desc
        assert desc.startswith(entry["band_name"] + " - ")
        assert 0.5 <= entry["holdout_symmetric_auc"] <= 0.90
    comp = reg_audit["holdout_comparison"]
    assert comp["mgc88_incumbent"] == holdout["scores"]["candidate"]
    assert comp["raw_control"] == holdout["scores"]["raw_control"]
    assert comp["cgo88_pure"]["dti"] < comp["mgc88_incumbent"]["dti"]
    assert comp["cgo88_joint"]["dti"] < comp["mgc88_incumbent"]["dti"]
    assert comp["paired_delta_cgo88_pure_vs_mgc88"]["ci95"][1] < 0
    assert comp["paired_delta_cgo88_joint_vs_mgc88"]["ci95"][1] < 0
    assert reg_audit["decision"]["beats_mgc88_incumbent"] is False
    assert reg_audit["decision"]["promoted"] is False
    assert reg_audit["decision"]["verdict"] == "negative"


def test_no_hallucinated_band_names_or_urls_in_docs():
    forbidden = (
        "cahill-lake-lahontan",
        "mag_anomaly",
        "tmi_vertical_gradient",
        "surface_conductivity",
        "horizontal_gravity_gradient",
        "strain_invariant",
        "radiometric_k",
    )
    for rel in (
        "docs/research.html",
        "research/candidate-hypotheses-20261022.md",
        "docs/research/candidate-hypotheses-20261022.md",
        "knowledge/field-guide.md",
    ):
        text = (ROOT / rel).read_text()
        for bad in forbidden:
            assert bad not in text, f"Found {bad!r} in {rel}"
