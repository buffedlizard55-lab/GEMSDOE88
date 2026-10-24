import json
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]


def test_vess88_run_card_and_artifact_consistency():
    reg = json.loads((ROOT / "registry/vess88_run_card.json").read_text())
    web = json.loads((ROOT / "docs/data/vess88_run_card.json").read_text())
    assert reg == web
    assert reg["lane"] == "H88-VESS" and reg["verdict"] == "negative"
    assert reg["ok_to_download"] is True and reg["ok_to_submit"] is False
    assert reg["organizer_confirmed_score"] is None and reg["weekly_slots_used"] == 0
    hd = reg["holdout_dti"]
    assert hd["evidence_class"] == "HOLDOUT-DTI" and hd["evaluator_version"] == "gems57-pooled-hide-v2"
    assert hd["withheld_positive_pixels_overall"] == 22893
    assert hd["overall"]["dti"] > 0.196237
    assert hd["paired_delta_vs_adhr_incumbent"]["ci95"][0] > 0
    assert reg["leakage_canary"]["passed"] and reg["leakage_canary"]["max_symmetric_auc"] <= 0.90
    assert len(reg["submission"]["submission_name"]) <= 140
    assert len(reg["submission"]["submission_note"]) <= 140
    tif = ROOT / reg["submission"]["file"]
    archive = ROOT / reg["submission"]["zip_file"]
    assert tif.is_file() and archive.is_file() and "DO-NOT-SUBMIT" in tif.name
    with zipfile.ZipFile(archive) as z:
        assert z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes()
    # validator output frozen in the card: no NaN inside footprint, [0,1], grid match
    checks = reg["validator_output"]["checks"]
    assert checks["no_nan_anywhere"] and checks["range_0_1_guaranteed"]
    assert checks["crs_epsg_32611"] and checks["transform_matches_sample_submission"]
    # duplicate status is disclosed, not hidden
    corr = reg["correlation_overlap_vs_registry"]
    assert corr["surface_preplacement_max_abs_spearman"] <= 0.90
    assert corr["final_worst_like_for_like_overlap_3px"]["value"] > 0.70
    assert corr["unique_literal"] is False
