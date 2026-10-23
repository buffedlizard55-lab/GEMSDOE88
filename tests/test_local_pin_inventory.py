import hashlib
import json
from scripts.audit_local_pins import inventory


def test_inventory_missing_mismatch_and_verified(tmp_path):
    (tmp_path / 'registry').mkdir()
    entries = []
    for name, content in [('missing', None), ('bad', b'wrong'), ('ok', b'expected')]:
        if content is not None:
            (tmp_path / name).write_bytes(content)
        entries.append({'id': name, 'local_path': name, 'bytes': 8,
                        'sha256': hashlib.sha256(b'expected').hexdigest()})
    (tmp_path / 'registry/data_manifest.json').write_text(json.dumps({'files': entries}))
    assert [x['status'] for x in inventory(tmp_path)] == ['MISSING', 'HASH_OR_SIZE_MISMATCH', 'VERIFIED']
