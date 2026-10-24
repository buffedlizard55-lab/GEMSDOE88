"""Tests for AXIS=TRACKB (Phase 2 geologist trace GeoJSON + 3 controlled variants)."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_trackb_variants as tb  # noqa: E402

EXPECTED_PARENT_R1 = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
EXPECTED_VARIANTS = {
    "speckle10minus": {
        "id": "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBspeckle10minus-20261023-3360100c",
        "sha256_nan": "3360100cde278dd83de9da97664c1b2c0218155ee86a62dcfcd2062ebcc7e20a",
        "sha256_zeros": "aa655ef6082b4ffe18a823a03c81b00cc948789f195196631150d16f0ea7e3eb",
        "n_dots": 33889,
        "pct": 10.0,
        "pred": "MODEL:+0.003",
    },
    "traceext10": {
        "id": "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtraceext10-20261023-05256d87",
        "sha256_nan": "05256d87c0b46211b7c13f348e1dc02f1ede3f73b0169c788c7ccb00e504e859",
        "sha256_zeros": "16003173ddbe068541734cc638ec931ff824d9386d62f3026028fc79fb2dcf49",
        "n_dots": 37654,
        "pct": 10.0,
        "pred": "MODEL:+0.004",
    },
    "tracespine10": {
        "id": "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtracespine10-20261023-a3a183d1",
        "sha256_nan": "a3a183d163d1dec0b230b559bef46113c35dbb2f7f1e9ec46bc1e57e10c9947d",
        "sha256_zeros": "be47ad67baf2f6bb15b91b26ebd9a00ef44e2459867fe2591e74c7ba0436cf66",
        "n_dots": 37654,
        "pct": 10.0,
        "pred": "MODEL:-0.003",
    },
}
EXPECTED_GEOJSON_SHA256 = "4a1d05415928b2f2ebf885fb6af3342fc60d9a1c88460e790ece43c0a2dbc305"
SYNTH_TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 1. Pure synthetic unit tests (always run in CI without local rasters)
# ---------------------------------------------------------------------------


def test_synthetic_trace_extraction_and_corridor_veto() -> None:
    H, W = 40, 40
    foot = np.ones((H, W), dtype=bool)
    d_cat = np.full((H, W), 10.0, dtype=np.float32)
    mask = np.zeros((H, W), dtype=bool)
    w_field = np.full((H, W), 0.1, dtype=np.float32)

    # Straight N-S 5-dot chain spaced 3 px (300 m) apart -> 1.2 km trace (>= 1000 m)
    for k, y in enumerate([6, 9, 12, 15, 18]):
        mask[y, 10] = True
        w_field[y, 10] = 0.5 - 0.01 * k

    # A second chain blocked at midpoint by a catalogue fault (d_cat <= 3 px)
    for y in [6, 9, 12, 15, 18]:
        mask[y, 25] = True
        w_field[y, 25] = 0.4
    d_cat[10, 25] = 1.5  # blocks step (9,25)->(12,25); neither half reaches 1000 m

    # Isolated singletons -> must NOT form >= 1.0 km traces
    mask[32, 32] = True
    mask[35, 5] = True

    traces, trace_mask = tb.extract_strike_consistent_traces(mask, w_field, foot, d_cat, SYNTH_TRANSFORM)
    assert len(traces) == 1
    assert int(trace_mask.sum()) == 5
    tr = traces[0]
    assert tr["n_dots"] == 5
    assert tr["arc_length_m"] == pytest.approx(1200.0)
    assert tr["chord_length_m"] == pytest.approx(1200.0)
    assert tr["tortuosity"] == pytest.approx(1.0)
    assert tr["strike_coherence_rbar"] > 0.99
    assert tr["min_catalogue_dist_m"] > 300.0

    traces_2, _ = tb.extract_strike_consistent_traces(mask, w_field, foot, d_cat, SYNTH_TRANSFORM)
    assert [(t["rows"], t["cols"]) for t in traces_2] == [(t["rows"], t["cols"]) for t in traces]


def test_synthetic_tip_cone_and_spaced_marginal_dti_add() -> None:
    H, W = 40, 40
    foot = np.ones((H, W), dtype=bool)
    d_cat = np.full((H, W), 12.0, dtype=np.float32)
    base = np.zeros((H, W), dtype=bool)
    for y in [14, 17, 20, 23, 26]:
        base[y, 20] = True
    w_field = np.full((H, W), 0.25, dtype=np.float32)

    traces, _ = tb.extract_strike_consistent_traces(base, w_field, foot, d_cat, SYNTH_TRANSFORM)
    assert len(traces) == 1

    cone = tb.build_tip_extension_cone_mask(
        traces, foot, d_cat, min_dist_px=2.8, max_dist_px=9.5, max_angle_deg=25.0, min_cat_px=3.0
    ) & (~base)
    assert bool(cone[8, 20]) is True
    assert bool(cone[32, 20]) is True
    assert bool(cone[20, 28]) is False

    out = tb.select_spaced_exact_marginal_dti_add(
        base_mask=base,
        cand_mask=cone,
        w=w_field,
        n_add=4,
        min_sep_px=2.8,
    )
    added = out & (~base)
    assert int(added.sum()) == 4
    ys, xs = np.nonzero(out)
    pts = np.column_stack([xs.astype(float), ys.astype(float)])
    ay, ax = np.nonzero(added)
    for y0, x0 in zip(ay, ax):
        d2 = (pts[:, 0] - x0) ** 2 + (pts[:, 1] - y0) ** 2
        d2_nonzero = d2[d2 > 0]
        assert float(np.sqrt(d2_nonzero.min())) >= np.sqrt(8.0) - 1e-6


def test_synthetic_isolated_speckle_donor_preserves_traces() -> None:
    H, W = 30, 30
    foot = np.ones((H, W), dtype=bool)
    d_cat = np.full((H, W), 10.0, dtype=np.float32)
    r1 = np.zeros((H, W), dtype=bool)
    w_field = np.full((H, W), 0.2, dtype=np.float32)

    trace_pts = [(5, 5), (8, 5), (11, 5), (14, 5), (17, 5)]
    for y, x in trace_pts:
        r1[y, x] = True
        w_field[y, x] = 0.05  # deliberately low w so naive drop would kill trace if unprotected!

    speckles = [(5, 22), (16, 22), (25, 18)]
    for k, (y, x) in enumerate(speckles):
        r1[y, x] = True
        w_field[y, x] = 0.10 + 0.05 * k

    traces, trace_mask = tb.extract_strike_consistent_traces(r1, w_field, foot, d_cat, SYNTH_TRANSFORM)
    assert len(traces) == 1
    pruned, dropped, donor_stats = tb.select_isolated_speckle_donors(
        r1, trace_mask, w_field, n_drop=2, isolation_radius_px=4.5
    )
    assert int(dropped.sum()) == 2
    assert donor_stats["isolated_pool_count"] == 3
    assert donor_stats["n_dropped"] == 2
    assert donor_stats["trace_dots_preserved"] == 5
    for y, x in trace_pts:
        assert bool(pruned[y, x]) is True
    assert bool(pruned[25, 18]) is True
    assert bool(pruned[5, 22]) is False
    assert bool(pruned[16, 22]) is False


# ---------------------------------------------------------------------------
# 2. Tracked registry, GeoJSON, dossier, ledger, and mechanism-card tests
# ---------------------------------------------------------------------------


def test_preregistration_frozen_before_proxy() -> None:
    prereg = json.loads((ROOT / "registry" / "trackb_preregistration.json").read_text())
    assert prereg["axis"] == "TRACKB"
    assert prereg["frozen_before_any_variant_proxy"] is True
    assert prereg["seed"] == 20261023
    assert prereg["parents"]["r0"]["sha256_nan"] == (
        "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
    )
    assert prereg["parents"]["immediate_gate_clean_parent"]["id"] == EXPECTED_PARENT_R1
    arms = {a["value"]: a for a in prereg["variants"]}
    assert set(arms) == set(EXPECTED_VARIANTS)
    for val, exp in EXPECTED_VARIANTS.items():
        assert arms[val]["preregistered_predicted_change"] == exp["pred"]


def test_geojson_rfc7946_traces_and_geologist_paragraphs() -> None:
    gj_path = ROOT / "evidence" / "trackb_traces_geologist.geojson"
    assert gj_path.exists()
    assert _sha256(gj_path) == EXPECTED_GEOJSON_SHA256

    gj = json.loads(gj_path.read_text())
    assert gj["type"] == "FeatureCollection"
    feats = gj["features"]
    assert len(feats) == 1259

    seen_ids = set()
    for feat in feats:
        assert feat["type"] == "Feature"
        geom = feat["geometry"]
        assert geom["type"] == "LineString"
        coords = geom["coordinates"]
        assert len(coords) >= 3
        for lon, lat in coords:
            assert -121.5 <= lon <= -113.0
            assert 36.0 <= lat <= 42.5

        props = feat["properties"]
        tid = props["trace_id"]
        assert tid not in seen_ids
        seen_ids.add(tid)
        assert props["arc_length_m"] >= 1000.0
        assert props["chord_length_m"] >= 1000.0
        assert 1.0 <= props["tortuosity"] <= 1.2001
        assert props["min_catalogue_dist_m"] > 300.0
        para = props["geologist_evidence"]
        assert isinstance(para, str) and len(para) >= 180
        assert tid in para
        assert "ruling out" in para

    dossier = (ROOT / "evidence" / "trackb_geologist_dossier.md").read_text()
    assert EXPECTED_GEOJSON_SHA256 in dossier
    assert "TRACKB-0001" in dossier and "TRACKB-0025" in dossier


def test_trackb_receipts_validation_and_blind_sgmc_ordering() -> None:
    report = json.loads((ROOT / "evidence" / "trackb_axis_report.json").read_text())
    assert report["axis"] == "TRACKB"
    assert report["leakage_canaries"]["all_le_0_90"] is True
    assert report["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    assert report["trace_inventory"]["geojson_sha256"] == EXPECTED_GEOJSON_SHA256
    assert report["trace_inventory"]["trace_count"] == 1259
    assert (
        report["trace_inventory"]["trace_dot_mean_sgmc_credit"]
        > report["trace_inventory"]["isolated_donor_mean_sgmc_credit"]
    )

    by_val = {v["value"]: v for v in report["variants"]}
    assert set(by_val) == set(EXPECTED_VARIANTS)

    for val, exp in EXPECTED_VARIANTS.items():
        v = by_val[val]
        assert v["id"] == exp["id"]
        assert v["parent"] == EXPECTED_PARENT_R1
        assert v["sha256"] == exp["sha256_nan"]
        assert v["sha256_zeros"] == exp["sha256_zeros"]
        assert v["n_dots"] == exp["n_dots"]
        assert v["parent_diff"]["pct_changed_moved"] == pytest.approx(exp["pct"])
        assert 1.0 <= v["parent_diff"]["pct_changed_moved"] <= 50.0
        assert v["parent_diff"]["min_dist_catalogue_px"] > 3.0
        assert v["parent_diff"]["dots_le_3px"] == 0
        assert all(v["gates"].values())
        assert len(v["form_note"]) <= 140

        receipt_path = ROOT / "releases" / f"{exp['id']}.json"
        assert receipt_path.exists()
        rc = json.loads(receipt_path.read_text())
        assert rc["sha256"] == exp["sha256_nan"]
        assert rc["sha256_zeros"] == exp["sha256_zeros"]
        assert rc["geojson_traces"]["sha256"] == EXPECTED_GEOJSON_SHA256

    assert by_val["traceext10"]["nearest_neighbour_stats"]["added_min_nn_px"] >= 2.828
    sgmc_ext = by_val["traceext10"]["report_only_diagnostics"]["sgmc_control"]["dti"]
    sgmc_spine = by_val["tracespine10"]["report_only_diagnostics"]["sgmc_control"]["dti"]
    sgmc_minus = by_val["speckle10minus"]["report_only_diagnostics"]["sgmc_control"]["dti"]
    assert sgmc_ext > sgmc_spine + 0.005
    assert sgmc_ext > sgmc_minus + 0.005

    val_doc = json.loads((ROOT / "registry" / "trackb_variant_validation.json").read_text())
    assert val_doc["gates_all_pass"] is True
    assert len(val_doc["results"]) == 6
    assert all(item["gates_pass"] is True for item in val_doc["results"])


def test_ledger_and_mechanism_cards_complete_and_unique() -> None:
    with (ROOT / "ledger" / "submissions.csv").open() as f:
        rows = list(csv.DictReader(f))
    trackb_rows = [r for r in rows if r["axis"] == "TRACKB"]
    assert len(trackb_rows) == 3

    seen_pairs = set()
    seen_hashes = set()
    for r in rows:
        key = (r["parent"], r["axis"], r["value"])
        assert key not in seen_pairs, f"Duplicate (parent, axis, value): {key}"
        seen_pairs.add(key)
        for col in ("sha256", "sha256_zeros"):
            h = r[col]
            if h and not (col == "sha256_zeros" and h == r["sha256"]):  # single-file de-novo: no distinct twin
                assert h not in seen_hashes, f"Duplicate hash in ledger: {h}"
                seen_hashes.add(h)

    for r in trackb_rows:
        exp = EXPECTED_VARIANTS[r["value"]]
        assert r["id"] == exp["id"]
        assert r["parent"] == EXPECTED_PARENT_R1
        assert r["status"] == "BUILT"
        assert int(r["n_dots"]) == exp["n_dots"]
        assert float(r["pct_changed"]) == pytest.approx(exp["pct"])
        assert r["predicted_change"] == exp["pred"]
        assert r["receipt_score"] == ""

    mc = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
    required_fields = {
        "parent",
        "axis",
        "value",
        "hypothesis",
        "mechanism",
        "non_fault_mimic",
        "predicted_sign_size",
        "falsifier",
    }
    for exp in EXPECTED_VARIANTS.values():
        assert exp["id"] in mc
        card = mc[exp["id"]]
        assert card["axis"] == "TRACKB"
        assert required_fields.issubset(card.keys())
        for k in required_fields:
            assert str(card[k]).strip() != ""


@pytest.mark.skipif(
    not (
        ROOT
        / "releases"
        / "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-TRACKBtraceext10-20261023-05256d87.tif"
    ).exists(),
    reason="local gitignored GeoTIFFs not present in CI checkout",
)
def test_local_geotiffs_match_ledger_sha256() -> None:
    for exp in EXPECTED_VARIANTS.values():
        p_nan = ROOT / "releases" / f"{exp['id']}.tif"
        p_zer = ROOT / "releases" / f"{exp['id']}-zeros.tif"
        assert _sha256(p_nan) == exp["sha256_nan"]
        assert _sha256(p_zer) == exp["sha256_zeros"]
