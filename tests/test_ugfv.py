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
    """The canonical card records this review and mirrors all required paths."""
    paths = [
        ROOT / "registry/run_card.json",
        ROOT / "docs/data/run-card.json",
        ROOT / "docs/run_card.json",
        ROOT / "evidence/run-card.json",
    ]
    texts = [p.read_text() for p in paths]
    assert len(set(texts)) == 1, "All 4 run-card JSON copies must be byte-identical"

    card = json.loads(texts[0])
    assert card["schema"] == "gems88.session-review-card.v1"
    assert card["run_id"] == "GEMSDOE88-PROTOCOL-REVIEW-20261025"
    assert card["lane"] == "protocol-integrity-only; no geological model run"
    assert card["verdict"] == "negative"
    assert card["correlation_overlap_vs_registry"]["decision"] == "DUPLICATE_STOP"
    assert card["ok_to_download_for_research"] is True
    assert card["ok_to_submit"] is False
    assert card["experiment_budget"]["experiments_run_this_session"] == 0
    assert card["experiment_budget"]["new_rasters_generated"] == 0
    assert card["experiment_budget"]["weekly_slots_used"] == 0
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["holdout"]["withheld_positive_pixels"] == 22_893
    assert card["holdout"]["ci95"] == [0.12768777369706202, 0.15611205556213584]
    assert card["correlation_overlap_vs_registry"]["universal_nonempty_candidate_blocker"] is True
    assert card["correlation_overlap_vs_registry"]["existing_h88_dhtc_literal_forward_dot_overlap_3px_remeasured"] == 1.0
    assert len(card["submission_note"]) <= 140
    assert card["submission_name"] is None

    status_doc = json.loads((ROOT / "docs/status.json").read_text())
    current_doc = json.loads((ROOT / "docs/data/current_release.json").read_text())
    assert current_doc["candidate"] == "H88-TDKL"
    assert status_doc["raster_sha256"] == current_doc["file_sha256"]
    assert status_doc["run_card"] == "registry/tdkl88_run_card.json"
    assert status_doc["review_card"] == "registry/session_20261025_run_card.json"
    assert status_doc["ok_to_submit"] is False
    assert status_doc["ok_to_download_for_research"] is True
