import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_template_is_unmodified():
    pins = json.loads((ROOT / "registry/vendor_pins.json").read_text())
    files = list((ROOT / "vendor/gems57").glob("*.py"))
    assert len(files) == len(pins["sha256"])
    for p in files:
        assert hashlib.sha256(p.read_bytes()).hexdigest() == pins["sha256"][p.name], (
            p.name
        )
    assert pins["modifications"].startswith("none")
