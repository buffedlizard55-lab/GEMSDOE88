"""Independent Euclidean-neighbourhood audit uses no square or wraparound shortcut."""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_h33_collar import disk_neighbourhood, inspect  # noqa: E402


def test_radius_two_is_euclidean_not_square():
    mask = np.zeros((9, 9), dtype=bool)
    mask[4, 4] = True
    result = disk_neighbourhood(mask, 2)
    assert result.sum() == 13
    assert result[2, 4] and result[3, 3]
    assert not result[2, 2] and not result[2, 3]


def test_neighbourhood_does_not_wrap_edges():
    mask = np.zeros((5, 5), dtype=bool)
    mask[0, 0] = True
    result = disk_neighbourhood(mask, 2)
    assert result.sum() == 6
    assert not result[-1, -1]
    assert np.array_equal(disk_neighbourhood(mask, 0), mask)
    with pytest.raises(ValueError):
        disk_neighbourhood(mask, -1)


def test_pinned_h33_lineage_when_inputs_are_restored():
    if not (ROOT / 'data/registry/h33_education.tif').exists():
        pytest.skip('validation-tier inputs not restored')
    report = inspect()
    counts = report['counts']
    assert report['h33_subset_of_d28'] and report['h33_subset_of_solo'] and report['solo_subset_of_d28']
    assert counts['d28_minus_h33'] == 6436
    assert counts['d28_minus_solo'] == 3891
    assert counts['solo_minus_h33'] == 2545
    assert counts['d28_minus_h33_over_2px'] == 0
    assert counts['h33_at_most_2px'] == 0
    assert report['organizer_confirmed_score'] is None
