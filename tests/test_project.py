import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from scripts.readiness import assess, current_status, verify_template  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402
from gems57 import metric, evaluate_holdout, uniqueness  # noqa: E402


def test_template_bytes_unchanged():
    verify_template()


def test_real_card_stays_blocked():
    if not (ROOT / "data/bridge/existing_faults.tif").is_file():
        pytest.skip("full release recomputation requires ignored data/bridge inputs; restore inputs first")
    assert json.loads((ROOT / "docs/run_card.json").read_text()) == json.loads(
        (ROOT / "registry/run_card.json").read_text()
    )
    result = current_status()
    assert result["status"] == "BLOCKED"
    assert not result["approved_for_weekly_slot"]
    assert not result["ok_to_submit"]
    assert result["ok_to_download_for_research"]
    # The current feed must follow latest H88-MVRD, not a historical PHASE/MRR run.
    assert result["problems"] and any(p.split(":")[0] in {"HOLDOUT", "UNIQUENESS", "FINGERPRINT", "FORMAT"} for p in result["problems"])
    assert "binding-literal-all-registry-v1" in result["policy"]
    current = json.loads((ROOT / "docs/data/current_release.json").read_text())
    card = json.loads((ROOT / "registry/mvrd_run_card.json").read_text())
    assert result["raster_sha256"] == current["file_sha256"] == card["raster_sha256"]
    assert current["file"] == card["artifact"]
    assert current["ok_to_submit"] is False and current["duplicate"] is True
    assert current["distance_fingerprint_ok"] is False


def eligible_record(tmp_path):
    out = tmp_path / "docs/downloads/unit-test.tif"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"synthetic gate receipt fixture, not a real TIFF")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    return {
        "lane": "test-only",
        "feature_cache_verified": True,
        "feature_names": ["x"],
        "experiment_count": 1,
        "elapsed_seconds": 1,
        "artifact": "docs/downloads/unit-test.tif",
        "raster_sha256": digest,
        "submission_name": "synthetic",
        "note": "synthetic fixture",
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "withheld_positives": 10,
            "ci95": [0.1, 0.3],
            "dti": 0.2,
            "paired_delta_ci95": [0.01, 0.02],
            "baseline_sha256": "test",
            "whole_segments": True,
            "buffered": True,
            "visible_only_features": True,
            "pixel_exact_mask": True,
        },
        "canaries": [{"feature": "x", "auc": 0.6}],
        "uniqueness": {
            "registry_complete": True,
            "registry_sha256": ["test"],
            "surface": [{"sha256": "test", "rho": 0.2, "overlap_3px": 0.1}],
            "dots": [{"sha256": "test", "rho": 0.2, "overlap_3px": 0.1}],
        },
        "validator": dict.fromkeys(
            [
                "no_nan_inside",
                "range_0_1",
                "crs_match",
                "shape_match",
                "transform_match",
            ],
            True,
        )
        | {"raster_sha256": digest},
    }


def test_schema_eligibility_is_never_slot_approval(tmp_path):
    result = assess(eligible_record(tmp_path), tmp_path)
    assert result["status"] == "SELECTOR_REQUIRED"
    assert not result["approved_for_weekly_slot"]


@pytest.mark.parametrize("stage", ["surface", "dots"])
@pytest.mark.parametrize(
    "field,value", [("rho", 0.901), ("overlap_3px", 0.701), ("rho", float("nan"))]
)
def test_duplicate_or_undefined_comparison_blocks(tmp_path, stage, field, value):
    card = eligible_record(tmp_path)
    card["uniqueness"][stage][0][field] = value
    assert assess(card, tmp_path)["status"] == "BLOCKED"


def test_leakage_canary_and_missing_feature(tmp_path):
    card = eligible_record(tmp_path)
    card["canaries"][0]["auc"] = 0.901
    assert assess(card, tmp_path)["status"] == "BLOCKED"
    card = eligible_record(tmp_path)
    card["feature_names"].append("untested")
    assert assess(card, tmp_path)["status"] == "BLOCKED"


