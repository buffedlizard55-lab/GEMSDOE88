"""Fast diagnostic screening plus separate full-footprint shared verification.

Sampled rank checks cannot clear either phase of the literal uniqueness gate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import rankdata

from vendor.gems57 import uniqueness as vend_uniq

PORTFOLIO_DIR = Path("/tmp/gems88_portfolio")
RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70
JACCARD_LIMIT = 0.50


class PortfolioUniquenessAuditor:
    """Bit-exact 3-px halo overlap + 250k-stratified Spearman check across all 1,167 org rasters."""

    def __init__(self, portfolio_dir: Path = PORTFOLIO_DIR) -> None:
        self.portfolio_dir = Path(portfolio_dir)
        self.index_meta = json.loads((self.portfolio_dir / "registry_index.json").read_text())
        self.rasters: list[dict[str, Any]] = self.index_meta["rasters"]
        self.halos_packed = np.load(self.portfolio_dir / "halos_live_packed.npy", mmap_mode="r")
        self.unit_ranks = np.load(self.portfolio_dir / "unit_ranks.npy", mmap_mode="r")
        self.is_const = np.load(self.portfolio_dir / "is_const.npy")
        self.sub_idx = np.load(self.portfolio_dir / "sub_idx.npy")
        self.n_rasters = len(self.rasters)
        self.halo_cov = np.array([float(r["halo_coverage"]) for r in self.rasters], dtype=np.float64)
        self.pos_counts = np.array([int(r["positive_pixels"]) for r in self.rasters], dtype=np.float64)
        self.is_discriminating = self.halo_cov < OVERLAP_LIMIT

    def audit_surface(
        self, surface_2d: np.ndarray, footprint_mask: np.ndarray, active_mask: np.ndarray, label: str
    ) -> dict[str, Any]:
        """Audit continuous pre-placement surface (`sub_idx` flat grid indices, `halos_packed` on `live_active`)."""
        vals_act = np.asarray(surface_2d[active_mask], dtype=np.float64)
        sub_vals = np.asarray(surface_2d.ravel()[self.sub_idx], dtype=np.float64)
        if not vals_act.size or not np.isfinite(vals_act).all() or not np.isfinite(sub_vals).all():
            raise ValueError('empty or non-finite surface cannot be screened')
        r = rankdata(sub_vals).astype(np.float64)
        r -= r.mean()
        nrm = float(np.linalg.norm(r))
        rhos = np.zeros(self.n_rasters, dtype=np.float64)
        if nrm > 0:
            valid_r = ~self.is_const
            rhos[valid_r] = (self.unit_ranks[valid_r] @ r.astype(np.float32)) / nrm

        # Pre-placement support check on top 37,654 active pixels (matching target support size)
        k = min(37_654, vals_act.size)
        top_idx = np.argpartition(vals_act, -k)[-k:]
        byte_idx = top_idx >> 3
        bit_mask = (1 << (7 - (top_idx & 7))).astype(np.uint8)
        hits = ((self.halos_packed[:, byte_idx] & bit_mask[None, :]) != 0).sum(axis=1)
        ov = hits.astype(np.float64) / float(k)

        abs_rhos = np.abs(rhos)
        wi_rho = int(np.argmax(abs_rhos))
        disc_ov = np.where(self.is_discriminating, ov, -1.0)
        wi_ov = int(np.argmax(disc_ov))
        wi_raw = int(np.argmax(ov))

        dup_rho = int((abs_rhos > RHO_LIMIT).sum())
        # Dense priors are binding too. Discriminating-only values below are
        # retained as diagnostics, never as the all-registry decision.
        dup_ov = int((ov > OVERLAP_LIMIT).sum())
        err_n = len(self.index_meta["errors"]) if isinstance(self.index_meta["errors"], list) else int(self.index_meta["errors"])
        screening_passed = (dup_rho == 0 and dup_ov == 0 and err_n == 0
                            and nrm > 0 and np.isfinite(rhos).all() and not self.is_const.any()
                            and self.index_meta.get("complete_accessible_scan") is True)
        return {
            "stage": "pre_placement_surface",
            "label": label,
            "repos_scanned": int(self.index_meta["repos_scanned"]),
            "rasters_checked": self.n_rasters,
            "discriminating_checked": int(self.is_discriminating.sum()),
            "space_filling_checked": int((~self.is_discriminating).sum()),
            "errors": err_n,
            "worst_abs_spearman": round(float(abs_rhos[wi_rho]), 6),
            "worst_signed_spearman": round(float(rhos[wi_rho]), 6),
            "worst_spearman_raster": f"{self.rasters[wi_rho]['repo_first']}:{self.rasters[wi_rho]['submission']}",
            "worst_top37654_discriminating_3px_overlap": (round(float(disc_ov[wi_ov]), 6)
                                                            if self.is_discriminating.any() else None),
            "worst_overlap_raster": (f"{self.rasters[wi_ov]['repo_first']}:{self.rasters[wi_ov]['submission']}"
                                      if self.is_discriminating.any() else None),
            "worst_raw_overlap_including_spacefill": round(float(ov[wi_raw]), 6),
            "worst_literal_overlap_raster": f"{self.rasters[wi_raw]['repo_first']}:{self.rasters[wi_raw]['submission']}",
            "duplicate_by_rho_count": dup_rho,
            "duplicate_by_overlap_count": dup_ov,
            "screening_passed": bool(screening_passed),
            "screening_only": True,
            "decision": "DUPLICATE_STOP" if dup_rho or dup_ov else "FULL_CHECK_REQUIRED",
            # A sampled-Spearman screen cannot authorize dot placement.
            "passed": False,
            "stop_required": True,
        }

    def audit_dots(
        self, pred_2d: np.ndarray, footprint_mask: np.ndarray, active_mask: np.ndarray, label: str
    ) -> dict[str, Any]:
        """Exact bit-unpacked 3-px forward overlap (`live_active`) + Spearman (`sub_idx` flat grid) across all 1,167 rasters."""
        vals_act = np.asarray(pred_2d[active_mask], dtype=np.float32)
        if not np.isfinite(vals_act).all():
            raise ValueError("non-finite candidate cannot be screened")
        dot_idx = np.flatnonzero(vals_act > 0)
        n_dots = int(dot_idx.size)
        if n_dots == 0:
            raise ValueError("Candidate prediction has 0 positive dots!")

        byte_idx = dot_idx >> 3
        bit_mask = (1 << (7 - (dot_idx & 7))).astype(np.uint8)
        hits = ((self.halos_packed[:, byte_idx] & bit_mask[None, :]) != 0).sum(axis=1)
        ov = hits.astype(np.float64) / float(n_dots)

        sub_vals = np.asarray(pred_2d.ravel()[self.sub_idx], dtype=np.float64)
        if not np.isfinite(sub_vals).all():
            raise ValueError("non-finite candidate cannot be screened")
        r = rankdata(sub_vals).astype(np.float64)
        r -= r.mean()
        nrm = float(np.linalg.norm(r))
        rhos = np.zeros(self.n_rasters, dtype=np.float64)
        if nrm > 0:
            valid_r = ~self.is_const
            rhos[valid_r] = (self.unit_ranks[valid_r] @ r.astype(np.float32)) / nrm

        abs_rhos = np.abs(rhos)
        wi_rho = int(np.argmax(abs_rhos))
        disc_ov = np.where(self.is_discriminating, ov, -1.0)
        wi_ov = int(np.argmax(disc_ov))
        wi_raw = int(np.argmax(ov))

        dup_rho = int((abs_rhos > RHO_LIMIT).sum())
        dup_ov = int((ov > OVERLAP_LIMIT).sum())

        top5 = []
        discriminating_indices = np.flatnonzero(self.is_discriminating)
        for idx in discriminating_indices[np.argsort(-ov[discriminating_indices])[:8]]:
            idx = int(idx)
            top5.append({
                "repo": self.rasters[idx]["repo_first"],
                "submission": self.rasters[idx]["submission"],
                "sha256_prefix": self.rasters[idx]["sha256"][:16],
                "their_dots": int(self.rasters[idx]["positive_pixels"]),
                "my_dots_within_3px_of_theirs": round(float(ov[idx]), 6),
                "spearman_rho": round(float(rhos[idx]), 6),
            })

        err_n = len(self.index_meta["errors"]) if isinstance(self.index_meta["errors"], list) else int(self.index_meta["errors"])
        screening_passed = (dup_rho == 0 and dup_ov == 0 and err_n == 0
                            and nrm > 0 and np.isfinite(rhos).all() and not self.is_const.any()
                            and self.index_meta.get("complete_accessible_scan") is True)
        return {
            "stage": "post_placement_dots",
            "label": label,
            "my_dots": n_dots,
            "repos_scanned": int(self.index_meta["repos_scanned"]),
            "rasters_checked": self.n_rasters,
            "discriminating_checked": int(self.is_discriminating.sum()),
            "space_filling_checked": int((~self.is_discriminating).sum()),
            "errors": err_n,
            "worst_abs_spearman": round(float(abs_rhos[wi_rho]), 6),
            "worst_signed_spearman": round(float(rhos[wi_rho]), 6),
            "worst_spearman_raster": f"{self.rasters[wi_rho]['repo_first']}:{self.rasters[wi_rho]['submission']}",
            "worst_discriminating_3px_overlap": (round(float(disc_ov[wi_ov]), 6)
                                                    if self.is_discriminating.any() else None),
            "worst_overlap_raster": (f"{self.rasters[wi_ov]['repo_first']}:{self.rasters[wi_ov]['submission']}"
                                      if self.is_discriminating.any() else None),
            "worst_raw_overlap_including_spacefill": round(float(ov[wi_raw]), 6),
            "worst_literal_overlap_raster": f"{self.rasters[wi_raw]['repo_first']}:{self.rasters[wi_raw]['submission']}",
            "duplicate_by_rho_count": dup_rho,
            "duplicate_by_overlap_count": dup_ov,
            "top_nearest_discriminating_priors": top5,
            "screening_passed": bool(screening_passed),
            "screening_only": True,
            "decision": "DUPLICATE_STOP" if dup_rho or dup_ov else "FULL_CHECK_REQUIRED",
            # A sampled rank check cannot approve the final raster.
            "passed": False,
            "stop_required": True,
        }


def _audit_worker(args: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Worker for full 5,167,373-pixel `vendor/gems57/uniqueness.compare_array_to_registry` chunk."""
    mine_path, fp_path, sub_records, file_sha = args
    import rasterio as _rio
    from vendor.gems57 import uniqueness as _vu

    with _rio.open(mine_path) as src:
        mine = src.read(1).astype(np.float32)
    fp = np.load(fp_path, mmap_mode="r")
    res = _vu.compare_array_to_registry(
        mine,
        {"complete_accessible_scan": True, "errors": [], "rasters": sub_records},
        fp,
        file_sha256=file_sha,
        include_reverse=False,
    )
    return res["rows"]


