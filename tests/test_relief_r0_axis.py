"""Unit & integration tests for the AXIS=RELIEF controlled variants of R0 (h33-h33-2-b2).

Covers:
1. Pure helpers: sentinel sanitisation, area terciles, proportional donor split (largest remainder).
2. Synthetic end-to-end build_relief_variant: count fixed, donors only from donor terciles and never
   from the frozen collar, adds only on un-emitted ridge pixels inside the receiver tercile at
   d_cat > 3 px, deterministic.
3. Tracked evidence: evidence/relief_r0_axis_report.json, releases/*.json receipts, ledger rows,
   mechanism cards, pre-registration file; on-disk GeoTIFF/ZIP re-read when the untracked rasters
   are present locally (skipped otherwise, e.g. in CI with --validation restore only).
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402
from scripts import build_relief_r0_variants as brv  # noqa: E402

REPORT = ROOT / "evidence" / "relief_r0_axis_report.json"
VALUES = {"basin12", "pied12", "range12"}


# ---------------------------------------------------------------------------
# 1. Pure helpers
# ---------------------------------------------------------------------------


def test_sanitize_band_replaces_sentinels_with_footprint_median():
    foot = np.ones((4, 4), dtype=bool)
    foot[0, 0] = False
    arr = np.arange(16, dtype=np.float32).reshape(4, 4)
    arr[1, 1] = -3.4028235e38
    arr[2, 2] = np.nan
    out, n_bad = brv.sanitize_band(arr, foot)
    assert n_bad == 2
    good = foot.copy()
    good[1, 1] = good[2, 2] = False
    med = float(np.median(arr[good]))
    assert out[1, 1] == med and out[2, 2] == med
    assert out[0, 0] == 0.0
    assert np.isfinite(out).all()


def test_relief_terciles_split_footprint_into_equal_area_classes():
    rng = np.random.default_rng(3)
    foot = np.ones((60, 60), dtype=bool)
    foot[:5, :] = False
    det = rng.normal(0.0, 100.0, size=(60, 60))
    cls, (lo, hi) = brv.relief_terciles(det, foot)
    assert lo < hi
    assert set(np.unique(cls[~foot])) == {0}
    n = int(foot.sum())
    counts = [int((cls == k).sum()) for k in (1, 2, 3)]
    assert sum(counts) == n
    for c in counts:
        assert abs(c - n / 3) <= 2
    assert det[cls == 1].max() <= lo + 1e-9
    assert det[cls == 3].min() >= hi - 1e-9


def test_proportional_donor_counts_largest_remainder():
    counts = brv.proportional_donor_counts(100, {1: 300, 2: 100, 3: 600}, (1, 3))
    assert counts == {1: 33, 3: 67}
    counts = brv.proportional_donor_counts(7, {1: 5, 2: 5, 3: 1}, (1, 2))
    assert sum(counts.values()) == 7 and sorted(counts.values()) == [3, 4]
    with pytest.raises(ValueError):
        brv.proportional_donor_counts(10, {1: 4, 2: 4, 3: 4}, (1, 2))


# ---------------------------------------------------------------------------
# 2. Synthetic end-to-end variant build
# ---------------------------------------------------------------------------


def _synthetic():
    H, W = 60, 90
    foot = np.ones((H, W), dtype=bool)
    yy, xx = np.mgrid[0:H, 0:W]
    det = (xx - W / 2).astype(float) * 10.0  # three vertical bands: basin | piedmont | range
    cls, _ = brv.relief_terciles(det, foot)
    catalogue = np.zeros((H, W), dtype=bool)
    catalogue[30, :] = True  # one known E-W fault
    from scipy.ndimage import distance_transform_edt

    d_cat = distance_transform_edt(~catalogue)
    # ridge support: horizontal ribbons every 6 rows, 2 px thick
    h19 = np.zeros((H, W), dtype=bool)
    for r in range(3, H, 6):
        h19[r : r + 2, :] = True
    # parent: dots every 3 columns on the first ribbon row, excluding d_cat <= 2
    r0 = np.zeros((H, W), dtype=bool)
    r0[3::6, ::3] = True
    r0 &= h19 & (d_cat > 2.0)
    rng = np.random.default_rng(11)
    w = np.where(h19, 0.05 + 0.2 * rng.random((H, W)), 0.001).astype(np.float32)
    w[catalogue] = 0.0
    return foot, cls, catalogue, d_cat, h19, r0, w


def test_build_relief_variant_invariants_and_determinism():
    foot, cls, catalogue, d_cat, h19, r0, w = _synthetic()
    n_move = int(round(0.12 * r0.sum()))
    out, st = brv.build_relief_variant(
        r0, cls, 3, (1, 2), n_move, w_field=w, h19_5=h19, foot=foot, catalogue=catalogue, d_cat=d_cat
    )
    out2, _ = brv.build_relief_variant(
        r0, cls, 3, (1, 2), n_move, w_field=w, h19_5=h19, foot=foot, catalogue=catalogue, d_cat=d_cat
    )
    assert np.array_equal(out, out2)
    assert int(out.sum()) == int(r0.sum())
    removed = r0 & ~out
    added = out & ~r0
    assert int(removed.sum()) == int(added.sum()) == n_move
    assert st["n_move"] == n_move and st["receiver"] == "range"
    # donors only from donor terciles and never from the frozen collar
    assert not np.any(removed & (cls == 3))
    assert not np.any(removed & (d_cat <= 3.0))
    assert sum(st["donor_counts"].values()) == n_move
    # adds only on un-emitted ridge pixels in the receiver tercile, off catalogue, > 3 px from it
    assert np.all(cls[added] == 3)
    assert np.all(h19[added])
    assert not np.any(added & catalogue)
    assert float(d_cat[added].min()) > 3.0
    # collar dots unchanged and tercile shares move the right way
    assert np.array_equal(out & (d_cat <= 3.0), r0 & (d_cat <= 3.0))
    assert st["shares_after"]["range"]["n_dots"] == st["shares_before"]["range"]["n_dots"] + n_move
    assert st["shares_after"]["basin"]["n_dots"] + st["shares_after"]["piedmont"]["n_dots"] == (
        st["shares_before"]["basin"]["n_dots"] + st["shares_before"]["piedmont"]["n_dots"] - n_move
    )


def test_constant_count_relief_shift_is_pure_relocation_in_dti_algebra():
    """At fixed S, DTI change is set only by Delta T and Delta M (no mass term)."""
    truth = np.zeros((40, 40), dtype=bool)
    truth[20, 5:35] = True
    a = np.zeros((40, 40), dtype=bool)
    a[20, 8:32:3] = True  # 8 dots on the trace
    a[5, 4:28:3] = True  # 8 dots far away (no credit)
    b = a.copy()
    b[5, 4:10:3] = False  # move 2 far dots onto the trace
    b[20, 9] = True
    b[20, 30] = True
    ca = bpv.dti_algebra_components(a, truth)
    cb = bpv.dti_algebra_components(b, truth)
    assert ca["S"] == cb["S"]
    dT, dM = cb["T"] - ca["T"], cb["M"] - ca["M"]
    rhs = ((1.0 - 0.2 * ca["dti"]) * dT + 0.2 * ca["dti"] * dM) / (ca["denom"] + 0.2 * (dT - dM))
    assert (cb["dti"] - ca["dti"]) == pytest.approx(rhs, rel=1e-12, abs=1e-12)


# ---------------------------------------------------------------------------
# 3. Tracked evidence & ledger
# ---------------------------------------------------------------------------


def _report():
    if not REPORT.is_file():
        pytest.skip("evidence/relief_r0_axis_report.json not present")
    return json.loads(REPORT.read_text())


def test_relief_report_design_and_canaries():
    rep = _report()
    assert rep["axis"] == "RELIEF"
    assert rep["dose_pct"] == 12.0
    assert rep["n_move"] == 4518
    assert rep["parent_r0"]["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert rep["parent_r0"]["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    assert rep["provided_bands_only_for_relief"] is True
    assert rep["leakage_canaries"]["passed"] is True
    assert rep["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    rc = rep["relief_classification"]
    sizes = [rc["classes"][k]["footprint_px"] for k in ("basin", "piedmont", "range")]
    assert sum(sizes) == 5_167_373
    assert max(sizes) - min(sizes) <= 2
    assert rc["tercile_cuts_m"][0] < rc["tercile_cuts_m"][1]
    assert rep["ranking_quality_vs_blind_sgmc"]["evidence_label"] == "PROXY"
    pre = rep["pre_registration"]["pre_registered_model_predictions"]
    assert set(pre) >= VALUES
    assert set(rep["final_model_predictions"]) == VALUES


def test_relief_variants_receipts_ledger_cards_and_disk_reread():
    rep = _report()
    assert len(rep["variants"]) == 3
    assert {v["value"] for v in rep["variants"]} == VALUES

    with (ROOT / "ledger" / "submissions.csv").open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    shas = [r["sha256"] for r in rows]
    shas_z = [r["sha256_zeros"] for r in rows]
    assert len(shas) == len(set(shas)) == len(rows)
    assert len(shas_z) == len(set(shas_z)) == len(rows)
    assert len(set(shas) & set(shas_z)) == 0
    keys = [(r["parent"], r["axis"], r["value"]) for r in rows]
    assert len(keys) == len(set(keys)), "repeated (parent, axis, value)"
    relief_rows = {r["id"]: r for r in rows if r["axis"] == "RELIEF" and r["parent"] == "h33-h33-2-b2"}
    assert {r["value"] for r in relief_rows.values()} == VALUES

    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
    prereg = json.loads((ROOT / "registry" / "relief_r0_preregistration.json").read_text())

    for v in rep["variants"]:
        assert v["axis"] == "RELIEF"
        assert v["n_dots"] == 37_654
        pdif = v["parent_diff"]
        assert pdif["n_added"] == pdif["n_removed"] == 4518
        assert pdif["pct_changed_moved"] == pytest.approx(12.0, abs=0.01)
        assert 1.0 <= pdif["pct_changed_moved"] <= 50.0
        assert pdif["dots_le_2px"] == 0
        assert pdif["dots_le_3px"] == 2_171
        assert pdif["min_dist_added_catalogue_px"] > 3.0
        assert pdif["collar_dots_2_3px_unchanged"] is True
        assert len(v["form_note"]) <= 140
        assert all(v["gates"].values())
        st = v["relief"]
        assert st["n_move"] == 4518
        assert sum(st["donor_counts"].values()) == 4518
        assert st["receiver"] not in st["donors"]
        assert st["shares_after"][st["receiver"]]["n_dots"] == st["shares_before"][st["receiver"]]["n_dots"] + 4518
        assert st["added_min_dcat_px"] > 3.0
        assert st["sgmc_decomposition"]["evidence_label"] == "PROXY"
        assert st["sgmc_random_donor_sensitivity"]["evidence_label"] == "PROXY"

        row = relief_rows[v["id"]]
        assert row["sha256"] == v["sha256"] and row["sha256_zeros"] == v["sha256_zeros"]
        assert row["status"] == "BUILT"
        assert row["receipt_score"] == "" and row["receipt_date"] == ""
        assert row["predicted_change"].startswith("MODEL:")
        assert row["predicted_change"] == f"MODEL:{brv.FINAL_MODEL[v['value']]['delta_live_vs_r0']:+.3f}"

        card = cards[v["id"]]
        for field in ("hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"):
            assert field in card and len(card[field]) > 20
        assert "MODEL" in card["predicted_sign_size"]
        assert card["pre_registered_model"] == prereg["pre_registered_model_predictions"][v["value"]]
        assert card["final_model"] == brv.FINAL_MODEL[v["value"]]

        rec_path = ROOT / "releases" / f"{v['id']}.json"
        assert rec_path.is_file()
        rec = json.loads(rec_path.read_text())
        assert rec["sha256"] == v["sha256"] and rec["sha256_zeros"] == v["sha256_zeros"]
        assert rec["parent_sha256_zeros"] == bpv.PARENT_SHA_ZEROS

        p_nan = ROOT / v["file_nan"]
        p_zeros = ROOT / v["file_zeros"]
        if not (p_nan.is_file() and p_zeros.is_file()):
            continue  # rasters are gitignored; only present after a local build
        import rasterio
        from scipy.ndimage import distance_transform_edt

        assert bpv.sha256_file(p_nan) == v["sha256"]
        assert bpv.sha256_file(p_zeros) == v["sha256_zeros"]
        with zipfile.ZipFile(ROOT / v["zip_nan"]) as zf:
            assert hashlib.sha256(zf.read(p_nan.name)).hexdigest() == v["sha256"]
        with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as tpl:
            ref = (tpl.shape, tpl.crs, tpl.transform)
            foot = np.isfinite(tpl.read(1))
        with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ef:
            catalogue = (ef.read(1) > 0) & foot
        d_cat = distance_transform_edt(~catalogue)
        with rasterio.open(p_nan) as ds_n, rasterio.open(p_zeros) as ds_z:
            assert (ds_n.shape, ds_n.crs, ds_n.transform) == ref == (ds_z.shape, ds_z.crs, ds_z.transform)
            assert ds_n.count == ds_z.count == 1
            assert ds_n.dtypes[0] == ds_z.dtypes[0] == "float32"
            arr_n = ds_n.read(1)
            arr_z = ds_z.read(1)
        assert np.isfinite(arr_n[foot]).all() and np.isnan(arr_n[~foot]).all()
        assert np.isfinite(arr_z).all() and np.all(arr_z[~foot] == 0.0)
        assert np.array_equal(arr_n[foot], arr_z[foot])
        assert 0.0 <= float(arr_n[foot].min()) and float(arr_n[foot].max()) <= 1.0
        mask = arr_z > 0.5
        assert int(mask.sum()) == 37_654
        assert int((mask & catalogue).sum()) == 0
        assert int((mask & (d_cat <= 2.0)).sum()) == 0
        assert int((mask & (d_cat <= 3.0)).sum()) == 2_171
