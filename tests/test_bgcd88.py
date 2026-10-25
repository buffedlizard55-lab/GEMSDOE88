"""Unit and byte-level release tests for Lane H88-BGCD and streaming DBF fixes."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor"), str(ROOT / "src")]

from gems88 import bgcd, physics  # noqa: E402
from scripts import validate_bgcd88  # noqa: E402


def _make_minimal_dbf(rows: list[tuple[str, str, bool]]) -> bytes:
    """Construct a minimal valid dBASE III binary table in memory."""
    fields = [(b"LongDegree\x00", 10), (b"T2m\x00\x00\x00\x00\x00\x00\x00\x00", 8)]
    hdr_len = 32 + 32 * len(fields) + 1
    rec_len = 1 + sum(fl for _, fl in fields)
    header = bytearray(32)
    header[0] = 0x03
    struct.pack_into("<IHH", header, 4, len(rows), hdr_len, rec_len)
    fdesc = bytearray()
    for name11, flen in fields:
        fd = bytearray(32)
        fd[:11] = name11
        fd[11] = ord("C")
        fd[16] = flen
        fdesc.extend(fd)
    body = bytearray()
    for lon_s, t2m_s, deleted in rows:
        flag = 0x2A if deleted else 0x20
        body.append(flag)
        body.extend(lon_s.encode("ascii").ljust(10)[:10])
        body.extend(t2m_s.encode("ascii").ljust(8)[:8])
    return bytes(header) + bytes(fdesc) + b"\x0D" + bytes(body) + b"\x1A"


def test_iter_dbf_records_matches_eager_and_filters_columns():
    dbf_bytes = _make_minimal_dbf([
        ("-118.25", "34.5", False),
        ("-119.00", "99.9", True),
        ("-117.50", "21.2", False),
    ])
    eager = physics._read_dbf_records(dbf_bytes)
    streamed = list(physics._iter_dbf_records(dbf_bytes))
    assert streamed == eager == [
        {"LongDegree": "-118.25", "T2m": "34.5"},
        {"LongDegree": "-117.50", "T2m": "21.2"},
    ]
    filtered = list(physics._iter_dbf_records(dbf_bytes, wanted={"T2m"}))
    assert filtered == [{"T2m": "34.5"}, {"T2m": "21.2"}]


def test_frangi_2d_pure_float32_enhances_linear_ridge_over_blob():
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    ridge = np.exp(-(((xx - 32.0) / 1.8) ** 2)).astype(np.float32)
    blob = np.exp(-(((xx - 16.0) ** 2 + (yy - 16.0) ** 2) / (2.0 * 3.0**2))).astype(np.float32)
    resp_ridge = bgcd._frangi_2d(ridge, sigmas=(1.5, 2.5))
    resp_blob = bgcd._frangi_2d(blob, sigmas=(1.5, 2.5))
    assert resp_ridge.dtype == np.float32
    assert np.isfinite(resp_ridge).all()
    assert float(resp_ridge.min()) >= 0.0 and float(resp_ridge.max()) <= 1.0
    assert float(resp_ridge[32, 32]) > 3.0 * float(resp_blob[16, 16])


def test_compute_visible_slip_fp_zero_leakage_from_hidden_faults(tmp_path):
    class DummyGrid:
        shape = (24, 24)
        footprint = np.ones((24, 24), dtype=bool)
        catalogue = np.zeros((24, 24), dtype=bool)

    g = DummyGrid()
    vis = np.zeros((24, 24), dtype=bool)
    vis[4:12, 6] = True
    hid = np.zeros((24, 24), dtype=bool)
    hid[16:22, 18] = True
    g.catalogue = vis | hid

    n_fp = int(g.footprint.sum())
    x_vis22 = np.zeros((n_fp, 22), dtype=np.float32)
    x_vis22[:, 0] = 3.0   # d1
    x_vis22[:, 1] = 1.0   # d_perp
    x_vis22[:, 2] = 2.0   # d_par_abs
    x_vis22[:, 16] = 8.0  # d2
    x_vis22[:, 18] = 0.5  # relay_facing

    slip_a = np.zeros((24, 24), dtype=np.float32)
    slip_a[vis] = 0.8
    slip_a[hid] = 0.1

    slip_b = slip_a.copy()
    slip_b[hid] = 999.0  # massive perturbation strictly on hidden faults

    mm_a = np.asarray(bgcd.compute_visible_slip_fp(g, vis, slip_a, x_vis22, tmp_path / "a", "t"))
    mm_b = np.asarray(bgcd.compute_visible_slip_fp(g, vis, slip_b, x_vis22, tmp_path / "b", "t"))
    assert mm_a.shape == (n_fp, 3) and mm_a.dtype == np.float32
    assert np.array_equal(mm_a, mm_b), "Hidden fault slip rates leaked into visible slip features!"


def test_bgcd88_frozen_release_and_fail_closed_gate(tmp_path):
    rep = validate_bgcd88.validate_bgcd88(ROOT)
    assert rep["ok"] is True
    assert rep["lane"] == "H88-BGCD"
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["verdict"] == "negative"
    assert rep["positive_pixels"] == 35000
    assert rep["share_le2"] == 0.0
    assert rep["share_gt25"] >= 0.35
    assert rep["canary_max_symmetric_auc"] <= 0.90
    assert rep["preplacement_max_abs_rho"] <= 0.90
    assert rep["worst_like_for_like_overlap_3px_extended"] <= 0.70
    assert rep["extended_rasters_checked"] >= 300
    assert validate_bgcd88.main([]) == 0
    assert validate_bgcd88.main(["--require-submit"]) == 2
