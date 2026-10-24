"""Unit and integration tests for Lane GTHC-88 (Geothermal Transtensional Hydrothermal-Conduit & SCRD)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from gems88 import gthc  # noqa: E402


def test_gthc_feature_kernels_synthetic_physics_and_mimic_suppression():
    shape = (48, 48)
    fp = np.ones(shape, dtype=bool)
    fp[:4, :] = False

    # 1. Uranium redox argillic halo
    u = np.full(shape, 100.0, dtype=np.float32)
    uk = np.full(shape, 90.0, dtype=np.float32)
    uth = np.full(shape, 70.0, dtype=np.float32)
    tc = np.full(shape, 120.0, dtype=np.float32)
    cond = np.zeros(shape, dtype=np.float32)
    tmi_vg = np.zeros(shape, dtype=np.float32)
    u[:, 22:26] = 220.0
    uk[:, 22:26] = 200.0
    uth[:, 22:26] = 170.0
    cond[:, 22:26] = 2.5
    tmi_vg[:, 22:26] = -15.0
    f1 = gthc.uranium_redox_argillic_halo(u, uk, uth, tc, cond, tmi_vg, fp)
    assert f1.shape == shape and np.isfinite(f1).all()
    assert np.all(f1[~fp] == 0.0)
    assert float(f1[10:40, 22:26].mean()) > float(f1[10:40, 6:16].mean())

    # 2. Upward magnetic basement admittance
    tmi_up150 = np.full(shape, 128.0, dtype=np.float32)
    tmi_up150[:, 24:] = 200.0
    grav_hg = np.zeros(shape, dtype=np.float32)
    grav_hg[:, 22:26] = 3.0
    dtb = np.full(shape, 600.0, dtype=np.float32)
    shear = np.full(shape, 30.0, dtype=np.float32)
    dilat = np.full(shape, 15.0, dtype=np.float32)
    f2 = gthc.upward_mag_basement_admittance(tmi_vg, tmi_up150, grav_hg, dtb, shear, dilat, fp)
    assert f2.shape == shape and np.isfinite(f2).all() and np.all(f2[~fp] == 0.0)
    assert float(f2[10:40, 22:26].mean()) > float(f2[10:40, 6:16].mean())

    # 3. Fluvial knickpoint & raised incision with pluvial shoreline attenuation
    chan_n = np.full(shape, 20.0, dtype=np.float32)
    knick_n = np.full(shape, 8.0, dtype=np.float32)
    raised_n = np.full(shape, 6.0, dtype=np.float32)
    valid_n = np.full(shape, 100.0, dtype=np.float32)
    ksn = np.full(shape, 150.0, dtype=np.float32)
    z_lahontan = np.full(shape, 1330.0, dtype=np.float32)
    z_tectonic = np.full(shape, 1800.0, dtype=np.float32)
    f3_shore = gthc.fluvial_knick_raised_incision(chan_n, knick_n, raised_n, valid_n, ksn, z_lahontan, fp)
    f3_tect = gthc.fluvial_knick_raised_incision(chan_n, knick_n, raised_n, valid_n, ksn, z_tectonic, fp)
    assert np.isfinite(f3_shore).all() and np.isfinite(f3_tect).all()
    assert float(f3_shore[fp].mean()) < float(f3_tect[fp].mean())

    # 4. Bajada aspect monocline
    aspect_coh = np.full(shape, 50.0, dtype=np.float32)
    steep_frac = np.full(shape, 20.0, dtype=np.float32)
    slope_std = np.full(shape, 40.0, dtype=np.float32)
    relief = np.full(shape, 30.0, dtype=np.float32)
    slope_p90 = np.full(shape, 80.0, dtype=np.float32)
    aspect_coh[:, 22:26] = 230.0
    steep_frac[:, 22:26] = 180.0
    slope_std[:, 22:26] = 10.0
    f4 = gthc.bajada_aspect_monocline(aspect_coh, steep_frac, slope_std, relief, slope_p90, fp)
    assert np.isfinite(f4).all() and np.all(f4[~fp] == 0.0)
    assert float(f4[10:40, 22:26].mean()) > float(f4[10:40, 6:16].mean())

    # 5. LiDAR normal-fault scarp polarity asymmetry
    ex_mean = np.full(shape, 80.0, dtype=np.float32)
    downface = np.full(shape, 50.0, dtype=np.float32)
    upface = np.full(shape, 50.0, dtype=np.float32)
    cross_max = np.full(shape, 40.0, dtype=np.float32)
    valid_lidar = np.full(shape, 200.0, dtype=np.float32)
    downface[:, 22:26] = 220.0
    upface[:, 22:26] = 20.0
    cross_max[:, 22:26] = 200.0
    f5 = gthc.lidar_normal_polarity_asymmetry(ex_mean, downface, upface, cross_max, valid_lidar, fp)
    assert np.isfinite(f5).all() and np.all(f5[~fp] == 0.0)
    assert float(f5[10:40, 22:26].mean()) > float(f5[10:40, 6:16].mean())


def test_scrd_completeness_regime_decomposition_preserves_expectation_and_lifts_blind_basin():
    rng = np.random.default_rng(88)
    n = 2000
    d_vis = np.linspace(2.5, 45.0, n, dtype=np.float32)
    # Structural head decays away from visible catalogue; physical head stays active in blind basin
    p_full = (0.12 * np.exp(-d_vis / 7.0)).astype(np.float32)
    m_full = np.clip(2.2 * p_full, p_full, 1.0).astype(np.float32)
    p_phys = rng.uniform(0.01, 0.08, size=n).astype(np.float32)
    p_phys[d_vis > 25.0] = 0.09
    m_phys = np.clip(2.4 * p_phys, p_phys, 1.0).astype(np.float32)

    k_target = 100.0
    p_scrd, m_scrd = gthc._fuse_scrd_log_odds(p_full, m_full, p_phys, m_phys, d_vis, k_target, beta_phys=0.42)
    assert p_scrd.shape == (n,) and m_scrd.shape == (n,)
    assert np.isfinite(p_scrd).all() and np.isfinite(m_scrd).all()
    assert np.all((p_scrd >= 0.0) & (p_scrd <= 1.0))
    assert np.all((m_scrd >= p_scrd) & (m_scrd <= 1.0))
    assert np.isclose(float(p_scrd.sum()), k_target, rtol=1e-3)
    # Blind basin share of total probability mass under SCRD exceeds constant 50/50 ADHR fusion
    from gems88 import adhr
    p_adhr, _ = adhr._fuse_log_odds(p_full, m_full, p_phys, m_phys, k_target, beta_phys=0.35)
    assert float(p_scrd[d_vis > 25.0].sum()) > float(p_adhr[d_vis > 25.0].sum())


def test_gthc88_frozen_run_card_and_release_integrity():
    card = json.loads((ROOT / "registry/gthc88_run_card.json").read_text())
    pub_card = json.loads((ROOT / "docs/data/gthc88_run_card.json").read_text())
    validation = json.loads((ROOT / "docs/data/gthc88_validation.json").read_text())
    current = json.loads((ROOT / "docs/data/current_release.json").read_text())
    status = json.loads((ROOT / "docs/status.json").read_text())
    ho = json.loads((ROOT / "evidence/gthc88_holdout.json").read_text())
    gate_v3 = json.loads((ROOT / "registry/gthc88_gate_v3.json").read_text())

    assert card == pub_card
    assert card["lane"] == "GTHC-88"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    assert card["slots_spent"] == 0 and card["organizer_confirmed"] is None
    assert 0 < len(card["submission_name"]) <= 140
    assert 0 < len(card["submission_note"]) <= 140
    assert card["experiment_count"] == 3

    # Holdout evidence: unstratified SCRD beats H88-ADHR incumbent; stratified FP beats MDC-88
    assert ho["evidence_class"] == "HOLDOUT-DTI"
    assert ho["evaluator_version"] == "gems57-pooled-hide-v2"
    sc_scrd = card["unstratified_scrd_holdout_dti"]
    sc_strat = card["holdout_dti"]
    inc = card["incumbent_holdout_dti"]
    assert sc_scrd["withheld_positive_pixels"] == 22893
    assert sc_strat["withheld_positive_pixels"] == 22893
    assert sc_scrd["dti"] > inc["dti"]
    assert sc_scrd["dti"] > ho["bars"]["h88_adhr_overall_recomputed"]
    assert sc_strat["dti"] > 0.14885  # beats MDC-88

    # Canary check across all 50 features
    assert ho["canary"]["passed"] is True
    assert ho["canary"]["n_features_checked"] == 50
    assert ho["canary"]["max_sym_auc"] <= 0.90

    # Uniqueness & fingerprint check
    reg = card["correlation_overlap_vs_registry"]
    assert reg["registry_rasters_checked"] >= 220
    assert reg["preplacement_max_abs_rho"] <= 0.90
    assert reg["like_for_like_unique"] is True
    assert reg["like_for_like_worst_overlap_3px"]["value"] <= 0.70
    assert reg["fingerprint_screen_passed"] is True
    assert reg["fingerprint_profile"]["share_le2"] == 0.0
    assert reg["fingerprint_profile"]["share_gt25"] >= 0.35
    assert reg["final_overlap_3px"] == 1.0  # literal overlap vs universal dense 17GEMSDOE witness

    # File & ZIP integrity
    tif = ROOT / card["download"]
    zipped = ROOT / card["zip_download"]
    assert tif.is_file() and zipped.is_file()
    assert "DO-NOT-SUBMIT" in tif.name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zipped.read_bytes()).hexdigest() == card["zip_sha256"]
    with zipfile.ZipFile(zipped) as z:
        assert z.namelist() == [tif.name] and z.testzip() is None

    # Alignment with validation.json and gate_v3.json
    assert card["raster_sha256"] == gate_v3["sha256"] == validation["tif_sha256"]
    assert card["zip_sha256"] == validation["zip_sha256"]
    assert validation["ok_to_download"] is True and validation["ok_to_submit"] is False
    assert gate_v3["ok_to_submit"] is False and gate_v3["like_for_like_unique"] is True
    if (ROOT / "data/bridge/sample_submission.tif").is_file():
        from scripts.validate_gthc88 import main as validate_gthc88_main
        assert validate_gthc88_main([]) == 0
        assert validate_gthc88_main(["--require-submit"]) == 2

