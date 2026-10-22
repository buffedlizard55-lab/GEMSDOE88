"""Restore hash-pinned owner mirrors, NOT organizer-authenticated competition data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def restore(features=False):
    manifest = json.loads((ROOT / 'research/mirror-manifest.json').read_text())
    wanted = {'labels', 'existing_faults', 'sample_submission'}
    if features:
        wanted.add('training_features')
    receipts = []
    for item in manifest['files']:
        if item['id'] not in wanted:
            continue
        dest = ROOT / 'data' / item['dest']
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix('.partial')
        try:
            with tmp.open('wb') as out:
                for part in item.get('parts', [item.get('path')]):
                    subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github.raw+json',
                        f"repos/{item['repo']}/contents/{part}?ref={item['ref']}"], stdout=out, check=True)
            with tmp.open('rb') as inp:
                digest = hashlib.file_digest(inp, 'sha256').hexdigest()
            if digest != item['sha256'] or tmp.stat().st_size != item['bytes']:
                raise ValueError(f"Integrity failure: {item['id']}")
            tmp.replace(dest)
            receipts.append({'id': item['id'], 'sha256': digest, 'integrity': 'PASS',
                             'organizer_authenticated': False})
        finally:
            tmp.unlink(missing_ok=True)
    (ROOT / 'evidence/input-restoration.json').write_text(json.dumps(receipts, indent=2)+'\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--features', action='store_true', help='Also restore the approximately 419 MB feature raster')
    restore(p.parse_args().features)
