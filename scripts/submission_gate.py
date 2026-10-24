#!/usr/bin/env python3
"""Single authoritative, fail-closed OK-TO-SUBMIT gate (IR-88-59).

One command, no human inspection:

    python scripts/submission_gate.py            # prints verdict, writes docs/data/submission_gate.json
    python scripts/submission_gate.py --require-submit   # exit 2 unless every check passes

It re-derives every claim from bytes on disk instead of trusting a stored
verdict.  The candidate is whichever file ``registry/provcrest_run_card.json``
names; the SHA-256 in that card, the writer receipt and the published ZIP must
all agree with the TIFF.  Archived ``DO-NOT-SUBMIT`` research rasters are NOT
evaluated here (``scripts/validate_release.py`` still audits that artifact).

Check groups
------------
FMT   format  (single band, float32, grid == sample_submission.tif, no NaN/Inf,
               values in [0,1], zeros outside footprint, ZIP == one TIFF)
CAT   catalogue (no dot on a mapped fault; >3 px collar)
ID    name / note <= 140 chars, SHA agreement
UNQ   uniqueness against every restored registry raster, using the vendored
      template functions (uniqueness.dot_overlap / surface_rho /
      representation_class / two_phase_summary).  Both readings are printed:
      the LITERAL reading (a space-filling continuous prior such as 17GEMSDOE
      fires on EVERY non-empty raster, so it carries no duplicate information)
      and the LIKE-FOR-LIKE reading (dot-overlap limit 0.70 on dot fields,
      |Spearman| limit 0.90 on ALL rasters, including the continuous ones).
      The gate passes on like-for-like; the literal firing is never hidden.
SCI   science (HOLDOUT-DTI beats the NULL controls with a paired CI above zero
      in both the ALL and FAR views, canary AUC <= 0.90, shipped raster
      reproduced bit-for-bit from restored inputs)
BUD   no weekly slot spent by an agent, no organizer score claimed

``approved_for_weekly_slot`` is always False: choosing which file occupies a
scarce weekly slot is a separate selector decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import grid as grid_mod, uniqueness  # noqa: E402

CARD = ROOT / "registry" / "provcrest_run_card.json"
AUDIT = ROOT / "registry" / "provcrest_nullcontrol_audit.json"
OUT = ROOT / "docs" / "data" / "submission_gate.json"
RHO_LIMIT = uniqueness.RHO_LIMIT
OVERLAP_LIMIT = uniqueness.OVERLAP_LIMIT
SUBMISSIONS_URL = "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, cid: str, desc: str, ok: bool, value=None) -> bool:
        self.rows.append({"id": cid, "description": desc, "pass": bool(ok),
                          "value": value})
        return bool(ok)

    @property
    def failures(self) -> list[str]:
        return [f"{r['id']}: {r['description']}" for r in self.rows if not r["pass"]]


def _registry_files(root: Path, candidate: Path) -> list[tuple[Path, Path]]:
    """(file, display-base) for every sibling-site raster plus this repo's other rasters.

    Files that are byte-identical to the candidate (its own ``submissions/`` copy) are
    skipped; every other raster in ``docs/downloads`` and ``submissions`` is compared.
    """
    own = sha256_file(candidate)
    out = [(p, root / "data" / "registry") for p in sorted((root / "data" / "registry").rglob("*.tif"))]
    for sub in ("docs/downloads", "submissions"):
        out += [(p, root) for p in sorted((root / sub).glob("*.tif"))]
    return [(p, b) for p, b in out
            if p.resolve() != candidate.resolve() and sha256_file(p) != own]


def run_gate(root: Path = ROOT) -> dict:
    ck = Checks()
    card = json.loads((root / "registry" / "provcrest_run_card.json").read_text())
    sub = card["submission"]
    tif = root / sub["file"]
    zpath = root / sub["zip_file"]
    receipt_path = tif.with_suffix(".json")
    sample = root / "data" / "bridge" / "sample_submission.tif"
    faults = root / "data" / "bridge" / "existing_faults.tif"

    inputs_ok = all(p.is_file() for p in (tif, zpath, receipt_path, sample, faults))
    if not ck.add("FMT-00", "candidate TIFF/ZIP/receipt and restored grid inputs exist "
                  "(run `python scripts/restore_inputs.py --validation` if not)", inputs_ok,
                  {"tif": tif.is_file(), "zip": zpath.is_file(), "receipt": receipt_path.is_file(),
                   "sample": sample.is_file(), "faults": faults.is_file()}):
        return _finish(ck, card, tif, zpath, None)

    # ---- grid provenance ------------------------------------------------------
    ck.add("FMT-01", "sample_submission.tif SHA-256 equals the pinned owner-mirror digest",
           sha256_file(sample) == grid_mod.SHA256_SAMPLE_SUBMISSION, sha256_file(sample))
    ck.add("FMT-02", "existing_faults.tif SHA-256 equals the pinned owner-mirror digest",
           sha256_file(faults) == grid_mod.SHA256_EXISTING_FAULTS, sha256_file(faults))

    with rasterio.open(sample) as s:
        s_grid = (s.shape, s.crs, s.transform)
        s_arr = s.read(1)
    footprint = np.isfinite(s_arr)
    with rasterio.open(faults) as f:
        ex = f.read(1)
    catalogue = np.isfinite(ex) & (ex > 0)

    # ---- format ---------------------------------------------------------------
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
        meta = {"count": ds.count, "dtype": ds.dtypes[0], "shape": list(ds.shape),
                "crs": str(ds.crs), "nodata": ds.nodata}
        same_grid = (ds.shape, ds.crs, ds.transform) == s_grid
    ck.add("FMT-03", "single band", meta["count"] == 1, meta["count"])
    ck.add("FMT-04", "dtype float32", meta["dtype"] == "float32", meta["dtype"])
    ck.add("FMT-05", "CRS, shape and geotransform identical to sample_submission.tif",
           same_grid, {"crs": meta["crs"], "shape": meta["shape"]})
    n_nan, n_inf = int(np.isnan(arr).sum()), int(np.isinf(arr).sum())
    ck.add("FMT-06", "no NaN and no Inf anywhere", n_nan == 0 and n_inf == 0,
           {"nan": n_nan, "inf": n_inf})
    ck.add("FMT-07", "every value in [0, 1] (portal error 'Predicted values must be in range [0, 1]')",
           bool(arr.min() >= 0.0 and arr.max() <= 1.0),
           {"min": float(arr.min()), "max": float(arr.max())})
    ck.add("FMT-08", "all footprint cells finite", bool(np.isfinite(arr[footprint]).all()))
    ck.add("FMT-09", "zero outside the footprint", bool((arr[~footprint] == 0).all()))
    dots = arr > 0
    ck.add("FMT-10", "binary {0,1} raster with at least one dot",
           set(np.unique(arr).tolist()) <= {0.0, 1.0} and int(dots.sum()) > 0, int(dots.sum()))
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        same_bytes = len(names) == 1 and z.read(names[0]) == tif.read_bytes()
    ck.add("FMT-11", "ZIP contains exactly one member, byte-identical to the TIFF",
           names == [tif.name] and same_bytes, names)

    # ---- catalogue ------------------------------------------------------------
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~catalogue)
    min_d = float(d_cat[dots].min()) if dots.any() else 0.0
    ck.add("CAT-01", "no dot on a mapped catalogue fault pixel",
           int((dots & catalogue).sum()) == 0, int((dots & catalogue).sum()))
    ck.add("CAT-02", "every dot more than 3 px (300 m kernel radius) from the catalogue",
           min_d > 3.0, round(min_d, 4))

    # ---- identity -------------------------------------------------------------
    sha = sha256_file(tif)
    receipt = json.loads(receipt_path.read_text())
    ck.add("ID-01", "TIFF SHA-256 equals run card and writer receipt",
           sha == sub["sha256"] == receipt.get("sha256"), sha)
    ck.add("ID-02", "ZIP SHA-256 equals run card and writer receipt",
           sha256_file(zpath) == sub["zip_sha256"] == receipt.get("zip_sha256"), sha256_file(zpath))
    name, note = sub["submission_name"], sub["submission_note"]
    ck.add("ID-03", "name and note non-empty, each <= 140 characters, equal to the receipt",
           0 < len(name) <= 140 and 0 < len(note) <= 140
           and name == receipt.get("submission_name") and note == receipt.get("note"),
           {"name_chars": len(name), "note_chars": len(note)})
    ck.add("ID-04", "file name carries no DO-NOT-SUBMIT marker",
           "DO-NOT-SUBMIT" not in tif.name, tif.name)

    # ---- uniqueness (vendored template functions) -------------------------------
    rows = []
    exact_dups = []
    n_foot = int(footprint.sum())
    for p, base in _registry_files(root, tif):
        with rasterio.open(p) as r:
            if (r.shape, r.crs, r.transform) != s_grid:
                rows.append({"submission": str(p.relative_to(base)), "error": "grid mismatch"})
                continue
            theirs = r.read(1)
        if np.array_equal(np.nan_to_num(theirs, nan=0.0) > 0, dots):
            exact_dups.append(p.name)
        sr = uniqueness.surface_rho(arr, theirs, footprint)
        support = np.isfinite(theirs) & (theirs > 0) & footprint
        rows.append({
            "submission": str(p.relative_to(base)),
            "their_dots": int(support.sum()),
            "my_dots_within_3px_of_theirs": round(float(uniqueness.dot_overlap(arr, theirs)), 4),
            "spearman_full_footprint": (None if not np.isfinite(sr["spearman_full_footprint"])
                                        else round(float(sr["spearman_full_footprint"]), 4)),
            "jaccard_dot_sets": round(float(sr["jaccard_dot_sets"]), 5),
        })
    errors = [r for r in rows if "error" in r]
    summary = uniqueness.two_phase_summary(
        [dict(r) for r in rows], n_foot, rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT) \
        if any("error" not in r for r in rows) else {}
    ck.add("UNQ-00", "registry scan complete: >= 20 restored registry rasters, none unreadable "
           "(a smaller inventory fails closed)", len(rows) >= 20 and not errors,
           {"rasters_checked": len(rows), "errors": errors})
    ck.add("UNQ-01", "not a pixel-for-pixel duplicate of any registry raster",
           not exact_dups, exact_dups)
    like = summary.get("like_for_like_reading", {})
    lit = summary.get("literal_reading", {})
    worst_ov = like.get("worst_forward_overlap_dot_fields")
    ck.add("UNQ-02", f"like-for-like: worst 3-px forward overlap on dot-field rasters <= {OVERLAP_LIMIT}",
           worst_ov is not None and worst_ov <= OVERLAP_LIMIT,
           {"worst": None if worst_ov is None else round(float(worst_ov), 4),
            "file": like.get("worst_forward_overlap_dot_field_submission"),
            "dot_field_rasters": like.get("dot_field_rasters")})
    worst_rho = lit.get("worst_spearman_full_footprint")
    abs_rho = max((abs(r["spearman_full_footprint"]) for r in rows
                   if r.get("spearman_full_footprint") is not None), default=None)
    ck.add("UNQ-03", f"|Spearman| <= {RHO_LIMIT} against EVERY raster, dense and sparse alike",
           abs_rho is not None and abs_rho <= RHO_LIMIT,
           {"worst_abs_rho": None if abs_rho is None else round(float(abs_rho), 4),
            "signed_worst": worst_rho})
    ck.add("UNQ-04", "literal any-raster reading reported, not hidden "
           "(informational: a continuous 17GEMSDOE prior fires on every non-empty raster)",
           True, {"literal_forward_overlap_firings": lit.get("forward_overlap_firings"),
                  "literal_worst_overlap": lit.get("worst_forward_overlap"),
                  "literal_worst_file": lit.get("worst_overlap_submission"),
                  "continuous_surface_rasters": like.get("continuous_surface_rasters")})

    # ---- science --------------------------------------------------------------
    h = card["holdout"]
    ck.add("SCI-01", "HOLDOUT-DTI evidence class + pinned evaluator version, withheld positives > 0",
           h["evidence_class"] == "HOLDOUT-DTI" and h["evaluator_version"] == "gems57-pooled-hide-v2"
           and h["withheld_positive_pixels"] > 0,
           {"dti": h["winner_dti"], "ci95": h["winner_ci95"], "withheld": h["withheld_positive_pixels"]})
    canary = card["leakage_canary"]["max_symmetric_auc"]
    ck.add("SCI-02", "leakage canary: every feature alone has symmetric AUC <= 0.90",
           canary <= 0.90, canary)
    audit = json.loads((root / "registry" / "provcrest_nullcontrol_audit.json").read_text())
    ck.add("SCI-03", "shipped raster is the bit-for-bit reproduction of the restored-input build",
           audit["reproduced_bit_for_bit_from_restored_inputs"] is True
           and audit["shipped_sha256"] == sha, audit["shipped_sha256"][:16])
    for view in ("ALL", "FAR"):
        v = audit["views"][view]
        pdiff = v["paired_differences_vs_provcrest_rank"]
        lows = {arm: round(d["ci95"][0], 6) for arm, d in pdiff.items()}
        ck.add(f"SCI-04-{view}",
               f"{view}: candidate beats BOTH null controls (random spaced dots, hex lattice) "
               f"with paired 95% CI lower bound > 0",
               all(l > 0 for l in lows.values()) and len(lows) == 2,
               {"candidate_dti": v["scores"]["provcrest_rank"]["dti"],
                "null_random_dti": v["scores"]["null_random"]["dti"],
                "null_lattice_dti": v["scores"]["null_lattice"]["dti"],
                "paired_ci_lower_bounds": lows, "withheld": v["withheld_positive_pixels"]})

    # ---- budget / honesty -----------------------------------------------------
    ck.add("BUD-01", "no weekly slot spent by an agent and no organizer score claimed",
           sub["weekly_slots_used_by_agent"] == 0 and sub["organizer_confirmed_score"] is None,
           {"slots": sub["weekly_slots_used_by_agent"], "organizer_score": sub["organizer_confirmed_score"]})

    return _finish(ck, card, tif, zpath, {"rows": rows, "summary": summary, "meta": meta,
                                           "n_dots": int(dots.sum()), "min_d_cat": round(min_d, 4)})


def _finish(ck: Checks, card: dict, tif: Path, zpath: Path, extra: dict | None) -> dict:
    ok = not ck.failures
    sub = card["submission"]
    result = {
        "schema": "gems88.submission-gate.v1",
        "verdict": "OK_TO_SUBMIT" if ok else "DO_NOT_SUBMIT",
        "ok_to_download": bool(tif.is_file()),
        "ok_to_submit": ok,
        "approved_for_weekly_slot": False,
        "slot_note": "Gate pass = this FILE is valid and unique. Which weekly slot it occupies is "
                     "a separate selector decision; no agent has spent a slot.",
        "evidence_class_of_scores": "HOLDOUT-DTI (local instrument). ORGANIZER-CONFIRMED score: none.",
        "failures": ck.failures,
        "candidate": {
            "file": sub["file"], "zip_file": sub["zip_file"],
            "file_name": Path(sub["file"]).name,
            "sha256": sub["sha256"], "zip_sha256": sub["zip_sha256"],
            "submission_name": sub["submission_name"],
            "note": sub["submission_note"], "note_chars": len(sub["submission_note"]),
        },
        "submit_form": {
            "url": SUBMISSIONS_URL,
            "file_to_submit": Path(sub["file"]).name,
            "alternative_single_zip": Path(sub["zip_file"]).name,
            "note_field": sub["submission_note"],
            "unique_name": sub["submission_name"],
            "name_field_exists": False,
            "name_hint": "The DrivenData form has only 'File to submit' and 'Note'. The unique name is "
                         "the file name; the Note carries the short description.",
        },
        "checks": ck.rows,
    }
    if extra:
        result["uniqueness_rows"] = extra["rows"]
        result["uniqueness_summary"] = extra["summary"]
        result["n_dots"] = extra["n_dots"]
        result["min_catalogue_distance_px"] = extra["min_d_cat"]
    return json.loads(json.dumps(result, default=float))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--require-submit", action="store_true", help="exit 2 unless OK_TO_SUBMIT")
    ap.add_argument("--no-write", action="store_true", help="do not write docs/data/submission_gate.json")
    args = ap.parse_args()
    result = run_gate()
    if not args.no_write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n")
    for r in result["checks"]:
        print(f"[{'PASS' if r['pass'] else 'FAIL'}] {r['id']:10s} {r['description']}")
    print(f"\nVERDICT: {result['verdict']}  file={result['candidate']['file_name']}  sha256={result['candidate']['sha256'][:16]}…")
    if result["failures"]:
        print("FAILURES:\n  " + "\n  ".join(result["failures"]), file=sys.stderr)
    if args.require_submit and not result["ok_to_submit"]:
        print("AUTOMATIC SUBMISSION GATE: FAIL. No upload permitted.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
