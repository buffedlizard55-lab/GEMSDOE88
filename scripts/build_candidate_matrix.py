#!/usr/bin/env python3
"""Build the one-table candidate gate matrix from machine records (no typed-in results).

Every HOLDOUT-DTI value and CI below is asserted to appear in the cited record
before it is written. Writes docs/data/candidate_matrix.json and replaces the block
between <!-- MATRIX:START --> and <!-- MATRIX:END --> in docs/index.html.
Labels: HOLDOUT-DTI = local hide-and-recover (gems57-pooled-hide-v2), NOT an
organizer score. ORGANIZER-CONFIRMED: none exists in this repository.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import rasterio
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import _dots  # noqa: E402

DL = "docs/downloads/"
DIAG = {r["candidate"]: r for r in json.loads((ROOT / "evidence/dense_prior_topn_diagnostic.json").read_text())["topN_like_for_like"]}

# (label, tif or None, record, dti, ci, withheld, paired_delta, paired_ci, note)
ROWS = [
    ("PHASE-88 (archived compatibility record)", DL + "gems88-phase88-crossgrad-20261024-d7d02ab4-DO-NOT-SUBMIT.tif",
     "registry/phase88_run_card.json", 0.05306174540296061, [0.04606433072520727, 0.06023288744301309], 22893, None, None,
     "RTP/gravity cross-gradient"),
    ("MRR-BPR-88", DL + "gems88-mrr-bpr-blockresid-dinkelbach-20261024-v1-DO-NOT-SUBMIT.tif",
     "registry/run_card_mrr88.json", 0.18525582109578861, [0.1715190223372919, 0.19996477117347985], 22893,
     -0.004378034745084858, [-0.007902211641196701, -0.000623090528560107], "block residual; paired vs incumbent (CI < 0)"),
    ("MDC-88 (label corrected 2026-10-24)", DL + "gemsdoe88-mdc88-pu-concentration-2p83px-20261024T0740Z-zeros-DO-NOT-SUBMIT.tif",
     "registry/kdmc_gate.json", 0.1488495052282044, [0.13317761870164363, 0.1741312800501426], 22893, None, None,
     "pu concentration; was ok_to_submit=true, now false"),
    ("MDPS-88 (latest audited experiment; far regime)", DL + "gems88-mdps88-mix-29742dots-20261024-zeros-DO-NOT-SUBMIT.tif",
     "registry/mdps88_run_card.json", 0.07272295955361242, [0.05911330711505152, 0.08628315696691566], 10791,
     0.003596261052015104, [-0.006021409065574782, 0.012787871207464562], "paired vs fold-fair control crosses 0"),
    ("KTH-88", DL + "gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif",
     "registry/kth88_run_card.json", 0.05265580824432912, [0.045911112529722096, 0.059150702260526954], 22893, None, None,
     "K/Th antisymmetric step"),
    ("TILTZERO", DL + "gems88-tiltzero-rank-denovo-37654-20261024-a2150eeb-zeros-DO-NOT-SUBMIT.tif",
     "registry/tiltzero_run_card.json", 0.055083, [0.046419, 0.063081], 22663, None, None,
     "seeds 20+30 (cross-run)"),
    ("LBCAL", DL + "gems88-lbcal-receipt-38278-20261024-0aeb6eed-zeros-DO-NOT-SUBMIT.tif",
     "registry/lbcal_gate_v3.json", 0.061566, [0.05191, 0.072787], 22663, None, None,
     "seeds 20+30 (cross-run)"),
    ("PROVCREST", DL + "gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros-DO-NOT-SUBMIT.tif",
     "registry/provcrest_run_card.json", 0.076277, [0.067653, 0.084607], 22663, None, None,
     "seeds 20+30; literal gate fails"),
    ("IBL-88 (basin lattice, merged from main)", DL + "gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.tif",
     "registry/ibl88_run_card.json", 0.0, [0.0, 0.0], 22893, None, None,
     "HOLDOUT 0.0 is structural per record (b2+ gate-clean); literal 1.0"),
    ("H88-ADHR incumbent (stored bar, not a row file here)", None,
     "registry/phase88_run_card.json", 0.18788764184958875, [0.17169764852656258, 0.20326012211176936], 22893, None, None,
     "bar used by every gate; itself unverifiable from clean checkout (IR-88-75)"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def assert_in_record(rec_path: str, value, label: str) -> None:
    text = (ROOT / rec_path).read_text()
    if isinstance(value, list):
        for v in value:
            s = repr(v) if isinstance(v, float) else str(v)
            assert s in text or f"{v:.5f}" in text, f"{label}: {v} not found in {rec_path}"
    else:
        s = repr(value)
        assert s in text, f"{label}: {value!r} not found in {rec_path}"


def dot_count(tif: Path) -> int:
    with rasterio.open(tif) as src:
        return int(_dots(src.read(1)).sum())


def main() -> int:
    out_rows = []
    for label, tif, rec, dti, ci, n, dlt, dci, note in ROWS:
        # every quoted number must literally appear in the cited record (repr of the float)
        assert_in_record(rec, dti, label + " dti")
        ci_rec = "docs/data/kdmc-run-card.json" if rec == "registry/kdmc_gate.json" else rec
        assert_in_record(ci_rec, ci, label + " ci")
        assert str(n) in (ROOT / ci_rec).read_text(), f"{label}: withheld {n} not in {ci_rec}"
        if dlt is not None:
            assert_in_record(rec, dlt, label + " paired delta")
        row = {"label": label, "record": rec, "holdout_dti": dti, "ci95": ci, "withheld_positive_px": n,
               "note": note, "evidence_class": "HOLDOUT-DTI (gems57-pooled-hide-v2)",
               "organizer_confirmed": None}
        if dlt is not None:
            row["paired_delta"] = dlt
            row["paired_delta_ci95"] = dci
        if tif:
            p = ROOT / tif
            assert p.is_file(), tif
            row["tif"] = tif
            row["tif_sha256"] = sha(p)
            zp = p.with_suffix(".zip")
            row["zip"] = str(zp.relative_to(ROOT)) if zp.is_file() else None
            row["dots"] = dot_count(p)
            d = DIAG.get(p.name)
            row["literal_overlap_vs_17GEMSDOE"] = d["literal_forward_3px_overlap_vs_all_positive_witness_cells"] if d else None
            row["topN_like_for_like_overlap"] = d["forward_3px_overlap_vs_witness_topN"] if d else None
        row["ok_to_download_research"] = bool(tif)
        row["ok_to_submit"] = False
        row["reason_not_submit"] = (
            "literal 17GEMSDOE overlap 1.0 > 0.70 AND holdout does not beat 0.18789 bar" if tif else "reference bar only")
        out_rows.append(row)
    doc = {"schema": "gems88.candidate-matrix.v1", "generated_by": "scripts/build_candidate_matrix.py",
           "organizer_confirmed_scores": 0, "weekly_slots_used": 0, "rows": out_rows,
           "diagnostic": "evidence/dense_prior_topn_diagnostic.json"}
    (ROOT / "docs/data/candidate_matrix.json").write_text(json.dumps(doc, indent=2) + "\n")

    def f(x, nd=4):
        return "—" if x is None else f"{x:.{nd}f}"
    lines = ['<table class="matrix"><thead><tr><th>Candidate</th><th>Download</th><th>Dots</th>'
             '<th>HOLDOUT-DTI [95% CI]</th><th>Literal overlap vs 17GEMSDOE</th><th>Top-N like-for-like overlap</th>'
             '<th>OK to download (research)</th><th>OK to submit</th></tr></thead><tbody>']
    for r in out_rows:
        dl = (f'<a href="{r["tif"][5:]}" download>TIF</a>' + (f' · <a href="{r["zip"][5:]}" download>ZIP</a>' if r.get("zip") else "")) if r.get("tif") else "—"
        lines.append(
            f'<tr><td>{r["label"]}</td><td>{dl}</td><td>{r.get("dots", "—")}</td>'
            f'<td>{f(r["holdout_dti"])} [{f(r["ci95"][0])}, {f(r["ci95"][1])}] (n={r["withheld_positive_px"]:,})</td>'
            f'<td>{f(r.get("literal_overlap_vs_17GEMSDOE"), 3)}</td><td>{f(r.get("topN_like_for_like_overlap"), 3)}</td>'
            f'<td>{"YES (research)" if r["ok_to_download_research"] else "n/a"}</td><td><strong>NO</strong></td></tr>')
    lines.append("</tbody></table>")
    html = "\n".join(lines)
    idx = ROOT / "docs/index.html"
    s = idx.read_text()
    start, end = "<!-- MATRIX:START -->", "<!-- MATRIX:END -->"
    assert start in s and end in s, "matrix markers missing in docs/index.html"
    a, b = s.index(start) + len(start), s.index(end)
    idx.write_text(s[:a] + "\n" + html + "\n" + s[b:])
    print(f"wrote {len(out_rows)} rows; index.html matrix updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
