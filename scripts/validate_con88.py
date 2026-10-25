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
