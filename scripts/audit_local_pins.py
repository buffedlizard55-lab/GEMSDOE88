#!/usr/bin/env python3
"""Offline startup inventory. Never treats missing inputs or old receipts as verified."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def inventory(root):
    manifest = root / 'registry/data_manifest.json'
    entries = json.loads(manifest.read_text())['files']
    results = []
    for entry in entries:
        path = root / entry['local_path']
        digest = None
        if path.is_file():
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(4 << 20), b''):
                    h.update(chunk)
            digest = h.hexdigest()
        status = 'MISSING' if digest is None else (
            'VERIFIED' if digest == entry['sha256'] and path.stat().st_size == entry['bytes']
            else 'HASH_OR_SIZE_MISMATCH')
        results.append({'id': entry['id'], 'path': entry['local_path'],
                        'status': status, 'expected_sha256': entry['sha256'],
                        'actual_sha256': digest})
    return results


def main():
    inputs = inventory(ROOT)
    ledger = ROOT / 'ledger/submissions.csv'
    rows = list(csv.DictReader(ledger.open()))
    report = {
        'date_utc': '2026-10-23',
        'git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'axis': 'MASS', 'decision': ('STOP_STARTUP_GATE' if any(x['status'] != 'VERIFIED' for x in inputs)
                                    else 'PINS_VERIFIED_REBUILD_STILL_REQUIRED'),
        'manifest_sha256': hashlib.sha256((ROOT / 'registry/data_manifest.json').read_bytes()).hexdigest(),
        'inputs': inputs, 'verified_count': sum(x['status'] == 'VERIFIED' for x in inputs),
        'r0_rebuild': 'NOT_RUN by this inventory; exact rebuild separately required',
        'historical_r0_verification': 'NOT_FRESH_VALIDATION',
        'ledger_sha256': hashlib.sha256(ledger.read_bytes()).hexdigest(),
        'ledger_rows': len(rows),
        'portal_receipt_rows': sum(bool(x['receipt_score'] and x['receipt_date']) for x in rows),
        'existing_mass_values': [x['value'] for x in rows if x['axis'] == 'MASS' and x['parent'] == 'h33-h33-2-b2'],
        'new_variants': 0, 'predicted_change': None,
        'network_data_restore_attempted': False,
        'tracked_raster_archive_paths_data_use_unchecked': subprocess.check_output(
            ['git', 'ls-files', '*.tif', '*.zip'], cwd=ROOT, text=True).splitlines(),
    }
    out = ROOT / 'evidence/session_20261023_cbfc0a92_startup.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['decision']}: {report['verified_count']}/{len(inputs)} pins verified; {out.relative_to(ROOT)}")
    return 1 if any(x['status'] != 'VERIFIED' for x in inputs) else 0


if __name__ == '__main__':
    raise SystemExit(main())
