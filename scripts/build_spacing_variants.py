#!/usr/bin/env python3
"""Build up to 3 SPACING variants of R0 (h33-h33-2-b2) per GEMS agent brief v2 §5.

AXIS = SPACING (lowest priority per SLOT_PLAN.md). Held fixed across variants:
  * parent R0 mask (37,654 unit dots, rebuilt & verified earlier),
  * count N = 37,654 (matched count),
  * exclusions: inside footprint of sample_submission.tif and d_cat > 2 px from
    existing_faults.tif (identical to R0),
  * seed 20261023, rebuilt kept-set ranking (parent's own recipe is not stored;
    rebuilt as 0.6*clip(d_cat/50, 0, 1) + 0.4*Uniform(seed 88)).

Each variant moves exactly 25.00% of R0's dots (9,414 dots = bottom-ranked
quarter) onto pattern sites within the same allowed domain; the top-ranked 75%
(28,240 dots) stay at their parent locations.  Variants differ ONLY in the
spacing pattern of the moved fraction:

  * lattice25    - square-lattice sites at matched density (~2.3 km pitch)
  * poissondisk25 - Bridson Poisson-disk sites (12 px min separation)
  * alongstrike25 - sites placed along local strike from the parent dot field
                    (structure tensor, sigma = 3 px)

Writes releases/<id>.tif (NaN outside), <id>-zeros.tif (0 outside), one .zip
per TIFF, and <id>.json receipt; re-verifies every gate from disk after write;
appends BUILT rows to ledger/submissions.csv (16-column schema preserved) and
mechanism cards to ledger/mechanism_cards.json.

Report-only (never gates): block-density CV (10 km / 12 km blocks), SGMC
off-catalogue fault proximity, nearest-neighbour spacing stats.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt, gaussian_filter, sobel
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "data" / "bridge"
REGISTRY = ROOT / "data" / "registry"
EXTERNAL = ROOT / "data" / "external"
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"

PARENT_ID = "h33-h33-2-b2"
PARENT_SHA_ZEROS = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
PARENT_SHA_NAN = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
SAMPLE = BRIDGE / "sample_submission.tif"
EXISTING = BRIDGE / "existing_faults.tif"
PIN_SAMPLE = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
PIN_EXISTING = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"

FIXED_DATE = "20261023"
SEED = 20261023
RNG_RANK = 88
N_PARENT = 37_654
MOVE_FRAC = 0.25
N_MOVED = int(N_PARENT * MOVE_FRAC)          # 9,414
N_KEPT = N_PARENT - N_MOVED                  # 28,240
MIN_DIST_CATALOGUE = 2.0                     # R0 collar: nothing <= 2 px
MIN_NEW_TO_KEPT = 1.5                        # px; do not crowd held dots
POISSON_R = 12.0                             # px min separation among new dots
STRIKE_SIGMA = 3.0                           # px structure-tensor smoothing
STEP_MIN, STEP_MAX = 2.0, 7.0                # px along-strike step
MAX_ATTEMPTS = 300


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def verify_pins() -> None:
    checks = [
        (SAMPLE, PIN_SAMPLE, "sample_submission.tif"),
        (EXISTING, PIN_EXISTING, "existing_faults.tif"),
        (REGISTRY / "h33_education.tif", PARENT_SHA_ZEROS, "parent R0 zeros twin"),
    ]
    for path, want, label in checks:
        got = sha256_file(path)
        assert got == want, f"PIN MISMATCH {label}: got {got}, want {want}"
        print(f"pin OK  {label}  {got[:12]}...")


def load_arrays():
    with rasterio.open(SAMPLE) as src:
        sample_profile = src.profile.copy()
        footprint = np.isfinite(src.read(1)) & (src.read_masks(1) > 0)
        ref = (src.height, src.width, str(src.crs), src.transform)
    with rasterio.open(EXISTING) as src:
        ef = src.read(1)
    footprint = footprint & ((ef == 0) | (ef == 1))
    catalogue = (ef == 1) & footprint
    dist = distance_transform_edt(~catalogue).astype(np.float32)
    with rasterio.open(REGISTRY / "h33_education.tif") as src:
        parent = src.read(1)
    parent_mask = parent > 0.5
    assert int(parent_mask.sum()) == N_PARENT, int(parent_mask.sum())
    dvals = dist[parent_mask]
    assert float(dvals.min()) > MIN_DIST_CATALOGUE, float(dvals.min())
    assert not (parent_mask & catalogue).any()
    print(f"parent OK: {N_PARENT:,} dots, min d_cat = {dvals.min():.4f} px, "
          f"{int((dvals <= 3.0).sum())} dots in (2, 3] px collar")
    return footprint, catalogue, dist, parent_mask, sample_profile, ref


def rebuilt_ranking(parent_mask, dist):
    """Re-built kept-set ranking (parent recipe not stored): MODEL ranking only."""
    rng = np.random.default_rng(RNG_RANK)
    rows, cols = np.where(parent_mask)
    score = 0.6 * np.clip(dist[parent_mask] / 50.0, 0.0, 1.0) + 0.4 * rng.random(rows.size)
    order = np.argsort(-score)  # highest first
    return rows, cols, order


def select_kept(rows, cols, order):
    keep_idx = order[:N_KEPT]
    move_idx = order[N_KEPT:]
    return set(zip(rows[keep_idx].tolist(), cols[keep_idx].tolist())), (rows[move_idx], cols[move_idx])


def allowed_domain(footprint, catalogue, dist):
    return footprint & (dist > MIN_DIST_CATALOGUE)


def lattice_sites(allowed, kept_tree, n_new):
    H, W = allowed.shape
    pitch = float(np.sqrt(allowed.sum() / max(n_new * 1.3, 1)))  # over-generate; kept-dot exclusion filters some
    rng = np.random.default_rng(SEED)
    off_y, off_x = rng.random(2) * pitch
    ys = np.arange(off_y, H, pitch)
    xs = np.arange(off_x, W, pitch)
    YY, XX = np.meshgrid(ys, xs, indexing="ij")
    cand_rows = np.rint(YY).astype(int).ravel()
    cand_cols = np.rint(XX).astype(int).ravel()
    inside = (cand_rows < H) & (cand_cols < W) & allowed[cand_rows, cand_cols]
    cand_rows, cand_cols = cand_rows[inside], cand_cols[inside]
    order = np.lexsort((cand_cols, cand_rows))  # row-major
    cand_rows, cand_cols = cand_rows[order], cand_cols[order]
    sites = []
    for r, c in zip(cand_rows.tolist(), cand_cols.tolist()):
        if kept_tree.query_ball_point([r, c], MIN_NEW_TO_KEPT):
            continue
        sites.append((r, c))
        if len(sites) >= n_new:
            break
    if len(sites) < n_new:
        raise RuntimeError(f"lattice: only {len(sites)} valid sites < {n_new}")
    return sites[:n_new], pitch


def poisson_disk_sites(allowed, kept_tree, new_tree_points, n_new, r=POISSON_R):
    H, W = allowed.shape
    cell = r / np.sqrt(2.0)
    cols = int(np.ceil(W / cell)) + 1
    rows_g = int(np.ceil(H / cell)) + 1
    grid = [[[] for _ in range(cols)] for _ in range(rows_g)]
    accepted = []
    rng = np.random.default_rng(SEED + 1)

    def cell_of(rc):
        return int(rc[0] / cell), int(rc[1] / cell)

    def ok_point(rc):
        if not (0 <= rc[0] < H and 0 <= rc[1] < W and allowed[rc[0], rc[1]]):
            return False
        if kept_tree.query_ball_point(rc, MIN_NEW_TO_KEPT):
            return False
        gi, gj = cell_of(rc)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                ci, cj = gi + di, gj + dj
                if 0 <= ci < rows_g and 0 <= cj < cols:
                    for q in grid[ci][cj]:
                        if (q[0] - rc[0]) ** 2 + (q[1] - rc[1]) ** 2 < r * r:
                            return False
        return True

    # seed with a random allowed point
    tries = 0
    while True:
        tries += 1
        rc = (int(rng.random() * H), int(rng.random() * W))
        if ok_point(rc):
            break
        if tries > 100000:
            raise RuntimeError("poisson-disk: cannot seed first point")
    accepted.append(rc)
    gi, gj = cell_of(rc)
    grid[gi][gj].append(rc)
    active = [0]

    while len(accepted) < n_new and active:
        idx = int(rng.random() * len(active))
        base = accepted[active[idx]]
        placed = False
        for _ in range(30):
            a = rng.random() * 2.0 * np.pi
            rad = r * (1.0 + rng.random())
            cand = (int(round(base[0] + rad * np.sin(a))), int(round(base[1] + rad * np.cos(a))))
            if ok_point(cand):
                accepted.append(cand)
                gi, gj = cell_of(cand)
                grid[gi][gj].append(cand)
                active.append(len(accepted) - 1)
                placed = True
                break
        if not placed:
            active[idx] = active[-1]
            active.pop()
    if len(accepted) < n_new:
        raise RuntimeError(f"poisson-disk: only {len(accepted)}/{n_new} sites")
    return accepted[:n_new], r


def strike_field(parent_mask):
    img = parent_mask.astype(np.float32)
    smooth = gaussian_filter(img, STRIKE_SIGMA)
    ix = sobel(smooth, axis=1)
    iy = sobel(smooth, axis=0)
    Ixx = gaussian_filter(ix * ix, STRIKE_SIGMA)
    Iyy = gaussian_filter(iy * iy, STRIKE_SIGMA)
    Ixy = gaussian_filter(ix * iy, STRIKE_SIGMA)
    theta = 0.5 * np.arctan2(2.0 * Ixy, Ixx - Iyy)  # max-variance axis (across line)
    strike = theta + 0.5 * np.pi  # along-line direction
    return strike


def alongstrike_sites(allowed, kept_tree, kept_points, parent_rows, parent_cols, strike, n_new):
    H, W = allowed.shape
    rng = np.random.default_rng(SEED + 2)
    accepted = []
    new_tree_pts = []
    kept_arr = np.array(kept_points, dtype=float) if kept_points else np.zeros((0, 2))
    fallback = 0
    allowed_rc = np.argwhere(allowed)
    for _ in range(n_new):
        placed = False
        for _ in range(MAX_ATTEMPTS):
            s = kept_points[int(rng.random() * len(kept_points))]
            th = strike[s[0], s[1]]
            d = STEP_MIN + rng.random() * (STEP_MAX - STEP_MIN)
            sign = 1.0 if rng.random() < 0.5 else -1.0
            cand = (int(round(s[0] + sign * d * np.sin(th))),
                    int(round(s[1] + sign * d * np.cos(th))))
            if not (0 <= cand[0] < H and 0 <= cand[1] < W and allowed[cand[0], cand[1]]):
                continue
            if kept_arr.shape[0] and np.min((kept_arr[:, 0] - cand[0]) ** 2 + (kept_arr[:, 1] - cand[1]) ** 2) < MIN_NEW_TO_KEPT ** 2:
                continue
            if new_tree_pts and np.min((np.array(new_tree_pts)[:, 0] - cand[0]) ** 2 + (np.array(new_tree_pts)[:, 1] - cand[1]) ** 2) < MIN_NEW_TO_KEPT ** 2:
                continue
            accepted.append(cand)
            new_tree_pts.append(cand)
            placed = True
            break
        if not placed:
            # fallback: uniform allowed rejection sample
            for _ in range(5000):
                rc = allowed_rc[int(rng.random() * len(allowed_rc))]
                rc = (int(rc[0]), int(rc[1]))
                if kept_arr.shape[0] and np.min((kept_arr[:, 0] - rc[0]) ** 2 + (kept_arr[:, 1] - rc[1]) ** 2) < MIN_NEW_TO_KEPT ** 2:
                    continue
                if new_tree_pts and np.min((np.array(new_tree_pts)[:, 0] - rc[0]) ** 2 + (np.array(new_tree_pts)[:, 1] - rc[1]) ** 2) < MIN_NEW_TO_KEPT ** 2:
                    continue
                accepted.append(rc)
                new_tree_pts.append(rc)
                placed = True
                fallback += 1
                break
        if not placed:
            raise RuntimeError("alongstrike: cannot place dot")
    return accepted, fallback


def write_and_verify(mask, footprint, catalogue, dist, parent_mask, sample_profile, ref,
                     axis, value, note_template, existing_shas):
    """Write <id>.tif (NaN outside) + <id>-zeros.tif + .zip x2 + .json; re-read verify."""
    import time  # not needed; kept minimal
    RELEASES.mkdir(parents=True, exist_ok=True)
    height, width = ref[0], ref[1]
    prof_nan = sample_profile.copy()
    prof_nan.update(driver="GTiff", dtype="float32", count=1, compress="deflate",
                    predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256,
                    nodata=np.nan)
    prof_zeros = prof_nan.copy()
    prof_zeros.update(nodata=None)

    arr_nan = np.where(footprint, mask.astype(np.float32), np.nan).astype(np.float32)
    arr_zeros = np.where(footprint, mask.astype(np.float32), 0.0).astype(np.float32)

    prefix = f"{PARENT_ID}-{axis}{value}-{FIXED_DATE}"
    tmp_nan = RELEASES / f".tmp-{prefix}.tif"
    tmp_zeros = RELEASES / f".tmp-{prefix}-zeros.tif"
    with rasterio.open(tmp_nan, "w", **prof_nan) as dst:
        dst.write(arr_nan, 1)
    with rasterio.open(tmp_zeros, "w", **prof_zeros) as dst:
        dst.write(arr_zeros, 1)

    sha_nan = sha256_file(tmp_nan)
    sha_zeros = sha256_file(tmp_zeros)
    sha8 = sha_nan[:8]
    if sha_nan in existing_shas or sha_zeros in existing_shas:
        tmp_nan.unlink(missing_ok=True)
        tmp_zeros.unlink(missing_ok=True)
        raise RuntimeError(f"Duplicate SHA-256 already present in ledger: {sha_nan}")

    vid = f"{prefix}-{sha8}"
    final_nan = RELEASES / f"{vid}.tif"
    final_zeros = RELEASES / f"{vid}-zeros.tif"
    tmp_nan.replace(final_nan)
    tmp_zeros.replace(final_zeros)

    zip_nan = RELEASES / f"{vid}.zip"
    zip_zeros = RELEASES / f"{vid}-zeros.zip"
    for tif_p, zip_p in ((final_nan, zip_nan), (final_zeros, zip_zeros)):
        with zipfile.ZipFile(zip_p, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(tif_p, arcname=tif_p.name)
        tif_p.chmod(0o644)
        zip_p.chmod(0o644)

    # ---- MUST-PASS re-read verification from disk ----
    with rasterio.open(final_nan) as ds:
        back_nan = ds.read(1)
        assert (ds.height, ds.width, str(ds.crs), ds.transform) == ref, "grid mismatch (.tif)"
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert np.isfinite(back_nan[footprint]).all()
        assert np.isnan(back_nan[~footprint]).all()
        assert float(back_nan[footprint].min()) >= 0.0 and float(back_nan[footprint].max()) <= 1.0
        assert int((back_nan[catalogue] > 0.0).sum()) == 0
        assert np.array_equal(back_nan[footprint] > 0.5, mask[footprint])
    with rasterio.open(final_zeros) as ds:
        back_zeros = ds.read(1)
        assert (ds.height, ds.width, str(ds.crs), ds.transform) == ref
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert np.isfinite(back_zeros).all()
        assert np.all(back_zeros[~footprint] == 0.0)
        assert int((back_zeros[catalogue] > 0.0).sum()) == 0
        assert np.array_equal(back_zeros[footprint] > 0.5, mask[footprint])
    # second independent read
    with rasterio.open(final_nan) as ds:
        again = ds.read(1)
    assert np.array_equal(np.nan_to_num(again, nan=0.0), np.nan_to_num(back_nan, nan=0.0))

    d_cat = distance_transform_edt(~catalogue).astype(np.float32)
    dvals = d_cat[mask]
    n_dots = int(mask.sum())
    n_added = int((mask & ~parent_mask).sum())
    n_removed = int((parent_mask & ~mask).sum())
    pct_moved = 100.0 * n_removed / N_PARENT
    pct_sym = 100.0 * (n_added + n_removed) / N_PARENT
    assert 1.0 <= pct_moved <= 50.0, f"moved % outside [1, 50]: {pct_moved:.2f}"
    assert not (mask & catalogue).any()
    assert float(dvals.min()) > MIN_DIST_CATALOGUE

    note = note_template.format(sha8=sha8)
    assert len(note) <= 140, f"form note > 140 chars ({len(note)}): {note}"

    receipt = {
        "id": vid,
        "parent": PARENT_ID,
        "parent_sha256_zeros": PARENT_SHA_ZEROS,
        "parent_sha256_nan": PARENT_SHA_NAN,
        "axis": axis,
        "value": value,
        "seed": SEED,
        "git_sha": git_sha(),
        "file_nan": f"releases/{final_nan.name}",
        "sha256": sha_nan,
        "bytes_nan": final_nan.stat().st_size,
        "zip_nan": f"releases/{zip_nan.name}",
        "zip_nan_sha256": sha256_file(zip_nan),
        "file_zeros": f"releases/{final_zeros.name}",
        "sha256_zeros": sha_zeros,
        "bytes_zeros": final_zeros.stat().st_size,
        "zip_zeros": f"releases/{zip_zeros.name}",
        "zip_zeros_sha256": sha256_file(zip_zeros),
        "form_note": note,
        "form_note_chars": len(note),
        "n_dots": n_dots,
        "parent_diff": {
            "n_parent": N_PARENT,
            "n_added": n_added,
            "n_removed": n_removed,
            "pct_changed_moved": round(pct_moved, 2),
            "pct_changed_sym_diff": round(pct_sym, 2),
            "min_dist_catalogue_px": round(float(dvals.min()), 4),
            "dots_le_1px": int((dvals <= 1.0).sum()),
            "dots_le_2px": int((dvals <= 2.0).sum()),
            "dots_le_3px": int((dvals <= 3.0).sum()),
            "dots_le_4px": int((dvals <= 4.0).sum()),
        },
        "gates": {
            "crs_epsg_32611": str(ref[2]) == "EPSG:32611",
            "shape_3730x3292": ref[:2] == (3730, 3292),
            "transform_match": True,
            "dtype_float32": True,
            "band_count_1": True,
            "values_in_0_1": True,
            "no_nan_inside_footprint": True,
            "nan_outside_footprint": True,
            "zeros_fallback_valid": True,
            "zero_catalogue_mass": True,
            "reread_from_disk_verified": True,
        },
    }
    (RELEASES / f"{vid}.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt, vid, final_nan, final_zeros, {
        "n_dots": n_dots, "n_added": n_added, "n_removed": n_removed,
        "pct_moved": pct_moved, "min_dist": float(dvals.min()), "mask": mask}


def block_cv(mask, foot, block_px):
    H, W = foot.shape
    Hs, Ws = (H // block_px) * block_px, (W // block_px) * block_px
    fb = foot[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    interior = fb == (block_px * block_px)
    ab = mask[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    dens = ab[interior] / fb[interior]
    return float(dens.std() / dens.mean()) if dens.size and dens.mean() > 0 else float("nan")


def main() -> int:
    verify_pins()
    footprint, catalogue, dist, parent_mask, sample_profile, ref = load_arrays()
    allowed = allowed_domain(footprint, catalogue, dist)
    print(f"allowed domain: {int(allowed.sum()):,} px")

    rows, cols, order = rebuilt_ranking(parent_mask, dist)
    kept_set, (move_rows, move_cols) = select_kept(rows, cols, order)
    kept_points = list(kept_set)
    kept_arr = np.array(kept_points, dtype=float)
    kept_tree = cKDTree(kept_arr) if kept_arr.shape[0] else None
    print(f"kept {N_KEPT} dots (top 75% by rebuilt ranking); moving {N_MOVED} dots")

    specs = []
    lattice_sites_list, lattice_pitch = lattice_sites(allowed, kept_tree, N_MOVED)
    specs.append(("lattice25", lattice_sites_list, {"pitch_px": round(lattice_pitch, 3)}))

    pd_sites, pd_r = poisson_disk_sites(allowed, kept_tree, None, N_MOVED)
    specs.append(("poissondisk25", pd_sites, {"min_separation_px": pd_r}))

    strike = strike_field(parent_mask)
    as_sites, fallback = alongstrike_sites(allowed, kept_tree, kept_points, rows, cols, strike, N_MOVED)
    specs.append(("alongstrike25", as_sites, {"fallback_count": fallback, "step_px": [STEP_MIN, STEP_MAX]}))
    print(f"alongstrike fallbacks: {fallback}")

    existing_shas = set()
    if LEDGER.is_file():
        with LEDGER.open(newline="") as f:
            for row in csv.DictReader(f):
                for col in ("sha256", "sha256_zeros"):
                    h = (row.get(col) or "").strip()
                    if h:
                        existing_shas.add(h)

    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    new_rows = []
    sgmc_path = EXTERNAL / "derived_sgmc_faults_100m_u8.tif"
    sgmc_ok = sgmc_path.is_file()
    if sgmc_ok:
        with rasterio.open(sgmc_path) as src:
            sgmc = (src.read(1) == 1)

    for value, new_sites, diag_extra in specs:
        mask = np.zeros_like(footprint, dtype=bool)
        for r, c in kept_points:
            mask[r, c] = True
        for r, c in new_sites:
            mask[r, c] = True
        assert int(mask.sum()) == N_PARENT

        note_templates = {
            "lattice25": "h33-2-b2; SPACING lattice held at 37654 (~25% respaced; same >=2 px collar); pred MODEL 0.000",
            "poissondisk25": "h33-2-b2; SPACING poissondisk held at 37654 (~25% respaced, 12 px min separation; same >=2 px collar); pred MODEL 0.000",
            "alongstrike25": "h33-2-b2; SPACING alongstrike held at 37654 (~25% respaced along local strike; same >=2 px collar); pred MODEL 0.000",
        }
        descs = {
            "lattice25": "Move bottom-ranked quarter (~25%; 9413 dots target) of R0 onto square-lattice sites at matched density inside the allowed domain (footprint, d_cat>2 px); top ~75% held at parent locations; count fixed at 37654; tests whether marginal dots prefer lattice spacing.",
            "poissondisk25": "Move bottom-ranked quarter (~25%; 9413 dots target) of R0 onto Bridson Poisson-disk sites (12 px min separation) inside the allowed domain (footprint, d_cat>2 px); top ~75% held at parent locations; count fixed at 37654; tests whether dot crowding limits score.",
            "alongstrike25": "Move bottom-ranked quarter (~25%; 9413 dots target) of R0 along local strike (structure tensor of parent dot field, sigma=3 px) inside the allowed domain (footprint, d_cat>2 px); top ~75% held at parent locations; count fixed at 37654; tests along-strike clustering vs isotropic spacing.",
        }
        cards_tmpl = {
            "lattice25": {
                "hypothesis": "Geothermal faults segment at characteristic along-strike length scales; respacing the marginal 25% of dots on a square lattice at matched density (~2.3 km pitch) captures segmented strand centres that R0's retained clusters split across adjacent dots.",
                "mechanism": "DTI = T / (0.2 T + 0.2 (S - M) + 0.8 |G|): holding S = 37,654 isolates the spacing topology. A lattice places one dot per ~5.3 km^2 cell, removing sub-segment duplicate dots (FP_w waste) and assigning each segment's credit to its centre where line-like truth clears the k > 0.2*DTI (~0.056) threshold.",
                "non_fault_mimic": "Quasi-regular alluvial-fan distributary bifurcations, lake-terrace scarps and DEM tile-grid artifacts can produce regular ~2 km lineations that a lattice rewards without any slip.",
                "predicted_sign_size": "MODEL predicted live delta 0.000 (range [-0.010,+0.010]); matched count means TP/FP mass unchanged, so |delta| < 0.01 counts as no evidence per brief v2.",
                "falsifier": "Live gain >= +0.01 for lattice25 but not poissondisk25/alongstrike25 implicates grid or flight-line aliasing rather than fault segmentation; no gain on all three means location/mass dominate spacing.",
            },
            "poissondisk25": {
                "hypothesis": "Damage-zone main traces repel secondary slip within ~1 km; respacing the marginal 25% on a Poisson-disk field (12 px / 1.2 km min separation) reduces dot crowding on the same structures and lets kernel credit T concentrate on isolated blind strands.",
                "mechanism": "Fixed S with Poisson-disk minimum separation lowers multi-dot overlap of the 300 m triangular kernel on adjacent strands, cutting FP_w denominator waste while keeping TP_w on line-like truth whose credit exceeds k > 0.2*DTI (~0.056).",
                "non_fault_mimic": "Randomly spaced cooling joints, unseeded microfracture sets and homogeneous background fracture density pass a Poisson-disk filter without any seismogenic slip.",
                "predicted_sign_size": "MODEL predicted live delta 0.000 (range [-0.010,+0.010]); |delta| < 0.01 counts as no evidence.",
                "falsifier": "Live gain >= +0.01 proves crowding was suppressing score; three-way null result means spacing topology is not predictive for this footprint.",
            },
            "alongstrike25": {
                "hypothesis": "Unmapped geothermal faults grow as along-strike relay and splay clusters; respacing the marginal 25% along local strike (from the parent field's structure tensor) concentrates dots on strike-continuous segments rather than scattered isolations.",
                "mechanism": "Strike-consistent placement preserves along-strike linkage where a 300 m kernel bridges echelon splays into one credited line, while moving dots off non-fault isolations reduces FP_w; count S and exclusions identical to R0.",
                "non_fault_mimic": "Antithetic synthetic splays and anticlinal bend fractures that never link to a master fault align along strike locally but carry no slip; they would collect kernel credit without truth support.",
                "predicted_sign_size": "MODEL predicted live delta 0.000 (range [-0.010,+0.010]); |delta| < 0.01 counts as no evidence.",
                "falsifier": "Live gain >= +0.01 for alongstrike25 only supports strike-linked clusters; null on all three axes means spacing is not predictive at fixed N.",
            },
        }
        pred = "MODEL:0.000"
        pred_range = "[-0.010,+0.010]"
        ranking_basis = ("rebuilt ranking 0.6*clip(d_cat/50,0,1)+0.4*Uniform(seed88); "
                         "kept = top 75% (28,240 dots), moved = bottom 25% (9,414 dots); "
                         "parent's own ranking recipe is not stored")

        rec, vid, final_nan, final_zeros, stats = write_and_verify(
            mask, footprint, catalogue, dist, parent_mask, sample_profile, ref,
            "SPACING", value, note_templates[value], existing_shas)
        existing_shas.add(rec["sha256"]); existing_shas.add(rec["sha256_zeros"])

        # ---- report-only diagnostics ----
        dvals = dist[mask]
        new_pts = np.array([s for s in new_sites])
        kept_arr2 = np.array(kept_points)
        if len(new_pts) and len(kept_arr2):
            tree_new = cKDTree(new_pts)
            dist_to_new = tree_new.query(kept_arr2, k=1)[0]
            nn_stats = {"kept_to_new_mean_px": float(dist_to_new.mean()),
                        "kept_to_new_p50_px": float(np.median(dist_to_new))}
        else:
            nn_stats = {}
        diag = {
            "kept_dots": N_KEPT,
            "moved_dots": N_MOVED,
            "pct_moved": round(100.0 * N_MOVED / N_PARENT, 4),
            **diag_extra,
            "block_cv_10km": round(block_cv(mask, footprint, 100), 4),
            "block_cv_12km": round(block_cv(mask, footprint, 120), 4),
            "min_dist_catalogue_px": round(float(dvals.min()), 4),
            **nn_stats,
        }
        if sgmc_ok:
            dtm = distance_transform_edt(~mask).astype(np.float32)
            sgmc_px = sgmc & footprint
            diag["sgmc_close_3px"] = int((dtm[sgmc_px] <= 3.0).sum())
            diag["sgmc_total_px"] = int(sgmc_px.sum())
        rec["spacing_diagnostics"] = diag
        rec["report_only_not_gated"] = ["catalogue hide-and-recover PROXY", "leakage canary", "SGMC control"]
        (RELEASES / f"{vid}.json").write_text(json.dumps(receipt if False else rec, indent=2) + "\n")

        new_rows.append({
            "id": vid, "parent": PARENT_ID, "axis": "SPACING", "value": value,
            "n_dots": str(N_PARENT), "%_changed": f"{stats['pct_moved']:.2f}",
            "sha256": rec["sha256"], "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT", "predicted_change": pred, "predicted_range": pred_range,
            "ranking_basis": ranking_basis,
            "receipt_score": "", "receipt_date": "",
            "description": descs[value],
            "recommendation": "SPACING is lowest priority per SLOT_PLAN.md; spend a slot only on a live RECEIPT >= R0 + 0.01.",
        })
        card_id = vid
        cards[card_id] = cards_tmpl[value]
        print(f"BUILT {vid}  n={N_PARENT} moved={stats['n_removed']} ({stats['pct_moved']:.2f}%) min_d_cat={stats['min_dist']:.3f} sha={rec['sha256'][:8]}")

    # ---- update ledger (preserve schema + prior rows; idempotent by id) ----
    if LEDGER.is_file():
        with LEDGER.open(newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            prior = [r for r in reader if r["id"] not in {row["id"] for row in new_rows}]
    else:
        fieldnames = ["id", "parent", "axis", "value", "n_dots", "%_changed", "sha256",
                      "sha256_zeros", "status", "predicted_change", "predicted_range",
                      "ranking_basis", "receipt_score", "receipt_date", "description", "recommendation"]
        prior = []
    with LEDGER.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in [*prior, *new_rows]:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    CARDS.write_text(json.dumps(cards, indent=2) + "\n")
    print(f"ledger: {len(new_rows)} SPACING rows appended; {len(prior)} prior rows preserved")
    print("cards written:", len(cards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
