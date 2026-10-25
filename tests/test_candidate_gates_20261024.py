"""Regression tests for the 2026-10-24 correction (IR-88-86/87/88).

* No machine record may say ok_to_submit=true while the literal uniqueness rule or the holdout bar fails.
* The dense-prior top-N diagnostic must keep the literal result at 1.0 and must not grant a submission.
* Every downloadable TIF/ZIP under docs/downloads must carry DO-NOT-SUBMIT (or be cleared by its gate), except the exact hash-pinned negative XGCE pair inherited from main.
"""
import hashlib
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
    for rec in list((ROOT / "registry").glob("*.json")) + list((ROOT / "docs").rglob("*.json")) + list((ROOT / "evidence").glob("*.json")):
        try:
            data = json.loads(rec.read_text())
        except ValueError:
            continue
        offenders += [f"{rec.relative_to(ROOT)}:{p}" for p in _true_flags(data)]
    # The only sanctioned exception would need a literal-rule PASS and holdout PASS; none exists today.
    assert offenders == [], offenders


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


def test_downloads_are_marked_or_cleared():
    cleared = set()
    for g in (ROOT / "registry").glob("*gate*.json"):
        try:
            data = json.loads(g.read_text())
        except ValueError:
            continue
        name = Path((data.get("candidate") or {}).get("tif", "")).name
        if data.get("ok_to_submit") and name:
            cleared.add(name)
    # PR #105 on main introduced an unmarked research-only XGCE pair. Do not
    # pretend its literal duplicate is cleared; allow only these exact bytes.
    legacy = {
        "gems88-xgce-crossgradient-30000dots-20261025-zeros.tif":
            "199e6f30e2fc68bddae69e21ac5ea04823ec5d3f0b6239d3f32cb136c8a32c4c",
        "gems88-xgce-crossgradient-30000dots-20261025-zeros.zip":
            "f92fe721152ce04a0739a08c4c91314c76d144c91a7e7d7dac77d9e0e3040876",
    }
    card = json.loads((ROOT / "registry/xgce88_run_card.json").read_text())
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["uniqueness"]["literal_dense_witness_overlap"] == 1.0
    assert card["uniqueness"]["literal_dense_witness_pass"] is False
    assert {Path(card["submission"][key]).name for key in ("file", "zip_file")} == set(legacy)
    for f in (ROOT / "docs/downloads").iterdir():
        if f.suffix.lower() in (".tif", ".tiff", ".zip"):
            if f.name in legacy:
                assert hashlib.sha256(f.read_bytes()).hexdigest() == legacy[f.name]
            else:
                assert "DO-NOT-SUBMIT" in f.name or f.name in cleared, f.name
