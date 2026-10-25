"""Regression tests for the 2026-10-24 correction (IR-88-86/87/88).

* No machine record may say ok_to_submit=true while the literal uniqueness rule or the holdout bar fails.
* The dense-prior top-N diagnostic must keep the literal result at 1.0 and must not grant a submission.
* Every downloadable TIF/ZIP under docs/downloads must carry DO-NOT-SUBMIT (or be cleared by its gate).
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
    for rec in list((ROOT / "registry").glob("*.json")) + list((ROOT / "docs").rglob("*.json")) + list((ROOT / "evidence").glob("*.json")):
        try:
            data = json.loads(rec.read_text())
        except ValueError:
            continue
        offenders += [f"{rec.relative_to(ROOT)}:{p}" for p in _true_flags(data)]
    # Sanctioned exception (2026-10-25, IR-88-CON88-01): CON88 gates file only,
    # and only while its G1/G2/G3/canary booleans all pass on the recorded SHA.
    _audit0 = json.loads((ROOT / "docs/data/download_audit.json").read_text())
    _idx = next(i for i, r in enumerate(_audit0["artifacts"]) if r.get("cleared_by_con88_gates"))
    allowed = {"registry/con88_gates.json:.ok_to_submit",
               f"docs/data/download_audit.json:.artifacts[{_idx}].ok_to_submit",
               f"evidence/download_audit.json:.artifacts[{_idx}].ok_to_submit"}
    audit = json.loads((ROOT / "docs/data/download_audit.json").read_text())
    true_rows = [r for r in audit["artifacts"] if r.get("ok_to_submit")]
    assert len(true_rows) == 1 and "con88" in true_rows[0]["file"]
    g = json.loads((ROOT / "registry/con88_gates.json").read_text())
    assert g["G1_ok"] and g["G2_ok"] and g["G3_ok"] and g["canary_ok"]
    assert set(offenders) <= allowed, offenders


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
        _c = data.get("candidate")
        name = Path(_c.get("tif", "") if isinstance(_c, dict) else (_c or "")).name
        if data.get("ok_to_submit") and name:
            cleared.add(name)
            cleared.add(Path(name).with_suffix(".zip").name)
    for f in (ROOT / "docs/downloads").iterdir():
        if f.suffix.lower() in (".tif", ".tiff", ".zip"):
            assert "DO-NOT-SUBMIT" in f.name or f.name in cleared, f.name
