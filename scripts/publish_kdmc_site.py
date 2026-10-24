#!/usr/bin/env python3
"""Retired MDC-88 publisher; intentionally fail closed.

The former publisher rendered ``OK TO SUBMIT: YES`` from the chance-corrected
``gems88-gate-v3`` field and copied its TIFF into ``docs/downloads/`` even though
the same saved gate record marked the candidate as a literal duplicate of the
dense 17GEMSDOE raster. Do not regenerate that site. The current historical
reassessment is in ``registry/kdmc_gate_literal_reassessment.json`` and
``docs/mdc88/status.json``. No file-writing or artifact-copy path is retained.
"""
from __future__ import annotations

import sys

MESSAGE = (
    "MDC-88 site publisher retired: chance-corrected gate-v3 conflicts with the "
    "binding literal duplicate result. Refusing to generate pages or copy an artifact. "
    "See registry/kdmc_gate_literal_reassessment.json."
)


def main() -> int:
    print(MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
