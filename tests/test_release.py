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
    mgc_holdout = json.loads((ROOT / "registry/mgc88_holdout_result.json").read_text())
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
    assert comp["mgc88_incumbent"] == mgc_holdout["scores"]["candidate"]
    assert comp["raw_control"] == mgc_holdout["scores"]["raw_control"]
    assert holdout["scores"]["mgc88_incumbent"]["dti"] == pytest.approx(
        comp["mgc88_incumbent"]["dti"]
    )
    assert holdout["scores"]["raw_control"]["dti"] == pytest.approx(
        comp["raw_control"]["dti"]
    )
    assert comp["cgo88_pure"]["dti"] < comp["mgc88_incumbent"]["dti"]
    assert comp["cgo88_joint"]["dti"] < comp["mgc88_incumbent"]["dti"]
    assert comp["paired_delta_cgo88_pure_vs_mgc88"]["ci95"][1] < 0
    assert comp["paired_delta_cgo88_joint_vs_mgc88"]["ci95"][1] < 0
    assert reg_audit["decision"]["beats_mgc88_incumbent"] is False
    assert reg_audit["decision"]["promoted"] is False
    assert reg_audit["decision"]["verdict"] == "negative"


def test_str88_experiment3_and_official_band_verification():
    str_rec = json.loads((ROOT / "registry/str88_experiment_receipt.json").read_text())
    doc_rec = json.loads((ROOT / "docs/evidence/str88_experiment_receipt.json").read_text())
    holdout = json.loads((ROOT / "registry/holdout_result.json").read_text())
    card = json.loads((ROOT / "registry/run_card.json").read_text())
    assert str_rec == doc_rec
    assert str_rec["experiment_id"] == card["experiment_id"] == "STR-88"
    assert str_rec["experiment_budget_used"] == card["experiment_budget_used"] == 3
    assert str_rec["beats_mgc88_with_positive_95ci"] is True
    assert str_rec["like_for_like_discrete_uniqueness_passed"] is True
    assert str_rec["literal_dense_prior_duplicate"] is True
    assert str_rec["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    assert len(str_rec["leakage_canaries"]["features"]) == 18
    assert holdout["scores"]["candidate"]["dti"] > holdout["scores"]["mgc88_incumbent"]["dti"]
    assert holdout["paired_differences"]["mgc88_incumbent"]["ci95"][0] > 0.0
    assert holdout["paired_differences"]["raw_control"]["ci95"][0] > 0.0
    # Verify prospective IR-88-06 closure on preplacement registry
    pre = card["correlation_overlap_vs_registry"]["surface_preplacement"]
    assert len(pre) == 6
    for entry in pre.values():
        assert "positive_support_overlap_3px" in entry
        assert "top_1pct_crest_overlap_3px" in entry
        assert abs(entry["full_footprint_spearman"]) <= 0.90
    # Verify official organizer reference notebook band/grid equivalence receipt
    nb_ver = json.loads(
        (ROOT / "evidence/official-reference-band-verification.json").read_text()
    )
    doc_nb_ver = json.loads(
        (ROOT / "docs/evidence/official-reference-band-verification.json").read_text()
    )
    assert nb_ver == doc_nb_ver
    assert nb_ver["all_19_band_tags_match_exact"] is True
    assert len(nb_ver["bands"]) == 19


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
        "README.md",
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/research.html",
        "research/candidate-hypotheses-20261022.md",
        "docs/research/candidate-hypotheses-20261022.md",
        "research/candidate-hypotheses-20261023.md",
        "docs/research/candidate-hypotheses-20261023.md",
        "knowledge/field-guide.md",
    ):
        text = (ROOT / rel).read_text()
        for bad in forbidden:
            assert bad not in text, f"Found {bad!r} in {rel}"
