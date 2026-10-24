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
    # The brief requires a shared defect to be fixed ONCE in the template rather than
    # forked privately, so "no modifications at all" is not the right invariant. The
    # invariant is: every modification is declared, append-only, and carries a reason
    # and an irregularity id. An undeclared edit still fails, because the per-file
    # SHA-256 loop above compares against the pinned hashes.
    if pins["modifications"].startswith("none"):
        assert not pins.get("documented_patches")
        return
    patched = pins.get("documented_patches") or []
    assert patched, "modifications claimed but no documented_patches recorded"
    for info in patched:
        assert info["file"] in pins["sha256"]
        assert info["patched_sha256"] == pins["sha256"][info["file"]]
        assert info["append_only"] is True
        assert info["irregularity"].startswith("IR-88-")
        assert len(info["reason"]) > 80
