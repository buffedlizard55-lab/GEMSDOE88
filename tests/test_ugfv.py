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


def test_run_card_copies_and_current_ibl88_status_are_consistent():
    """Current status follows IBL-88; PHASE-88 stays a separate archive record."""
    paths = [
        ROOT / "run_card.json",
        ROOT / "registry/run_card.json",
        ROOT / "docs/data/run-card.json",
        ROOT / "docs/data/run_card.json",
        ROOT / "docs/run_card.json",
        ROOT / "evidence/run-card.json",
    ]
    texts = [p.read_text() for p in paths]
    assert len(set(texts)) == 1, "Canonical run-card copies must be byte-identical"
    card = json.loads(texts[0])
    assert card["lane"] == "IBL-88 basin blind lattice infill"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    assert card["approved_for_weekly_slot"] is False and card["slots_used_by_this_session"] == 0
    assert card["evidence_status"]["organizer_confirmed_live_score"] is None
    assert len(card["submission"]["submission_note"]) <= 140

    holdout = card["holdout_progression"]
    assert holdout["evidence_class"] == "HOLDOUT-DTI"
    assert holdout["evaluator_version"] == "gems57-pooled-hide-v2"
    assert holdout["withheld_positive_pixels"] == 22_893
    assert holdout["pooled_holdout_dti"] == 0.0
    assert holdout["far"]["withheld_positive_pixels"] == 10_791
    assert holdout["far"]["pooled_holdout_dti"] == 0.0

    literal = card["uniqueness"]["literal_binding_decision"]
    assert literal["duplicate"] is True and literal["stop_required"] is True
    assert literal["forward_overlap_3px"] == 1.0 and literal["limit"] == 0.70
    assert card["uniqueness"]["pre_placement_worst_abs_spearman"] == 0.0449

    status_doc = json.loads((ROOT / "docs/status.json").read_text())
    current_doc = json.loads((ROOT / "docs/data/ibl88-gate.json").read_text())
    assert status_doc["candidate"] == "IBL-88"
    assert status_doc["raster_sha256"] == current_doc["sha256"] == card["submission"]["sha256"]
    assert status_doc["ok_to_submit"] is False and status_doc["ok_to_download_for_research"] is True

    audit = json.loads((ROOT / "docs/data/ibl88-validation.json").read_text())
    assert audit["audit_passed"] and audit["strict_duplicate"] and not audit["ok_to_submit"]
    assert audit["checks"]["literal_forward_overlap_3px"] == 1.0

    # The PHASE-88 current_release record is deliberately independent of the
    # latest research-candidate status feed.
    current_release = json.loads((ROOT / "docs/data/current_release.json").read_text())
    phase = json.loads((ROOT / "registry/phase88_run_card.json").read_text())
    assert current_release["file"] == phase["download"]
    assert current_release["file_sha256"] == phase["raster_sha256"]
