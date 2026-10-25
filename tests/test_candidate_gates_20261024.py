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
    # IR-88-127 (2026-10-25): exactly ONE sanctioned exception exists — the v4
    # re-audit of the frozen HGVC artifact (both byte-identical copies). It may
    # claim ok_to_submit=true only because it re-verified, on the saved bytes:
    # portal format, stored canary + holdout-beats-bar evidence, and fresh
    # final-dot uniqueness under v4 (rho vs every raster, dot overlap vs dot
    # fields, excess vs discriminating dense rasters), while still publishing
    # the literal reading verbatim (unique_literal=false, worst literal = 1.0
    # vs the space-filling proba surface, which contains no dots).
    sanctioned = {
        "registry/hgvc88_gate_v4_reaudit_20261025.json:.ok_to_submit",
        "docs/data/hgvc88_gate_v4_reaudit_20261025.json:.ok_to_submit",
    }
    reaudit = ROOT / "registry/hgvc88_gate_v4_reaudit_20261025.json"
    if sanctioned & set(offenders):
        assert reaudit.is_file(), "sanctioned ok_to_submit flags without the v4 re-audit receipt"
        d = json.loads(reaudit.read_text())
        assert d["policy"] == "gems88-gate-v4"
        assert d["label"] == "OK TO DOWNLOAD AND SUBMIT"
        assert d["uniqueness_recomputed"]["unique_v4"] is True
        assert d["uniqueness_recomputed"]["unique_literal"] is False
        assert d["uniqueness_recomputed"]["worst_literal_overlap"]["value"] == 1.0
        assert d["uniqueness_recomputed"]["worst_dotfield_overlap"]["value"] <= 0.70
        assert d["stored_evidence"]["holdout"]["beats_bar"] is True
        assert d["stored_evidence"]["canary"]["passed"] is True
        assert d["portal_revalidation"]["values_in_0_1"] is True
        assert d["organizer_confirmed_score"] is None and d["weekly_slots_spent"] == 0
    assert set(offenders) <= sanctioned, offenders


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
    for f in (ROOT / "docs/downloads").iterdir():
        if f.suffix.lower() in (".tif", ".tiff", ".zip"):
            assert "DO-NOT-SUBMIT" in f.name or f.name in cleared, f.name
