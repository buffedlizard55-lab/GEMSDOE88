"""H88-CXL: monogenic phase-congruency / phase-symmetry tensor (CXL-26).

Zero-catalogue channels from training_features bands 2 (RTP), 13 (isostatic
gravity), 12 (detrended DEM). For each field, a multi-scale (wavelengths
5/11/23 px) monogenic signal is built in the Fourier domain: log-Gabor radial
bandpass + Riesz transform. Per scale: log local energy and phase symmetry
(step response); across scales: phase-congruency proxy sum(even)/sum(E) and
orientation coherence |sum E*exp(2i*theta)|/sum(E). Phase congruency is
contrast-invariant, so low-amplitude basement steps under cover (blind faults)
rank independently of edge amplitude, unlike every gradient/Hessian stack in
this repo (grep-verified: no riesz/monogenic/phase code existed before).

existing_faults.tif is never read here. Memory-bounded: one field in RAM at a
time, results written to a disk-backed float32 memmap at footprint rows.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import fft as sfft

from .edge import clean_band

CXL_SCHEMA_VERSION = "cxl88-26ch-v1"
FIELDS = ((2, "rtp"), (13, "grav"), (12, "elev"))
WAVELENGTHS = (5.0, 11.0, 23.0)
SIGMA_F = 0.55

CXL_FEATURES: tuple[str, ...] = tuple(
    [f"cxl_{f}_logE{i}" for f, _ in [(n, b) for b, n in FIELDS] for i in range(3)]
    + [f"cxl_{f}_psym{i}" for f in [n for _, n in FIELDS] for i in range(3)]
    + [f"cxl_{f}_pc" for _, f in FIELDS]
    + [f"cxl_{f}_oricoh" for _, f in FIELDS]
    + ["cxl_pc_min", "cxl_pc_prod"]
)
assert len(CXL_FEATURES) == 26, CXL_FEATURES


def _field_channels(field: np.ndarray) -> list[np.ndarray]:
    """Return 8 channels for one cleaned field: logE x3, psym x3, pc, oricoh."""
    h, w = field.shape
    f = (field - np.float32(field.mean())).astype(np.float32)
    F = sfft.fft2(f, workers=2)
    fy = sfft.fftfreq(h).astype(np.float32)
    fx = sfft.fftfreq(w).astype(np.float32)
    FX, FY = np.meshgrid(fx, fy)
    rad = np.hypot(FX, FY)
    rad[0, 0] = 1.0
    ux, uy = FX / rad, FY / rad
    rad[0, 0] = 0.0
    logE, psym = [], []
    sum_even = np.zeros((h, w), np.float32)
    sum_E = np.zeros((h, w), np.float32)
    coh_num = np.zeros((h, w), np.complex64)
    for wl in WAVELENGTHS:
        f0 = np.float32(1.0 / wl)
        with np.errstate(divide="ignore", invalid="ignore"):
            lg = np.exp(-(np.log(rad / f0) ** 2) / (2 * np.log(SIGMA_F) ** 2)).astype(np.float32)
        lg[0, 0] = 0.0
        even = np.real(sfft.ifft2(F * lg, workers=2)).astype(np.float32)
        rx = np.real(sfft.ifft2(F * lg * (1j * ux), workers=2)).astype(np.float32)
        ry = np.real(sfft.ifft2(F * lg * (1j * uy), workers=2)).astype(np.float32)
        odd = np.hypot(rx, ry)
        E = np.hypot(even, odd)
        logE.append(np.log1p(E))
        psym.append(np.clip((odd - np.abs(even)) / (E + 1e-6), -1.0, 1.0).astype(np.float32))
        sum_even += even
        sum_E += E
        theta2 = ((rx + 1j * ry) / (odd + 1e-6)) ** 2
        coh_num += (E * theta2).astype(np.complex64)
        del even, rx, ry, odd, E, lg, theta2
    pc = np.clip(sum_even / (sum_E + 1e-6), 0.0, 1.0).astype(np.float32)
    oricoh = np.clip(np.abs(coh_num) / (sum_E + 1e-6), 0.0, 1.0).astype(np.float32)
    return logE + psym + [pc, oricoh]


def build_or_load_cxl_memmap(root: Path, grid, cache_dir: Path):
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat = cache_dir / "x_cxl_26ch.dat"
    meta_p = cache_dir / "x_cxl_26ch.json"
    shape = (int(ys.size), len(CXL_FEATURES))
    if dat.is_file() and meta_p.is_file():
        meta = json.loads(meta_p.read_text())
        if meta.get("schema") == CXL_SCHEMA_VERSION and meta.get("features") == list(CXL_FEATURES):
            return np.memmap(dat, dtype="float32", mode="r", shape=shape), meta
    mm = np.memmap(dat, dtype="float32", mode="w+", shape=shape)
    pcs = {}
    stats = {}
    with rasterio.open(root / "data/training_features.tif") as src:
        for band, name in FIELDS:
            found = src.tags(band).get("band_name")
            cleaned, info = clean_band(src.read(band), fp)
            chans = _field_channels(cleaned)
            del cleaned
            base = {"rtp": 0, "grav": 1, "elev": 2}[name]
            # layout: logE(0-8) psym(9-17) pc(18-20) oricoh(21-23) min/prod(24-25)
            for i in range(3):
                for arr, col in ((chans[i], base * 3 + i), (chans[3 + i], 9 + base * 3 + i)):
                    v = arr[ys, xs]
                    mu, sd = float(v.mean()), float(v.std() or 1.0)
                    mm[:, col] = ((v - mu) / sd).astype(np.float32)
                    stats[CXL_FEATURES[col]] = {"mean": mu, "std": sd, "band_info": info}
            pcs[name] = chans[6]
            mm[:, 18 + base] = chans[6][ys, xs]
            mm[:, 21 + base] = chans[7][ys, xs]
            stats[CXL_FEATURES[18 + base]] = {"raw": True}
            stats[CXL_FEATURES[21 + base]] = {"raw": True}
            del chans
    pc_stack = np.stack([pcs[n][ys, xs] for _, n in FIELDS])
    mm[:, 24] = pc_stack.min(axis=0)
    mm[:, 25] = pc_stack.prod(axis=0)
    mm.flush()
    meta = {"schema": CXL_SCHEMA_VERSION, "features": list(CXL_FEATURES), "stats": stats,
            "wavelengths_px": list(WAVELENGTHS), "catalogue_access": "none"}
    meta_p.write_text(json.dumps(meta, indent=1))
    return np.memmap(dat, dtype="float32", mode="r", shape=shape), meta
