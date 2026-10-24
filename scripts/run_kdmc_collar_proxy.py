#!/usr/bin/env python3
"""KDMC-88 Experiment 3 — resolve the catalogue-collar question on the only
instrument that can answer it.

Why a third instrument is needed
--------------------------------
The hide-and-recover holdout withholds whole **catalogue** components, so a
candidate that refuses to place dots within 3 px of the catalogue is
structurally forbidden from scoring on the withheld truth: Experiment 2
measured pooled DTI of **exactly 0.00000** for all 24 collar arms, and the
registry's own ``h33_education.tif`` (pruned to ``d_cat >= 2.236 px`` against
the full catalogue) scores 0.00389 for the same reason.  The holdout therefore
cannot rank collar on / collar off, and saying otherwise would be dishonest.

The off-catalogue SGMC proxy is the complementary instrument that can: its
truth population is ``(USGS SGMC faults) minus (competition catalogue)``, i.e.
real mapped faults that the competition catalogue does **not** contain — the
closest public stand-in for the "faults not in the current public USGS
database" the competition actually asks for.  It is a PROXY, never a score.

Outputs ``evidence/kdmc_experiment3_collar.json``.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import grid as g57grid, metric, uniqueness  # noqa: E402
from gems88 import kdmc  # noqa: E402

COLLARS = (0.0, 1.5, 3.0, 4.0, 6.0)
DENSITY = 0.01
SEP = 2.8284271247461903


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def proxy_truth(grid):
    """``(SGMC > 0) & ~catalogue & footprint`` rebuilt from the pinned bytes.

    ``gems57.offcatalogue.load_proxy_truth`` additionally opens
    ``derived_sgmc_faults_100m.tif`` purely to restate IR-57-SGMC-01 in its
    receipt; that file is **not** in the restore manifest (same family as
    IR-88-72), so the proxy is rebuilt here with the identical derivation rule
    and the discrepancy note is carried as text instead.
    """
    p = ROOT / "data" / "external" / "sgmc_faults_100m.tif"
    with rasterio.open(p) as src:
        if str(src.crs) != "EPSG:32611" or tuple(src.shape) != tuple(grid.shape):
            raise ValueError("SGMC raster is not on the pinned competition grid")
        sgmc = src.read(1)
    sgmc = (sgmc > 0) & (sgmc != 255)
    truth = sgmc & ~grid.catalogue & grid.footprint
    return truth, dict(
        file=str(p.relative_to(ROOT)), sha256=kdmc.sha256_file(p),
        derivation="proxy = (sgmc_faults_100m > 0) & ~catalogue & footprint",
        sgmc_pixels=int(sgmc.sum()), proxy_pixels=int(truth.sum()),
        evidence_class="PROXY (public SGMC compilation minus the competition catalogue)",
        declared_limit=("never an organizer label and never a score; it is the public "
                        "fault compilation the competition catalogue omits"),
        missing_input_note=("derived_sgmc_faults_100m.tif is referenced by "
                            "gems57.offcatalogue.load_proxy_truth but is absent from the "
                            "restore manifest; the proxy is rebuilt from the raw SGMC bytes "
                            "with the identical rule (IR-88-72 family)"))


def main() -> int:
    t0 = time.time()
    grid = g57grid.load_grid()
    truth, receipt = proxy_truth(grid)
    log(f"off-catalogue SGMC proxy: {int(truth.sum()):,} px "
        f"({truth.sum() / grid.footprint.sum() * 100:.3f}% of footprint)")

    rho = np.load(ROOT / ".cache" / "kdmc" / "rho_oof.npy").astype(np.float32)
    E = kdmc.expected_credit(rho)
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    base_allowed = grid.footprint & ~grid.catalogue

    def score(mask):
        return float(metric.dti_binary(mask, truth, valid=grid.footprint,
                                       known=grid.catalogue)["dti"])

    arms = []
    # Anchors: reproduce the repository's own documented proxy values so the
    # instrument is verified before it is used to decide anything.
    for nm, f in (("ANCHOR_h33_registry", "data/registry/h33_education.tif"),
                  ("ANCHOR_gems83_h83_gvcd", "data/registry/gems83_h83_gvcd.tif"),
                  ("ANCHOR_gems82_csam_dink", "data/registry/gems82_csam_dink.tif")):
        with rasterio.open(ROOT / f) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & grid.footprint
        arms.append(dict(arm=nm, collar_px=None, n_dots=int(m.sum()),
                         sgmc_proxy_dti=score(m), evidence_class="PROXY"))
        log(f"  {nm:<26} dots={int(m.sum()):>7,}  SGMC-PROXY={arms[-1]['sgmc_proxy_dti']:.6f}")

    n_target = int(round(DENSITY * base_allowed.sum()))
    masks = {}
    for collar in COLLARS:
        allowed = base_allowed if collar <= 0 else (base_allowed & (d_cat > collar))
        dots = kdmc.allocate_separated(E, allowed, SEP, -np.inf, max_rounds=400)
        idx = np.flatnonzero(dots.ravel())
        order = idx[np.lexsort((idx, -E.ravel()[idx]))][:n_target]
        m = np.zeros(grid.shape, bool)
        m.ravel()[order] = True
        masks[collar] = m
        s = score(m)
        pk = kdmc.packing_efficiency(m, grid.footprint)
        arms.append(dict(arm=f"MDC88_collar{collar:g}", collar_px=collar, n_dots=int(m.sum()),
                         sgmc_proxy_dti=s, evidence_class="PROXY",
                         min_d_catalogue_px=float(d_cat[m].min()),
                         frac_dots_within_3px_of_catalogue=float((d_cat[m] <= 3).mean()),
                         frac_dots_beyond_1km=float((d_cat[m] > 10).mean()),
                         packing_efficiency=pk["packing_efficiency"]))
        log(f"  MDC88_collar{collar:<14g} dots={int(m.sum()):>7,}  SGMC-PROXY={s:.6f}  "
            f"min d_cat={d_cat[m].min():.3f}px")

    best = max((a for a in arms if a["arm"].startswith("MDC88")),
               key=lambda a: a["sgmc_proxy_dti"])
    zero = next(a for a in arms if a["arm"] == "MDC88_collar0")
    h33 = next(a for a in arms if a["arm"] == "ANCHOR_h33_registry")
    report = dict(
        experiment="kdmc-88-exp3-collar-on-off-catalogue-proxy",
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        question=("Should the production field keep a d_catalogue collar? The blocked holdout "
                  "cannot answer: every collar arm scores exactly 0.00000 there by construction, "
                  "because the holdout's truth IS withheld catalogue geometry."),
        instrument=dict(name="off-catalogue SGMC proxy", scored_by="gems57.metric.dti_binary",
                        alpha=metric.ALPHA, beta=metric.BETA, radius_px=metric.RADIUS_PX,
                        valid="footprint", known="competition catalogue (masked out)", **receipt),
        configuration=dict(separation_px=SEP, density=DENSITY, n_dots=n_target,
                           density_source="holdout optimum from kdmc_experiment1/2"),
        arms=sorted(arms, key=lambda a: -a["sgmc_proxy_dti"]),
        conclusion=dict(
            best_collar_px=best["collar_px"], best_proxy_dti=best["sgmc_proxy_dti"],
            collar0_proxy_dti=zero["sgmc_proxy_dti"],
            delta_best_minus_collar0=best["sgmc_proxy_dti"] - zero["sgmc_proxy_dti"],
            registry_anchor_h33=h33["sgmc_proxy_dti"],
            margin_vs_h33=best["sgmc_proxy_dti"] - h33["sgmc_proxy_dti"],
            caveat=("PROXY, not a score. The repository's own no-evidence floor is |delta| >= 0.01; "
                    "read any smaller difference as a tie.")),
    )
    out = ROOT / "evidence" / "kdmc_experiment3_collar.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out}  ({time.time() - t0:.0f}s)")
    log(json.dumps(report["conclusion"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
