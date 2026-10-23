"""Unit & integration test suite for GEMS v2 AXIS=PRUNE single-axis protocol.

Covers:
1. Exact DTI algebra identity: DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|) vs vendor metric
2. Isolated-pixel marginal gain threshold: strict increase iff credit > 0.2 * DTI
3. Multi-pixel line-like vs isolated gain & Z^2 proof against single-truth shortcut
4. Step-by-step exactness of local-window incremental select_exact_marginal_dti_{add,drop}
   against brute-force full-grid max_cover recomputation
5. Canonical data manifest (schema v2) integrity, licenses, URLs, and public-mirror flagging
6. Byte-exact 5-stage parent R0 (h33-h33-2-b2) lineage rebuild matching both pinned SHA-256s
7. Full disk re-read gates, parent-diff stats, SGMC control, block-density CV, mechanism cards,
   deduplicated historical climb ledger, and <=140-char form notes for all 3 PRUNE variants.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt as edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import metric  # noqa: E402
from scripts import build_prune_variants as bpv  # noqa: E402


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _brute_expected_dti(mask: np.ndarray, w: np.ndarray) -> float:
    return float(bpv.weighted_expected_dti(mask, w)["dti"])


def _brute_greedy_add(base: np.ndarray, cand: np.ndarray, w: np.ndarray, n_add: int) -> np.ndarray:
    state = base.copy()
    cy, cx = np.nonzero(cand & ~state)
    for _ in range(n_add):
        best_score = -1.0
        best_pt = None
        for y, x in zip(cy.tolist(), cx.tolist()):
            if state[y, x]:
                continue
            state[y, x] = True
            sc = _brute_expected_dti(state, w)
            state[y, x] = False
            if sc > best_score:
                best_score = sc
                best_pt = (y, x)
        assert best_pt is not None
        state[best_pt[0], best_pt[1]] = True
    return state


def _brute_greedy_drop(base: np.ndarray, pool: np.ndarray, w: np.ndarray, n_drop: int) -> np.ndarray:
    state = base.copy()
    py, px = np.nonzero(state & pool)
    for _ in range(n_drop):
        best_score = -1.0
        best_pt = None
        for y, x in zip(py.tolist(), px.tolist()):
            if not state[y, x]:
                continue
            state[y, x] = False
            sc = _brute_expected_dti(state, w)
            state[y, x] = True
            if sc > best_score:
                best_score = sc
                best_pt = (y, x)
        assert best_pt is not None
        state[best_pt[0], best_pt[1]] = False
    return state


def test_dti_algebra_matches_vendor_metric_exact_and_binary():
    """Verify DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|) matches gems57.metric to 1e-12."""
    rng = np.random.default_rng(20261023)
    foot = np.ones((40, 44), dtype=bool)
    known = np.zeros_like(foot)
    known[5, :] = True

    truth = np.zeros_like(foot)
    truth[14, 8:34] = True  # line-like fault segment
    truth[28, 20] = True    # isolated truth pixel
    truth &= ~known

    pred_mask = rng.random(foot.shape) < 0.04
    pred_mask &= ~known

    v_bin = metric.dti_binary(pred_mask, truth, foot, known)
    v_ex = metric.dti_exact(pred_mask.astype(np.float32), truth, foot, known)
    alg = bpv.dti_algebra_components(pred_mask, truth)

    # S == number of unit dots, G == number of truth pixels
    assert alg["S"] == float(pred_mask.sum())
    assert alg["G"] == float(truth.sum())
    assert abs(alg["dti"] - v_bin["dti"]) < 1e-12
    assert abs(alg["dti"] - v_ex["dti"]) < 1e-12
    assert abs(alg["T"] - v_bin["tp"]) < 1e-9
    assert abs((alg["S"] - alg["M"]) - v_bin["fp"]) < 1e-9
    assert abs((alg["G"] - alg["T"]) - v_bin["fn"]) < 1e-9


def test_isolated_pixel_threshold_is_strictly_0p2_times_dti():
    """Isolated unit-mass pixel with self-cover k increases DTI iff k > 0.2 * DTI."""
    # Construct continuous truth weights on an empty background with known initial DTI = 0.28
    # Choose T0 = 2.8, S0 - M0 = 6.0, W_tot = 10.0 => Den = 0.56 + 1.20 + 8.00 = 9.76? Wait:
    # For DTI_0 = 0.28 exactly: T0 / (0.2*T0 + 0.2*(S0-M0) + 0.8*W) = 0.28.
    # Let W = 10.0, T0 = 2.8, and set S0 - M0 = (2.8/0.28 - 0.2*2.8 - 8.0)/0.2 = 7.20 -> exact DTI = 0.28!
    w = np.zeros((30, 30), dtype=np.float64)
    pred = np.zeros((30, 30), dtype=bool)
    # Place 3 truth pixels hit identically at distance 0 (T0 = 2.8, M0 = 2.8) + 7.2 uncovered truth weight
    w[4, 4] = 2.8
    pred[4, 4] = True  # contributes T=2.8, S=1, M=1? Wait: in weighted_expected_dti M = sum_x max_g w(g)k(x,g) = 2.8 -> S-M = -1.8
    # Add 9 pure-false-positive dots in empty space so S - M = -1.8 + 9.0 = 7.2 => Den = 0.56 + 1.44 + 8.00 = 10.00!
    for c in range(10, 19):
        pred[25, c] = True
    w[4, 20] = 7.2  # far uncovered truth weight -> W_tot = 10.0, T0 = 2.8, Den = 10.0 => DTI_0 = 0.280000000000!

    base = bpv.weighted_expected_dti(pred, w)
    assert abs(base["dti"] - 0.28) < 1e-11
    threshold = 0.2 * base["dti"]  # 0.056 exactly

    # Case 1: isolated dot at (15, 15) with truth weight w_iso = 0.0559 < 0.056 MUST DECREASE DTI
    w_below = w.copy()
    w_below[15, 15] = threshold - 5e-4
    dti_before_below = bpv.weighted_expected_dti(pred, w_below)["dti"]
    pred_plus = pred.copy()
    pred_plus[15, 15] = True
    dti_after_below = bpv.weighted_expected_dti(pred_plus, w_below)["dti"]
    assert dti_after_below < dti_before_below

    # Case 2: isolated dot at (15, 15) with truth weight w_iso = 0.0565 > 0.056 MUST INCREASE DTI
    w_above = w.copy()
    w_above[15, 15] = threshold + 5e-4
    dti_before_above = bpv.weighted_expected_dti(pred, w_above)["dti"]
    dti_after_above = bpv.weighted_expected_dti(pred_plus, w_above)["dti"]
    assert dti_after_above > dti_before_above


def test_line_like_vs_isolated_gain_and_z2_shortcut_counterexample():
    """Prove line-like multi-pixel traces earn higher marginal DTI per dot & beat single-truth shortcut."""
    # Analytic Z^2 proof at DTI_0 = 0.30:
    # Truth pixels at (10-2, 10+2)=(8,12) and (10+2, 10+2)=(12,12) around candidate x=(10,10).
    # Each has Euclidean distance sqrt(8), so per-pixel kernel weight is k0 = 1 - sqrt(8)/3 ~= 0.05719096 < 0.06 = 0.2*0.30!
    # An isolated pixel at distance sqrt(8) LOSES DTI (0.05719 < 0.060),
    # whereas the 2-pixel fault strand GAINS +0.114382 TP for only (1 - 0.057191) = 0.942809 FP, INCREASING DTI!
    pred = np.zeros((32, 32), dtype=bool)
    truth_base = np.zeros((32, 32), dtype=bool)

    # Set baseline with 4 exact d=0 hits + 4 pure FPs + 12 base truth pixels:
    # With +1 truth pixel (|G|=13): Den = 0.8 + 0.8 + 0.8*13 = 12.0 => DTI = 4/12 = 0.3333 (0.2*DTI = 0.0667 > 0.05719)
    # With +2 truth pixels (|G|=14): Den = 0.8 + 0.8 + 0.8*14 = 12.8 => DTI = 4/12.8 = 0.3125 (0.2*DTI = 0.0625 > 0.05719)
    for k in range(4):
        truth_base[2, 2 + 3 * k] = True
        pred[2, 2 + 3 * k] = True
    for k in range(8):
        truth_base[2, 15 + 2 * k] = True
    for k in range(4):
        pred[28, 2 + 4 * k] = True

    # Add 1 isolated truth pixel at (8, 12): candidate (10, 10) has d=sqrt(8), k_self=0.05719 < 0.2*DTI -> DECREASES DTI
    truth_iso = truth_base.copy()
    truth_iso[8, 12] = True
    dti_iso_before = bpv.dti_algebra_components(pred, truth_iso)["dti"]
    pred_cand = pred.copy()
    pred_cand[10, 10] = True
    dti_iso_after = bpv.dti_algebra_components(pred_cand, truth_iso)["dti"]
    assert dti_iso_after < dti_iso_before, "Isolated distant truth pixel below 0.2*DTI must reduce DTI"

    # Now add a second colinear fault-strand pixel at (12, 12) (still k_self = 0.05719 < 0.2*DTI!):
    # Single-truth shortcut max_g k(x, g) = 0.05719 < 0.2 * dti_line_before STILL rejects (10, 10),
    # YET true multi-pixel DTI STRICTLY INCREASES!
    truth_line = truth_iso.copy()
    truth_line[12, 12] = True
    dti_line_before = bpv.dti_algebra_components(pred, truth_line)["dti"]
    dti_line_after = bpv.dti_algebra_components(pred_cand, truth_line)["dti"]
    k_self = 1.0 - (8.0**0.5) / 3.0
    assert k_self < 0.2 * dti_line_before, "Per-pixel self-cover must sit strictly below 0.2 * DTI shortcut"
    assert dti_line_after > dti_line_before, "Multi-pixel fault trace must strictly increase true DTI"


def test_incremental_exact_marginal_add_and_drop_match_bruteforce_oracle():
    """Verify fast 6-px local-window add/drop solvers match full-grid brute-force step-by-step."""
    rng = np.random.default_rng(88)
    w = rng.uniform(0.0, 0.25, size=(22, 24)).astype(np.float32)
    base = rng.random((22, 24)) < 0.05
    cand = (rng.random((22, 24)) < 0.09) & ~base

    fast_added = bpv.select_exact_marginal_dti_add(base, cand, w, n_add=8)
    brute_added = _brute_greedy_add(base, cand, w, n_add=8)
    assert np.array_equal(fast_added, brute_added)

    pool = rng.random((22, 24)) < 0.70
    fast_dropped = bpv.select_exact_marginal_dti_drop(fast_added, pool, w, n_drop=6)
    brute_dropped = _brute_greedy_drop(fast_added, pool, w, n_drop=6)
    assert np.array_equal(fast_dropped, brute_dropped)


def test_manifest_v2_integrity_and_byte_exact_parent_r0_rebuild():
    """Verify manifest metadata and bit-for-bit 5-stage parent R0 lineage reconstruction."""
    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    assert manifest["schema_version"] == 2
    assert len(manifest["files"]) == 15
    assert manifest["public_mirror_flag"]["status"] == "FLAGGED_DATA_USE_UNCHECKED"

    by_id = {entry["id"]: ROOT / entry["local_path"] for entry in manifest["files"]}
    for entry in manifest["files"]:
        assert entry["source_url"].startswith("https://")
        assert len(entry["license"]) > 3
        p = ROOT / entry["local_path"]
        if p.is_file():
            assert bpv.sha256_file(p) == entry["sha256"]
            assert p.stat().st_size == entry["bytes"]

    reb = bpv.rebuild_r0_from_lineage(by_id)
    r0_mask = reb["r0"]
    d_cat = reb["d_cat"]
    solo_d28 = reb["solo"]
    assert reb["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert reb["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    assert int(r0_mask.sum()) == 37_654
    assert int((r0_mask & (d_cat <= 2.0)).sum()) == 0
    assert int((solo_d28 & (d_cat > 1.0) & (d_cat <= 2.0)).sum()) == 2_545
    assert int((r0_mask & (d_cat <= 3.0)).sum()) == 2_171
    assert int((r0_mask & (d_cat <= 4.0)).sum()) == 3_825


def test_emitted_prune_variants_pass_all_must_gates_and_ledger_invariants():
    """Re-open all 6 GeoTIFFs + 6 zips from disk and verify every MUST gate & diagnostic."""
    report = json.loads((ROOT / "evidence" / "prune_axis_report.json").read_text())
    assert report["axis"] == "PRUNE"
    assert report["leakage_canaries"]["passed"] is True
    assert report["leakage_canaries"]["max_symmetric_auc"] <= 0.90

    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds_tmpl:
        tmpl_crs = ds_tmpl.crs
        tmpl_transform = ds_tmpl.transform
        tmpl_shape = (ds_tmpl.height, ds_tmpl.width)
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ds_ef:
        ef = ds_ef.read(1)
    foot = np.isfinite(ef) & ((ef == 0) | (ef == 1))
    catalogue = foot & (ef == 1)
    d_cat = edt(~catalogue)

    with rasterio.open(ROOT / "data" / "registry" / "h33_education.tif") as ds_r0:
        r0_mask = (ds_r0.read(1) > 0.5) & foot

    with rasterio.open(ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif") as ds_sgmc:
        sgmc_truth = (
            (ds_sgmc.read(1) > 0)
            & foot
            & ~catalogue
            & ~binary_dilation(catalogue, iterations=3)
        )

    # Check ledger uniqueness & schema
    with (ROOT / "ledger" / "submissions.csv").open("r", newline="", encoding="utf-8") as f:
        sub_rows = list(csv.DictReader(f))
    shas = [r["sha256"] for r in sub_rows]
    shas_z = [r["sha256_zeros"] for r in sub_rows]
    assert len(shas) == len(set(shas)), "Duplicate primary SHA-256 in ledger/submissions.csv!"
    assert len(shas_z) == len(set(shas_z)), "Duplicate fallback SHA-256 in ledger/submissions.csv!"

    # Check deduplicated historical climb ledger
    with (ROOT / "ledger" / "historical_climb.csv").open("r", newline="", encoding="utf-8") as f:
        hist_rows = list(csv.DictReader(f))
    hist_shas = [r["sha8"] for r in hist_rows]
    assert len(hist_shas) == len(set(hist_shas)), "Exact repeat left in ledger/historical_climb.csv!"

    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())

    expected_specs = {
        "p1px": (2545, 6.76, 1.0, 2545),
        "p3px": (2171, 5.77, 3.0, 0),
        "p4px": (3825, 10.16, 4.0, 0),
    }

    for v in report["variants"]:
        val = v["value"]
        exp_n_moved, exp_pct, min_collar_strict, exp_le_2px = expected_specs[val]
        assert v["axis"] == "PRUNE"
        assert v["n_dots"] == 37_654
        assert v["parent_diff"]["n_added"] == exp_n_moved
        assert v["parent_diff"]["n_removed"] == exp_n_moved
        assert v["parent_diff"]["pct_changed_moved"] == pytest.approx(exp_pct, abs=0.01)
        assert 1.0 <= v["parent_diff"]["pct_changed_moved"] <= 50.0
        assert len(v["form_note"]) <= 140

        # Mechanism card completeness check
        card = cards[v["id"]]
        for req_field in (
            "hypothesis",
            "mechanism",
            "non_fault_mimic",
            "predicted_sign_size",
            "falsifier",
        ):
            assert req_field in card and card[req_field]
        assert "MODEL" in card["predicted_sign_size"]
        assert card.get("references") and all(
            item.get("url", "").startswith("https://") for item in card["references"]
        )

        p_nan = ROOT / v["file_nan"]
        p_zeros = ROOT / v["file_zeros"]
        z_nan = ROOT / v["zip_nan"]
        z_zeros = ROOT / v["zip_zeros"]

        # Verify tracked JSON receipt in releases/ always
        rec_path = ROOT / "releases" / f"{v['id']}.json"
        assert rec_path.is_file()
        rec = json.loads(rec_path.read_text())
        assert rec["sha256"] == v["sha256"]
        assert rec["sha256_zeros"] == v["sha256_zeros"]

        # Re-read local rasters/zips from disk whenever present (gitignored in CI per data-use flag)
        if not (p_nan.is_file() and p_zeros.is_file()):
            continue

        assert bpv.sha256_file(p_nan) == v["sha256"]
        assert bpv.sha256_file(p_zeros) == v["sha256_zeros"]
        with zipfile.ZipFile(z_nan) as zf:
            assert _sha256_bytes(zf.read(p_nan.name)) == v["sha256"]
        with zipfile.ZipFile(z_zeros) as zf:
            assert _sha256_bytes(zf.read(p_zeros.name)) == v["sha256_zeros"]

        with rasterio.open(p_nan) as ds_n, rasterio.open(p_zeros) as ds_z:
            assert ds_n.crs == tmpl_crs == ds_z.crs
            assert (ds_n.height, ds_n.width) == tmpl_shape == (ds_z.height, ds_z.width)
            assert ds_n.transform == tmpl_transform == ds_z.transform
            assert ds_n.count == 1 == ds_z.count
            assert ds_n.dtypes[0] == "float32" == ds_z.dtypes[0]
            arr_n = ds_n.read(1)
            arr_z = ds_z.read(1)

        assert not np.any(np.isnan(arr_n[foot]))
        assert np.all(np.isnan(arr_n[~foot]))
        assert np.all(np.isfinite(arr_z))
        assert np.all(arr_z[~foot] == 0.0)
        assert np.array_equal(arr_n[foot], arr_z[foot])
        assert float(arr_n[foot].min()) >= 0.0 and float(arr_n[foot].max()) <= 1.0

        mask = arr_z > 0.5
        assert int(mask.sum()) == 37_654
        assert int((mask & catalogue).sum()) == 0
        assert float(d_cat[mask].min()) > min_collar_strict
        assert int((mask & (d_cat <= 2.0)).sum()) == exp_le_2px
        assert int((mask & ~r0_mask).sum()) == exp_n_moved
        assert int((r0_mask & ~mask).sum()) == exp_n_moved

        # Re-verify SGMC control independently on disk raster
        sgmc_res = metric.dti_binary(mask, sgmc_truth, foot, catalogue)
        assert sgmc_res["dti"] == pytest.approx(
            v["report_only_diagnostics"]["sgmc_control"]["dti"], abs=1e-5
        )
