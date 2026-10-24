"""Tests for AXIS=CONCENTRATION on the gate-clean parent R1 (PRUNEp3px).

Three layers (mirrors the other R1-family axis tests):

* A synthetic unit test for the label-free geophysical block prior
  :func:`build_concentration_r1_variants.physics_block_prior` (deterministic,
  monotone in the field).
* Static tests over tracked artifacts (preregistration, ledger, mechanism cards,
  axis report, receipts) that run in CI without the gitignored rasters.
* An artifact test that re-reads the released GeoTIFFs from disk and re-derives
  every MUST gate with the hardened ``validate_variant.py``; it skips when
  ``releases/`` lacks the family TIFFs (competition rasters are gitignored;
  regenerate with ``python3 scripts/build_concentration_r1_variants.py``).

No PROXY/MODEL value is ever asserted as a gate or called a score.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor"), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_concentration_r1.json"
REPORT = ROOT / "evidence" / "concentration_r1_axis_report.json"
VALIDATION = ROOT / "registry" / "concentration_r1_variant_validation.json"
RELEASES = ROOT / "releases"
CACHE = ROOT / ".cache" / "data"
PARENT = ROOT / "data" / "registry" / "h33_education.tif"

R1_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
OWN_VALUES = {"phys-c10", "phys-c20", "phys-c20-b5km"}
REVISED = {"phys-c10": "MODEL:-0.001", "phys-c20": "MODEL:-0.006",
           "phys-c20-b5km": "MODEL:-0.010"}
PRIMARY_IDS = {
    "phys-c10": f"{R1_ID}-CONCphys-c10-20261023-ced3de17",
    "phys-c20": f"{R1_ID}-CONCphys-c20-20261023-bde32688",
    "phys-c20-b5km": f"{R1_ID}-CONCphys-c20-b5km-20261023-4f6fdb20",
}


def _ledger_rows():
    with LEDGER.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _family_rows():
    return [r for r in _ledger_rows()
            if r["axis"] == "CONCENTRATION" and r["parent"] == R1_ID
            and r["value"] in OWN_VALUES]


# ---------------------------------------------------------------------------
# 1. Synthetic unit test: the block prior
# ---------------------------------------------------------------------------
def test_physics_block_prior_is_deterministic_and_monotone():
    import build_concentration_r1_variants as m
    foot = np.ones((40, 40), dtype=bool)
    fld = np.zeros((40, 40), dtype=np.float32)
    fld[10:30, 10:30] = 1.0
    pri, eligible, nb_c = m.physics_block_prior(fld, foot, 10)
    assert pri.shape == (16,) and nb_c == 4
    assert eligible.dtype == bool and int(eligible.sum()) == 16
    pri2, _, _ = m.physics_block_prior(fld, foot, 10)
    assert np.array_equal(pri, pri2), "prior must be deterministic (no RNG)"
    grid = pri.reshape(4, 4)
    assert float(grid[1:3, 1:3].mean()) > float(grid[0, 0]), \
        "geophysical prior must be higher where the field is higher"


# ---------------------------------------------------------------------------
# 2. Static artifact tests (CI-safe, no rasters needed)
# ---------------------------------------------------------------------------
def test_preregistration_is_before_any_proxy():
    pre = json.loads(PREREG.read_text())
    assert pre["registered_before_any_proxy"] is True
    assert pre["session_axis"] == "CONCENTRATION"
    assert pre["parent_id"] == R1_ID
    assert {a["value"] for a in pre["arms"]} == OWN_VALUES
    assert ">=3 px" in pre["why_this_parent_not_r0"]
    assert pre["prior_definition"].startswith("Label-free geophysical")


def test_ledger_family_rows_are_revised_and_built():
    rows = _family_rows()
    assert len(rows) == 3
    assert {r["value"] for r in rows} == OWN_VALUES
    for r in rows:
        assert r["n_dots"] == "37654"
        assert r["status"] == "BUILT"
        assert r["receipt_score"] == "" and r["receipt_date"] == ""
        # the honest revision to a negative MODEL is recorded, not a false positive
        assert r["predicted_change"] == REVISED[r["value"]]
        assert r["predicted_change"].startswith("MODEL:-")
        assert "REVISED" in r["description"]
        assert r["recommendation"].startswith("HOLD")
        assert "CONVERGE NEGATIVE" in r["recommendation"]
        assert 9.99 <= float(r["pct_changed"]) <= 20.01
    # exact-hash dedupe across the whole cumulative ledger
    allrows = _ledger_rows()
    shas = [r["sha256"] for r in allrows] + [r["sha256_zeros"] for r in allrows]
    assert len(set(shas)) == len(shas)


def test_report_records_convergent_falsification():
    rep = json.loads(REPORT.read_text())
    assert rep["axis"] == "CONCENTRATION" and rep["parent_r1"] == R1_ID
    assert rep["provided_bands_only"] is True and rep["external_lidar_used"] is False
    assert rep["leakage_canaries"]["max_symmetric_auc"] < 0.90
    assert ">3 px" in rep["gate_eligible"]
    pbo = rep["post_build_outcome"]
    assert pbo["all_arms_disposition"].startswith("HOLD")
    assert "CONVERGENT FALSIFICATION" in pbo["result"]
    for v, dv in pbo["instruments"]["blind_sgmc_PROXY_vs_r1"].items():
        assert dv < 0, f"{v} SGMC PROXY must be below parent"
    for v, dv in pbo["instruments"]["w_dti_MODEL_vs_r1"].items():
        assert dv < 0, f"{v} w-DTI MODEL must be negative"
    assert len(rep["variants"]) == 3
    for v in rep["variants"]:
        assert v["n_dots"] == 37654
        assert v["parent"] == R1_ID
        assert v["parent_diff"]["min_dist_catalogue_px"] >= 3.0
        assert v["parent_diff"]["n_added"] == v["parent_diff"]["n_removed"] > 0
        assert float(v["concentration_axis"]["cv_occupied_blocks_after"]) > \
            float(v["concentration_axis"]["cv_occupied_blocks_before"])


def test_mechanism_cards_and_receipts_carry_both_predictions():
    cards = json.loads(CARDS.read_text())
    for value, base in PRIMARY_IDS.items():
        card = cards[base]
        assert card["axis"] == "CONCENTRATION" and card["parent"] == R1_ID
        assert card["provided_bands_only"] is True
        assert card["post_build_instruments"]["both_instruments_negative"] is True
        assert card["revised_prediction_MODEL"] == REVISED[value]
        assert card["preregistered_prediction"].startswith("MODEL:+")
        for field in ("hypothesis", "mechanism", "non_fault_mimic", "confounder",
                      "predicted_sign_size", "falsifier"):
            assert field in card
        receipt = json.loads((RELEASES / f"{base}.json").read_text())
        assert receipt["id"] == base
        assert receipt["revised_prediction"]["value"] == REVISED[value]
        assert receipt["preregistered_prediction"]["value"].startswith("MODEL:+")
        # revised point stays inside the preregistered range (no silent redraw)
        lo, hi = (float(x) for x in
                  receipt["preregistered_prediction"]["range"].strip("[]").split(","))
        pt = float(receipt["revised_prediction"]["value"].split(":")[1])
        assert lo <= pt <= hi


# ---------------------------------------------------------------------------
# 3. On-disk MUST-gate re-derivation (skips in CI when rasters are absent)
# ---------------------------------------------------------------------------
def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_variant", ROOT / "scripts" / "validate_variant.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(
    not all((RELEASES / f"{PRIMARY_IDS[v]}.tif").is_file() for v in OWN_VALUES),
    reason="release rasters are local-only (gitignored); regenerate with "
           "scripts/build_concentration_r1_variants.py")
def test_every_release_passes_every_must_pass_gate():
    validator = _load_validator()
    with rasterio.open(CACHE / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
        sample_meta = {"crs": str(src.crs), "shape": [src.height, src.width],
                       "transform": [round(float(x), 6) for x in tuple(src.transform)[:6]]}
    with rasterio.open(CACHE / "existing_faults.tif") as src:
        catalogue = (src.read(1) == 1) & footprint
    dist = distance_transform_edt(~catalogue).astype(np.float32)
    with rasterio.open(PARENT) as src:
        parent = src.read(1) > 0.5
    hashes = validator.ledger_hashes()
    checked = 0
    for value, base in PRIMARY_IDS.items():
        for suffix in ("", "-zeros"):
            p = RELEASES / f"{base}{suffix}.tif"
            res = validator.validate(p, footprint, catalogue, dist, parent, sample_meta, hashes)
            failed = {k: c for k, c in res["checks"].items() if not c["ok"]}
            assert not failed, f"{p.name}: {failed}"
            assert res["n_dots"] == 37654
            # hardened non-PRUNE clearance gate must be explicitly satisfied
            assert res["checks"]["non_prune_clearance_ge_3px"]["ok"]
            checked += 1
    assert checked == 6


def test_recorded_validation_json_is_all_pass():
    if not VALIDATION.is_file():
        pytest.skip("validation JSON not present")
    val = json.loads(VALIDATION.read_text())
    assert val["gates_all_pass"] is True
    assert len(val["results"]) == 6
    assert all(r["gates_pass"] for r in val["results"])
