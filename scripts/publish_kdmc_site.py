#!/usr/bin/env python3
"""Retired legacy MDC-88 publisher; deliberately refuses to publish.

The former renderer could overwrite the canonical site with an obsolete
MDC-88 "OK TO SUBMIT" banner based on a chance-corrected exception to the
binding literal registry-overlap rule. Its output is not authorized. The old
research record is archived under ``docs/mdc88/``; the current canonical site
is ``docs/index.html`` and its release feed is KTH-88.
"""

import sys


def main() -> int:
    print(
        "Refusing to publish the retired MDC-88 site. It failed the binding "
        "literal registry-overlap rule; see docs/mdc88/ and "
        "registry/kdmc_literal_reassessment.json.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
