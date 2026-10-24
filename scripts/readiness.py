"""Fail-closed legacy schema gate and latest-experiment site status.

`assess` remains for synthetic eligibility fixtures inherited from main.
The live status follows the landing page's latest MDPS-88 artifact and binds
its run card, gate, audit, and on-disk TIFF hash. The legacy PHASE-88
``current_release.json`` record is not used as the latest-experiment pointer.
This module does not choose or spend weekly submission slots.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def assess(card, root=ROOT):
    problems = []
    def require(condition, message):
        if not condition:
            problems.append(message)
    require(bool(card.get('lane')), 'No assigned method lane')
    require(card.get('feature_cache_verified') is True, 'Cached feature stack not verified')
    h = card.get('holdout') or {}
    require(h.get('evidence_class') == 'HOLDOUT-DTI', 'Missing HOLDOUT-DTI evidence')
    require(h.get('evaluator_version') == 'gems57-pooled-hide-v2', 'Unrecognized evaluator version')
    require(finite(h.get('withheld_positives')) and h.get('withheld_positives', 0) > 0,
            'No withheld positives')
    ci = h.get('ci95')
    ci_ok = isinstance(ci, list) and len(ci) == 2 and all(finite(x) for x in ci)
    require(ci_ok and 0 <= ci[0] <= ci[1] <= 1, 'Missing/invalid HOLDOUT-DTI confidence interval')
    score = h.get('dti')
    require(finite(score) and ci_ok and ci[0] <= score <= ci[1], 'Missing/invalid HOLDOUT-DTI estimate')
    delta = h.get('paired_delta_ci95')
    require(isinstance(delta, list) and len(delta) == 2 and all(finite(x) for x in delta)
            and 0 < delta[0] <= delta[1], 'No paired improvement over current holdout best')
    require(bool(h.get('baseline_sha256')), 'Unidentified holdout incumbent')
    for flag in ('whole_segments', 'buffered', 'visible_only_features', 'pixel_exact_mask'):
        require(h.get(flag) is True, f'Holdout protocol not verified: {flag}')
    canaries = card.get('canaries') or []
    require(bool(canaries), 'Feature-alone leakage canaries missing')
    require(set(card.get('feature_names') or []) == {c.get('feature') for c in canaries}
            and bool(card.get('feature_names')), 'Canaries do not cover all features')
    for c in canaries:
        require(finite(c.get('auc')) and 0 <= c['auc'] <= 0.90,
                f'Leakage canary blocked: {c.get("feature")}')
    u = card.get('uniqueness') or {}
    require(u.get('registry_complete') is True, 'Registry inventory incomplete')
    for stage in ('surface', 'dots'):
        checks = u.get(stage) or []
        require(bool(checks), f'No {stage} registry comparisons')
        require({c.get('sha256') for c in checks} == set(u.get('registry_sha256') or [])
                and bool(u.get('registry_sha256')), f'Incomplete {stage} comparisons')
        for c in checks:
            require(finite(c.get('rho')) and abs(c['rho']) <= .90,
                    f'{stage} rank-correlation duplicate or invalid')
            require(finite(c.get('overlap_3px')) and 0 <= c['overlap_3px'] <= .70,
                    f'{stage} dot-overlap duplicate or invalid')
    v = card.get('validator') or {}
    for flag in ('no_nan_inside', 'range_0_1', 'crs_match', 'shape_match', 'transform_match'):
        require(v.get(flag) is True, f'Validator missing/failed: {flag}')
    name, note = card.get('submission_name'), card.get('note')
    require(isinstance(name, str) and 0 < len(name) <= 140, 'Missing/invalid unique name')
    require(isinstance(note, str) and 0 < len(note) <= 140, 'Missing/invalid note')
    artifact = card.get('artifact')
    safe = False
    if isinstance(artifact, str):
        path = (root / artifact).resolve()
        safe = path.is_relative_to((root / 'docs/downloads').resolve()) and path.suffix == '.tif'
        require(safe, 'Artifact must reside in docs/downloads and end in .tif')
        if safe:
            require(path.is_file(), 'Submission TIFF missing')
            if path.is_file():
                require(hashlib.sha256(path.read_bytes()).hexdigest() == card.get('raster_sha256'),
                        'Raster hash mismatch')
    else:
        problems.append('No generated TIFF')
    require(v.get('raster_sha256') == card.get('raster_sha256') and bool(card.get('raster_sha256')),
            'Validator not bound to raster hash')
    require(finite(card.get('experiment_count')) and 0 <= card['experiment_count'] <= 3
            and int(card['experiment_count']) == card['experiment_count'], 'Experiment budget missing/invalid or exceeded')
    require(finite(card.get('elapsed_seconds')) and 0 <= card['elapsed_seconds'] <= 7200,
            'Elapsed-time budget missing/invalid or exceeded')
    return {'evidence_schema_complete': not problems, 'approved_for_weekly_slot': False,
            'status': 'SELECTOR_REQUIRED' if not problems else 'BLOCKED', 'problems': problems}


def verify_template(root=ROOT):
    pin = json.loads((root / 'registry/template_pin.json').read_text())
    for name, digest in pin['files'].items():
        if hashlib.sha256((root / 'vendor/gems57' / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Shared template modified: {name}')


def current_status(root=ROOT):
    """Report the landing page's latest experiment, never a compatibility archive."""
    card = json.loads((root / 'registry/mdps88_run_card.json').read_text())
    gate = json.loads((root / 'docs/data/mdps88-gate.json').read_text())
    audit = json.loads((root / 'docs/data/mdps88_validation.json').read_text())
    artifact = root / card['raster']['file']
    problems = []
    exists = artifact.is_file()
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest() if exists else None
    card_digest = card['raster']['sha256']
    integrity_ok = (exists and digest == card_digest == gate.get('sha256')
                    == audit.get('sha256') and audit.get('audit_passed') is True)
    if not integrity_ok:
        problems.append('FORMAT: current artifact or independent byte-audit hash is missing/mismatched')
    checks = audit.get('checks', {})
    format_flags = ('single_band_float32', 'grid_matches_sample', 'nodata_is_none',
                    'all_finite', 'range_0_1', 'zero_dots_on_catalogue',
                    'zero_dots_outside_footprint', 'zip_one_member',
                    'zip_member_bytes_identical', 'zip_sha_matches_card')
    format_ok = integrity_ok and all(checks.get(flag) is True for flag in format_flags)
    if gate.get('ok_to_download') is not True or audit.get('ok_to_download') is not True or not format_ok:
        problems.append('FORMAT: research-download validation is not passing')
    holdout = card.get('holdout', {})
    far = holdout.get('far', {})
    paired = far.get('paired_vs_base283', {})
    far_ci = far.get('ci95')
    holdout_ok = (holdout.get('evidence_class') == 'HOLDOUT-DTI'
                  and holdout.get('evaluator_version') == 'gems57-pooled-hide-v2'
                  and finite(far.get('dti')) and isinstance(far_ci, list) and len(far_ci) == 2
                  and all(finite(x) for x in far_ci) and 0 <= far_ci[0] <= far['dti'] <= far_ci[1] <= 1
                  and finite(far.get('withheld_positive_pixels')) and far['withheld_positive_pixels'] > 0)
    if not holdout_ok:
        problems.append('HOLDOUT: latest card lacks a valid labelled far holdout result and confidence interval')
    stored_best = holdout.get('stored_reference_unpaired', {}).get('dti')
    if not finite(stored_best) or far.get('dti', 0) <= stored_best:
        problems.append('HOLDOUT: far candidate does not exceed stored holdout best')
    ci = paired.get('ci95')
    paired_ci_valid = (isinstance(ci, list) and len(ci) == 2 and all(finite(x) for x in ci)
                       and ci[0] <= ci[1])
    paired_ok = paired_ci_valid and ci[0] > 0
    if not paired_ok:
        problems.append('HOLDOUT: paired improvement over the fold-fair control is not established')
    uniqueness = card.get('correlation_overlap_vs_registry', {})
    rho = uniqueness.get('surface_preplacement_worst_abs_spearman')
    overlap = uniqueness.get('worst_literal_forward_overlap_3px')
    # Binding user rule is literal: do not replace a positive-everywhere prior
    # with a top-k/like-for-like reinterpretation. Keep that diagnostic separate.
    if not finite(rho) or abs(rho) > .90:
        problems.append('UNIQUENESS: pre-placement surface rank-correlation exceeds 0.90 or is missing')
    if not finite(overlap) or overlap > .70:
        problems.append('UNIQUENESS: literal final-dot overlap exceeds 0.70 or is missing')
    return {
        'latest_experiment': card.get('run_id'),
        'evidence_schema_complete': bool(format_ok and holdout_ok and paired_ci_valid and finite(rho) and finite(overlap)),
        'approved_for_weekly_slot': False,
        'status': 'BLOCKED' if problems else 'SELECTOR_REQUIRED',
        'problems': problems,
        'ok_to_download_for_research': bool(format_ok and gate.get('ok_to_download') is True),
        'ok_to_submit': False,  # no candidate has selector authorization
        'raster_sha256': digest,
        'evidence_class': holdout.get('evidence_class'),
        'holdout_evaluator': holdout.get('evaluator_version'),
        'holdout_far_dti': far.get('dti'),
        'holdout_far_ci95': far.get('ci95'),
        'withheld_far_positive_pixels': far.get('withheld_positive_pixels'),
        'literal_registry_overlap_3px': uniqueness.get('worst_literal_forward_overlap_3px'),
        'policy': 'literal-user-lane-rule-v1',
    }


if __name__ == '__main__':
    verify_template()
    report = current_status()
    (ROOT / 'docs/status.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
