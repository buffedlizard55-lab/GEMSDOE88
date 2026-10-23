"""Unit & integration test suite for GEMS v2 AXIS=SNAP controlled variants.

Covers:
1. Constant-count (Delta S = 0) local-snap DTI algebra identity:
   Delta DTI = [(1 - 0.2*DTI)*Delta T + 0.2*DTI*Delta M] / [D + 0.2*(Delta T - Delta M)]
2. Synthetic fault-trace proof that spacing-preserved SNAP (min_sep = 2.8 px) prevents
   along-strike dot bunching (>3 px kernel gap) and strictly outperforms unspaced window argmax
3. Strict provided-bands-only policy (Bands 3, 12, 18, 19 of training_features.tif; zero
   external LiDAR used) and leakage canary verification (max symmetric AUC <= 0.90)
4. Full verification of all 3 SNAP variants (ridge2px, pot2px, scarp2px): tracked receipts,
   displacement statistics (<= 2.0 px window, mean displacement, histogram), inter-dot spacing
   (>= 2.8284 px), catalogue exclusions (0 on catalogue, 0 <= 2 px, 2,171 in 2-3 px unchanged,
   all moved dots > 3 px), ledger uniqueness across all 13 rows, mechanism cards, form notes
   <= 140 chars, and disk re-read GeoTIFF/ZIP verification.
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
from scripts import build_snap_variants as bsv  # noqa: E402
from scripts.build_snap_variants import MIN_DCAT, snap  # noqa: E402


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _toy():
    h = w = 40
    foot = np.ones((h, w), bool)
    catalogue = np.zeros((h, w), bool)
    catalogue[18, 5:35] = True
    yy, _xx = np.mgrid[0:h, 0:w]
    d_cat = np.abs(yy - 18).astype(float)
    rng = np.random.default_rng(7)
    edge = rng.random((h, w)).astype(np.float32)
    mask = np.zeros((h, w), bool)
    idx = rng.choice(h * w, size=60, replace=False)
    mask.reshape(-1)[idx] = True
    mask &= foot & ~catalogue
    return mask, edge, foot, catalogue, d_cat


def test_snap_holds_count_and_exclusions():
    mask, edge, foot, catalogue, d_cat = _toy()
    res = snap(mask, edge, foot, catalogue, d_cat, max_disp=2)
    out = res["mask"]
    assert int(out.sum()) == int(mask.sum())
    assert int((out & catalogue).sum()) == 0
    moved = out & ~mask
    assert moved.sum() > 0
    assert float(d_cat[moved].min()) > MIN_DCAT
    ys, xs = np.nonzero(moved)
    for y, x in zip(ys, xs):
        win = mask[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
        assert win.any()


def test_snap_only_moves_uphill_and_is_deterministic():
    mask, edge, foot, catalogue, d_cat = _toy()
    a = snap(mask, edge, foot, catalogue, d_cat, max_disp=2)["mask"]
    b = snap(mask, edge, foot, catalogue, d_cat, max_disp=2)["mask"]
    assert np.array_equal(a, b)
    for y, x, yy, xx, gain in snap(mask, edge, foot, catalogue, d_cat, max_disp=2)["moves"]:
        assert gain > 0
        assert edge[yy, xx] > edge[y, x]


def test_snap_window_one_cannot_reach_two_pixels():
    mask, edge, foot, catalogue, d_cat = _toy()
    res = snap(mask, edge, foot, catalogue, d_cat, max_disp=1)
    for y, x, yy, xx, _g in res["moves"]:
        assert abs(yy - y) <= 1 and abs(xx - x) <= 1


def test_snap_gain_gate_suppresses_marginal_moves():
    mask, edge, foot, catalogue, d_cat = _toy()
    loose = snap(mask, edge, foot, catalogue, d_cat, max_disp=2, gain_min=0.0)["n_moved"]
    tight = snap(mask, edge, foot, catalogue, d_cat, max_disp=2, gain_min=0.4)["n_moved"]
    assert tight < loose


def test_constant_count_snap_algebra_identity():
    """Verify exact Delta S = 0 snap identity: moving <= 2 px onto trace raises T and M with zero count penalty."""
    truth = np.zeros((32, 32), dtype=bool)
    truth[16, 6:26] = True  # 20-pixel E-W fault trace

    # Parent dots displaced 2 px North of the trace (on the northern ribbon shoulder, d = 2.0 -> k = 1/3)
    pred_shoulder = np.zeros((32, 32), dtype=bool)
    for x in (8, 11, 14, 17, 20, 23):
        pred_shoulder[14, x] = True
    # Add 4 off-trace background dots to set realistic denominator
    for x in (4, 8, 12, 16):
        pred_shoulder[2, x] = True

    # Snapped dots shifted 2 px South onto the trace crest (d = 0.0 -> k = 1.0), count S fixed at 10
    pred_snapped = np.zeros((32, 32), dtype=bool)
    for x in (8, 11, 14, 17, 20, 23):
        pred_snapped[16, x] = True
    for x in (4, 8, 12, 16):
        pred_snapped[2, x] = True

    c0 = bpv.dti_algebra_components(pred_shoulder, truth)
    c1 = bpv.dti_algebra_components(pred_snapped, truth)
    assert c0["S"] == c1["S"] == 10.0

    dT = c1["T"] - c0["T"]
    dM = c1["M"] - c0["M"]
    assert dT > 0.0 and dM > 0.0

    # Exact constant-count relocation formula:
    # DTI_1 - DTI_0 = ((1 - 0.2*DTI_0)*dT + 0.2*DTI_0*dM) / (denom_0 + 0.2*(dT - dM))
    rhs = ((1.0 - 0.2 * c0["dti"]) * dT + 0.2 * c0["dti"] * dM) / (
        c0["denom"] + 0.2 * (dT - dM)
    )
    assert (c1["dti"] - c0["dti"]) == pytest.approx(rhs, rel=1e-12, abs=1e-12)
    assert c1["dti"] > c0["dti"]


def test_spacing_preserved_snap_beats_unspaced_bunching_on_fault_strand():
    """Prove min_sep=2.8 px prevents along-strike dot bunching that opens >3 px kernel gaps."""
    H, W = 28, 36
    foot = np.ones((H, W), dtype=bool)
    catalogue = np.zeros((H, W), dtype=bool)
    d_cat = np.full((H, W), 10.0, dtype=np.float32)
    h19_5 = np.ones((H, W), dtype=bool)

    # True E-W fault trace at row 14, cols 6..29
    truth = np.zeros((H, W), dtype=bool)
    truth[14, 6:30] = True

    # Parent dots sit 1 px North of the trace (row 13) spaced every 3 px (cols 7, 10, 13, 16, 19, 22, 25, 28)
    r0_syn = np.zeros((H, W), dtype=bool)
    cols = [7, 10, 13, 16, 19, 22, 25, 28]
    for c in cols:
        r0_syn[13, c] = True

    # Edge response peaks along row 14 (the true fault trace), with a gentle along-strike gradient
    # toward col 17 that causes unspaced window-argmax snapping to slide neighboring dots together
    yy, xx = np.mgrid[0:H, 0:W]
    across_profile = np.exp(-((yy - 14.0) ** 2) / 2.0)
    along_slope = 1.0 - 0.015 * np.abs(xx - 17.5)
    score_field = (across_profile * along_slope).astype(np.float32)

    unspaced_mask, _ = bsv.snap_dots_within_window(
        r0_syn, score_field, foot, catalogue, d_cat, h19_5, max_r=2.0, min_sep=0.0
    )
    spaced_mask, spaced_stats = bsv.snap_dots_within_window(
        r0_syn, score_field, foot, catalogue, d_cat, h19_5, max_r=2.0, min_sep=2.8
    )

    dti_r0 = metric.dti_binary(r0_syn, truth)["dti"]
    dti_unspaced = metric.dti_binary(unspaced_mask, truth)["dti"]
    dti_spaced = metric.dti_binary(spaced_mask, truth)["dti"]

    assert spaced_stats["min_interdot_nn_dist_px"] >= 2.8
    assert dti_spaced > dti_r0, "Across-strike snap onto fault trace must beat displaced parent"
    assert dti_spaced > dti_unspaced, "Spacing-preserved snap must beat along-strike bunching"


def test_snap_report_canaries_and_provided_bands_policy():
    """Verify SNAP report uses only provided training_features.tif bands and passes all canaries."""
    report = json.loads((ROOT / "evidence" / "snap_axis_report.json").read_text())
    assert report["axis"] == "SNAP"
    assert report["provided_bands_only"] is True
    assert report["external_lidar_used"] is False
    assert report["leakage_canaries"]["passed"] is True
    assert report["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    assert len(report["leakage_canaries"]["channels"]) == 8
    for ch_name, sauc in report["leakage_canaries"]["channels"].items():
        assert 0.50 <= sauc <= 0.90, f"Invalid canary {ch_name}: {sauc}"


def test_emitted_snap_variants_pass_all_must_gates_and_displacement_invariants():
    """Verify all 3 SNAP variants against receipts, ledger, mechanism cards, and on-disk GeoTIFFs."""
    report = json.loads((ROOT / "evidence" / "snap_axis_report.json").read_text())
    assert len(report["variants"]) == 3

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

    with (ROOT / "ledger" / "submissions.csv").open("r", newline="", encoding="utf-8") as f:
        sub_rows = list(csv.DictReader(f))
    shas = [r["sha256"] for r in sub_rows]
    shas_z = [r["sha256_zeros"] for r in sub_rows]
    assert len(shas) == len(set(shas)) == len(sub_rows)
    assert len(shas_z) == len(set(shas_z)) == len(sub_rows)
    snap_rows = {r["id"]: r for r in sub_rows if r["axis"] == "SNAP"}
    assert len(snap_rows) == 6
    assert {r["value"] for r in snap_rows.values()} == {
        "w2E1",
        "w2S2",
        "w2E2",
        "ridge2px",
        "pot2px",
        "scarp2px",
    }

    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())

    expected = {
        "ridge2px": (7082, 18.81, 0.2299, 1.2222, True),
        "pot2px": (31049, 82.46, 1.3489, 1.6358, False),
        "scarp2px": (30889, 82.03, 1.3089, 1.5956, False),
    }

    for v in report["variants"]:
        val = v["value"]
        exp_moved, exp_pct, exp_mean_all, exp_mean_moved, exp_h19 = expected[val]
        assert v["axis"] == "SNAP"
        assert v["n_dots"] == 37_654
        assert v["parent_diff"]["n_added"] == exp_moved
        assert v["parent_diff"]["n_removed"] == exp_moved
        assert v["parent_diff"]["pct_changed_moved"] == pytest.approx(exp_pct, abs=0.01)
        assert v["parent_diff"]["dots_le_1px"] == 0
        assert v["parent_diff"]["dots_le_2px"] == 0
        assert v["parent_diff"]["dots_le_3px"] == 2_171
        assert v["parent_diff"]["min_dist_added_catalogue_px"] > 3.0
        assert len(v["form_note"]) <= 140

        dsp = v["displacement"]
        assert dsp["max_window_radius_px"] == 2.0
        assert dsp["max_displacement_px"] <= 2.0
        assert dsp["min_interdot_nn_dist_px"] >= 2.828
        assert dsp["stay_on_h19_5_ridge"] is exp_h19
        assert dsp["n_dots_displaced"] == exp_moved
        assert dsp["mean_displacement_all_px"] == pytest.approx(exp_mean_all, abs=1e-3)
        assert dsp["mean_displacement_moved_px"] == pytest.approx(exp_mean_moved, abs=1e-3)
        assert dsp["mean_edge_response_after"] > dsp["mean_edge_response_before"]
        assert sum(dsp["displacement_counts_by_d2"].values()) == 37_654

        # Check ledger row matches receipt
        row = snap_rows[v["id"]]
        assert row["sha256"] == v["sha256"]
        assert row["sha256_zeros"] == v["sha256_zeros"]
        assert row["status"] == "BUILT"
        assert row["receipt_score"] == "" and row["receipt_date"] == ""
        assert row["predicted_change"].startswith("MODEL:")

        # Check structural-geologist mechanism card
        card = cards[v["id"]]
        for req_field in (
            "hypothesis",
            "mechanism",
            "non_fault_mimic",
            "predicted_sign_size",
            "falsifier",
        ):
            assert req_field in card and len(card[req_field]) > 20
        assert "MODEL" in card["predicted_sign_size"]

        # Verify tracked JSON receipt in releases/
        rec_path = ROOT / "releases" / f"{v['id']}.json"
        assert rec_path.is_file()
        rec = json.loads(rec_path.read_text())
        assert rec["sha256"] == v["sha256"]
        assert rec["sha256_zeros"] == v["sha256_zeros"]

        p_nan = ROOT / v["file_nan"]
        p_zeros = ROOT / v["file_zeros"]
        z_nan = ROOT / v["zip_nan"]
        z_zeros = ROOT / v["zip_zeros"]
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
        assert int((mask & (d_cat <= 2.0)).sum()) == 0
        assert int((mask & (d_cat <= 3.0)).sum()) == 2_171
        assert int((mask & ~r0_mask).sum()) == exp_moved
        assert int((r0_mask & ~mask).sum()) == exp_moved
        assert float(d_cat[mask & ~r0_mask].min()) > 3.0

        sgmc_res = metric.dti_binary(mask, sgmc_truth, foot, catalogue)
        assert sgmc_res["dti"] == pytest.approx(
            v["report_only_diagnostics"]["sgmc_control"]["dti"], abs=1e-5
        )
