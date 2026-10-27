#!/usr/bin/env python3
"""Stage the same canonical Pages URLs for branch and Actions deployments.

The repository's Pages source is the main branch root, where the reviewed
site lives at /docs/. An Actions artifact that uploads docs/ as its root would
instead publish incompatible URLs. Keep a small curated artifact with the
root landing page plus docs/, without copying local raw data or credentials.
"""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def stage(root: Path = ROOT) -> Path:
    root = Path(root).resolve()
    cache = root / '.cache'
    target = cache / 'pages-deployment'
    # Never follow a staging-directory or cache symlink when replacing it.
    if cache.is_symlink() or target.is_symlink():
        raise ValueError('Pages staging path cannot be a symlink')
    sources = (root / 'index.html', root / '.nojekyll', root / 'docs')
    if any(path.is_symlink() for path in sources) or not sources[0].is_file() or not sources[1].is_file() or not sources[2].is_dir():
        raise ValueError('Missing or symlinked Pages source')
    if any(path.is_symlink() for path in sources[2].rglob('*')):
        raise ValueError('symlinks are not permitted in published docs')
    if target.exists():
        if not target.is_dir():
            raise ValueError('Pages staging destination must be a directory')
        shutil.rmtree(target)
    target.mkdir(parents=True)
    shutil.copy2(sources[0], target / 'index.html')
    shutil.copy2(sources[1], target / '.nojekyll')
    shutil.copytree(sources[2], target / 'docs')
    return target


def main() -> int:
    try:
        print(f'PASS: staged root landing and /docs/ site at {stage()}')
        return 0
    except (OSError, ValueError) as exc:
        print(f'PAGES STAGING FAILED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
