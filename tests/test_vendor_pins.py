"""Shared-template changes must be declared and hash-linked, never hidden forks."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{64}\Z")


def test_shared_template_modifications_are_pinned_and_declared():
    pins = json.loads((ROOT / "registry/vendor_pins.json").read_text())
    files = list((ROOT / "vendor/gems57").glob("*.py"))
    assert len(files) == len(pins["sha256"])
    for path in files:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pins["sha256"][path.name], path.name
    if pins["modifications"].startswith("none"):
        assert not pins.get("documented_patches")
        return
    patches = pins.get("documented_patches") or []
    assert patches, "modifications claimed but no documented_patches recorded"
    last_by_file = {}
    for info in patches:
        name = info["file"]
        assert name in pins["sha256"]
        assert SHA.fullmatch(info["patched_sha256"])
        assert type(info["append_only"]) is bool
        assert info["irregularity"].startswith("IR-88-")
        assert len(info["reason"]) > 80
        previous = last_by_file.get(name)
        # Earlier consolidated historical entries share one final hash. Every
        # later change must explicitly link to the preceding recorded hash.
        if previous and info["patched_sha256"] != previous:
            assert info["previous_patched_sha256"] == previous
        if not info["append_only"]:
            # First local edit links to the pinned upstream bytes; later edits
            # link to the last locally recorded hash.
            assert info["previous_patched_sha256"] == (previous or info["upstream_sha256"])
            assert info.get("provenance")
            assert info.get("verification_tests")
            assert all((ROOT / test).is_file() for test in info["verification_tests"])
        last_by_file[name] = info["patched_sha256"]
    assert all(pins["sha256"][name] == digest for name, digest in last_by_file.items())
