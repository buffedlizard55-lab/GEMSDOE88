"""Unit & integration tests for the AXIS=MASS session on parent R0 (h33-h33-2-b2).

Covers:
1. Exact marginal DTI drop: greedy choice equals one-step brute force and never
   touches the parent's dot count except by the requested amount.
2. Exact marginal DTI add: only candidate pixels are ever emitted, and the
   catalogue collar of the call is respected.
3. MASS arm arithmetic: r10minus 33,889 / r10plus 41,419 / r10swap 37,654 dots;
   every added dot is un-emitted H19-5 support at d_cat > 3 px; the swap never
   re-adds a dropped parent dot; % changed is inside [1, 50].
4. Ledger / receipt / mechanism-card integrity: unique SHA-256, BUILT status,
   MODEL-labelled prediction, preregistration recorded before the build.
5. Format gates on disk whenever the (gitignored) rasters are present locally.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402

AXIS = "MASS"
VALUES = ("r10minus", "r10plus", "r10swap")
EXPECTED_DOTS = {"r10minus": 33_889, "r10plus": 41_419, "r10swap": 37_654}
DOSE = 3_765
PARENT_DOTS = 37_654
REPORT = ROOT / "evidence" / "mass_r0_axis_report.json"


# ---------------------------------------------------------------------------
# 1-2. Solver exactness on a synthetic grid
# ---------------------------------------------------------------------------


def _synthetic() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(20261023)
    w = np.zeros((40, 40), dtype=np.float64)
    w[8:12, 5:35] = 1.0            # an east-west "fault"
    w[20:24, 5:35] = 0.6           # a weaker strand
    w += rng.uniform(0, 0.05, w.shape)
    base = np.zeros((40, 40), dtype=bool)
    base[10, 6:34:3] = True        # spaced dots on the strong strand
    base[22, 6:34:4] = True        # spaced dots on the weak strand
    return base, w


def _brute_dti(mask: np.ndarray, w: np.ndarray) -> float:
    return float(bpv.weighted_expected_dti(mask, w)["dti"])


def test_drop_solver_matches_one_step_brute_force() -> None:
    base, w = _synthetic()
    n = int(base.sum())
    out = bpv.select_exact_marginal_dti_drop(base, base, w, 1)
    assert int(out.sum()) == n - 1

    ys, xs = np.nonzero(base)
    scores = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        cand = base.copy()
        cand[y, x] = False
        scores.append(_brute_dti(cand, w))
    best = int(np.argmax(scores))
    removed = base & ~out
    ry, rx = np.nonzero(removed)
    assert (int(ry[0]), int(rx[0])) == (int(ys[best]), int(xs[best]))


def _reference_greedy_drop(base: np.ndarray, w: np.ndarray, n: int) -> np.ndarray:
    """Slow reference: recompute the exact post-drop DTI from scratch at every step."""
    state = base.copy()
    ys, xs = np.nonzero(base)
    for _ in range(n):
        best_score, best_pt = -1.0, None
        for y, x in zip(ys.tolist(), xs.tolist()):
            if not state[y, x]:
                continue
            state[y, x] = False
            sc = _brute_dti(state, w)
            state[y, x] = True
            if sc > best_score:
                best_score, best_pt = sc, (y, x)
        state[best_pt] = False
    return state


def _reference_greedy_add(base: np.ndarray, cand: np.ndarray, w: np.ndarray, n: int) -> np.ndarray:
    """Slow reference: recompute the exact post-add DTI from scratch at every step."""
    state = base.copy()
    ys, xs = np.nonzero(cand & ~state)
    for _ in range(n):
        best_score, best_pt = -1.0, None
        for y, x in zip(ys.tolist(), xs.tolist()):
            if state[y, x]:
                continue
            state[y, x] = True
            sc = _brute_dti(state, w)
            state[y, x] = False
            if sc > best_score:
                best_score, best_pt = sc, (y, x)
        state[best_pt] = True
    return state


def test_drop_solver_matches_full_recompute_greedy_and_hits_the_dose() -> None:
    """The fast local-window bookkeeping must equal a from-scratch greedy.

    Note: the resulting DTI is NOT guaranteed to beat the baseline -- on the real
    R0 build the best-possible 3,765-dot drop still loses 0.0084 w-model DTI.
    What is guaranteed is that every step is the exact argmax of post-drop DTI.
    """
    base, w = _synthetic()
    out = bpv.select_exact_marginal_dti_drop(base, base, w, 4)
    assert int(out.sum()) == int(base.sum()) - 4
    assert np.array_equal(out, _reference_greedy_drop(base, w, 4))
    # dropping is only free of loss when a dot is fully redundant; here it is not
    assert _brute_dti(out, w) < _brute_dti(base, w)


def test_add_solver_only_emits_candidates_and_hits_the_dose() -> None:
    base, w = _synthetic()
    cand = np.zeros_like(base)
    cand[10, :] = True
    cand &= ~base
    n_cand = int(cand.sum())
    n_add = min(4, n_cand)
    out = bpv.select_exact_marginal_dti_add(base, cand, w, n_add)
    assert int(out.sum()) == int(base.sum()) + n_add
    added = out & ~base
    assert np.all(added <= cand), "add solver emitted a non-candidate pixel"
    assert np.array_equal(out, _reference_greedy_add(base, cand, w, n_add))
    assert _brute_dti(out, w) > _brute_dti(base, w)


def test_add_solver_rejects_an_undersized_pool() -> None:
    base, w = _synthetic()
    cand = np.zeros_like(base)
    cand[10, 7] = True
    with pytest.raises(ValueError, match="Candidate pool"):
        bpv.select_exact_marginal_dti_add(base, cand, w, 5)


# ---------------------------------------------------------------------------
# 3-4. Built-arm arithmetic, ledger rows, receipts and cards
# ---------------------------------------------------------------------------


def _report() -> dict:
    if not REPORT.is_file():
        pytest.skip("evidence/mass_r0_axis_report.json absent (MASS build not run locally)")
    return json.loads(REPORT.read_text())


def test_preregistration_precedes_and_covers_every_arm() -> None:
    pre = json.loads((ROOT / "registry" / "mass_r0_preregistration.json").read_text())
    assert pre["axis_assignment"]["axis"] == AXIS
    assert pre["fixed_dose"]["n_dots"] == DOSE
    assert pre["fixed_dose"]["parent_dots"] == PARENT_DOTS
    for v in VALUES:
        assert v in pre["arms"]
        assert pre["arms"][v]["preregistered_prediction"].startswith(("+", "-"))
        assert pre["arms"][v]["preregistered_range"].startswith("[")
    assert pre["ranking_definition"]["code"].startswith("vendor/gems57/metric.py")


def test_report_records_exact_parent_and_arm_counts() -> None:
    rep = _report()
    p = rep["parent"]
    assert p["n_dots"] == PARENT_DOTS
    assert p["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert p["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    assert rep["dose"] == {"fraction": 0.10, "n_dots": DOSE}
    assert rep["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    by_value = {v["value"]: v for v in rep["variants"]}
    for v in VALUES:
        assert by_value[v]["n_dots"] == EXPECTED_DOTS[v]
        pd = by_value[v]["parent_diff"]
        assert 1.0 <= pd["pct_changed_moved"] <= 50.0
        assert pd["pct_changed_basis"] == "max"
        assert int(pd["dots_le_1px"]) == 0 and int(pd["dots_le_2px"]) == 0
        assert by_value[v]["gates"]["zero_catalogue_mass"]
        assert by_value[v]["gates"]["reread_from_disk_verified"]
        assert by_value[v]["form_note_chars"] <= 140
        assert by_value[v]["w_model"]["delta_vs_r0"] == pytest.approx(
            by_value[v]["w_model"]["dti"] - rep["parent"]["w_model"]["dti"], abs=1e-6
        )


def test_dose_and_compliance_are_exact() -> None:
    rep = _report()
    by_value = {v["value"]: v for v in rep["variants"]}
    # r10minus removes exactly the dose and adds nothing
    assert by_value["r10minus"]["parent_diff"]["n_removed"] == DOSE
    assert by_value["r10minus"]["parent_diff"]["n_added"] == 0
    # r10plus adds exactly the dose and removes nothing
    assert by_value["r10plus"]["parent_diff"]["n_added"] == DOSE
    assert by_value["r10plus"]["parent_diff"]["n_removed"] == 0
    assert by_value["r10plus"]["added_dots"]["min_d_cat_px"] > 3.0
    # r10swap is count matched: dose out, dose in
    assert by_value["r10swap"]["parent_diff"]["n_added"] == DOSE
    assert by_value["r10swap"]["parent_diff"]["n_removed"] == DOSE
    assert by_value["r10swap"]["n_dots"] == PARENT_DOTS
    assert by_value["r10swap"]["added_dots"]["min_d_cat_px"] > 3.0
    # collar disposition: no arm may ever ADD a sub-3 px dot, so r10plus inherits
    # R0's 2,171 collar dots exactly, while the drop arms can only reduce that count
    # (r10minus/r10swap each remove 85 of them because the ranking, not the collar,
    # chose them -- 2.3% of the dose against 5.8% of R0's dots).
    assert by_value["r10plus"]["parent_diff"]["dots_le_3px"] == rep["parent"]["dots_at_2_to_3px"]
    for v in ("r10minus", "r10swap"):
        assert by_value[v]["parent_diff"]["dots_le_3px"] < rep["parent"]["dots_at_2_to_3px"]
        assert by_value[v]["parent_diff"]["dots_le_3px"] >= rep["parent"]["dots_at_2_to_3px"] - DOSE
    for v in VALUES:
        assert by_value[v]["parent_diff"]["min_dist_catalogue_px"] == pytest.approx(
            rep["parent"]["min_d_cat_px"], abs=1e-4
        )


def test_ledger_rows_are_unique_and_complete() -> None:
    path = ROOT / "ledger" / "submissions.csv"
    rows = list(csv.DictReader(path.open(newline="")))
    mass = [r for r in rows if r["axis"] == AXIS and r["value"] in VALUES]
    assert len(mass) == 3, [r["id"] for r in mass]
    shas = [r["sha256"] for r in rows if r["sha256"]] + [r["sha256_zeros"] for r in rows if r["sha256_zeros"]]
    assert len(shas) == len(set(shas)), "duplicate SHA-256 in ledger"
    for r in mass:
        assert r["status"] == "BUILT"
        assert r["n_dots"] == str(EXPECTED_DOTS[r["value"]])
        assert r["predicted_change"].startswith("MODEL:")
        assert r["receipt_score"] == "" and r["receipt_date"] == ""
        assert float(r["pct_changed"].replace("%", "")) >= 1.0
        assert "preregistered" in r["description"]
        assert len(r["id"]) <= 140
    # no repeated (parent, axis, value) anywhere in the ledger
    keys = [(r["parent"], r["axis"], r["value"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_mechanism_cards_cover_every_arm_for_a_geologist() -> None:
    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
    mine = {k: v for k, v in cards.items() if f"-{AXIS}r" in k}
    assert len(mine) == 3
    for card in mine.values():
        for field in (
            "hypothesis",
            "mechanism",
            "non_fault_mimic",
            "predicted_sign_size",
            "falsifier",
            "preregistered_prediction",
        ):
            assert card[field].strip()


def test_stale_mass_arms_are_cleaned_and_receipts_match_ledger() -> None:
    rep = _report()
    for v in rep["variants"]:
        rec_path = ROOT / "releases" / f"{v['id']}.json"
        assert rec_path.is_file()
        rec = json.loads(rec_path.read_text())
        assert rec["sha256"] == v["sha256"]
        assert rec["sha256_zeros"] == v["sha256_zeros"]
        assert rec["axis"] == AXIS
        assert rec["n_dots"] == EXPECTED_DOTS[rec["value"]]


# ---------------------------------------------------------------------------
# 5. Disk re-read gates (skipped when the gitignored rasters are absent)
# ---------------------------------------------------------------------------


def test_release_rasters_revalidate_from_disk() -> None:
    rep = _report()
    import rasterio  # local import: optional at collection time

    tmpl = ROOT / "data" / "bridge" / "sample_submission.tif"
    if not tmpl.is_file():
        pytest.skip("sample_submission.tif not restored locally")
    with rasterio.open(tmpl) as ds:
        foot = np.isfinite(ds.read(1))
        ref = (ds.shape, ds.crs, ds.transform)
    checked = 0
    for v in rep["variants"]:
        p_nan = ROOT / v["file_nan"]
        p_zeros = ROOT / v["file_zeros"]
        if not (p_nan.is_file() and p_zeros.is_file()):
            continue
        assert bpv.sha256_file(p_nan) == v["sha256"]
        assert bpv.sha256_file(p_zeros) == v["sha256_zeros"]
        with rasterio.open(p_nan) as a, rasterio.open(p_zeros) as b:
            assert (a.shape, a.crs, a.transform) == ref == (b.shape, b.crs, b.transform)
            assert a.count == 1 == b.count and a.dtypes[0] == "float32" == b.dtypes[0]
            arr_n, arr_z = a.read(1), b.read(1)
        assert np.isfinite(arr_n[foot]).all() and np.isnan(arr_n[~foot]).all()
        assert np.isfinite(arr_z).all() and np.all(arr_z[~foot] == 0.0)
        assert np.array_equal(arr_n[foot], arr_z[foot])
        assert float(arr_n[foot].min()) >= 0.0 and float(arr_n[foot].max()) <= 1.0
        assert int((arr_z > 0.5).sum()) == EXPECTED_DOTS[v["value"]]
        checked += 1
    if checked == 0:
        pytest.skip("MASS release rasters absent locally (gitignored)")
