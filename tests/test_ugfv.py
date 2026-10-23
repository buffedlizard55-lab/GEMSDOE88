"""Dedicated unit & audit tests for the H88-UGFV geophysical + structural pipeline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from gems57 import emit, uniqueness
from gems88.ugfv import (
    UGFV_STATIC_NAMES,
    UGFV_STRUCT_NAMES,
    build_halo_constraint_matrix,
    dinkelbach_candidate_coords,
    nested_visible_draw,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_ugfv_channel_schemas_unique_and_complete():
    assert len(UGFV_STATIC_NAMES) == 32
    assert len(UGFV_STRUCT_NAMES) == 16
    combined = [*UGFV_STATIC_NAMES, *UGFV_STRUCT_NAMES]
    assert len(set(combined)) == 48


def test_nested_visible_draw_enforces_zero_component_leakage():
    h, w = 80, 80
    fp = np.ones((h, w), dtype=bool)
    visible = np.zeros((h, w), dtype=bool)
    for idx, r0 in enumerate([8, 20, 32, 44, 56, 68]):
        visible[r0, 10 + idx : 30 + idx] = True

    inner_vis, inner_truth = nested_visible_draw(
        visible, fp, seed=20261022, hide_frac=0.30, buffer_px=3
    )
    assert inner_vis.any() and inner_truth.any()
    assert not np.any(inner_vis & inner_truth)
    assert np.all(inner_vis <= visible)
    assert np.all(inner_truth <= visible)
    assert np.all(ndi.distance_transform_edt(~inner_truth)[inner_vis] > 3.0)


def test_dinkelbach_knapsack_halo_constraints_enforced():
    h, w = 60, 260
    allowed = np.ones((h, w), dtype=bool)
    prob = np.zeros((h, w), dtype=np.float32)
    prob[30, 5:255] = 0.85
    self_credit = np.full((h, w), 0.80, dtype=np.float32)

    prior_dots = np.zeros((h, w), dtype=bool)
    prior_dots[30, 5:180] = True
    prior_dots[0:30, 5:210] = True

    cand_ys, cand_xs = dinkelbach_candidate_coords(prob, allowed)
    hc_mat, hc_caps = build_halo_constraint_matrix(
        cand_ys,
        cand_xs,
        [("synthetic_prior.tif", prior_dots, int(prior_dots.sum()))],
        max_overlap=0.50,
        budget=40,
    )
    assert hc_mat is not None and hc_caps is not None
    alloc = emit.dinkelbach_allocate(
        prob,
        self_credit,
        allowed,
        budget=40,
        k_truth=120.0,
        halo_constraints=hc_mat,
        halo_max_hits=hc_caps,
    )
    emitted = alloc.emitted
    assert 1 <= alloc.n_dots <= 40
    halo = uniqueness._near(prior_dots, 3)
    assert int(emitted[halo].sum()) <= int(hc_caps[0])


def test_run_card_four_way_parity_and_audit_invariants():
    paths = [
        ROOT / "registry/run_card.json",
        ROOT / "docs/data/run-card.json",
        ROOT / "docs/run_card.json",
        ROOT / "evidence/run-card.json",
    ]
    texts = [p.read_text() for p in paths]
    assert len(set(texts)) == 1, "All 4 run-card JSON copies must be byte-identical"

    card = json.loads(texts[0])
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["weekly_slots_used"] == 0
    assert len(card["submission_note"]) <= 140

    ladder = card["experiment_ladder"]
    assert len(ladder) == 3
    d0, d1, d2 = [row["holdout_dti"] for row in ladder]
    assert 0.03 < d0 < d1 < d2
    assert d2 > 0.17

    assert card["canary_max_auc"] <= 0.90
    canary_receipt = json.loads((ROOT / "registry/leakage_canaries.json").read_text())
    assert len(canary_receipt["features"]) >= 48
    feats = canary_receipt["features"]
    items = feats.values() if isinstance(feats, dict) else feats
    assert all(not row.get("leakage_flag", False) and row.get("pass", True) for row in items)

    reg = card["correlation_overlap_vs_registry"]
    surf = reg["surface_preplacement"]["summary_all_unique_rasters"]
    assert surf["checked_unique_rasters"] >= 19
    assert surf["max_abs_spearman"] <= 0.90
    assert surf["all_passed_le_090"] is True

    dots = reg["final_dots"]
    assert dots["discriminating_dot_rasters_summary"]["checked_count"] >= 18
    assert dots["discriminating_dot_rasters_summary"]["max_forward_dot_overlap_3px"] < 0.70
    assert dots["discriminating_dot_rasters_summary"]["all_passed_lt_070"] is True
    assert reg["like_for_like_dot_gate"]["passed"] is True
    assert reg["like_for_like_dot_gate"]["rasters_checked"] >= 18
    assert reg["literal_any_raster_gate"]["passed"] is False
    assert reg["literal_any_raster_gate"]["space_covering_witness_count"] >= 1
    assert dots["H33"]["forward_dot_overlap_3px"] < 0.70

    status_doc = json.loads((ROOT / "docs/status.json").read_text())
    assert status_doc["raster_sha256"] == card["raster_sha256"]
    assert status_doc["ok_to_submit"] is False
    assert status_doc["ok_to_download_for_research"] is True

    tif_path = ROOT / "docs" / card["downloadable_file"]
    zip_path = tif_path.with_suffix(".zip")
    receipt_path = tif_path.with_suffix(".json")
    assert tif_path.is_file() and zip_path.is_file() and receipt_path.is_file()
    assert _sha256(tif_path) == card["raster_sha256"]
    assert _sha256(zip_path) == card["zip_sha256"]
