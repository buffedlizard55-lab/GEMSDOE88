"""Fail-closed legacy schema gate and latest research-candidate status.

`assess` remains for synthetic eligibility fixtures. The live status feed follows
MDPS-88, the newest research candidate, and cross-checks its run card, strict
literal-overlap gate, independent TIFF/ZIP audit, and local holdout evidence.
The separate ``current_release.json`` may retain an older canonical artifact;
this script never chooses or spends a weekly submission slot.
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
    """Represent the newest candidate; a format PASS is not slot approval."""
    card = json.loads((root / 'registry/mdps88_run_card.json').read_text())
    gate = json.loads((root / 'docs/data/mdps88-gate.json').read_text())
    audit = json.loads((root / 'docs/data/mdps88_validation.json').read_text())
    rel = card['raster']['file']
    artifact = (root / rel).resolve()
    if not artifact.is_relative_to((root / 'docs/downloads').resolve()):
        raise ValueError('latest research artifact escapes docs/downloads')
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if not (artifact.is_file() and digest == card['raster_sha256'] == gate['sha256'] == audit['sha256']):
        raise ValueError('latest research artifact hash differs across card, gate, or audit')
    literal = card['correlation_overlap_vs_registry']['literal_binding_decision']
    if not (literal['duplicate'] is True and literal['stop_required'] is True
            and literal['forward_overlap_3px'] > literal['limit']
            and audit['checks']['literal_forward_overlap_3px_vs_dense_witness'] > literal['limit']):
        raise ValueError('latest candidate strict literal-overlap decision is inconsistent')
    if audit.get('audit_passed') is not True or gate.get('ok_to_download') is not True:
        raise ValueError('latest candidate saved-byte research audit did not pass')

    holdout = card['holdout']
    problems = []
    if not holdout['far']['paired_vs_base283']['ci95'][0] > 0:
        problems.append('HOLDOUT: far paired 95% CI does not clear zero versus fold-fair control')
    if literal['duplicate']:
        problems.append(f"UNIQUENESS: literal 3-px overlap {literal['forward_overlap_3px']:.4f} exceeds {literal['limit']:.2f}; DUPLICATE, stop")
    # The project feed remains fail-closed even if the research download itself is valid.
    return {
        'evidence_schema_complete': True,
        'approved_for_weekly_slot': False,
        'status': 'BLOCKED' if problems else 'SELECTOR_REQUIRED',
        'problems': problems,
        'ok_to_download_for_research': True,
        'ok_to_submit': False,
        'raster_sha256': digest,
        'policy': 'literal-all-registry-v1; chance-corrected diagnostics do not waive overlap',
        'run_card': 'registry/mdps88_run_card.json',
        'supersedes_status_of': 'PHASE-88 remains the separate docs/data/current_release.json record',
    }


if __name__ == '__main__':
    verify_template()
    report = current_status()
    (ROOT / 'docs/status.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
