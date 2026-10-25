import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cxl88_negative_card_consistent():
    ho = json.loads((ROOT / "evidence/cxl88_holdout_20261025.json").read_text())
    card = json.loads((ROOT / "registry/cxl88_run_card.json").read_text())
    cand = ho["pooled_overall"]["scores"]["exp02_cxl_poe_conduit"]
    assert cand["withheld_positive_pixels"] == 22893
    assert cand["dti"] < 0.2029470713394289
    assert ho["canary"]["max_symmetric_auc"] <= 0.90
    # phys44 control reproduces the stored HGVC-suite control exactly (evaluator integrity)
    assert abs(ho["pooled_overall"]["scores"]["phys44_zero_cat"]["dti"] - 0.1041632406049392) < 1e-9
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["new_tif_generated"] is False and card["raster_sha256"] is None


def test_cxl_features_declared():
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from gems88.cxl import CXL_FEATURES, CXL_SCHEMA_VERSION
    assert len(CXL_FEATURES) == 26 and CXL_SCHEMA_VERSION == "cxl88-26ch-v1"
