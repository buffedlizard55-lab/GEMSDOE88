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
    # invariant is: every modification is declared, pinned, and carries a reason
    # and an irregularity id. Non-append-only corrections must also explain their
    # class and prior hash; an undeclared edit still fails the per-file SHA loop.
    if pins["modifications"].startswith("none"):
        assert not pins.get("documented_patches")
        return
    patched = pins.get("documented_patches") or []
    assert patched, "modifications claimed but no documented_patches recorded"
    for info in patched:
        assert info["file"] in pins["sha256"]
        assert info["patched_sha256"] == pins["sha256"][info["file"]]
        if info["append_only"] is not True:
            # Some fail-closed defects cannot be repaired append-only: callers
            # must not keep reaching the unsafe earlier implementation. Such
            # edits need an explicit class and an immutable previous hash.
            assert info["append_only"] is False
            assert info["change_class"] in {"fail-closed correction", "documentation-only"}
            previous = info["previous_patched_sha256"]
            assert len(previous) == 64 and all(c in "0123456789abcdef" for c in previous)
            assert previous != info["patched_sha256"]
        assert info["irregularity"].startswith("IR-88-")
        assert len(info["reason"]) > 80
