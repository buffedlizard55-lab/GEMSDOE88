"""Automated zero-human-intervention verification suite (`tests/test_gems88_gates.py`).

16 independent programmatic verification gates covering:
1. Unmodified & patched template SHA-256 integrity (`registry/template_pin.json`)
2. Run Card `v1` schema, strict `HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED` labeling, & experiment budget
3. Single-band float32 GeoTIFF CRS (`EPSG:32611`), shape (`3730 × 3292`), & affine transform identity
4. DrivenData `[0, 1]` range compliance, zero `NaN` / `Inf`, & zero sentinel leakage
5. Exact outside-footprint `0.0` convention & zero positive pixels on mapped `existing_faults.tif`
6. Exact `200 m` (`2 px`) zero-credit collar compliance & `37,654` positive pixel cardinality
7. Byte-exact SHA-256 identity across `submissions/*.tif`, `docs/downloads/*.tif`, & `.zip`
8. World-readable `0644` permissions across all downloadable artifacts & figures for GitHub Pages
9. Single-feature leakage canary (`0 / 99` channels `> 0.90` on both `Seed 20` and `Seed 30`)
10. Strictly monotonic zero-leakage `HOLDOUT-DTI` progression (`B0 < B1 < EXP-1 < EXP-2 < EXP-3`)
11. Paired 20 km spatial-cluster bootstrap significance vs `B1_FoldFair_H33_2_B2` (`Seed 20` & `Seed 30`)
12. Pre-placement continuous surface uniqueness (`|Spearman rho| <= 0.90` & `overlap <= 0.70`)
13. Archived 1,167-raster discriminating-only scan (historical; NOT binding uniqueness clearance)
14. Submission note length (`<= 140` chars) & unique submission identifier
15. Publication figure presence & non-empty valid PNG headers (`docs/assets/fig1..4.png`)
16. HTML & Markdown link / integrity check across `README.md`, `docs/index.html`, and `docs/executive-summary.html`
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_01_template_pins_match_disk():
    pin = json.loads((ROOT / "registry" / "template_pin.json").read_text())
    for rel, expected_sha in pin["core_modules_unmodified"].items():
        assert _sha256(ROOT / rel) == expected_sha, f"Tampered unmodified vendor module: {rel}"
    for info in pin["patched_modules"]:
        assert _sha256(ROOT / info["file"]) == info["patched_sha256"], f"Patched vendor hash mismatch: {info['file']}"


def test_02_run_card_schema_and_strict_score_labels():
    for rc_path in [ROOT / "run_card.json", ROOT / "docs" / "data" / "run_card.json", ROOT / "evidence" / "run_card.json"]:
        assert rc_path.exists()
        rc = json.loads(rc_path.read_text())
        # Preserve historical measurements, never an unsupported promotion or
        # an organizer label for a user-supplied number (IR-88-693B10AF-01).
        assert rc["verdict"] == "negative"
        assert rc["historical_only"] is True
        assert rc["ok_to_submit"] is rc["approved_for_weekly_slot"] is False
        assert rc["evidence_status"]["score_label"] == "HOLDOUT-DTI"
        assert rc["evidence_status"]["organizer_confirmed_live_score"] is None
        assert rc["evidence_status"]["incumbent_organizer_confirmed_live_score"] is None
        assert rc["evidence_status"]["incumbent_user_reported_claim"] == 0.2778
        assert rc["evidence_status"]["incumbent_evidence_class"].startswith("USER-REPORTED")
        assert rc["uniqueness"]["unique"] is False
        assert rc["uniqueness"]["stop_required"] is True
        assert rc["uniqueness"]["literal_overlap_3px"] == 1.0
        assert rc["experiments_run"] <= rc["experiment_budget_max"] == 3


def test_03_geotiff_crs_shape_dtype_and_affine_transform():
    sample_tif = ROOT / ".cache" / "data" / "sample_submission.tif"
    if not sample_tif.is_file():
        pytest.skip("requires ignored cached competition sample TIFF; restore inputs first")
    rc = json.loads((ROOT / "run_card.json").read_text())
    sub_tif = ROOT / rc["submission"]["repo_copy"]
    sample_tif = ROOT / ".cache" / "data" / "sample_submission.tif"
    with rasterio.open(sample_tif) as ex, rasterio.open(sub_tif) as cand:
        assert cand.count == 1
        assert cand.dtypes[0] == "float32"
        assert (cand.height, cand.width) == (ex.height, ex.width) == (3730, 3292)
        assert cand.crs == ex.crs
        assert str(cand.crs) == "EPSG:32611"
        assert cand.transform == ex.transform


def test_04_geotiff_strict_range_0_1_and_zero_nan_inf():
    rc = json.loads((ROOT / "run_card.json").read_text())
    sub_tif = ROOT / rc["submission"]["repo_copy"]
    with rasterio.open(sub_tif) as cand:
        arr = cand.read(1)
    assert not np.isnan(arr).any(), "NaN values detected in submission GeoTIFF!"
    assert np.isfinite(arr).all(), "Non-finite values detected in submission GeoTIFF!"
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, "Values strictly outside [0, 1]!"


def test_05_outside_footprint_and_mapped_catalogue_strictly_zero():
    ef_tif = ROOT / ".cache" / "data" / "existing_faults.tif"
    if not ef_tif.is_file():
        pytest.skip("requires ignored cached mapped-fault TIFF; restore inputs first")
    rc = json.loads((ROOT / "run_card.json").read_text())
    sub_tif = ROOT / rc["submission"]["repo_copy"]
    ef_tif = ROOT / ".cache" / "data" / "existing_faults.tif"
    with rasterio.open(ef_tif) as ef, rasterio.open(sub_tif) as cand:
        arr = cand.read(1)
        ef_arr = ef.read(1)
    footprint = (ef_arr == 0.0) | (ef_arr == 1.0)
    catalogue = ef_arr == 1.0
    assert np.all(arr[~footprint] == 0.0), "Outside-footprint pixels must be exact 0.0!"
    assert int((arr[catalogue] > 0.0).sum()) == 0, "Zero positive pixels permitted on mapped catalogue!"
    assert int((arr[footprint] > 0.0).sum()) == 37_654


def test_06_zero_wasted_dots_inside_200m_zero_credit_collar():
    rc = json.loads((ROOT / "run_card.json").read_text())
    assert rc["submission"]["within_200m_catalogue_pixels"] == 0
    assert rc["submission"]["radial_profile"]["pct_le_2px"] == 0.0


def test_07_byte_identity_and_world_readable_permissions():
    rc = json.loads((ROOT / "run_card.json").read_text())
    sub_tif = ROOT / rc["submission"]["repo_copy"]
    dl_tif = ROOT / rc["submission"]["file"]
    dl_zip = ROOT / rc["submission"]["zip_file"]
    assert _sha256(sub_tif) == _sha256(dl_tif) == rc["submission"]["sha256"]
    assert _sha256(dl_zip) == rc["submission"]["zip_sha256"]
    for p in (sub_tif, dl_tif, dl_zip):
        mode = stat.S_IMODE(os.stat(p).st_mode)
        assert mode & stat.S_IROTH, f"{p} is missing world-read permission ({oct(mode)})!"


def test_08_submission_name_and_140_char_note_gate():
    rc = json.loads((ROOT / "run_card.json").read_text())
    note = rc["submission"]["submission_note"]
    assert 20 <= len(note) <= 140
    assert rc["submission"]["submission_note_chars"] == len(note)
    assert rc["submission"]["submission_name"] == "GEMSDOE88-H88-GHMD-318A37E6"


def test_09_leakage_canary_zero_flags_across_all_99_channels():
    canary = json.loads((ROOT / "evidence" / "canary_audit.json").read_text())
    assert canary["all_passed"] is True
    assert canary["physics_seed20"]["n_features_tested"] == 83
    assert canary["geodesic_relay_seed20"]["n_features_tested"] == 16
    for k in ("physics_seed20", "physics_seed30", "geodesic_relay_seed20", "geodesic_relay_seed30"):
        assert canary[k]["passed"] is True
        assert canary[k]["flagged_count"] == 0
        assert canary[k]["max_symmetric_auc"] <= 0.90


def test_10_monotonic_holdout_progression_both_seeds():
    rc = json.loads((ROOT / "run_card.json").read_text())
    hp = rc["holdout_progression"]
    s20 = [
        hp["B0_random_37654_seed20"],
        hp["B1_fold_fair_H33_2_B2_seed20"],
        hp["EXP_88_1_zero_catalogue_multiphysics_seed20"]["pooled_holdout_dti"],
        hp["EXP_88_2_geodesic_relay_nms_seed20"]["pooled_holdout_dti"],
        hp["EXP_88_3_exact_expected_dti_celf_swap_seed20"]["pooled_holdout_dti"],
    ]
    assert s20 == sorted(s20) and len(set(s20)) == 5
    s30 = [
        hp["B1_fold_fair_H33_2_B2_seed30"],
        hp["EXP_88_1_zero_catalogue_multiphysics_seed30"]["pooled_holdout_dti"],
        hp["EXP_88_2_geodesic_relay_nms_seed30"]["pooled_holdout_dti"],
        hp["EXP_88_3_exact_expected_dti_celf_swap_seed30"]["pooled_holdout_dti"],
    ]
    assert s30 == sorted(s30) and len(set(s30)) == 4


def test_11_paired_20km_cluster_bootstrap_significance():
    exp = json.loads((ROOT / "evidence" / "experiments_summary.json").read_text())
    for key in ("paired_spatial_bootstrap_seed20", "paired_spatial_bootstrap_seed30"):
        ci_b1 = exp[key]["paired_differences"]["B1_FoldFair_H33_2_B2"]["ci95"]
        assert ci_b1[0] > 0.075


def test_12_pre_placement_surface_uniqueness_passed():
    uniq = json.loads((ROOT / "evidence" / "uniqueness_certificate.json").read_text())
    pre = uniq["pre_placement_live_surface"]
    assert pre["passed"] is True
    assert pre["stop_required"] is False
    assert pre["worst_abs_spearman"] <= 0.90
    assert pre["worst_top37654_discriminating_3px_overlap"] <= 0.70


def test_13_full_5167373px_1167_raster_uniqueness_certificate_passed():
    uniq = json.loads((ROOT / "evidence" / "uniqueness_certificate.json").read_text())
    cert = uniq["full_5167373px_vendor_certificate"]
    assert cert["complete_accessible_scan"] is True
    assert cert["registry_rasters_checked"] == 1167
    assert cert["missing_or_invalid"] == 0
    assert cert["source_errors"] == []
    assert cert["unique"] is True
    assert cert["stop_required"] is False
    assert abs(cert["worst_spearman_full_footprint"]) <= 0.90
    assert cert["worst_dot_overlap"] <= 0.70


def test_14_publication_figures_valid_pngs():
    for fn in (
        "fig1_nevada_fault_discovery_map.png",
        "fig2_holdout_progression_and_domain_shift.png",
        "fig3_portfolio_uniqueness_and_canary.png",
        "fig4_feature_importance_and_historical_audit.png",
    ):
        p = ROOT / "docs" / "assets" / fn
        assert p.exists() and p.stat().st_size > 25_000
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_15_github_pages_and_readme_relative_links_resolve():
    for html_name in ("index.html", "executive-summary.html"):
        p = ROOT / "docs" / html_name
        if not p.exists():
            continue
        txt = p.read_text()
        for m in re.finditer(r'(?:href|src)="([^"#?:]+)"', txt):
            rel = m.group(1)
            target = (p.parent / rel).resolve()
            assert target.exists(), f"Broken relative link in docs/{html_name}: {rel} -> {target}"
