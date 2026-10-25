"""Regression tests for the retired CON88 exception and literal overlap rule.

* No machine record may claim clearance while the universal literal gate binds.
* Dense-prior top-N is an informational diagnostic and never grants clearance.
* Every published research TIFF/ZIP carries DO-NOT-SUBMIT; no gate exception exists.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _true_flags(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "ok_to_submit" and v is True:
                yield path + "." + k
            yield from _true_flags(v, path + "." + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _true_flags(v, f"{path}[{i}]")


def test_no_record_claims_submit_true_after_correction():
    offenders = []
    records = (list((ROOT / "registry").glob("*.json"))
               + list((ROOT / "docs").rglob("*.json"))
               + list((ROOT / "evidence").glob("*.json"))
               + list(ROOT.glob("run_card*.json")))
    for rec in records:
        try:
            data = json.loads(rec.read_text())
        except ValueError:
            continue
        offenders += [f"{rec.relative_to(ROOT)}:{p}" for p in _true_flags(data)]
    assert not offenders, offenders
    audit = json.loads((ROOT / "docs/data/download_audit.json").read_text())
    assert all(row["ok_to_submit"] is False for row in audit["artifacts"])
    assert audit["protocol_eligible_count"] == 0
    gate = json.loads((ROOT / "registry/con88_gates.json").read_text())
    assert gate["ok_to_submit"] is False
    assert gate["verdict"] == "negative"
    assert gate["current_protocol"]["decision"] == "DUPLICATE_STOP"


def test_dense_prior_diagnostic_is_informational_only():
    d = json.loads((ROOT / "evidence/dense_prior_topn_diagnostic.json").read_text())
    assert d["status"].startswith("DIAGNOSTIC ONLY")
    assert d["literal_rule"]["literal_forward_overlap_all_candidates"] == 1.0
    assert d["count_candidates"] >= 1
    for row in d["topN_like_for_like"]:
        assert row["literal_forward_3px_overlap_vs_all_positive_witness_cells"] == 1.0
        assert "passes_0_70_like_for_like" in row


def test_matrix_rows_never_submit_and_cite_records():
    m = json.loads((ROOT / "docs/data/candidate_matrix.json").read_text())
    assert m["organizer_confirmed_scores"] == 0 and m["weekly_slots_used"] == 0
    for row in m["rows"]:
        assert row["ok_to_submit"] is False
        assert (ROOT / row["record"]).is_file()


def test_downloads_are_marked_do_not_submit_without_gate_exceptions():
    for directory in (ROOT / "docs/downloads", ROOT / "docs/research-variants"):
        for f in directory.iterdir():
            if f.suffix.lower() in (".tif", ".tiff", ".zip"):
                assert "DO-NOT-SUBMIT" in f.name, f.name
    report = json.loads((ROOT / "docs/data/download_audit.json").read_text())
    assert all(row["negative_filename_markers"] is True for row in (
        report["artifacts"] + report.get("additional_research_artifacts", [])
    ))