def test_hash_and_path_gate(tmp_path):
    card = eligible_record(tmp_path)
    card["raster_sha256"] = "wrong"
    assert assess(card, tmp_path)["status"] == "BLOCKED"
    card["artifact"] = "../../outside.tif"
    assert assess(card, tmp_path)["status"] == "BLOCKED"


def test_shared_metric_matches_bruteforce():
    rng = np.random.default_rng(81)
    pred = rng.random((11, 13)) * (rng.random((11, 13)) > 0.8)
    truth = rng.random((11, 13)) > 0.9
    exact = metric.dti_exact(pred, truth)
    brute = metric.dti_bruteforce(pred, truth)
    assert exact["dti"] == pytest.approx(brute["dti"])


def test_visible_pixels_are_masked_by_shared_evaluator():
    truth = np.zeros((12, 12), bool)
    truth[5, 5] = True
    known = np.zeros_like(truth)
    known[8, 8] = True
    pred = truth.astype(float)
    pred[known] = 1
    fold = {"region": np.ones_like(truth), "visible": known, "truth": truth}
    result, terms = evaluate_holdout.evaluate(pred, fold, np.ones_like(truth))
    assert result["dti"] == pytest.approx(1)
    assert result["n_emitted"] == 1
    assert terms[:, 3].sum() == 1


def test_literal_overlap_three_pixels():
    a, b = np.zeros((20, 20)), np.zeros((20, 20))
    a[8, 8], b[8, 11] = 1, 1
    assert uniqueness.dot_overlap(a, b) == 1


def write_tif(path, array, **changes):
    profile = dict(
        driver="GTiff",
        width=array.shape[1],
        height=array.shape[0],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=from_origin(100, 200, 10, 10),
    )
    profile.update(changes)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype("float32"), 1)


@pytest.mark.parametrize("bad", [-1, 1.001, np.nan, np.inf])
def test_raw_invalid_values_fail_even_when_nodata_masked(tmp_path, bad):
    sample, candidate = tmp_path / "sample.tif", tmp_path / "test.tif"
    write_tif(sample, np.ones((4, 5)))
    a = np.zeros((4, 5))
    a[1, 1] = bad
    write_tif(candidate, a, nodata=bad if np.isfinite(bad) else np.nan)
    assert not validate_artifact(candidate, sample)["ok"]


def test_format_valid_and_wrong_grid(tmp_path):
    sample, candidate = tmp_path / "sample.tif", tmp_path / "test.tif"
    write_tif(sample, np.ones((4, 5)))
    write_tif(candidate, np.zeros((4, 5)))
    assert validate_artifact(candidate, sample)["ok"]
    write_tif(candidate, np.zeros((4, 5)), crs="EPSG:4326")
    assert not validate_artifact(candidate, sample)["ok"]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(v for k, v in attrs if k in ("href", "src"))


def test_static_site_local_links_exist():
    for file in (ROOT / "docs").glob("*.html"):
        parser = Links()
        parser.feed(file.read_text())
        for link in parser.links:
            if not link.startswith(("https:", "http:", "#")):
                assert (file.parent / link.split("#")[0]).is_file(), (file, link)


@pytest.mark.parametrize("count", [None, -1, 4, 1.5, True])
def test_invalid_experiment_budget_blocks(tmp_path, count):
    card = eligible_record(tmp_path)
    card["experiment_count"] = count
    assert assess(card, tmp_path)["status"] == "BLOCKED"


def test_transform_shape_and_interior_nan(tmp_path):
    sample, candidate = tmp_path / "sample.tif", tmp_path / "test.tif"
    write_tif(sample, np.ones((4, 5)))
    write_tif(candidate, np.zeros((4, 5)), transform=from_origin(101, 200, 10, 10))
    assert not validate_artifact(candidate, sample)["transform_match"]
    write_tif(candidate, np.zeros((3, 5)))
    assert not validate_artifact(candidate, sample)["shape_match"]
    a = np.zeros((4, 5))
    a[2, 3] = np.nan
    write_tif(candidate, a)
    assert not validate_artifact(candidate, sample)["no_nan_inside"]
