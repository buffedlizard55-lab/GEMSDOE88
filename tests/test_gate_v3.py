"""Fast synthetic tests for the v3 gate (no data/ dependency)."""
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems88 import gate  # noqa: E402

H, W = 60, 80
TR = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def _write(path, arr, *, nodata=None, dtype="float32", count=1, compress="lzw", tiled=False):
    prof = dict(driver="GTiff", height=H, width=W, count=count, dtype=dtype, crs="EPSG:32611",
                transform=TR, compress=compress, nodata=nodata)
    if tiled:
        prof.update(tiled=True, blockxsize=16, blockysize=16)
    with rasterio.open(path, "w", **prof) as ds:
        for i in range(count):
            ds.write(arr.astype(dtype), i + 1)


@pytest.fixture()
def world(tmp_path):
    fp = np.zeros((H, W), bool)
    fp[5:55, 5:75] = True
    sample = np.where(fp, 0.0, np.nan).astype("float32")
    sp = tmp_path / "sample.tif"
    _write(sp, sample, nodata=np.nan)
    return tmp_path, fp, sp


def _cand(fp, pts):
    a = np.zeros((H, W), "float32")
    for y, x in pts:
        a[y, x] = 1.0
    return a


def test_portal_validate_accepts_clean_file(world):
    tmp, fp, sp = world
    c = tmp / "c.tif"
    _write(c, _cand(fp, [(10, 10), (20, 30)]))
    r = gate.portal_validate(c, sp, fp)
    assert r["ok"], r["problems"]
    assert r["checks"]["portal_range_check_nan_strict"] and r["n_dots"] == 2


@pytest.mark.parametrize("mutate,expected", [
    ("nan", "all_finite"),
    ("over", "max_le_1"),
    ("neg", "min_ge_0"),
])
def test_portal_validate_rejects_bad_values(world, mutate, expected):
    tmp, fp, sp = world
    a = _cand(fp, [(10, 10)])
    if mutate == "nan":
        a[0, 0] = np.nan
    elif mutate == "over":
        a[10, 10] = 1.0000001
    else:
        a[11, 11] = -1e-6
    c = tmp / f"{mutate}.tif"
    _write(c, a)
    r = gate.portal_validate(c, sp, fp)
    assert not r["ok"] and r["checks"][expected] is False


def test_portal_validate_rejects_wrong_dtype_bands_and_nodata(world):
    tmp, fp, sp = world
    c = tmp / "f64.tif"
    _write(c, _cand(fp, [(10, 10)]), dtype="float64")
    assert not gate.portal_validate(c, sp, fp)["ok"]
    c2 = tmp / "two.tif"
    _write(c2, _cand(fp, [(10, 10)]), count=2)
    assert not gate.portal_validate(c2, sp, fp)["ok"]
    c3 = tmp / "nd.tif"
    _write(c3, _cand(fp, [(10, 10)]), nodata=-9999.0)
    assert not gate.portal_validate(c3, sp, fp)["ok"]


