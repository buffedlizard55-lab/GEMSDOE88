#!/usr/bin/env python3
"""Bind executive-table research metrics to the exact archived files and arms.

This is a read-only audit. Cross-validation is evidence about a method on mapped
faults, not a measurement of a fixed production TIFF or a leaderboard forecast.
It never changes a verdict, produces predictions, or accesses the portal.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = "gems57-pooled-hide-v2"

# A single explicit mapping makes experiment/arm substitutions reviewable.
# Each tuple is: run-card, raster field, holdout evidence, arm name, overall
# path in card, blind path in card. QTS has no separate holdout evidence file.
SOURCES = {
    "TDKL": ("registry/tdkl88_run_card.json", ("raster", "file"),
             "evidence/tdkl88_holdout_20261024.json", "h88_tdkl",
             ("holdout_dti", "experiments", "Exp03_h88_tdkl_primary", "overall"),
             ("holdout_dti", "experiments", "Exp03_h88_tdkl_primary", "blind_gt25px")),
    "BPWD": ("registry/bpwd88_run_card.json", ("download",),
             "evidence/bpwd88_holdout_20261025.json", "exp03_psgv_tri_poe",
             ("holdout_dti", "candidate_exp03"), ("holdout_dti", "blind_gt25px")),
    "HGVC": ("registry/hgvc88_run_card.json", ("download",),
             "evidence/hgvc88_holdout_20261024.json", "exp03_hgvc_poe_conduit",
             ("holdout_dti", "candidate_exp03"), ("holdout_dti", "blind_gt25px")),
    "QTS": ("registry/qts88_run_card.json", ("file",), None, None,
            ("holdout", "experiments", "exp3_qts_hybrid_debiased"), None),
}


def get_path(data: dict, keys: tuple[str, ...]):
    for key in keys:
        data = data[key]
    return data


def checked_metric(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("missing holdout metric")
    keys = ("evidence_class", "evaluator_version", "withheld_positive_pixels", "dti", "ci95")
    result = {key: value[key] for key in keys}
    n, score, ci = result["withheld_positive_pixels"], result["dti"], result["ci95"]
    def numeric(x):
        return type(x) in (int, float) and math.isfinite(x)
    if (result["evidence_class"] != "HOLDOUT-DTI" or result["evaluator_version"] != VERSION
            or type(n) is not int or n <= 0 or not numeric(score) or not 0 <= score <= 1
            or not isinstance(ci, list) or len(ci) != 2 or not all(numeric(x) for x in ci)
            or not 0 <= ci[0] <= ci[1] <= 1):
        raise ValueError("invalid holdout evidence class, evaluator, sample size, score or CI")
    return result


def safe_archived_file(root: Path, relative: object, sha256: object) -> Path:
    if not isinstance(relative, str) or not isinstance(sha256, str):
        raise ValueError("missing raster path or digest")
    path = Path(relative)
    if path.parent != Path("docs/downloads") or "DO-NOT-SUBMIT" not in path.name:
        raise ValueError("executive-table raster must be a labeled research download")
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise ValueError("invalid raster digest")
    target = (root / path).resolve()
    if not target.is_relative_to((root / "docs/downloads").resolve()) or not target.is_file():
        raise ValueError("missing or escaped research raster")
    with target.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != sha256:
        raise ValueError("research raster does not match its run card")
    return target


def inspect(root: Path = ROOT) -> dict:
    root = Path(root)
    results = {}
    for lane, (card_rel, raster_keys, evidence_rel, arm, overall_keys, blind_keys) in SOURCES.items():
        card_path = root / card_rel
        card_bytes = card_path.read_bytes()
        web_card = root / "docs/data" / card_path.name
        if card_bytes != web_card.read_bytes():
            raise ValueError(f"{lane}: run-card mirror mismatch")
        card = json.loads(card_bytes)
        if card.get("verdict") != "negative" or card.get("ok_to_submit") is not False:
            raise ValueError(f"{lane}: research card cannot authorize a submission")
        raster = get_path(card, raster_keys)
        digest = card["raster_sha256"]
        safe_archived_file(root, raster, digest)
        overall = checked_metric(get_path(card, overall_keys))
        blind = checked_metric(get_path(card, blind_keys)) if blind_keys else None
        if evidence_rel:
            evidence_path = root / evidence_rel
            evidence_bytes = evidence_path.read_bytes()
            if evidence_bytes != (root / "docs/evidence" / evidence_path.name).read_bytes():
                raise ValueError(f"{lane}: published holdout evidence mismatch")
            evidence = json.loads(evidence_bytes)
            if not card.get("preregistration_id") or card["preregistration_id"] != evidence.get("preregistration_id"):
                raise ValueError(f"{lane}: preregistration linkage mismatch")
            for section, result in (("pooled_overall", overall), ("pooled_blind_gt25px", blind)):
                if checked_metric(evidence[section]["scores"][arm]) != result:
                    raise ValueError(f"{lane}: {section} arm does not match the card")
        results[lane] = {
            "research_tiff": raster,
            "raster_sha256": digest,
            "run_card": card_rel,
            "holdout_evidence": evidence_rel,
            "overall": overall,
            "blind_gt25px": blind,
            "experiment": arm if arm is not None else "exp3_qts_hybrid_debiased",
            "ok_to_submit": False,
        }
    return results


def main() -> int:
    try:
        report = inspect()
        print(json.dumps({"status": "PASS", "metrics": report, "ok_to_submit": False}, indent=2, allow_nan=False))
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc), "ok_to_submit": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
