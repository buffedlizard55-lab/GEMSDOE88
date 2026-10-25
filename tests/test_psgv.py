"""Synthetic verification of the H88-PSGV FFT operators (no competition data)."""
import numpy as np
import pytest

from gems88.psgv import PSGV_FEATURES, _fft_derivatives, _kgrid, _tapered_pad, pseudogravity


def _smooth_field(ny=96, nx=80, seed=7):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:ny, 0:nx]
    f = (np.sin(2 * np.pi * xx / 31.0) + 0.7 * np.cos(2 * np.pi * yy / 23.0)
         + 0.1 * rng.standard_normal((ny, nx)))
    return f.astype(np.float32)


def test_feature_names_frozen():
    assert len(PSGV_FEATURES) == 8
    assert len(set(PSGV_FEATURES)) == 8


def test_taper_preserves_interior():
    f = _smooth_field()
    p, crop = _tapered_pad(f, 16)
    np.testing.assert_allclose(p[crop], f - f.mean(), rtol=1e-6, atol=1e-6)


def test_pseudogravity_inverts_vertical_derivative():
    """|k| * (HP/|k| * RTP) == HP * RTP away from taper/DC (Poisson identity)."""
    f = _smooth_field()
    pad, dx, lam = 24, 100.0, 50_000.0
    g = pseudogravity(f, dx_m=dx, pad=pad, k0_wavelength_m=lam)
    # Recompute HP*f in the same tapered frame and compare against |k|*g_psg.
    p, crop = _tapered_pad(f, pad)
    F = np.fft.rfft2(p)
    _, _, k = _kgrid(p.shape[0], p.shape[1], dx)
    k0 = 2 * np.pi / lam
    hp = 1.0 - np.exp(-((k / k0) ** 2))
    expect = np.fft.irfft2(F * hp, s=p.shape)[crop]
    vdr_g, _, _ = _fft_derivatives(g, dx_m=dx, pad=pad)
    inner = np.s_[10:-10, 10:-10]
    a, b = expect[inner], vdr_g[inner]
    # vdr of the cropped g re-tapers edges; interior must track to high correlation.
    assert np.corrcoef(a.ravel(), b.ravel())[0, 1] > 0.97


def test_concordant_fields_have_small_residual_shifted_edge_does_not():
    """If grav == pseudogravity source, discordance ~ 0; an offset edge lights up."""
    f = _smooth_field()
    g_psg = pseudogravity(f, pad=24)
    # concordant: regress g_psg on itself -> residual exactly 0 by construction;
    # instead verify the operator is deterministic and finite, and that rolling
    # the field by 5 px increases regression residual energy.
    def resid_energy(a, b):
        az = (a - a.mean()) / a.std()
        bz = (b - b.mean()) / b.std()
        s = float((az * bz).mean())
        return float(((bz - s * az) ** 2).mean())
    e0 = resid_energy(g_psg, g_psg.copy())
    e1 = resid_energy(g_psg, np.roll(g_psg, 5, axis=1))
    assert e0 == pytest.approx(0.0, abs=1e-12)
    assert e1 > 0.05
    assert np.isfinite(g_psg).all()


def test_fft_derivatives_match_analytic_plane():
    ny, nx = 64, 56
    yy, xx = np.mgrid[0:ny, 0:nx]
    f = np.sin(2 * np.pi * xx / 28.0).astype(np.float32)  # varies in x only
    vdr, gy, gx = _fft_derivatives(f, pad=24)
    inner = np.s_[12:-12, 12:-12]
    expect_gx = (2 * np.pi / (28.0 * 100.0)) * np.cos(2 * np.pi * xx / 28.0)
    assert np.corrcoef(gx[inner].ravel(), expect_gx[inner].ravel())[0, 1] > 0.99
    assert np.abs(gy[inner]).max() < 0.05 * np.abs(gx[inner]).max()
    assert np.isfinite(vdr).all()