def run_full_vendor_uniqueness_certificate(
    tif_path: Path,
    footprint: np.ndarray,
    portfolio_dir: Path = PORTFOLIO_DIR,
    n_workers: int = 2,
) -> dict[str, Any]:
    """Run full-resolution 5,167,373-pixel `vendor/gems57/uniqueness.py` check across ALL 1,167 `.tif` blobs via `spawn`."""
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor

    meta = json.loads((portfolio_dir / "registry_index.json").read_text())
    tifs_dir = portfolio_dir / "tifs"
    hydrated_rasters = [
        {**r, "cache_file": str(tifs_dir / f"{r['sha256']}.tif"), "sources": [r["submission"]]}
        for r in meta["rasters"]
    ]
    fp_tmp = Path("/tmp/gems88_cache/footprint_bool.npy")
    np.save(fp_tmp, np.asarray(footprint, dtype=bool))
    file_sha = hashlib.sha256(Path(tif_path).read_bytes()).hexdigest()

    import rasterio as _rio
    with _rio.open(tif_path) as src:
        mine = src.read(1).astype(np.float32)
    decoded_sha = hashlib.sha256(np.ascontiguousarray(mine).tobytes()).hexdigest()
    my_dots = int(((mine > 0) & footprint).sum())
    rank_var = bool(np.ptp(mine[footprint]) > 0)
    del mine
    import gc as _gc
    _gc.collect()

    chunks = [hydrated_rasters[i::n_workers] for i in range(n_workers)]
    all_rows: list[dict[str, Any]] = []
    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=ctx) as pool:
        for part in pool.map(_audit_worker, [(str(tif_path), str(fp_tmp), c, file_sha) for c in chunks]):
            all_rows.extend(part)

    res = vend_uniq.summarize_registry_rows(
        all_rows,
        registry_rasters_expected=len(hydrated_rasters),
        complete_accessible_scan=bool(meta["complete_accessible_scan"]),
        source_errors=meta["errors"],
        candidate_meta={
            "my_file": str(tif_path),
            "my_dots": my_dots,
            "candidate_decoded_sha256": decoded_sha,
            "candidate_file_sha256": file_sha,
            "candidate_rank_variation": rank_var,
        },
        scope="Full 5,167,373-pixel SHA-256-pinned scan across all 1,167 unique accessible EPSG:32611 rasters across all 92 buffedlizard55-lab repositories.",
    )
    rows = res.pop("rows", [])
    disc = [r for r in rows if not r.get("space_filling_prior", False) and "error" not in r]
    disc.sort(key=lambda x: -x["my_dots_within_3px_of_theirs"])
    res["top12_discriminating_rows"] = disc[:12]
    res["candidate_file_sha256_verified"] = file_sha
    return res
