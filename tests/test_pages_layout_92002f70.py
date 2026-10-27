"""Both GitHub Pages deployment paths must preserve the public guide URL."""
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import stage_pages  # noqa: E402


def make_source(root):
    (root / 'docs').mkdir(parents=True)
    (root / 'index.html').write_text('<a href="docs/executive-summary.html">Guide</a>')
    (root / '.nojekyll').write_text('')
    (root / 'docs/index.html').write_text('overview')
    (root / 'docs/executive-summary.html').write_text('guide')
    (root / 'data').mkdir()
    (root / 'data/private-not-for-publication').write_text('raw data')


def test_staging_has_same_public_paths_as_legacy_root_and_no_private_data(tmp_path):
    make_source(tmp_path)
    target = stage_pages.stage(tmp_path)
    assert (target / 'index.html').read_bytes() == (tmp_path / 'index.html').read_bytes()
    assert (target / '.nojekyll').is_file()
    for name in ('index.html', 'executive-summary.html'):
        assert (target / 'docs' / name).read_bytes() == (tmp_path / 'docs' / name).read_bytes()
    assert not (target / 'data').exists()
    (target / 'stale').write_text('old')
    (tmp_path / 'docs/executive-summary.html').write_text('new guide')
    assert stage_pages.stage(tmp_path) == target
    assert not (target / 'stale').exists()
    assert (target / 'docs/executive-summary.html').read_text() == 'new guide'


@pytest.mark.parametrize('which', ['docs', 'inside-docs', 'cache', 'target'])
def test_staging_rejects_symlinked_inputs_or_destination(tmp_path, which):
    make_source(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'sentinel'
    sentinel.write_text('safe')
    if which == 'docs':
        (tmp_path / 'docs').rename(tmp_path / 'original-docs')
        (tmp_path / 'docs').symlink_to(tmp_path / 'original-docs', target_is_directory=True)
    elif which == 'inside-docs':
        (tmp_path / 'docs/link').symlink_to(sentinel)
    elif which == 'cache':
        (tmp_path / '.cache').symlink_to(outside, target_is_directory=True)
    else:
        (tmp_path / '.cache').mkdir()
        (tmp_path / '.cache/pages-deployment').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        stage_pages.stage(tmp_path)
    assert sentinel.read_text() == 'safe'


def test_workflow_and_readme_point_to_root_consistent_docs_paths():
    workflow = (ROOT / '.github/workflows/pages.yml').read_text()
    assert 'python scripts/stage_pages.py' in workflow
    assert 'path: .cache/pages-deployment' in workflow
    readme = (ROOT / 'README.md').read_text()
    host = 'https://buffedlizard55-lab.github.io/GEMSDOE88/'
    assert host + 'docs/index.html' in readme
    assert host + 'docs/executive-summary.html' in readme
    landing = (ROOT / 'index.html').read_text()
    for dest in re.findall(r'href="(docs/[^"]+)"', landing):
        assert (ROOT / dest).is_file(), dest
