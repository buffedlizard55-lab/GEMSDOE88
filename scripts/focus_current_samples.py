#!/usr/bin/env python3
"""Sample one README-cited TIFF per focus repository, without selecting a slot.

The HEADs come from the existing GitHub-only freshness snapshot. At each exact
commit we inspect the first bare docs/downloads/ or docs/research/ TIFF path in the first 16 KiB of README;
this is deliberately a sample, not the newest, highest-scoring, or best file.
No DrivenData request, prediction, training, or submission is performed.
--refresh downloads at most nine bounded GitHub blobs into an ignored temporary
directory, reopens them and publishes dated negative/unknown observations.
--check validates the stored report and its HEAD bindings offline.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57 import grid, uniqueness  # noqa: E402
from scripts import focus_freshness as freshness  # noqa: E402
from scripts.audit_literal_protocol import pinned  # noqa: E402
from scripts.preflight_mtas88 import WITNESS_REL, WITNESS_SHA  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402

SCHEMA = "gems88.focus-current-samples.v1"
DEFAULT_OUTPUT = Path("docs/data/focus-current-samples.json")
README_PREFIX_BYTES = 16_384
README_LIMIT = 2_000_000
RASTER_LIMIT = 30_000_000
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
# Do not match a path inside another repository's https://.../docs/ URL.
LOCAL_TIF = re.compile(r"(?<![A-Za-z0-9_./-])(docs/(?:downloads|research)/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.tiff?)(?![A-Za-z0-9_.-])", re.IGNORECASE)


def first_local_tiff(readme: bytes) -> str | None:
    """Deterministic discovery only; no claim that the first path is a winner."""
    prefix = readme[:README_PREFIX_BYTES].decode("utf-8", errors="replace")
    match = LOCAL_TIF.search(prefix)
    path = match.group(1) if match else None
    if path and (".." in Path(path).parts or path.startswith("/")):
        raise ValueError("unsafe README path")
    return path


def fetch_blob(site: str, head: str, path: str, limit: int) -> bytes:
    if site not in freshness.SITES or not freshness.SHA.fullmatch(head):
        raise ValueError("invalid repository or pinned HEAD")
    if path != "README.md" and (not LOCAL_TIF.fullmatch(path) or ".." in Path(path).parts):
        raise ValueError("invalid repository-local path")
    route = quote(path, safe="/")
    url = f"https://api.github.com/repos/{freshness.OWNER}/{site}/contents/{route}?ref={head}"
    headers = {"Accept": "application/vnd.github.raw+json", "User-Agent": "GEMSDOE88-focus-samples/1.0",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with build_opener(freshness.GitHubOnlyRedirect()).open(Request(url, headers=headers), timeout=20) as response:
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > limit:
            raise ValueError("GitHub blob exceeds size limit")
        raw = response.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError("empty or oversized GitHub blob")
    return raw


def load_freshness(root: Path, snapshot: Path) -> tuple[dict, str]:
    payload = snapshot.read_bytes()
    report = json.loads(payload)
    pins, digest = freshness.baseline(root)
    freshness.validate_report(report, pins, digest)
    return report, hashlib.sha256(payload).hexdigest()


def collect(root: Path = ROOT, *, snapshot: Path | None = None, fetch=fetch_blob,
            checked_at: str | None = None) -> dict:
    root = Path(root)
    snapshot = snapshot or root / freshness.DEFAULT_OUTPUT
    observed, snapshot_sha = load_freshness(root, snapshot)
    checked_at = checked_at or freshness.utc_now()
    if not freshness.timestamp(checked_at):
        raise ValueError("invalid sample-audit time")
    # Do not call an expired or future HEAD snapshot current.
    now = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    at = datetime.fromisoformat(observed["checked_at_utc"].replace("Z", "+00:00"))
    age = (now - at).total_seconds()
    if age < -300 or age > freshness.STALE_AFTER_HOURS * 3600:
        raise ValueError("HEAD snapshot expired or from the future")
    pinned(root, "data/bridge/sample_submission.tif", grid.SHA256_SAMPLE_SUBMISSION)
    pinned(root, "data/bridge/existing_faults.tif", grid.SHA256_EXISTING_FAULTS)
    witness_path = pinned(root, WITNESS_REL, WITNESS_SHA)
    g = grid.load_grid(root / "data/bridge")
    with rasterio.open(witness_path) as ds:
        witness = uniqueness._read_registry_values(ds, g.footprint,
                                                    expected_grid=(g.shape, g.crs, g.transform))
    near = uniqueness._near((witness > 0) & g.footprint, 3)
    rows = []
    with tempfile.TemporaryDirectory(prefix="focus-current-") as directory:
        for revision in observed["sites"]:
            site, head = revision["site"], revision["current_head"]
            row = {"site": site, "head": head, "readme_url": None, "path": None,
                   "source_url": None, "sha256": None, "format_pass": None,
                   "positive_inside_footprint": None, "overlap_3px": None,
                   "decision": "UNKNOWN", "reason": None, "ok_to_submit": False}
            if head is None:
                row["reason"] = "GitHub HEAD unavailable"
                rows.append(row)
                continue
            row["readme_url"] = f"https://github.com/{freshness.OWNER}/{site}/blob/{head}/README.md"
            try:
                readme = fetch(site, head, "README.md", README_LIMIT)
                path = first_local_tiff(readme)
                if path is None:
                    row.update(decision="NOT_DISCOVERED", reason="No matching bare docs/downloads or docs/research TIFF in README prefix")
                    rows.append(row)
                    continue
                row["path"] = path
                row["source_url"] = f"https://github.com/{freshness.OWNER}/{site}/blob/{head}/{path}"
                raw = fetch(site, head, path, RASTER_LIMIT)
                temporary = Path(directory) / f"{site}.tif"
                temporary.write_bytes(raw)
                fmt = validate_artifact(temporary, root / "data/bridge/sample_submission.tif")
                row.update(sha256=hashlib.sha256(raw).hexdigest(), format_pass=bool(fmt["ok"]))
                with rasterio.open(temporary) as ds:
                    if (ds.count != 1 or (ds.shape, ds.crs, ds.transform) != (g.shape, g.crs, g.transform)):
                        raise ValueError("sample grid mismatch")
                    values = uniqueness._read_registry_values(ds, g.footprint,
                                                               expected_grid=(g.shape, g.crs, g.transform))
                positive = (values > 0) & g.footprint
                n = int(positive.sum())
                if n == 0:
                    row.update(decision="INVALID_RASTER", reason="No positive in-footprint pixels")
                else:
                    overlap = float(near[positive].mean())
                    row.update(positive_inside_footprint=n, overlap_3px=overlap,
                               decision="DUPLICATE_STOP" if overlap > 0.70 else "NOT_CLEARED",
                               reason="Literal witness exceeds overlap limit" if overlap > 0.70 else
                                      "One witness is not a complete uniqueness or holdout audit")
            except (HTTPError, URLError, TimeoutError):
                row.update(decision="UNKNOWN", reason="GitHub blob unavailable")
            except Exception:
                # Never expose credentials or raw upstream text in published JSON.
                row.update(decision="INVALID_RASTER", reason="Sample unavailable, oversized, or invalid")
            rows.append(row)
    counts = {key: sum(row["decision"] == key for row in rows)
              for key in ("DUPLICATE_STOP", "NOT_CLEARED", "INVALID_RASTER", "NOT_DISCOVERED", "UNKNOWN")}
    report = {
        "schema": SCHEMA, "checked_at_utc": checked_at,
        "head_snapshot_checked_at_utc": observed["checked_at_utc"],
        "head_snapshot_sha256": snapshot_sha, "witness_sha256": WITNESS_SHA,
        "scope": "First bare docs/downloads/ or docs/research/ TIFF path in the first 16384 README bytes at each pinned HEAD; excludes other paths/URLs and is not a winner search or complete inventory.",
        "score_status": "NOT MEASURED: no holdout rerun or organizer receipt; no leaderboard estimate.",
        "rows": rows, "counts": counts, "ok_to_submit": False, "approved_for_weekly_slot": False,
        "new_tiffs_generated": 0, "weekly_slots_used": 0,
    }
    validate_report(report, observed, snapshot_sha)
    return report


def validate_report(report: dict, observed: dict, snapshot_sha: str) -> None:
    if (not isinstance(report, dict) or report.get("schema") != SCHEMA
            or not freshness.timestamp(report.get("checked_at_utc"))
            or report.get("head_snapshot_checked_at_utc") != observed.get("checked_at_utc")
            or report.get("head_snapshot_sha256") != snapshot_sha
            or report.get("witness_sha256") != WITNESS_SHA
            or report.get("ok_to_submit") is not False or report.get("approved_for_weekly_slot") is not False
            or report.get("new_tiffs_generated") != 0 or report.get("weekly_slots_used") != 0):
        raise ValueError("invalid or unsafe current-sample report")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != len(freshness.SITES):
        raise ValueError("current samples must contain exactly nine rows")
    counts = {key: 0 for key in ("DUPLICATE_STOP", "NOT_CLEARED", "INVALID_RASTER", "NOT_DISCOVERED", "UNKNOWN")}
    for row, revision in zip(rows, observed["sites"]):
        if (not isinstance(row, dict) or row.get("site") != revision["site"]
                or row.get("head") != revision["current_head"] or row.get("ok_to_submit") is not False
                or row.get("decision") not in counts or not isinstance(row.get("reason"), str)):
            raise ValueError("invalid current-sample identity or decision")
        head, site, path = row["head"], row["site"], row.get("path")
        if row.get("readme_url") != (f"https://github.com/{freshness.OWNER}/{site}/blob/{head}/README.md" if head else None):
            raise ValueError("untrusted README URL")
        if path is not None:
            if not isinstance(path, str) or not LOCAL_TIF.fullmatch(path) or ".." in Path(path).parts:
                raise ValueError("untrusted raster path")
            if row.get("source_url") != f"https://github.com/{freshness.OWNER}/{site}/blob/{head}/{path}":
                raise ValueError("untrusted raster URL")
        elif row.get("source_url") is not None:
            raise ValueError("source URL without path")
        sha = row.get("sha256")
        if (sha is not None and (not isinstance(sha, str) or not HEX64.fullmatch(sha) or path is None)):
            raise ValueError("invalid raster digest")
        if row.get("format_pass") is not None and type(row["format_pass"]) is not bool:
            raise ValueError("invalid format flag")
        if (sha is None) != (row.get("format_pass") is None):
            raise ValueError("format result is not bound to a raster digest")
        if head is None and (row["decision"] != "UNKNOWN" or path is not None or sha is not None):
            raise ValueError("unobserved HEAD cannot have a path or measured decision")
        if row["decision"] == "UNKNOWN" and sha is not None:
            raise ValueError("unknown sample cannot contain a format result")
        if row["decision"] == "NOT_DISCOVERED" and (path is not None or sha is not None):
            raise ValueError("undiscovered sample has a file")
        if row["decision"] in ("DUPLICATE_STOP", "NOT_CLEARED"):
            ov, n = row.get("overlap_3px"), row.get("positive_inside_footprint")
            if (path is None or sha is None or type(row.get("format_pass")) is not bool
                    or type(n) is not int or n <= 0 or type(ov) not in (int, float)
                    or not np.isfinite(ov) or not 0 <= ov <= 1
                    or (row["decision"] == "DUPLICATE_STOP") != (ov > 0.70)):
                raise ValueError("invalid measured sample")
        elif row.get("overlap_3px") is not None or row.get("positive_inside_footprint") is not None:
            raise ValueError("unmeasured sample contains a claimed overlap")
        counts[row["decision"]] += 1
    if report.get("counts") != counts:
        raise ValueError("current sample counts disagree")


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--refresh", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--snapshot", type=Path, default=root / freshness.DEFAULT_OUTPUT)
    parser.add_argument("--output", type=Path, default=root / DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.refresh:
            report = collect(root, snapshot=args.snapshot)
            freshness.write_atomic(args.output, report)
        else:
            observed, digest = load_freshness(root, args.snapshot)
            report = json.loads(args.output.read_text())
            validate_report(report, observed, digest)
        print(json.dumps({"status": "PASS", "checked_at_utc": report["checked_at_utc"],
                          "counts": report["counts"], "ok_to_submit": False}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": type(exc).__name__, "ok_to_submit": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
