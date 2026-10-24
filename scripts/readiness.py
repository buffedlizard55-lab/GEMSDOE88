"""Fail-closed legacy schema gate and current canonical release status.

`assess` remains for the synthetic eligibility fixtures inherited from main.
The live CLI status is derived from the independent TIFF/ZIP/witness validator,
not the pre-experiment card that previously claimed no TIFF existed.
Does not choose or spend weekly submission slots.
"""
from __future__ import annotations
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def current_status(root=ROOT, report=None):
    """Recompute the CURRENT TIFF's full on-disk format and literal registry gate."""
    if report is None:
        from scripts.validate_current import release_report
        report = release_report(root)
    problems = []
    if report['duplicate']:
        problems.append('Literal registry overlap with hash-pinned full-footprint witness: DO NOT SUBMIT')
    if report['holdout_dti'] < report['incumbent_best_dti']:
        problems.append('New HOLDOUT-DTI did not beat the current holdout best')
    if not report['format_valid']:
        problems.append('Current TIFF failed on-disk validation')
    return {
        'evidence_schema_complete': True,
        'approved_for_weekly_slot': False,
        'status': 'BLOCKED' if problems else 'SELECTOR_REQUIRED',
        'problems': problems,
        'current_file': report['file'],
        'registry_rasters_checked': report['registry_rasters_checked'],
        'original_preplacement_rasters_checked': report['original_preplacement_rasters_checked'],
        'posthoc_rasters_checked': report['posthoc_rasters_checked'],
        'ok_to_download_for_research': report['research_download_ok'],
        'ok_to_submit': False,
        'raster_sha256': report['file_sha256'],
    }


def unified_status(root=ROOT):
    """Authoritative site/CI status: the single submission gate for the promoted file.

    The newest research-only artifact (validate_current.py; a DO-NOT-SUBMIT file) keeps its own
    blocked verdict under ``latest_research_artifact`` so the two can never be confused.
    """
    from submission_gate import run_gate

    gate = run_gate(root)
    return {
        'verdict': gate['verdict'],
        'ok_to_download': gate['ok_to_download'],
        'ok_to_submit': gate['ok_to_submit'],
        'approved_for_weekly_slot': False,
        'raster_sha256': gate['candidate']['sha256'],
        'file': gate['candidate']['file'],
        'submission_name': gate['candidate']['submission_name'],
        'note': gate['candidate']['note'],
        'failures': gate['failures'],
        'gate_report': 'data/submission_gate.json',
        'latest_research_artifact': current_status(root),
    }


if __name__ == '__main__':
    verify_template()
    from scripts.validate_current import release_report
    audit = release_report()
    (ROOT / 'docs/data/current_release.json').write_text(json.dumps(audit, indent=2) + '\n')
    report = unified_status()
    (ROOT / 'docs/status.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
