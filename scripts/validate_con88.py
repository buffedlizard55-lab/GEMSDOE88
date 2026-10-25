#!/usr/bin/env python3
"""Read-only saved-byte CON88 research audit; NEVER refits or grants clearance.

The old equal-support/format-only approval path is withdrawn. Reuse the shared
literal preflight and format validator; do not load feature caches or re-score
fixed full-catalogue-masked predictions as hide-and-recover evidence.
Exit 0 = research checks pass, 1 = audit error, 2 = --require-submit denied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.generation_guard import inspect as preflight
from scripts.validate_artifact import validate_artifact

FILE = 'docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif'
SHA256 = 'e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68'


def _load_canary_surface(path: Path):
    """Legacy read-only diagnostic helper, never used by the approval path.

    Retained for compatibility with the parallel missing-input regression test.
    The current validator does not require or evaluate these historical caches.
    """
    if not path.is_file():
        print(json.dumps({'decision': 'AUDIT_ERROR',
                          'missing_prerequisite': str(path),
                          'ok_to_submit': False}), file=sys.stderr)
        raise SystemExit(1)
    import numpy as np
    return np.load(path, allow_pickle=False)


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-submit', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = Path(root)
        proof = preflight(root)
        candidate = root / FILE
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != SHA256:
            raise ValueError('CON88 archived TIFF SHA-256 mismatch')
        checks = validate_artifact(candidate, root / 'data/bridge/sample_submission.tif')
        with zipfile.ZipFile(candidate.with_suffix('.zip')) as archive:
            package_ok = (archive.namelist() == [candidate.name]
                          and archive.read(candidate.name) == candidate.read_bytes())
        if not checks['ok'] or not package_ok:
            raise ValueError('CON88 saved-byte format/one-TIFF ZIP check failed')

        gates_reg = root / 'registry/con88_gates.json'
        gates_web = root / 'docs/data/con88_gates.json'
        if gates_web.is_file() and gates_reg.read_bytes() != gates_web.read_bytes():
            raise ValueError('CON88 gates mirror drift between registry/ and docs/data/')
        gates_obj = json.loads(gates_reg.read_text(encoding='utf-8'))
        if gates_obj.get('ok_to_submit') is not False or gates_obj.get('verdict') != 'negative':
            raise ValueError('con88_gates.json must remain negative (ok_to_submit=False)')

        rc_root = json.loads((root / 'run_card_con88.json').read_text(encoding='utf-8'))
        if rc_root.get('ok_to_submit') is not False or rc_root.get('verdict') != 'negative':
            raise ValueError('run_card_con88.json must remain negative (ok_to_submit=False)')
        rc_reg_path = root / 'registry/con88_run_card.json'
        rc_web_path = root / 'docs/data/con88_run_card.json'
        if rc_reg_path.is_file() and rc_web_path.is_file():
            if rc_reg_path.read_bytes() != rc_web_path.read_bytes():
                raise ValueError('CON88 run_card mirror drift between registry/ and docs/data/')
            rc_reg = json.loads(rc_reg_path.read_text(encoding='utf-8'))
            if rc_reg.get('ok_to_submit') is not False or rc_reg.get('verdict') != 'negative':
                raise ValueError('registry/con88_run_card.json must remain negative (ok_to_submit=False)')

        w_ev = root / 'evidence/con88_clearance_withdrawal_20261025.json'
        w_web = root / 'docs/data/con88_clearance_withdrawal_20261025.json'
        if w_ev.is_file() and w_web.is_file():
            if w_ev.read_bytes() != w_web.read_bytes():
                raise ValueError('CON88 withdrawal receipt mirror drift between evidence/ and docs/data/')
            w_obj = json.loads(w_ev.read_text(encoding='utf-8'))
            if w_obj.get('ok_to_submit') is not False or w_obj.get('verdict') != 'negative':
                raise ValueError('CON88 withdrawal receipt must remain negative (ok_to_submit=False)')
        result = dict(schema='gems88.con88-research-audit.v1', file=FILE,
                      raster_sha256=SHA256, validator_output=checks,
                      zip_single_matching_tiff=package_ok,
                      decision=proof['decision'],
                      preplacement_registry_proof=proof['preplacement_registry_proof'],
                      research_download_ok=True, ok_to_submit=False,
                      approved_for_weekly_slot=False, verdict='negative',
                      historical_holdout_valid_for_promotion=False,
                      new_rasters_generated=0, experiments_run=0)
        code = 2 if args.require_submit else 0
    except Exception as exc:
        result = dict(schema='gems88.con88-research-audit.v1', decision='AUDIT_ERROR',
                      error=f'{type(exc).__name__}: {exc}', research_download_ok=False,
                      ok_to_submit=False, approved_for_weekly_slot=False, verdict='negative')
        code = 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
