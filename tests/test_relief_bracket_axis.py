"""Tests for AXIS=RELIEF bracket family (parent R1 = PRUNEp3px): single-source tercile brackets.

One of two concurrently built RELIEF families (IR-88-36); the up/dn family is
covered by tests/test_relief_axis.py. This module covers only rng2*/bas2*.

Two layers, mirroring tests/test_snap_r1_axis.py:

* Unit tests on a synthetic grid for ``tercile_classes`` / ``relief_shift`` /
  ``saturation_stats`` — partition, fixed count, exact source->target move
  accounting, untouched-tercile invariance and determinism are properties of
  the algorithm, not of the shipped files.
* Artifact tests that re-read the three releases from disk and re-derive the
  MUST gates (format, zero catalogue mass, >3 px collar, fixed 37,654 count,
  12.00% parent diff vs R1, preregistered predictions, ledger + cards).

Artifact tests skip when the gitignored rasters are absent (fresh clone):
regenerate with ``python scripts/build_relief_bracket_variants.py`` after restoring
the pinned inputs. PROXY values are asserted to be *reported*, never gated.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_relief_bracket_variants as brv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
REPORT = ROOT / "evidence" / "relief_axis_report.json"
PREREG = ROOT / "registry" / "relief_preregistration.json"

EXPECTED = {
    "rng2bas12": ("h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFrng2bas12-20261023-56093882",
                  "560938824a6ddae52e45662fe506b7d0f5dea6191746ab517869d5e1205307bb", "MODEL:+0.008"),
    "rng2pmt12": ("h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFrng2pmt12-20261023-52717cf5",
                  "52717cf542642a2f9304d077f462dd0973d1f6b87f811c8d3b4039ff18c82521", "MODEL:+0.002"),
    "bas2rng12": ("h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-RELIEFbas2rng12-20261023-f4c6dc18",
                  "f4c6dc18f0cf5b2fa22f0c54374d1d3e7c782ef6246136e71770c188cbf6d663", "MODEL:-0.010"),
}
RELIEF_JSON = [
    p for v in EXPECTED
    for p in sorted(RELEASES.glob(f"{brv.R1_ID}-RELIEF{v}-*.json"))
    if (RELEASES / f"{p.stem}.tif").is_file()
]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def _toy():
    h = w_ = 36
    foot = np.ones((h, w_), dtype=bool)
    foot[0, :] = False
    catalogue = np.zeros((h, w_), dtype=bool)
    catalogue[3, 3] = True
    d_cat = distance_transform_edt(~catalogue)
    field = np.tile(np.arange(w_, dtype=np.float32), (h, 1))  # west low -> east high
    cls, q1, q2 = brv.tercile_classes(field, foot)
    mask = np.zeros((h, w_), dtype=bool)
    for r in (8, 14, 20, 26, 32):
        for c in (4, 8, 16, 20, 28, 32):
            mask[r, c] = True
    mask &= d_cat > 3.0
    rng = np.random.default_rng(brv.bp.SEED)
    w = (0.05 + 0.2 * rng.random((h, w_))).astype(np.float32) * foot
    cand = foot & (d_cat > 3.0)
    return foot, catalogue, d_cat, field, cls, q1, q2, mask, w, cand


def test_tercile_classes_partition_the_footprint():
    foot, _c, _d, field, cls, q1, q2, _m, _w, _cand = _toy()
    assert q1 < q2
    inside = [int(((cls == k) & foot).sum()) for k in range(3)]
    assert sum(inside) == int(foot.sum())
    assert max(inside) - min(inside) <= 40  # equal thirds up to ties/edge row
    assert (cls[~foot] == -1).all()
    assert (cls[foot & (field <= q1)] == 0).all()
    assert (cls[foot & (field > q2)] == 2).all()


def test_relief_shift_moves_exactly_n_source_to_target_at_fixed_count():
    foot, catalogue, d_cat, _f, cls, _q1, _q2, mask, w, cand = _toy()
    out, stats = brv.relief_shift(mask, cls, source=2, target=0, cand_base=cand, w=w, n_shift=3)
    assert int(out.sum()) == int(mask.sum())
    donors, receivers = mask & ~out, out & ~mask
    assert int(donors.sum()) == int(receivers.sum()) == 3
    assert (cls[donors] == 2).all() and (cls[receivers] == 0).all()
    assert float(d_cat[receivers].min()) > 3.0
    assert not out[catalogue].any()
    # untouched tercile count is parent-exact; source/target move by exactly n
    for k, delta in ((0, 3), (1, 0), (2, -3)):
        assert int((out & (cls == k)).sum()) == int((mask & (cls == k)).sum()) + delta
    assert stats["dots_after"]["T1_basin"] == stats["dots_before"]["T1_basin"] + 3
    assert stats["w_weighted_dti_before"] >= 0.0 and stats["w_weighted_dti_after"] >= 0.0


def test_relief_shift_is_deterministic_and_refuses_same_tercile():
    _foot, _c, _d, _f, cls, _q1, _q2, mask, w, cand = _toy()
    a, sa = brv.relief_shift(mask, cls, 2, 1, cand, w, 2)
    b, sb = brv.relief_shift(mask, cls, 2, 1, cand, w, 2)
    assert np.array_equal(a, b) and sa == sb
    with pytest.raises(ValueError):
        brv.relief_shift(mask, cls, 1, 1, cand, w, 1)
    with pytest.raises(ValueError):  # source tercile cannot fund an oversized shift
        brv.relief_shift(mask, cls, 0, 2, cand, w, 10_000)


def test_saturation_stats_reports_kernel_geometry():
    _foot, _c, _d, _f, cls, _q1, _q2, mask, w, cand = _toy()
    out, _ = brv.relief_shift(mask, cls, 2, 0, cand, w, 3)
    sat = brv.saturation_stats(mask, out, cand, cls)
    r = sat["receiver_dist_to_survivor_px"]
    assert 0.0 <= r["frac_le_2p8"] <= 1.0 and r["median"] >= 1.0
    assert 0.0 <= sat["donor_dist_to_survivor_after_removal_px"]["frac_gt_3"] <= 1.0
    assert set(sat["h19_support_within_3px_variant"]) == set(brv.TERCILE_NAMES)


def test_preregistration_matches_builder_variants_and_predictions():
    prereg = json.loads(PREREG.read_text())
    fixed = {v["value"]: v for v in prereg["variants_fixed_before_any_proxy"]}
    assert set(fixed) == {v for v, _s, _t, _p, _r in brv.VARIANTS}
    for value, source, target, pred, pred_range in brv.VARIANTS:
        assert fixed[value]["n_shift"] == brv.N_SHIFT == 4518
        assert fixed[value]["predicted_change_vs_parent_R1_live"] == f"MODEL:{pred}"
        assert fixed[value]["predicted_range_vs_parent_R1_live"] == pred_range
        assert fixed[value]["source"] == brv.TERCILE_NAMES[source]
        assert fixed[value]["target"] == brv.TERCILE_NAMES[target]
    assert prereg["parent"]["sha256_nan"] == brv.R1_SHA_NAN
    assert prereg["parent"]["sha256_zeros"] == brv.R1_SHA_ZEROS


# ---------------------------------------------------------------------------
# Artifact tests (skip without locally built rasters)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not RELIEF_JSON, reason="RELIEF releases not built in this checkout")
def test_relief_variants_pass_every_must_gate_on_reread():
    report = json.loads(REPORT.read_text())
    variants = {v["value"]: v for v in report["variants"]}
    assert set(variants) == set(EXPECTED)
    bridge = ROOT / "data" / "bridge"
    if not (bridge / "sample_submission.tif").is_file():
        pytest.skip("pinned bridge inputs not restored")
    with rasterio.open(bridge / "sample_submission.tif") as ds:
        tmpl = (ds.shape, ds.crs, ds.transform)
        foot = np.isfinite(ds.read(1))
    with rasterio.open(bridge / "existing_faults.tif") as ds:
        catalogue = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~catalogue)

    for value, (vid, sha, _pred) in EXPECTED.items():
        rec = variants[value]
        assert rec["id"] == vid and rec["sha256"] == sha
        assert rec["parent"] == brv.R1_ID and rec["n_dots"] == 37_654
        assert rec["parent_diff"]["n_added"] == rec["parent_diff"]["n_removed"] == 4518
        assert rec["parent_diff"]["pct_changed_moved"] == pytest.approx(12.00, abs=0.01)
        assert 1.0 <= rec["parent_diff"]["pct_changed_moved"] <= 50.0
        assert rec["parent_diff"]["dots_le_3px"] == 0
        assert rec["parent_diff"]["min_dist_catalogue_px"] > 3.0
        assert len(rec["form_note"]) <= 140

        p_nan, p_zeros = ROOT / rec["file_nan"], ROOT / rec["file_zeros"]
        receipt = json.loads((RELEASES / f"{vid}.json").read_text())
        assert receipt["sha256"] == rec["sha256"] == _sha256(p_nan)
        assert receipt["sha256_zeros"] == rec["sha256_zeros"] == _sha256(p_zeros)
        for tif_p, zip_key in ((p_nan, "zip_nan"), (p_zeros, "zip_zeros")):
            with zipfile.ZipFile(ROOT / rec[zip_key]) as zf:
                names = zf.namelist()
            assert names == [tif_p.name]

        with rasterio.open(p_nan) as dn, rasterio.open(p_zeros) as dz:
            assert (dn.shape, dn.crs, dn.transform) == tmpl == (dz.shape, dz.crs, dz.transform)
            assert dn.count == dz.count == 1 and dn.dtypes[0] == dz.dtypes[0] == "float32"
            assert str(dn.crs) == "EPSG:32611"
            arr_n, arr_z = dn.read(1), dz.read(1)
        assert np.isfinite(arr_n[foot]).all() and np.isnan(arr_n[~foot]).all()
        assert np.isfinite(arr_z).all() and (arr_z[~foot] == 0.0).all()
        assert np.array_equal(arr_n[foot], arr_z[foot])
        assert 0.0 <= float(arr_n[foot].min()) and float(arr_n[foot].max()) <= 1.0
        mask = arr_z > 0.5
        assert int(mask.sum()) == 37_654
        assert int((mask & catalogue).sum()) == 0
        assert float(d_cat[mask].min()) > 3.0

        # Tercile accounting is re-derived only where the 419 MB stack is present.
        feats = ROOT / "data" / "training_features.tif"
        if feats.is_file():
            det = brv.read_clean_band(feats, 12, foot)
            cls, q1, q2 = brv.tercile_classes(det, foot)
            assert q1 == pytest.approx(rec["relief_terciles"]["q1_footprint_tercile"])
            assert q2 == pytest.approx(rec["relief_terciles"]["q2_footprint_tercile"])
            after = {brv.TERCILE_NAMES[k]: int((mask & (cls == k)).sum()) for k in range(3)}
            assert after == rec["relief_statistics"]["dots_after"]


@pytest.mark.skipif(not RELIEF_JSON, reason="RELIEF releases not built in this checkout")
def test_relief_ledger_cards_and_hash_uniqueness():
    with LEDGER.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    all_hashes = [h for r in rows for h in (r["sha256"], r["sha256_zeros"]) if h]
    assert len(all_hashes) == len(set(all_hashes)), "duplicate SHA-256 in ledger"
    pairs = [(r["parent"], r["axis"], r["value"]) for r in rows if r["axis"] == "RELIEF"]
    assert len(pairs) == len(set(pairs)), "repeated (parent, axis, value) pair"
    assert {p[2] for p in pairs} >= set(EXPECTED)

    cards = json.loads(CARDS.read_text())
    relief_rows = {r["value"]: r for r in rows if r["axis"] == "RELIEF"}
    for value, (vid, sha, pred) in EXPECTED.items():
        row = relief_rows[value]
        assert row["id"] == vid and row["sha256"] == sha and row["parent"] == brv.R1_ID
        assert row["status"] == "BUILT" and row["n_dots"] == "37654"
        assert row["predicted_change"] == pred and not row["receipt_score"]
        card = cards[vid]
        for field in ("hypothesis", "mechanism", "non_fault_mimic",
                      "predicted_sign_size", "falsifier", "post_build_report_only"):
            assert card.get(field)
        assert "MODEL" in card["predicted_sign_size"]
        assert card["references"] and all(r["url"].startswith("https://") for r in card["references"])


@pytest.mark.skipif(not RELIEF_JSON, reason="RELIEF releases not built in this checkout")
def test_relief_proxies_are_reported_not_gated():
    report = json.loads(REPORT.read_text())
    r1_sgmc = report["parent_R1"]["diagnostics"]["sgmc_control"]["dti"]
    assert r1_sgmc == pytest.approx(0.096083, abs=1e-6)
    assert report["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    for v in report["variants"]:
        d = v["report_only_diagnostics"]
        # Hide-and-recover is degenerate by construction for >3 px files (IR-88-20),
        # and every MUST gate still passes: the proxy cannot fail a variant.
        assert d["holdout_proxy"]["dti"] == 0.0
        assert d["holdout_proxy"]["evidence_label"] == "PROXY"
        assert d["sgmc_control"]["evidence_label"] == "PROXY"
        assert d["sgmc_delta_vs_R1_PROXY"] == pytest.approx(
            d["sgmc_control"]["dti"] - r1_sgmc, abs=1e-6)
        assert all(v["gates"].values())
        sat = v["relief_statistics"]["post_build_saturation_REPORT_ONLY"]
        assert 0.0 <= sat["receiver_dist_to_survivor_px"]["frac_le_2p8"] <= 1.0
