"""H88-PGTD: Laplace-consistent Marussi tensor dimensionality (zero catalogue).

For potential fields Phi (RTP magnetics band2, isostatic gravity band13),
T = grad grad Phi is trace-free in source-free space: Tzz=-(Txx+Tyy).
Txz,Tyz are horizontal derivatives of the measured vertical gradient
(tmi_vg band9, iso_grav_anom_vg band11). Over a 2D dipping fault sheet one
eigenvalue ~0 => det(T)~0; over 3D plugs det(T) is large. Dimensionality
proxy I = |det T| / (||T||_F^3/(3*sqrt(6))) in [0,1] (1=isotropic 3D);
sheetness = 1-I. Fault score gates sheetness by gradient magnitude so flat
noise is not promoted. Topo (band12) gets 2D Hessian anisotropy
(|l1|-|l2|)/(|l1|+|l2|). No catalogue/label/prior input. See
research/session-838cc402-hypotheses.md sec 3.2 (Pedersen & Rasmussen 1990;
Beiki & Pedersen 2010; Reid et al. 1990). Euler N omitted: needs source
location solve; documented limitation, not silently claimed.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, sobel
from gems88.mfs88 import clean_band

SCHEMA = "pgtd88-v1"
PGTD_FEATURES = tuple(
    f"pgtd_{f}_{k}" for f in ("rtp", "grav") for k in ("sheet", "sheetxgrad", "dim", "aniso2d")
) + ("pgtd_topo_aniso", "pgtd_topo_sheetxgrad", "pgtd_cross_sheet", "pgtd_cross_grad")
FIELDS = (("rtp", 2, 9), ("grav", 13, 11))  # name, Phi band, dPhi/dz band

def _d(a, axis):
    return sobel(a, axis=axis) * np.float32(0.125)

def tensor_channels(phi, vg, sigma=1.5):
    """Return sheet, sheetxgrad, dim, aniso2d float32 maps."""
    p = gaussian_filter(phi, sigma, mode="nearest")
    v = gaussian_filter(vg, sigma, mode="nearest")
    txx = _d(_d(p, 1), 1); tyy = _d(_d(p, 0), 0); txy = _d(_d(p, 1), 0)
    txz = _d(v, 1); tyz = _d(v, 0); tzz = -(txx + tyy)
    # Frobenius norm^2 and determinant of symmetric 3x3
    f2 = txx*txx + tyy*tyy + tzz*tzz + 2*(txy*txy + txz*txz + tyz*tyz)
    det = (txx*(tyy*tzz - tyz*tyz) - txy*(txy*tzz - tyz*txz) + txz*(txy*tyz - tyy*txz))
    norm = np.sqrt(np.maximum(f2, 1e-30))
    dim = np.clip(np.abs(det) / (norm**3 / (3*np.sqrt(6)) + 1e-30), 0, 1).astype(np.float32)
    sheet = (1.0 - dim).astype(np.float32)
    gy, gx = _d(p, 0), _d(p, 1)
    grad = np.hypot(gy, gx).astype(np.float32)
    # 2D horizontal Hessian anisotropy
    tr = txx + tyy; rad = np.hypot(txx - tyy, 2*txy)
    l1 = 0.5*(tr + rad); l2 = 0.5*(tr - rad)
    aniso = (np.abs(l1) - np.abs(l2)) / (np.abs(l1) + np.abs(l2) + 1e-12)
    return sheet, (sheet * grad).astype(np.float32), dim, np.clip(aniso, -1, 1).astype(np.float32), grad

def build_or_load(root: Path, fp: np.ndarray, cache: Path):
    cache.mkdir(parents=True, exist_ok=True)
    meta_p, mmap_p = cache / "pgtd88_meta.json", cache / "pgtd88_X_f32.mmap"
    n_fp = int(fp.sum())
    feats19 = []
    with rasterio.open(root / "data/training_features.tif") as ds:
        assert (ds.height, ds.width) == fp.shape and ds.count == 19
        for i in range(1, 20):
            feats19.append(f"b{i:02d}_{(ds.descriptions[i-1] or f'band{i}').split(' - ')[0].strip()}")
    names = feats19 + list(PGTD_FEATURES)
    meta = {"schema": SCHEMA, "n_valid": n_fp, "names": names}
    if meta_p.exists() and mmap_p.exists() and json.loads(meta_p.read_text()) == meta \
            and mmap_p.stat().st_size == n_fp * len(names) * 4:
        return np.memmap(mmap_p, dtype=np.float32, mode="r", shape=(n_fp, len(names))), meta
    X = np.memmap(mmap_p, dtype=np.float32, mode="w+", shape=(n_fp, len(names)))
    raw = {}
    with rasterio.open(root / "data/training_features.tif") as ds:
        for j in range(19):
            band = clean_band(ds.read(j + 1), fp)
            X[:, j] = band[fp]
            if (j + 1) in (2, 9, 11, 12, 13):
                raw[j + 1] = band
    col = 19; sheets = []; grads = []
    for _name, bphi, bvg in FIELDS:
        sheet, sxg, dim, aniso, grad = tensor_channels(raw[bphi], raw[bvg])
        for arr in (sheet, sxg, dim, aniso):
            X[:, col] = arr[fp]; col += 1
        sheets.append(sheet); grads.append(grad)
    # topo 2D anisotropy
    t = gaussian_filter(raw[12], 1.5, mode="nearest")
    txx = _d(_d(t, 1), 1); tyy = _d(_d(t, 0), 0); txy = _d(_d(t, 1), 0)
    tr = txx + tyy; rad = np.hypot(txx - tyy, 2*txy)
    l1 = 0.5*(tr + rad); l2 = 0.5*(tr - rad)
    topo_aniso = np.clip((np.abs(l1)-np.abs(l2))/(np.abs(l1)+np.abs(l2)+1e-12), -1, 1).astype(np.float32)
    gy, gx = _d(t, 0), _d(t, 1); tgrad = np.hypot(gy, gx).astype(np.float32)
    X[:, col] = topo_aniso[fp]; col += 1
    X[:, col] = (topo_aniso * tgrad)[fp]; col += 1
    X[:, col] = (sheets[0] * sheets[1])[fp]; col += 1
    X[:, col] = np.minimum(grads[0], grads[1])[fp]; col += 1
    assert col == len(names), (col, len(names))
    X.flush(); meta_p.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(mmap_p, dtype=np.float32, mode="r", shape=(n_fp, len(names))), meta
