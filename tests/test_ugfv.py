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
    """The canonical card now describes the current MRR negative deliverable."""
    paths = [
        ROOT / "registry/run_card.json",
        ROOT / "docs/data/run-card.json",
        ROOT / "docs/run_card.json",
        ROOT / "evidence/run-card.json",
    ]
    texts = [p.read_text() for p in paths]
    assert len(set(texts)) == 1, "All 4 run-card JSON copies must be byte-identical"

    card = json.loads(texts[0])
    assert card["lane"] == "H88-MRR-BPR"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["weekly_slots_used"] == 0
    assert card["organizer_confirmed"]["score"] is None
    assert len(card["submission_note"]) <= 140

    holdout = card["holdout_dti"]
    assert holdout["evidence_class"] == "HOLDOUT-DTI"
    assert holdout["evaluator_version"] == "gems57-pooled-hide-v2"
    assert holdout["withheld_positive_pixels"] == 22_893
    assert holdout["candidate"] < holdout["incumbent_recomputed"]
    assert holdout["paired_delta_vs_incumbent"] < 0
    assert holdout["paired_delta_ci95"][1] < 0

    canaries = card["leakage_canary"]
    assert canaries["passed"] is True
    assert canaries["features_tested"] == 4
    assert canaries["max_symmetric_auc"] <= 0.90
    assert all(row["pass"] for row in canaries["features"])

    reg = card["correlation_overlap_vs_registry"]
    assert reg["rasters_checked"] == 21
    assert reg["surface_preplacement_max_abs_spearman"] <= reg["surface_limit"]
    assert reg["final_max_forward_overlap_3px_sparse_rasters"] <= reg["overlap_limit"]
    assert reg["final_max_forward_overlap_3px_all_rasters"] == 1.0
    assert reg["literal_binding_decision"]["duplicate"] is True
    assert reg["universal_witness"]["universal_overlap_blocker"] is True

    # The current status feed follows the later canonical current-release
    # validator, while the four-way MRR card remains immutable history.
    status_doc = json.loads((ROOT / "docs/status.json").read_text())
    current_doc = json.loads((ROOT / "docs/data/current_release.json").read_text())
    assert status_doc["raster_sha256"] == current_doc["file_sha256"]
    assert status_doc["raster_sha256"] != card["raster_sha256"]
    assert status_doc["ok_to_submit"] is False
    assert status_doc["ok_to_download_for_research"] is True

    tif_path = ROOT / card["artifact"]
    zip_path = ROOT / card["zip_artifact"]
    receipt_path = tif_path.with_suffix(".json")
    assert tif_path.is_file() and zip_path.is_file() and receipt_path.is_file()
    assert _sha256(tif_path) == card["raster_sha256"]
    assert _sha256(zip_path) == card["zip_sha256"]
