"""Gates and bookkeeping for the CONCENTRATION axis releases.

These tests re-read the committed ``releases/*.tif`` bytes; they never trust the
builder's in-memory arrays, and they do not evaluate any PROXY instrument as a
gate (brief v2, sections 6 and 8).
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "releases"
CACHE = ROOT / ".cache" / "data"
PARENT = ROOT / "data" / "registry" / "h33_education.tif"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_variant", ROOT / "scripts" / "validate_variant.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def report():
    return json.loads((ROOT / "registry" / "concentration_report.json").read_text())


@pytest.fixture(scope="module")
def projection():
    return json.loads((ROOT / "registry" / "concentration_projection.json").read_text())


@pytest.fixture(scope="module")
def ledger_rows():
    with (ROOT / "ledger" / "submissions.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def _variant_ids(report):
    return [vid[:-4] if vid.endswith(".tif") else vid for vid in report["variants"]]


def _rasters_present(report):
    return all((ROOT / v[k]["path"]).is_file()
               for v in report["variants"].values() for k in ("nan", "zeros"))


def test_three_variants_with_distinct_hashes(report, ledger_rows):
    assert len(report["variants"]) == 3
    shas = []
    for vid, v in report["variants"].items():
        shas += [v["nan"]["sha256"], v["zeros"]["sha256"]]
    assert len(set(shas)) == 6, "variant hashes must be unique"
    ledger_shas = [r["sha256"] for r in ledger_rows] + [r["sha256_zeros"] for r in ledger_rows]
    assert len(set(ledger_shas)) == len(ledger_shas) == 14, "14 unique hashes across 7 rows"


def test_receipts_are_tracked_and_match_the_report(report, projection, ledger_rows):
    """The rasters stay local; the receipts must still carry identity and hashes."""
    ledger = {r["id"]: r for r in ledger_rows}
    for vid, v in report["variants"].items():
        base = vid[:-4] if vid.endswith(".tif") else vid
        receipt = json.loads((RELEASES / f"{base}-receipt.json").read_text())
        assert receipt["candidate"] == base
        assert receipt["file"]["sha256"] == v["nan"]["sha256"] == ledger[base]["sha256"]
        assert receipt["file"]["sha256_zeros"] == v["zeros"]["sha256"] == ledger[base]["sha256_zeros"]
        assert receipt["submission"]["name"] == base
        assert 20 <= len(receipt["submission"]["note"]) <= 140
        assert receipt["submission"]["note_chars"] == len(receipt["submission"]["note"])
        assert receipt["gates"]["primary_all_pass"] and receipt["gates"]["zeros_all_pass"]
        point = projection["variants"][vid]["point_estimate"]
        assert receipt["prediction"]["delta"] == pytest.approx(point, abs=1e-4)
        assert receipt["disposition"].startswith("HOLD"), "collar inheritance must stay visible"
        assert receipt["file"]["tracked_in_git"] is False


@pytest.mark.skipif(not (RELEASES / "h33-h33-2-b2-CONCb10px-m20-20261023-c42cd475.tif").is_file(),
                    reason="release rasters are local-only (data-use flag); the tracked receipt "
                           "records the gate run performed before untracking")
def test_every_release_passes_every_must_pass_gate(report):
    validator = _load_validator()
    with rasterio.open(CACHE / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
        sample_meta = {"crs": str(src.crs), "shape": [src.height, src.width],
                       "transform": [round(float(x), 6) for x in tuple(src.transform)[:6]]}
    with rasterio.open(CACHE / "existing_faults.tif") as src:
        catalogue = (src.read(1) == 1) & footprint
    from scipy.ndimage import distance_transform_edt
    dist = distance_transform_edt(~catalogue).astype(np.float32)
    with rasterio.open(PARENT) as src:
        parent = src.read(1) > 0.5
    hashes = validator.ledger_hashes()

    for v in report["variants"].values():
        for key in ("nan", "zeros"):
            p = ROOT / v[key]["path"]
            res = validator.validate(p, footprint, catalogue, dist, parent, sample_meta, hashes)
            failed = {k: c for k, c in res["checks"].items() if not c["ok"]}
            assert not failed, f"{p.name}: {failed}"
            assert res["n_dots"] == 37_654
            assert res["sha256"] == v[key]["sha256"]
            assert res["parent_diff"]["removed"] == res["parent_diff"]["added"] > 0


def test_axis_invariants(report):
    parent_stats = report["parent_stats"]
    for vid, v in report["variants"].items():
        d = v["diff_stats"]
        assert d["n_dots"] == 37_654, "MASS must be held constant on this axis"
        assert 9.99 <= d["pct_of_parent_dots_moved"] <= 20.01  # integer dot counts
        assert d["dots_within_2px_catalogue"] == 0
        # the 2-3 px collar is inherited unchanged from R0, never grown
        assert d["dots_within_3px_catalogue"] == parent_stats["dots_within_3px_catalogue"] == 2171
        # no block is emptied: this is concentration, not disguised pruning
        assert d["blocks_emptied"] == 0
        assert d["blocks_gained"] <= 64
        # receivers are welded to surviving host dots, donors come from colder blocks
        assert d["added_distance_to_host_px_max"] <= 1.415
        assert d["added_block_prior_mean"] > 1.5 * d["removed_block_prior_mean"]
        # count + overlap bookkeeping
        assert abs(d["parent_overlap_fraction"] - (1 - d["pct_of_parent_dots_moved"] / 100)) < 1e-6
        # exposed statistics, both CV definitions, and the 5 km-smoothed variant
        for key in ("cv_occupied_blocks", "cv_all_eligible_blocks", "gini_occupied",
                    "mass_share_in_top1pct_prior_blocks"):
            assert key in d["block_stats_after"]
        assert "cv_density_smoothed_5blocks" in d["smoothed_density_cv_after"]
        # the manipulation really does raise clustering on every estimator
        assert d["block_stats_after"]["cv_occupied_blocks"] > d["block_stats_before"]["cv_occupied_blocks"]
        assert d["block_stats_after"]["gini_occupied"] > d["block_stats_before"]["gini_occupied"]


def test_ledger_matches_releases_and_projection(report, projection, ledger_rows):
    conc = [r for r in ledger_rows if r["axis"] == "CONCENTRATION"]
    assert len(conc) == 3
    for row in conc:
        v = report["variants"][row["id"] + ".tif"]
        assert row["sha256"] == v["nan"]["sha256"]
        assert row["sha256_zeros"] == v["zeros"]["sha256"]
        assert row["status"] == "BUILT"
        assert row["receipt_score"] == "" and row["receipt_date"] == ""
        assert row["recommendation"].startswith("HOLD")
        point = projection["variants"][row["id"] + ".tif"]["point_estimate"]
        assert row["predicted_change"] == f"MODEL:{point:+.3f}"
        lo, hi = projection["variants"][row["id"] + ".tif"]["range_scenarios"]
        assert row["predicted_range"] == f"[{lo:+.3f},{hi:+.3f}]"
        assert abs(float(row["pct_changed"]) - 10.0) < 0.01 or \
               abs(float(row["pct_changed"]) - 20.0) < 0.01


def test_projection_arithmetic_is_self_consistent(projection):
    cal = projection["calibration"]
    assert cal["T_R0_CLAM"] > 0 and cal["D_R0_CLAM"] > 0
    assert 0.0 < cal["coverage_T_over_G_if_M_zero"] < 1.0
    assert calibration_reproduces_claims(cal) == pytest.approx(0.2600, abs=5e-5)
    for vid, v in projection["variants"].items():
        for s in v["scenarios"]:
            T1 = cal["T_R0_CLAM"] + s["delta_T"]
            D1 = cal["D_R0_CLAM"] + s["delta_D"]
            assert s["delta_DTI"] == pytest.approx(T1 / D1 - cal["T_R0_CLAM"] / cal["D_R0_CLAM"], abs=1e-12)
        lo, hi = v["range_scenarios"]
        assert lo <= v["point_estimate"] <= hi


def calibration_reproduces_claims(cal):
    """Recompute D2.8's DTI from the calibration: T, D and 6,436 zero-credit collar dots."""
    d28 = cal["D_R0_CLAM"] + 0.2 * 6436
    return cal["T_R0_CLAM"] / d28


def test_proxy_is_labelled_and_not_a_gate():
    p = ROOT / "registry" / "concentration_proxy.json"
    if not p.is_file():
        pytest.skip("proxy not computed in this environment")
    proxy = json.loads(p.read_text())
    assert proxy["evidence_class"] == "PROXY"
    assert proxy["withheld_positive_pixels"] == 22893
    assert "not a gate" in proxy["caveat"].lower()
    for v in proxy["pooled"]["scores"].values():
        assert v["evidence_class"] == "HOLDOUT-DTI"
        assert 0.0 <= v["dti"] <= 1.0
    assert proxy["pooled"]["scores"]["R0_parent"]["dti"] < 0.01, (
        "this instrument has almost no power on a 2 px-collar dot file; that is why "
        "it is report-only")


def test_kill_switch_no_rank_or_overlap_thresholds_were_applied(report):
    """Section 6 forbids rank-correlation / overlap uniqueness thresholds as gates."""
    text = (ROOT / "scripts" / "make_concentration_variants.py").read_text().lower()
    for banned in ("spearman", "jaccard", "overlap <= 0.70", "uniqueness gate"):
        assert banned not in text
