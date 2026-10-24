"""Session 2026-10-24 release tests: run card, hash bindings, verdict/filename consistency, decision rules.

Only committed files are used, so these run in CI without the large input rasters.
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems88 import gate  # noqa: E402

GV = json.loads((ROOT / "registry/gate_verdict.json").read_text())
CARD = json.loads((ROOT / "registry/run_card_20261024.json").read_text())
NAME = GV["name"]
TIF = ROOT / "docs/downloads" / f"{NAME}.tif"
ZIP = ROOT / "docs/downloads" / f"{NAME}.zip"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_run_card_has_every_protocol_field():
    for key in ("hypothesis", "mechanism", "named_non_fault_mimics", "holdout", "overlap_vs_registry", "raster_sha256",
                "validator_output", "submission_name", "submission_note", "verdict", "canary", "gate", "limits"):
        assert key in CARD, key
    assert CARD["verdict"] in ("promote-to-selector-only", "negative")
    h = CARD["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["evaluator_version"] == "gems57-pooled-hide-v2"
    for arm in ("emitted_arm_overall", "emitted_arm_far_subset"):
        assert h[arm]["withheld_positives"] > 0 and len(h[arm]["ci95"]) == 2 and h[arm]["ci95"][0] <= h[arm]["dti"] <= h[arm]["ci95"][1]
    assert h["emitted_arm_overall"]["withheld_positives"] == 22893  # identical folds to the H88-ADHR run
    assert len(CARD["submission_name"]) <= 140 and 0 < len(CARD["submission_note"]) <= 140
    assert CARD["session"]["slots_spent"] == 0 and CARD["session"]["submissions_picked"] == 0
    assert CARD["session"]["experiments_used"] <= CARD["session"]["experiments_budget"] == 3
    assert "ORGANIZER-CONFIRMED" not in json.dumps(CARD["holdout"]).replace("no number here is ORGANIZER-CONFIRMED", "")


def test_site_copies_are_byte_identical():
    assert (ROOT / "docs/data/run-card-20261024.json").read_text() == (ROOT / "registry/run_card_20261024.json").read_text()
    assert (ROOT / "docs/data/gate-verdict.json").read_text() == (ROOT / "registry/gate_verdict.json").read_text()
    for name in ("h33_forensics_20261024", "proxy_calibration_20261024", "fleet_distance_prior_20261024", "halo_experiments_20261024",
                 "sibling_overlap_vs_R0_20261024"):
        assert sha(ROOT / "docs/evidence" / f"{name}.json") == sha(ROOT / "evidence" / f"{name}.json"), name
    for name in ("h33-forensics-20261024.md", "hypotheses-20261024.md"):
        assert sha(ROOT / "docs/research" / name) == sha(ROOT / "research" / name), name
    assert sha(ROOT / "docs/data/uniqueness_v3.json") == sha(ROOT / "registry/uniqueness_v3.json")


def test_hashes_and_zip_bind_to_the_files():
    assert sha(TIF) == CARD["raster_sha256"] == GV["sha256"]
    assert sha(ZIP) == CARD["zip_sha256"] == GV["zip_sha256"]
    with zipfile.ZipFile(ZIP) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()
    receipt = json.loads((ROOT / "docs/downloads" / f"{NAME}.json").read_text())
    assert receipt["sha256"] == sha(TIF) and receipt["name"] == NAME and receipt["note"] == CARD["submission_note"]


def test_verdict_is_encoded_in_the_file_name_and_consistent():
    assert GV["policy"] == "gems88-gate-v3" and CARD["gate"]["label"] == GV["label"]
    if GV["ok_to_submit"]:
        assert NAME.endswith("GATE-PASS") and CARD["verdict"] == "promote-to-selector-only" and not GV["blocking_reasons"]
    else:
        assert NAME.endswith("DO-NOT-SUBMIT") and CARD["verdict"] == "negative" and GV["blocking_reasons"]
    assert GV["ok_to_download"] is True


def test_file_reopens_like_the_portal_with_pinned_constants_and_sample_layout():
    e = gate.EXPECTED
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32" and ds.crs.to_epsg() == e["epsg"] and ds.shape == e["shape"]
        assert tuple(ds.transform)[:6] == e["transform"] and ds.nodata is None
        assert ds.profile["compress"] == "lzw" and not ds.profile["tiled"] and ds.block_shapes[0] == (1, e["shape"][1])
    assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    assert set(np.unique(a)) <= {0.0, 1.0}
    assert bool(np.all((a >= 0) & (a <= 1)))  # the NaN-strict portal reading
    with zipfile.ZipFile(ZIP) as z, rasterio.MemoryFile(z.read(TIF.name)) as mf, mf.open() as ds:
        assert np.array_equal(ds.read(1), a)


def test_validate_release_v3_passes_and_matches_verdict():
    from validate_release import release_report_v3
    rep = release_report_v3(ROOT)
    assert rep["ok_to_submit"] == GV["ok_to_submit"] and rep["raster_sha256"] == CARD["raster_sha256"]
    assert rep["unique_like_for_like"] is True


def test_site_guard_passes():
    import check_site
    check_site.main(ROOT)


def test_preregistration_precedes_results_and_rules_reproduce_the_verdicts():
    pre = json.loads((ROOT / "registry/preregistration_halo88.json").read_text())
    receipt = json.loads((ROOT / "docs/downloads" / f"{NAME}.json").read_text())
    assert pre["written_before_results"] is True and pre["written_utc"] < receipt["generated_utc"]
    ho = json.loads((ROOT / "evidence/halo_experiments_20261024.json").read_text())
    far = ho["pooled"]["far__candidate_fbmt"]
    allp = ho["pooled"]["all__candidate_fbmt"]
    # E1 keep rule: far DTI(fbmt) > far DTI(base) AND paired CI excludes 0
    d1 = far["paired_differences"]["base"]
    keep1 = far["scores"]["fbmt"]["dti"] > far["scores"]["base"]["dti"] and (d1["ci95"][0] > 0 or d1["ci95"][1] < 0)
    far_ccr = ho["pooled"]["far__candidate_fbmt_ccr"]["paired_differences"]["fbmt"]
    keep2 = far_ccr["delta"] > 0 and far_ccr["ci95"][0] > 0
    far_rcp = ho["pooled"]["far__candidate_fbmt_ccr_rcp"]["paired_differences"]["fbmt_ccr"]
    keep3 = far_rcp["delta"] > 0 and far_rcp["ci95"][0] > 0
    assert (keep1, keep2, keep3) == (False, False, False)
    assert {k: v["verdict"] for k, v in CARD["hypothesis"]["tested"].items()} == {"E1_FBMT": "negative", "E2_CCR": "negative", "E3_RCP": "null"}
    bar = CARD["holdout"]["bar"]
    beats = allp["scores"]["base"]["dti"] > bar["overall"] or far["scores"]["base"]["dti"] > bar["far"]
    assert beats == CARD["holdout"]["beats_bar"]
    assert ho["canary"]["max_symmetric_auc"] <= 0.90 and ho["canary"]["passed"]
    assert far["scores"]["base"]["withheld_positive_pixels"] == 10791 and allp["scores"]["base"]["withheld_positive_pixels"] == 22893


def test_uniqueness_report_is_complete_and_vacuity_witness_present():
    uq = json.loads((ROOT / "registry/uniqueness_v3.json").read_text())
    assert uq["missing"] == 0 and uq["registry_rasters"] >= 200 and uq["unique_like_for_like"] is True
    assert uq["vacuity_witness"]["literal_rule_vacuous"] is True and uq["vacuity_witness"]["literal_overlap"] > 0.70
    labels = " ".join(r["label"] for r in uq["rows"])
    for site in ("GEMSDOE86", "GEMSDOE87", "GEMSDOE89", "GEMSDOE92"):
        assert site in labels, site


def test_sibling_inventory_pins_every_site():
    inv = json.loads((ROOT / "registry/sibling_inventory.json").read_text())
    assert set(inv["sites"]) == {"GEMSDOE86", "GEMSDOE87", "GEMSDOE89", "GEMSDOE90", "GEMSDOE91", "GEMSDOE92"}
    for site, info in inv["sites"].items():
        assert len(info["commit"]) == 40
        assert all(len(r["sha256"]) == 64 for r in info["files"])


def _clone_release(tmp_path):
    import shutil
    for rel in ("registry/gate_verdict.json", "registry/run_card_20261024.json", "registry/uniqueness_v3.json",
                "docs/data/run-card-20261024.json", "evidence/halo_experiments_20261024.json", "registry/holdout_result.json",
                f"docs/downloads/{NAME}.json", f"docs/downloads/{NAME}.tif", f"docs/downloads/{NAME}.zip"):
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    return tmp_path


def test_release_validator_detects_a_hand_edited_verdict(tmp_path):
    from validate_release import release_report_v3
    root = _clone_release(tmp_path)
    release_report_v3(root)  # untouched copy verifies
    gv = json.loads((root / "registry/gate_verdict.json").read_text())
    gv["ok_to_submit"] = True
    gv["label"] = "OK TO DOWNLOAD - OK TO SUBMIT"
    gv["blocking_reasons"] = []
    (root / "registry/gate_verdict.json").write_text(json.dumps(gv))
    with pytest.raises(ValueError):
        release_report_v3(root)


def test_release_validator_detects_changed_bytes_and_removed_blocker(tmp_path):
    from validate_release import release_report_v3
    root = _clone_release(tmp_path)
    t = root / "docs/downloads" / f"{NAME}.tif"
    b = bytearray(t.read_bytes())
    b[-1] ^= 0xFF
    t.write_bytes(bytes(b))
    with pytest.raises(Exception):
        release_report_v3(root)
    root2 = _clone_release(tmp_path / "second")
    card = json.loads((root2 / "registry/run_card_20261024.json").read_text())
    card["holdout"]["beats_bar"] = True  # lie about the holdout while the verdict still blocks on it
    text = json.dumps(card)
    (root2 / "registry/run_card_20261024.json").write_text(text)
    (root2 / "docs/data/run-card-20261024.json").write_text(text)
    with pytest.raises(ValueError):
        release_report_v3(root2)
