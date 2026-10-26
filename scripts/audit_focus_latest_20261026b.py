#!/usr/bin/env python3
"""Independent GEMSDOE88 audit of the nine focus sites' latest 2026-10-26 heads.

Session arena/0b582cf7-gemsdoe88 (2026-10-26, second focus audit of the day).

The prior audit (scripts/audit_focus_sites_20261026.py, session c59db412)
pinned each focus repository at the HEAD observed earlier on 2026-10-26.
All nine repositories have since advanced (parallel sessions merged new
2026-10-26 candidates).  This script re-pins the new HEADs, downloads each
site's single headline/latest candidate GeoTIFF at that exact commit via
``gh api`` (github.com / api.github.com only), and re-measures it locally:

* SHA-256 of the saved bytes (vs the sibling-claimed SHA-256 where published);
* strict full-grid format: one band, dtype, EPSG:32611, 3730x3292, exact
  sample geotransform, all 12,279,160 cells finite and inside [0, 1]
  (the portal error class "Predicted values must be in range [0, 1]");
* positive-pixel ("dot") count, dots on the public catalogue, dots at
  catalogue distance <= 2 px, share of dots > 25 px from the catalogue;
* 3-px forward dot overlap and exact 0-px fraction against the SHA-pinned
  registry references already restored in ``data/registry/``:
  the dense 17GEMSDOE witness (literal Parallel-Run Protocol rule 1),
  19GEMSDOE H19-5, GEMSDOE25/30 D2.8 and GEMSDOE32 H33-2-B2.

Sibling holdout numbers are transcribed from each repository's README at the
pinned HEAD and are labelled SIBLING-REPORTED — they are NOT re-run here and
are NOT HOLDOUT-DTI (gems57-pooled-hide-v2) unless the sibling used that
evaluator.  No number produced by this script is a leaderboard score.

Default mode is an offline check of the stored deliverables (used by tests).
``--regenerate`` performs the network fetch + raster measurement and rewrites
the deliverables; it requires the restored ``data/`` inputs
(``bash scripts/download_competition_data.sh --validation``).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUDIT_DATE_UTC = "2026-10-26"
SESSION_BRANCH = "arena/0b582cf7-gemsdoe88"
SCHEMA = "gems88.focus-latest-audit-20261026b.v1"

# HEADs captured 2026-10-26 with `git ls-remote ... HEAD` in this session.
HEADS = {
    "GEMSDOE24": "17496743a9695974370512db64d8140ea1ccfd2f",
    "GEMSDOE25": "88a29e094989b0e23916136e593474875d067656",
    "GEMSDOE27": "426426b402f90f4e0786990b4edd261d9dd48085",
    "GEMSDOE28": "348ff086e29b9c48bb7104daacb647af31a184bf",
    "GEMSDOE30": "73db382d3c990d0aa0b5126997a67213cc56dee4",
    "GEMSDOE31": "e6e85b357914068b3ba57ace0f899dde13f110a6",
    "GEMSDOE32": "9e55d5d61cb748533691ed183b1b2f2e04643add",
    "GEMSDOE33": "fded538406627b8d154a2fef5b5331f656d7e0f2",
    "GEMSDOE36": "4938a123133b4747079cc1c1c93a11e50c1376a7",
}

# HEADs pinned by the earlier same-day audit (evidence/focus_sites_20261026_audit.json).
PRIOR_HEADS = {
    "GEMSDOE24": "758af9ffb6ac5e3f82af6bd472f82d246dce55f0",
    "GEMSDOE25": "0a45b3ca6403f7e8d4deac5d8b208797d5e8f477",
    "GEMSDOE27": "927322eadbde56be42ae129ccdfb9b37540d8e60",
    "GEMSDOE28": "7066e7e9b546027e0cccf835af906e05384cba60",
    "GEMSDOE30": "78ae70817af861c077ce1655c3f9115c5b0f537a",
    "GEMSDOE31": "3c1be4993a059fa0af8b6782d86882efddd0f489",
    "GEMSDOE32": "15a5fce9494da62a2d8e41943669a7e645c06f75",
    "GEMSDOE33": "b542e5ce4186b54dbd07a6a6e8756be676a3f088",
    "GEMSDOE36": "1f92ee9c685db3f079b5995bffc71dda53e23497",
}

FOCUS_SITES = list(HEADS.keys())

# One headline/latest candidate per site, taken from the top decision banner
# of each repository README at the pinned HEAD.  Sibling fields are verbatim
# transcriptions (shortened) of that banner; they are SIBLING-REPORTED only.
CANDIDATES = [
    {
        "site": "GEMSDOE24",
        "path": "docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
        "candidate_id": "H24-DPRF1",
        "sibling_claimed_sha256": "c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1",
        "sibling_verdict": "DO_NOT_SUBMIT (gems-selector-v2-literal-quota-fail-closed: spacing-5 lattice + unknown quota)",
        "sibling_holdout": "SIBLING-REPORTED HOLDOUT-DTI 0.16379 [0.15045, 0.17739], gems-segment-pooled-v1, 60,988 withheld positives (not re-run here; not gems57-pooled-hide-v2)",
    },
    {
        "site": "GEMSDOE25",
        "path": "docs/downloads/gems25-h71-hgpc-blind-b2-sapd3-k3p5-20261026-9eb0c31e5149-zeros.tif",
        "candidate_id": "H71-HGPC-BLIND",
        "sibling_claimed_sha256": None,
        "sibling_verdict": "DO NOT SUBMIT (HOLDOUT-DTI FAIL vs H35)",
        "sibling_holdout": "SIBLING-REPORTED HOLDOUT-DTI 0.0506 vs H35 0.1499 (own lane instrument, GATE FAIL; not re-run here)",
    },
    {
        "site": "GEMSDOE27",
        "path": "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
        "candidate_id": "H31-1-DRCG-WL-CELF28",
        "sibling_claimed_sha256": "2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe",
        "sibling_verdict": "CLAIMED 'OK TO DOWNLOAD AND SUBMIT' by GEMSDOE27 (27-raster screen: 12 peers + 2 own scored + 13 own research; private gems27.metric.dti_binary v1 blind instrument)",
        "sibling_holdout": "SIBLING-REPORTED blind pooled HOLDOUT-DTI 0.047302, gems27.metric.dti_binary v1 + 600m-buffered-quadrant-40cell, seeds 400-409, 289,180 withheld positive occurrences (repeated-seed occurrences; not gems57-pooled-hide-v2; not re-run here)",
    },
    {
        "site": "GEMSDOE28",
        "path": "docs/downloads/gems28-s20-nchc-20261026-d432a1d5d6ee-allfinite.tif",
        "candidate_id": "S20-NCHC",
        "sibling_claimed_sha256": None,
        "sibling_verdict": "DO NOT SUBMIT (verdict negative; paired delta CI below zero)",
        "sibling_holdout": "SIBLING-REPORTED HOLDOUT-DTI 0.131263 [0.120346, 0.141838] vs baseline 0.144433, gems-segment-pooled-v1, 60,988 withheld positives (not re-run here)",
    },
    {
        "site": "GEMSDOE30",
        "path": "docs/research/2026-10-26-fflidar/gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif",
        "candidate_id": "FFL-1-MSDB-LIDAR-FUSION",
        "sibling_claimed_sha256": "7950607036e51faaf0258b4efeff29d75b8f12eb712aa592cd661822d3c85c07",
        "sibling_verdict": "DO NOT SUBMIT — DUPLICATE-STOPPED (78.28% of dots within 3 px of MSDB-1v2 > 70%)",
        "sibling_holdout": "SIBLING-REPORTED HOLDOUT-DTI 0.182417 [0.168230, 0.196433] vs 0.175639 same-run control, component-holdout-v3-blockstats-20261025, 60,988 withheld positives (not re-run here)",
    },
    {
        "site": "GEMSDOE31",
        "path": "docs/downloads/gems31-xfcoh31-xfield-coherence-37654-20261026-zeros.tif",
        "candidate_id": "XFCOH31",
        "sibling_claimed_sha256": None,
        "sibling_verdict": "DO NOT SUBMIT (holdout-negative; also literal 695-registry lattice STOP recorded in repo)",
        "sibling_holdout": "SIBLING-REPORTED HOLDOUT-DTI 0.04588 vs base-19 control 0.04812, gemsdoe31-holdout-v1, 58,625 withheld positives (not re-run here)",
    },
    {
        "site": "GEMSDOE32",
        "path": "docs/downloads/gemsdoe32-h38g1-lidar-geodawn-gdr-celf37654-20261026T013500Z-35859e28-zeros.tif",
        "candidate_id": "EXP3_H38_G1_CORROB",
        "sibling_claimed_sha256": "6efe140229c46b274ab7431bab0b9c1318ade642096ca8a1ff8c36317d2d68ff",
        "sibling_verdict": "DO NOT SUBMIT (SGMC proxy trails champion; 99.71% vs r13-lattice-s5; 77.56% vs local hcvf2)",
        "sibling_holdout": "SIBLING-REPORTED HOLDOUT-DTI 0.11696 [0.10053, 0.13204], GEMSDOE32-HIDE-RECOVER-v3.0 (not re-run here; paired vs champion 0.09920 on same private instrument)",
    },
    {
        "site": "GEMSDOE33",
        "path": "docs/downloads/gemsdoe33-a33-r2-csht-transfer-37654-20261026-0b78c04d5fad-zeros.tif",
        "candidate_id": "A33-R2-CSHT",
        "sibling_claimed_sha256": "14ab452c22aaf07444cd02e589fce4627d682e99f44c63e78dc1383955e0c602",
        "sibling_verdict": "DO NOT SUBMIT (verdict duplicate: pre-placement surface >70% 3-px overlap vs GEMSDOE30 MSDB1 / GEMSDOE24 GVC1 / GEMSDOE25 H66 surfaces)",
        "sibling_holdout": "SIBLING-REPORTED screen HOLDOUT-DTI 0.136716 / confirmation 0.131169 vs incumbent 0.112418/0.115122, 8/8 folds (own instrument; not re-run here)",
    },
    {
        "site": "GEMSDOE36",
        "path": "docs/downloads/gemsdoe36-atvr36-20261026.tif",
        "candidate_id": "ATVR-36-EXP2",
        "sibling_claimed_sha256": "54f493f4fa5c74ed3a02f88ca6d47272b0c3cee0cc0bd9bbd9cb94eaf997204a",
        "sibling_verdict": "DO NOT SUBMIT — HOLD WEEKLY SLOT (verdict negative; literal 201-raster blanket check FAIL 0.8936)",
        "sibling_holdout": "SIBLING-REPORTED HOLDOUT-DTI 0.114542 [0.078547, 0.151221] (gems36-segment-audit-v1) / 0.117925 [0.101961, 0.132998] (gems-segment-pooled-v1) (not re-run here)",
    },
]

REFS = [
    ("dense_17gemdoe", "data/registry/dense_17gemdoe.tif", "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"),
    ("gems19_h19_5", "data/registry/gems19_h19_5.tif", "ef2ae808eb7179861b9f1ff753fd3ded625ace7b7c158e29cec45bbd8fa3cfaa"),
    ("gems25_d28", "data/registry/gems25_d28.tif", "3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd3091845cd9bcc30"),
    ("h33_h33_2_b2", "data/registry/h33_education.tif", "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"),
]

EVIDENCE_JSON = Path("evidence/focus_latest_20261026b_audit.json")
PUBLIC_JSON = Path("docs/data/focus_latest_20261026b.json")
PUBLIC_CSV = Path("docs/data/focus_latest_20261026b.csv")
CACHE_DIR = Path(".scratch/focus_latest_20261026b")


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def fetch_candidate(site: str, path: str, head: str, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{site}__{Path(path).name}"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    route = f"repos/buffedlizard55-lab/{site}/contents/{path}?ref={head}"
    proc = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw", route],
        capture_output=True, check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(f"gh fetch failed for {site}:{path}: {proc.stderr[:400]!r}")
    dest.write_bytes(proc.stdout)
    return dest


def regenerate(root: Path) -> dict:
    import numpy as np
    import rasterio
    from scipy import ndimage

    sample_path = root / "data/bridge/sample_submission.tif"
    faults_path = root / "data/bridge/existing_faults.tif"
    for required in (sample_path, faults_path):
        if not required.exists():
            raise FileNotFoundError(
                f"{required} missing — run: bash scripts/download_competition_data.sh --validation"
            )

    with rasterio.open(sample_path) as ds:
        sample = ds.read(1)
        grid = {
            "shape": [ds.height, ds.width],
            "crs": str(ds.crs),
            "transform": [float(v) for v in ds.transform[:6]],
        }
    footprint = np.isfinite(sample)
    with rasterio.open(faults_path) as ds:
        catalogue = ds.read(1) > 0
    allowed = footprint & ~catalogue
    if int(footprint.sum()) != 5167373 or int(allowed.sum()) != 5106385:
        raise ValueError("footprint/allowed counts differ from the pinned grid record")

    ref_dists = {}
    ref_supports = {}
    for name, rel, pinned_sha in REFS:
        blob = (root / rel).read_bytes()
        if sha256_bytes(blob) != pinned_sha:
            raise ValueError(f"registry reference pin mismatch: {rel}")
        with rasterio.open(root / rel) as ds:
            arr = ds.read(1)
        support = np.isfinite(arr) & (arr > 0)
        ref_supports[name] = support
        ref_dists[name] = ndimage.distance_transform_edt(~support)
    cat_dist = ndimage.distance_transform_edt(~catalogue)

    cache = root / CACHE_DIR
    rows = []
    for cand in CANDIDATES:
        site = cand["site"]
        head = HEADS[site]
        local = fetch_candidate(site, cand["path"], head, cache)
        blob = local.read_bytes()
        digest = sha256_bytes(blob)
        with rasterio.open(io.BytesIO(blob)) as ds:
            arr = ds.read(1)
            meta = {
                "band_count": ds.count,
                "dtype": ds.dtypes[0],
                "shape": [ds.height, ds.width],
                "crs": str(ds.crs),
                "transform": [float(v) for v in ds.transform[:6]],
                "nodata": None if ds.nodata is None else float(ds.nodata),
            }
        finite = np.isfinite(arr)
        pos = finite & (arr > 0)
        n_pos = int(pos.sum())
        if n_pos == 0:
            raise ValueError(f"{site} candidate has no positive pixels")
        dcat = cat_dist[pos]
        metrics = {
            "positive_pixels": n_pos,
            "positive_on_catalogue": int((pos & catalogue).sum()),
            "positive_outside_footprint": int((pos & ~footprint).sum()),
            "d_cat_le2_px": int((dcat <= 2.0).sum()),
            "frac_gt25_px_from_catalogue": float((dcat > 25.0).mean()),
        }
        for name, _rel, _sha in REFS:
            d = ref_dists[name][pos]
            metrics[f"overlap_3px_vs_{name}"] = float((d <= 3.0).mean())
            metrics[f"exact_0px_frac_vs_{name}"] = float((d == 0.0).mean())
        portal_safe = bool(
            meta["band_count"] == 1
            and meta["shape"] == grid["shape"]
            and meta["crs"] == grid["crs"]
            and meta["transform"] == grid["transform"]
            and bool(finite.all())
            and float(arr[finite].min()) >= 0.0
            and float(arr[finite].max()) <= 1.0
        )
        literal_overlap = metrics["overlap_3px_vs_dense_17gemdoe"]
        rows.append({
            "site": site,
            "pages_url": f"https://buffedlizard55-lab.github.io/{site}/",
            "repo_url": f"https://github.com/buffedlizard55-lab/{site}",
            "inspected_repo_head_sha": head,
            "prior_audit_head_sha": PRIOR_HEADS[site],
            "head_advanced_since_prior_audit": head != PRIOR_HEADS[site],
            "candidate_id": cand["candidate_id"],
            "candidate_path_in_repo": cand["path"],
            "candidate_source_url": f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/{cand['path']}",
            "readme_source_url": f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/README.md",
            "sha256": digest,
            "bytes": len(blob),
            "sibling_claimed_sha256": cand["sibling_claimed_sha256"],
            "sha256_matches_sibling_claim": (
                None if cand["sibling_claimed_sha256"] is None
                else digest == cand["sibling_claimed_sha256"]
            ),
            "raster": meta,
            "finite_cells": int(finite.sum()),
            "total_cells": int(arr.size),
            "min_finite": float(arr[finite].min()),
            "max_finite": float(arr[finite].max()),
            "portal_safe_full_grid_0_1_and_grid_match": portal_safe,
            **metrics,
            "sibling_verdict": cand["sibling_verdict"],
            "sibling_holdout": cand["sibling_holdout"],
            "sibling_claims_ok_to_submit": site == "GEMSDOE27",
            "gemsdoe88_literal_protocol_verdict": (
                "DUPLICATE_STOP" if literal_overlap > 0.70 else "NOT_DUPLICATE_ON_DENSE_WITNESS_ONLY"
            ),
            "cleared_to_submit_under_gemsdoe88_literal_protocol": False,
            "organizer_receipt": None,
            "organizer_confirmed_score": None,
        })

    promoting = [r["site"] for r in rows if r["sibling_claims_ok_to_submit"]]
    audit = {
        "schema": SCHEMA,
        "audit_date_utc": AUDIT_DATE_UTC,
        "session_branch": SESSION_BRANCH,
        "evidence_policy": {
            "sibling_holdout_values": "SIBLING-REPORTED — transcribed from each README at the pinned HEAD; NOT re-run by GEMSDOE88; evaluators differ by repo and are not comparable to each other or to a leaderboard score",
            "overlap_and_format_values": "REGISTRY-MEASUREMENT — computed by GEMSDOE88 in this session from saved bytes (float64 EDT, radius <= 3 px)",
            "organizer_receipts_present": 0,
            "literal_all_registry_overlap_limit_3px": 0.7,
            "universal_witness_file": "data/registry/dense_17gemdoe.tif",
            "universal_witness_sha256": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
            "allowed_off_catalogue_footprint_pixels": int(allowed.sum()),
            "grid": grid,
        },
        "summary_verdict": {
            "focus_site_count": 9,
            "heads_advanced_since_prior_audit": int(sum(r["head_advanced_since_prior_audit"] for r in rows)),
            "latest_candidates_measured": len(rows),
            "sibling_sites_claiming_ok_to_submit": promoting,
            "cleared_under_gemsdoe88_literal_protocol_count": 0,
            "ok_to_submit": False,
            "decision": "DUPLICATE_STOP",
            "note": (
                "Every latest 2026-10-26 headline candidate is a nonempty dot set inside the "
                "allowed domain, so its literal 3-px forward overlap with the dense 17GEMSDOE "
                "witness exceeds the 0.70 limit (see per-site measurements). GEMSDOE27 is the "
                "only focus site whose own narrower 27-raster screen + private metric currently "
                "claims OK TO SUBMIT; that claim does not survive the GEMSDOE88 literal "
                "all-registry rule and is flagged IR-88-0B582CF7-01. Selector scoping of dense "
                "priors/lattices remains a separate human/selector decision (Protocol rule 6)."
            ),
        },
        "focus_sites": rows,
    }
    return audit


def write_outputs(root: Path, audit: dict) -> None:
    payload = (json.dumps(audit, indent=2) + "\n").encode("utf-8")
    for rel in (EVIDENCE_JSON, PUBLIC_JSON):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
    dest = root / PUBLIC_CSV
    dest.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "site", "inspected_repo_head_sha", "candidate_id", "sha256", "positive_pixels",
        "portal_safe_full_grid_0_1_and_grid_match", "d_cat_le2_px",
        "frac_gt25_px_from_catalogue", "overlap_3px_vs_dense_17gemdoe",
        "overlap_3px_vs_gems19_h19_5", "overlap_3px_vs_gems25_d28",
        "overlap_3px_vs_h33_h33_2_b2", "sibling_claims_ok_to_submit",
        "cleared_to_submit_under_gemsdoe88_literal_protocol",
    ]
    with dest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in audit["focus_sites"]:
            w.writerow({k: row[k] for k in fields})


def check(root: Path) -> dict:
    ev = (root / EVIDENCE_JSON).read_bytes()
    pub = (root / PUBLIC_JSON).read_bytes()
    if ev != pub:
        raise ValueError("evidence/docs focus-latest JSON copies differ")
    audit = json.loads(ev)
    if audit["schema"] != SCHEMA:
        raise ValueError("schema mismatch")
    rows = audit["focus_sites"]
    if [r["site"] for r in rows] != FOCUS_SITES:
        raise ValueError("focus site order/count mismatch")
    verdict = audit["summary_verdict"]
    if verdict["ok_to_submit"] is not False or verdict["decision"] != "DUPLICATE_STOP":
        raise ValueError("summary verdict must stay fail-closed")
    if verdict["cleared_under_gemsdoe88_literal_protocol_count"] != 0:
        raise ValueError("no candidate may be cleared under the literal protocol")
    for row in rows:
        if row["inspected_repo_head_sha"] != HEADS[row["site"]]:
            raise ValueError(f"head pin mismatch: {row['site']}")
        if row["cleared_to_submit_under_gemsdoe88_literal_protocol"] is not False:
            raise ValueError(f"candidate wrongly cleared: {row['site']}")
        if not row["overlap_3px_vs_dense_17gemdoe"] > 0.70:
            raise ValueError(f"dense-witness overlap must exceed literal limit: {row['site']}")
        if row["organizer_confirmed_score"] is not None or row["organizer_receipt"] is not None:
            raise ValueError(f"organizer evidence invented: {row['site']}")
        if row["sibling_claimed_sha256"] is not None and row["sha256_matches_sibling_claim"] is not True:
            raise ValueError(f"SHA-256 mismatch vs sibling claim: {row['site']}")
    with (root / PUBLIC_CSV).open(encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))
    if [r["site"] for r in csv_rows] != FOCUS_SITES:
        raise ValueError("CSV site order/count mismatch")
    return audit


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate", action="store_true",
                        help="fetch candidates at pinned HEADs and rewrite deliverables")
    parser.add_argument("--require-submit", action="store_true",
                        help="exit 2 unless a candidate is cleared (expected: never here)")
    args = parser.parse_args(argv)
    try:
        if args.regenerate:
            audit = regenerate(root)
            write_outputs(root, audit)
            audit = check(root)
        else:
            audit = check(root)
    except Exception as exc:  # fail closed with a machine-readable status
        print(json.dumps({"status": "FAIL", "error": str(exc), "ok_to_submit": False}))
        return 1
    ok = bool(audit["summary_verdict"]["ok_to_submit"])
    print(json.dumps({
        "status": "PASS",
        "decision": audit["summary_verdict"]["decision"],
        "focus_sites": len(audit["focus_sites"]),
        "sibling_sites_claiming_ok_to_submit": audit["summary_verdict"]["sibling_sites_claiming_ok_to_submit"],
        "cleared_under_gemsdoe88_literal_protocol_count": 0,
        "ok_to_submit": ok,
    }))
    if args.require_submit and not ok:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
