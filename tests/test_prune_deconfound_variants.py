"""Unit and tracked-artifact tests for the AXIS=PRUNE deconfounding variants."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import metric  # noqa: E402
import build_prune_deconfound_variants as bpd  # noqa: E402


def test_directional_crest_1d_isolates_ridges_and_respects_valid_mask() -> None:
    H, W = 21, 21
    valid = np.ones((H, W), dtype=bool)
    valid[0, :] = False
    score = np.zeros((H, W), dtype=np.float32)
    for x in range(W):
        for y in range(H):
            score[y, x] = max(0.0, 1.0 - abs(y - 10) * 0.25)
    crest = bpd.directional_crest_1d(score, valid)
    assert np.all(crest[10, 1:-1])
    assert not np.any(crest[0, :])
    assert not np.any(crest[4, :])


def test_spaced_farthest_point_add_enforces_lock_is_deterministic_and_fails_closed() -> None:
    H, W = 40, 40
    base = np.zeros((H, W), dtype=bool)
    base[5, 5] = True
    base[34, 34] = True
    cand = np.zeros((H, W), dtype=bool)
    cand[4:36:2, 4:36:2] = True
    cand &= ~base

    out1, st1 = bpd.spaced_farthest_point_add(base, cand, n_add=12, spacing_px=3.5)
    out2, st2 = bpd.spaced_farthest_point_add(base, cand, n_add=12, spacing_px=3.5)
    assert np.array_equal(out1, out2)
    assert st1 == st2
    assert int(out1.sum()) == int(base.sum()) + 12
    assert np.all(out1[base])

    pts_all = np.argwhere(out1).astype(np.float64)
    pts_add = np.argwhere(out1 & ~base).astype(np.float64)
    nn_add = cKDTree(pts_all).query(pts_add, k=2)[0][:, 1]
    assert float(nn_add.min()) >= 3.5 - 1e-9

    with pytest.raises(ValueError, match="exhausted pool|required"):
        bpd.spaced_farthest_point_add(base, cand, n_add=250, spacing_px=3.5)


def test_build_lt3_spaced_arm_preserves_exact_3px_zero_kernel_dots() -> None:
    # Verify official metric kernel at exact d == 3.0 px is identically 0.0
    assert float(metric.kernel(np.array(3.0))) == 0.0
    assert float(metric.kernel(np.array(np.sqrt(8.0)))) > 0.0  # d = 2.8284 < 3.0

    H, W = 50, 50
    cat = np.zeros((H, W), dtype=bool)
    cat[25, 25] = True
    d_cat = distance_transform_edt(~cat)

    parent = np.zeros((H, W), dtype=bool)
    parent[25 + 2, 25 + 1] = True  # d^2 = 5 -> 2.2361 < 3.0 (removed)
    parent[25 + 2, 25 + 2] = True  # d^2 = 8 -> 2.8284 < 3.0 (removed)
    parent[25, 25 + 3] = True      # d^2 = 9 -> 3.0000 == 3.0 (MUST BE PRESERVED)
    parent[25 - 3, 25] = True      # d^2 = 9 -> 3.0000 == 3.0 (MUST BE PRESERVED)
    parent[10, 10] = True          # d > 3.0 (survivor)

    support = np.zeros((H, W), dtype=bool)
    support[5:45:5, 5:45:5] = True
    support |= parent

    yy, xx = np.mgrid[0:H, 0:W]
    w = np.where(~cat, 0.05 + 0.15 * ((yy + xx) / float(H + W)), 0.0).astype(np.float32)

    out, st = bpd.build_lt3_spaced_arm(parent, support, d_cat, w, spacing_px=3.5)
    assert st["n_removed"] == 2
    assert st["n_added"] == 2
    assert st["preserved_exact_3px_parent_dots"] == 2
    assert int(out.sum()) == int(parent.sum())
    assert bool(out[25, 28]) is True
    assert bool(out[22, 25]) is True
    assert int((d_cat[out] < 3.0).sum()) == 0


def test_preregistration_ledger_cards_receipts_and_validator_consistency() -> None:
    assert bpd.PREREG_PATH.is_file()
    assert bpd.REPORT_PATH.is_file()
    assert bpd.VALIDATION_PATH.is_file()
    assert bpd.RECON_VALIDATION_PATH.is_file()

    prereg = json.loads(bpd.PREREG_PATH.read_text(encoding="utf-8"))
    report = json.loads(bpd.REPORT_PATH.read_text(encoding="utf-8"))
    val_doc = json.loads(bpd.VALIDATION_PATH.read_text(encoding="utf-8"))
    recon_doc = json.loads(bpd.RECON_VALIDATION_PATH.read_text(encoding="utf-8"))
    cards = json.loads(bpd.CARDS_PATH.read_text(encoding="utf-8"))

    assert prereg["frozen_before_any_variant_proxy_or_sgmc"] is True
    assert val_doc["gates_all_pass"] is True
    assert len(val_doc["results"]) == 6
    assert recon_doc["gates_all_pass"] is True
    assert len(recon_doc["results"]) == 4

    assert report["leakage_canaries"]["passed"] is True
    assert report["leakage_canaries"]["max_single_feature_symmetric_auc"] <= 0.90
    assert report["support_cardinalities"]["exact_cardinality_matched"] is True
    assert report["support_cardinalities"]["provided_crest_union_px"] == 157_085

    with bpd.LEDGER.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # Global deduplication invariants across the entire ledger
    seen_pairs: set[tuple[str, str, str]] = set()
    seen_shas: set[str] = set()
    for r in rows:
        pair = (r["parent"], r["axis"], r["value"])
        assert pair not in seen_pairs, f"Duplicate ledger (parent, axis, value): {pair}"
        seen_pairs.add(pair)
        for col in ("sha256", "sha256_zeros"):
            assert r[col] not in seen_shas, f"Duplicate SHA-256 in ledger: {r[col]}"
            seen_shas.add(r[col])

    # Scoped strictly to OUR_VALUES (IR-88-42)
    our_rows = {
        r["value"]: r
        for r in rows
        if r["parent"] == bpd.PARENT_ID and r["axis"] == bpd.AXIS and r["value"] in bpd.OUR_VALUES
    }
    assert set(our_rows.keys()) == set(bpd.OUR_VALUES)

    rep_by_val = {v["value"]: v for v in report["variants"]}
    for val in bpd.OUR_VALUES:
        r = our_rows[val]
        v = rep_by_val[val]
        pre = prereg["arms"][val]
        vid = r["id"]

        assert int(r["n_dots"]) == 37_654
        pct = float(r["pct_changed"])
        assert 1.0 <= pct <= 50.0
        assert r["status"] == "BUILT"
        assert r["receipt_score"] == ""
        assert r["predicted_change"] == f"MODEL:{pre['predicted_change_model']}"
        assert r["sha256"] == v["sha256"]
        assert r["sha256_zeros"] == v["sha256_zeros"]
        assert len(v["form_note"]) <= 140

        rec_path = bpd.RELEASES / f"{vid}.json"
        assert rec_path.is_file()
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        assert rec["sha256"] == r["sha256"]
        assert rec["sha256_zeros"] == r["sha256_zeros"]
        assert rec["gates"]["zero_catalogue_mass"] is True
        assert rec["gates"]["reread_from_disk_verified"] is True
        assert float(rec["parent_diff"]["min_dist_catalogue_px"]) >= 3.0
        assert rec["not_submitted"] is True

        assert vid in cards
        card = cards[vid]
        for req_key in ("hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"):
            assert card.get(req_key), f"Missing {req_key} in mechanism card {vid}"

    # Verify hardened validator recorded 0 pixels < 3 px on every validated raster
    for vr in val_doc["results"]:
        assert vr["gates_pass"] is True
        assert vr["checks"]["non_prune_clearance_ge_3px"]["detail"]["positive_pixels_below_3px"] == 0


@pytest.mark.skipif(
    not (bpd.RELEASES / "h33-h33-2-b2-PRUNEp3space35fp-20261024-8d29a2f7.tif").is_file()
    or not (ROOT / "data" / "bridge" / "sample_submission.tif").is_file(),
    reason="Local gitignored release GeoTIFFs or data/bridge rasters not present in CI checkout",
)
def test_local_release_geotiffs_match_receipts_and_clearance() -> None:
    report = json.loads(bpd.REPORT_PATH.read_text(encoding="utf-8"))
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~cat)

    for v in report["variants"]:
        vid = v["id"]
        p_nan = bpd.RELEASES / f"{vid}.tif"
        p_z = bpd.RELEASES / f"{vid}-zeros.tif"
        assert hashlib.sha256(p_nan.read_bytes()).hexdigest() == v["sha256"]
        assert hashlib.sha256(p_z.read_bytes()).hexdigest() == v["sha256_zeros"]
        with rasterio.open(p_nan) as d_n, rasterio.open(p_z) as d_z:
            an = d_n.read(1)
            az = d_z.read(1)
        assert np.all(np.isnan(an[~foot]))
        assert np.all(az[~foot] == 0.0)
        assert np.array_equal(an[foot], az[foot])
        pos = az > 0
        assert int(pos.sum()) == 37_654
        assert not np.any(pos & cat)
        assert float(d_cat[pos].min()) >= 3.0