def test_zip_must_hold_exactly_one_flat_tif(world):
    tmp, fp, sp = world
    c = tmp / "c.tif"
    _write(c, _cand(fp, [(10, 10)]))
    z1 = tmp / "ok.zip"
    with zipfile.ZipFile(z1, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(c, "c.tif")
    assert gate.portal_validate(z1, sp, fp)["ok"]
    z2 = tmp / "two.zip"
    with zipfile.ZipFile(z2, "w") as z:
        z.write(c, "c.tif")
        z.writestr("readme.txt", "x")
    assert not gate.portal_validate(z2, sp, fp)["ok"]
    z3 = tmp / "dir.zip"
    with zipfile.ZipFile(z3, "w") as z:
        z.write(c, "sub/c.tif")
    assert not gate.portal_validate(z3, sp, fp)["ok"]


def test_layout_parity_flag(world):
    tmp, fp, sp = world
    c = tmp / "tiled.tif"
    _write(c, _cand(fp, [(10, 10)]), compress="deflate", tiled=True)
    r = gate.portal_validate(c, sp, fp)
    assert r["ok"] and r["layout_parity_with_sample"] is False


def test_uniqueness_literal_vs_like_for_like_and_vacuity(world):
    tmp, fp, sp = world
    rng = np.random.default_rng(1)
    ys, xs = np.nonzero(fp)
    # candidate: dots in the left half
    left = [(y, x) for y, x in zip(ys, xs) if x < 30][::37]
    cand = tmp / "cand.tif"
    _write(cand, _cand(fp, left))
    # sparse registry raster far from candidate (right half) -> pass
    right = [(y, x) for y, x in zip(ys, xs) if x > 60][::31]
    far = tmp / "far.tif"
    _write(far, _cand(fp, right))
    # sparse raster identical to candidate -> blocks both readings
    same = tmp / "same.tif"
    _write(same, _cand(fp, left))
    # dense raster: positive on the entire footprint, with highest values in the RIGHT half
    dense = np.where(fp, 0.05, 0.0).astype("float32")
    dense[:, 60:] = np.where(fp[:, 60:], 0.9 + 0.001 * rng.random((H, W - 60)), 0.0)
    dn = tmp / "dense.tif"
    _write(dn, dense.astype("float32"))
    rep = gate.uniqueness_report(cand, [("far", far), ("dense", dn)], fp)
    assert rep["unique_like_for_like"] is True
    assert rep["unique_literal"] is False and "dense" in rep["literal_blockers"]
    assert rep["vacuity_witness"]["literal_rule_vacuous"] is True
    rep2 = gate.uniqueness_report(cand, [("far", far), ("same", same), ("dense", dn)], fp)
    assert rep2["unique_like_for_like"] is False and "same" in rep2["like_for_like_blockers"]


def test_decide_matrix():
    ok_portal = dict(ok=True, problems=[])
    uniq_ok = dict(unique_like_for_like=True, unique_literal=False, literal_blockers=["dense"], like_for_like_blockers=[])
    v = gate.decide(portal=ok_portal, uniqueness=uniq_ok, canary_passed=True, holdout_beats_bar=True,
                    name="gems88-new-1", note="short note", used_names=["old"])
    assert not v["ok_to_submit"] and v["ok_to_download"]
    assert not v["eligible_for_selector"]
    assert any("literal registry rule" in r for r in v["blocking_reasons"])
    v2 = gate.decide(portal=ok_portal, uniqueness=uniq_ok, canary_passed=True, holdout_beats_bar=False,
                     name="gems88-new-1", note="n", used_names=[])
    assert v2["ok_to_download"] and not v2["ok_to_submit"] and any(r.startswith("HOLDOUT") for r in v2["blocking_reasons"])
    v3 = gate.decide(portal=dict(ok=False, problems=["x"]), uniqueness=uniq_ok, canary_passed=True,
                     holdout_beats_bar=True, name="a", note="n", used_names=[])
    assert not v3["ok_to_download"] and not v3["ok_to_submit"]
    v4 = gate.decide(portal=ok_portal, uniqueness=uniq_ok, canary_passed=True, holdout_beats_bar=True,
                     name="a" * 141, note="n", used_names=[])
    assert not v4["ok_to_submit"]
    v5 = gate.decide(portal=ok_portal, uniqueness=uniq_ok, canary_passed=True, holdout_beats_bar=True,
                     name="dup", note="n", used_names=["dup"])
    assert not v5["ok_to_submit"]


def test_spearman_binary_matches_scipy():
    from scipy.stats import spearmanr
    rng = np.random.default_rng(2)
    fp = np.ones((30, 30), bool)
    a = (rng.random((30, 30)) > 0.9).astype("float32")
    b = (rng.random((30, 30)) > 0.8).astype("float32")
    assert gate.spearman_on_footprint(a, b, fp) == pytest.approx(spearmanr(a.ravel(), b.ravel())[0], abs=1e-9)
    c = rng.random((30, 30)).astype("float32")
    assert gate.spearman_on_footprint(a, c, fp) == pytest.approx(spearmanr(a.ravel(), c.ravel())[0], abs=1e-9)


def _decision(**overrides):
    args = dict(portal={"ok": True, "problems": []},
                uniqueness={"unique_literal": True, "registry_complete": True,
                            "surface_checked": True, "literal_blockers": []},
                canary_passed=True, holdout_beats_bar=True,
                name="synthetic-only", note="unit test, not geological evidence", used_names=[])
    args.update(overrides)
    return gate.decide(**args)


def test_local_pass_is_selector_eligibility_not_slot_approval():
    result = _decision()
    assert result["eligible_for_selector"] is True
    assert result["ok_to_submit"] is False
    assert result["approved_for_weekly_slot"] is False
    assert "SELECTOR REQUIRED" in result["label"]


@pytest.mark.parametrize("key,value", [
    ("unique_literal", False), ("unique_literal", None),
    ("registry_complete", False), ("surface_checked", False),
    ("unique_literal", "true"),
])
def test_compatibility_gate_fails_closed(key, value):
    u = dict(unique_literal=True, registry_complete=True, surface_checked=True)
    u[key] = value
    result = _decision(uniqueness=u)
    assert not result["eligible_for_selector"] and not result["ok_to_submit"]


@pytest.mark.parametrize("name,note", [(None, "n"), ("a", None), ("   ", "n"), ("a", " ")])
def test_invalid_identity_is_blocked_without_exception(name, note):
    result = _decision(name=name, note=note)
    assert not result["eligible_for_selector"] and not result["ok_to_submit"]


def test_empty_registry_never_unique(world):
    tmp, fp, _ = world
    c = tmp / "c.tif"
    _write(c, _cand(fp, [(10, 10)]))
    report = gate.uniqueness_report(c, [], fp)
    assert not report["unique_literal"] and not report["unique_like_for_like"]
    assert not report["registry_complete"] and not report["surface_checked"]


def test_equal_support_different_values_do_not_share_rank_cache(world):
    tmp, fp, _ = world
    a = np.zeros((H, W), np.float32)
    a[fp] = np.linspace(0.01, 1.0, int(fp.sum()))
    b = np.where(fp, 1.01 - a, 0).astype(np.float32)
    c, one, two = (tmp / n for n in ("c.tif", "one.tif", "two.tif"))
    for p, values in ((c, a), (one, a), (two, b)):
        _write(p, values)
    report = gate.uniqueness_report(c, [("one", one), ("two", two)], fp, surface=a)
    r1, r2 = report["rows"]
    assert "duplicate_of" not in r2
    assert r1["rho_final"] == pytest.approx(1.0)
    assert r2["rho_final"] == pytest.approx(-1.0)


def test_surface_positive_support_is_checked_before_placement(world):
    tmp, fp, _ = world
    cand, prior = tmp / "c.tif", tmp / "p.tif"
    a = _cand(fp, [(10, 10)])
    b = _cand(fp, [(40, 65)])
    _write(cand, a)
    _write(prior, b)
    surface = a + b
    report = gate.uniqueness_report(cand, [("prior", prior)], fp, surface=surface)
    row = report["rows"][0]
    assert report["surface_checked"] is True
    assert row["literal_overlap_3px"] == 0
    assert row["surface_literal_overlap_3px"] == .5
    surface = b + a * 0  # placement no longer resembles its input: both phases bind
    report = gate.uniqueness_report(cand, [("prior", prior)], fp, surface=surface)
    assert report["rows"][0]["surface_literal_overlap_3px"] == 1
    assert report["unique_literal"] is False


@pytest.mark.parametrize("kind", ["shape", "nan"])
def test_invalid_surface_rejected(world, kind):
    tmp, fp, _ = world
    c = tmp / "c.tif"
    a = _cand(fp, [(10, 10)])
    _write(c, a)
    surface = a[:-1] if kind == "shape" else np.where(fp, np.nan, 0)
    with pytest.raises(ValueError, match="surface"):
        gate.uniqueness_report(c, [], fp, surface=surface)


def test_empty_effective_dot_request(world):
    _, fp, _ = world
    assert not gate.effective_dots(fp.astype(np.float32), fp, 0).any()
