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
# Direct CLI execution sets sys.path[0] to scripts/, not the repository root.
# Keep package-qualified imports working both from Python and as a script.
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
    names = card.get('feature_names') or []
    require(set(names) == {c.get('feature') for c in canaries}
            and bool(names) and len(names) == len(set(names)) == len(canaries),
            'Canaries must cover each feature exactly once')
    for c in canaries:
        require(finite(c.get('auc')) and 0 <= c['auc'] <= 1
                and max(c['auc'], 1 - c['auc']) <= 0.90,
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
    """Represent the canonical lane (H88-SDTL v2 run card). Every flag is derived
    from the card plus a fresh byte check; nothing here is hand-set (IR-88-SDTL-01)."""
    import hashlib

    card = json.loads((root / 'registry/sdtl88_run_card.json').read_text())
    if card.get('schema') != 'gems88.run_card.v2' or card.get('lane') != 'H88-SDTL':
        raise ValueError('canonical run card is not a gems88.run_card.v2 H88-SDTL card')
    tif = root / card['raster']['file']
    with tif.open('rb') as stream:
        on_disk = hashlib.file_digest(stream, 'sha256').hexdigest()
    if on_disk != card['raster']['sha256']:
        raise ValueError('canonical TIFF bytes differ from run card')
    h = card['holdout_dti']
    u = card['correlation_overlap_vs_registry']
    problems = []
    if not h['success']:
        problems.append('HOLDOUT: preregistered rule (delta>0, CI low>0, >=5/8 folds) not met')
    if not card['leakage_canary']['passed']:
        problems.append('CANARY: single-feature symmetric AUC exceeds 0.90')
    if not (u['surface_ok'] and u['dots_ok']):
        problems.append('UNIQUENESS: v5 equal-support overlap or rank correlation exceeds the limit')
    if not card['validator']['ok']:
        problems.append('FORMAT: saved-byte validation failed')
    promote = card['verdict'] == 'promote' and card['ok_to_submit'] is True
    if promote and problems:
        raise ValueError('run card says promote but a gate fails: ' + '; '.join(problems))
    if (not promote) and not problems:
        problems.append('VERDICT: run card is negative')
    return {
        'evidence_schema_complete': bool(card['validator']['ok']),
        'approved_for_weekly_slot': False,
        'status': 'OK_TO_SUBMIT' if promote else 'BLOCKED',
        'problems': problems,
        'ok_to_download_for_research': True,
        'ok_to_submit': promote,
        'raster_sha256': card['raster']['sha256'],
        'policy': 'IR-88-SDTL-01: holdout rule + canary + uniqueness v5 (equal-support) + shared validator',
        'run_card': 'registry/sdtl88_run_card.json',
        'current_review': 'data/sdtl88_run_card.json',
        'current_review_status': card['verdict'],
        'new_tif_generated': True,
        'new_tif_sha256': card['raster']['sha256'],
        'current_review_note': (
            ('Verdict promote: all four automated gates pass; OK to download and submit. ' if promote else
             'Verdict negative: a gate failed; research download only. ')
            + 'Weekly slot choice remains the owner\'s; no slot is picked here.'
        ),
    }


def main():
    """Rewrite public status on every path; never leave stale success behind."""
    try:
        verify_template()
        report = current_status()
    except (OSError, ValueError, KeyError) as exc:
        report = {
            'evidence_schema_complete': False,
            'approved_for_weekly_slot': False,
            'status': 'BLOCKED',
            'problems': [f'AUDIT_ERROR: {exc}'],
            'ok_to_download_for_research': False,
            'ok_to_submit': False,
            'policy': 'IR-88-SDTL-01: holdout rule + canary + uniqueness v5 (equal-support) + shared validator',
        }
    (ROOT / 'docs/status.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['evidence_schema_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
