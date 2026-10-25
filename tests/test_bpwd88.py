"""Automated unit and release-artifact verification tests for H88-BPWD (`tests/test_bpwd88.py`)."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
import tifffile
from scipy import fft as sp_fft
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "vendor", ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from gems88 import bpwd as psgv, gate  # noqa: E402
from validate_bpwd88 import main as validate_bpwd88_main, bpwd88_report  # noqa: E402


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_baranov_pseudogravity_recovers_poisson_gravity_step():
    """Exact 2D FFT Baranov integration of a Poisson RTP derivative recovers the basement step."""
    ny, nx = 224, 224
    fp = np.ones((ny, nx), dtype=bool)
    fp[:16, :] = False
    fp[-16:, :] = False
    fp[:, :16] = False
    fp[:, -16:] = False
    d_out, near_idx = ndi.distance_transform_edt(~fp, return_distances=True, return_indices=True)

    _, xx = np.indices((ny, nx), dtype=np.float32)
    g_true = -np.tanh((xx - 112.0) / 5.5).astype(np.float32)
    g_buf, off = psgv.prepare_tapered_fft_grid(g_true, fp, near_idx, d_out.astype(np.float32), pad_px=32)
    k_rad = psgv.spectral_radial_wavenumber(g_buf.shape, cell_m=100.0)
    spec_g = sp_fft.rfft2(g_buf, workers=2)

    # Exact Poisson 1VD relation: F{T_RTP}(k) = 2*pi*|k| * F{g}(k)
    rtp_full = sp_fft.irfft2(spec_g * (2.0 * np.pi * k_rad), s=g_buf.shape, workers=2)
    rtp_obs = rtp_full[off[0] : off[0] + ny, off[1] : off[1] + nx]
    rtp_buf, _ = psgv.prepare_tapered_fft_grid(rtp_obs, fp, near_idx, d_out.astype(np.float32), pad_px=32)
    spec_r = sp_fft.rfft2(rtp_buf, workers=2)
    psg_rec = psgv.baranov_pseudogravity_2d(spec_r, k_rad, g_buf.shape, off, (ny, nx), stabilizer_wavelength_m=60_000.0)

    inner = (slice(36, 188), slice(36, 188))
    corr = float(np.corrcoef(g_true[inner].ravel(), psg_rec[inner].ravel())[0, 1])
    assert corr > 0.985


def test_upward_continuation_and_60deg_updip_backprojection():
    """Upward continuation attenuates short wavelengths monotonically and 60-deg back-projection hits z=0 trace."""
    ny, nx = 192, 192
    fp = np.ones((ny, nx), dtype=bool)
    d_out, near_idx = ndi.distance_transform_edt(~fp, return_distances=True, return_indices=True)
    _, xx = np.indices((ny, nx), dtype=np.float32)
    wave = np.sin(2.0 * np.pi * xx / 16.0).astype(np.float32)
    buf, off = psgv.prepare_tapered_fft_grid(wave, fp, near_idx, d_out.astype(np.float32), pad_px=24)
    k_rad = psgv.spectral_radial_wavenumber(buf.shape, cell_m=100.0)
    spec = sp_fft.rfft2(buf, workers=2)

    u200 = psgv.upward_continue_2d(spec, k_rad, 200.0, buf.shape, off, (ny, nx))
    u1400 = psgv.upward_continue_2d(spec, k_rad, 1400.0, buf.shape, off, (ny, nx))
    assert float(np.std(u1400)) < 0.25 * float(np.std(u200))

    # Surface trace at x=96 dipping east (+x hanging wall) -> worm observed at x=101 for dr=5 px
    deep_worm = np.exp(-0.5 * ((xx - 101.0) / 1.4) ** 2).astype(np.float32)
    fw_ny = np.zeros_like(deep_worm)
    fw_nx = -np.ones_like(deep_worm)
    z_base = np.full_like(deep_worm, 5.0 * 100.0 * psgv.TAN_60)
    z0 = psgv._advect_updip_to_z0(deep_worm, fw_ny, fw_nx, z_base, fp, max_shift_px=12.0)
    assert int(np.argmax(z0[96, :])) == 96


def test_tri_specialist_poe_pool_invariants():
    rng = np.random.default_rng(88)
    p1 = rng.uniform(0.01, 0.4, size=500).astype(np.float32)
    m1 = np.clip(p1 + rng.uniform(0.0, 0.3, size=500), p1, 0.99).astype(np.float32)
    p2 = rng.uniform(0.01, 0.4, size=500).astype(np.float32)
    m2 = np.clip(p2 + rng.uniform(0.0, 0.3, size=500), p2, 0.99).astype(np.float32)
    p3 = rng.uniform(0.01, 0.4, size=500).astype(np.float32)
    m3 = np.clip(p3 + rng.uniform(0.0, 0.3, size=500), p3, 0.99).astype(np.float32)
    dv = np.linspace(0.0, 50.0, 500, dtype=np.float32)
    po, mo = psgv.tri_specialist_poe_pool(p1, m1, p2, m2, p3, m3, dv)
    assert np.isfinite(po).all() and np.isfinite(mo).all()
    assert bool(np.all((po >= 0.0) & (po <= 1.0)))
    assert bool(np.all((mo >= po) & (mo <= 1.0)))


def test_bpwd_memmap_builder_never_touches_catalogue():
    """AST static audit: ``build_or_load_psgv_memmap`` in ``bpwd.py`` has zero access to ``catalogue`` or ``existing_faults``."""
    src_text = (ROOT / "src/gems88/bpwd.py").read_text(encoding="utf-8")
    tree = ast.parse(src_text)
    fn_nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_or_load_psgv_memmap"]
    assert len(fn_nodes) == 1
    seg = ast.get_source_segment(src_text, fn_nodes[0]) or ""
    assert "existing_faults" not in seg
    for node in ast.walk(fn_nodes[0]):
        if isinstance(node, ast.Attribute):
            assert node.attr != "catalogue"


def test_bpwd88_preregistration_holdout_record_and_artifact_integrity():
    pre_reg = ROOT / "registry/preregistration_bpwd88.json"
    pre_doc = ROOT / "docs/data/preregistration_bpwd88.json"
    rc_reg = ROOT / "registry/bpwd88_run_card.json"
    rc_doc = ROOT / "docs/data/bpwd88_run_card.json"
    rc_ev = ROOT / "evidence/bpwd88_run_card.json"
    gv_reg = ROOT / "registry/bpwd88_gate_v3.json"
    gv_doc = ROOT / "docs/data/bpwd88_gate_v3.json"

    assert _sha256(pre_reg) == _sha256(pre_doc)
    assert _sha256(rc_reg) == _sha256(rc_doc) == _sha256(rc_ev)
    assert _sha256(gv_reg) == _sha256(gv_doc)

    pre = json.loads(pre_reg.read_text(encoding="utf-8"))
    rc = json.loads(rc_reg.read_text(encoding="utf-8"))
    assert pre["frozen_before_feature_canary_holdout_or_production_build"] is True
    assert len(pre["ranked_candidate_hypotheses"]) == 5
    assert pre["psgv20_features"] == list(psgv.PSGV_FEATURES)

    assert rc["experiments_executed"] == rc["experiment_budget_max"] == 3
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["features_tested"] == 107
    assert rc["leakage_canary"]["max_symmetric_auc"] <= 0.90
    assert rc["leakage_canary"]["zero_test_quadrant_leakage_scramble_equal"] is True

    ho = rc["holdout_dti"]
    assert ho["evidence_class"] == "HOLDOUT-DTI"
    assert ho["evaluator_version"] == "gems57-pooled-hide-v2"
    assert ho["withheld_positive_pixels"] == 22893
    assert ho["candidate_exp03"]["dti"] > ho["control_h88_hgvc_incumbent"]["dti"]
    assert ho["candidate_exp03"]["dti"] > 0.205
    assert ho["paired_delta_vs_hgvc_overall"]["delta"] > 0.003
    assert ho["paired_delta_vs_hgvc_overall"]["ci95"][0] > 0.0
    assert ho["paired_delta_vs_adhr_overall"]["delta"] > 0.011
    assert ho["paired_delta_vs_adhr_overall"]["ci95"][0] > 0.0
    assert ho["folds_won_vs_hgvc"] >= 6
    assert ho["folds_won_vs_adhr"] == 8

    # Verify GeoTIFF + single-member ZIP + permissions + multi-decoder parity
    tif_path = ROOT / rc["download"]
    zip_path = ROOT / rc["zip_download"]
    sub_copy = ROOT / rc["repo_copy"]
    for p in (tif_path, zip_path, sub_copy):
        assert p.is_file()
        assert stat.S_IMODE(os.stat(p).st_mode) & stat.S_IROTH

    e = gate.EXPECTED
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert ds.crs.to_epsg() == e["epsg"] == 32611
        assert ds.shape == e["shape"] == (3730, 3292)
        assert tuple(ds.transform)[:6] == e["transform"]
        assert ds.nodata is None
        assert ds.block_shapes[0] == (1, 3292)
    assert np.array_equal(arr, tifffile.imread(tif_path))
    assert np.isfinite(arr).all() and bool(np.all((arr >= 0.0) & (arr <= 1.0)))
    assert int((arr > 0.5).sum()) == 37654

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert hashlib.sha256(zf.read(tif_path.name)).hexdigest() == rc["raster_sha256"]

    # Standalone validator exit codes (0 for research download, 2 for --require-submit)
    rep = bpwd88_report(ROOT)
    assert rep["ok_to_download"] is True
    assert rep["all_5_discriminating_gates_pass"] is True
    assert rep["beats_hgvc_holdout_best"] is True
    assert rep["worst_like_for_like_overlap_3px"] <= 0.70
    assert rep["ok_to_submit"] is False
    assert rep["verdict"] == "negative"
    assert validate_bpwd88_main([]) == 0
    assert validate_bpwd88_main(["--require-submit"]) == 2


def test_bpwd_live_banner_js_fails_closed_on_missing_or_valid_feed():
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        return
    snippet = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const bpwdBanner = {textContent: 'init'};
const fail = process.env.MISSING_BPWD === '1';
const env = {
  document: {
    querySelector: sel => sel === '[data-bpwd-status]' ? bpwdBanner : null,
    querySelectorAll: () => [],
  },
  fetch: async url => {
    if (fail && url === 'data/bpwd88_run_card.json') return {ok: false};
    const data = JSON.parse(fs.readFileSync(path.join('docs', url), 'utf8'));
    return {ok: true, json: async () => data};
  },
  setTimeout, clearTimeout, console, Date,
};
vm.runInNewContext(fs.readFileSync('docs/assets/site.js', 'utf8'), env);
setImmediate(() => {
  if (fail) {
    if (bpwdBanner.textContent !== 'BPWD PRE-FLIGHT UNAVAILABLE — DO NOT SUBMIT') process.exitCode = 1;
  } else {
    if (!bpwdBanner.textContent.includes('H88-BPWD HOLDOUT-DTI 0.205991 RECORD') || !bpwdBanner.textContent.includes('DO NOT SUBMIT')) process.exitCode = 1;
  }
});
"""
    for flag in ("0", "1"):
        r = subprocess.run([node, "-e", snippet], cwd=ROOT, env={**os.environ, "MISSING_BPWD": flag}, check=False)
        assert r.returncode == 0

