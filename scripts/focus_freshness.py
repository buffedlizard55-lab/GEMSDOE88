#!/usr/bin/env python3
"""Check GitHub revision drift for the nine audited focus sites, never eligibility.

Only the public GitHub REST API is contacted. No DrivenData account, leaderboard,
training data, model, or submission endpoint is accessed. The pinned audit is
not rerun: a changed HEAD means the historic table is stale; an unchanged HEAD
means only that no revision drift was observed at the stated time. Network or
schema failures become UNKNOWN, never an assumed pass or submission approval.

--refresh writes a self-contained dated JSON snapshot atomically; --check validates
an existing snapshot without network access. GitHub Pages refreshes the snapshot
in its deployment artifact, not by pushing a branch. The browser additionally
marks a snapshot older than twelve hours as overdue.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"
SITES = tuple(f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36))
BASELINE = Path("docs/data/focus_sites_20261026.json")
EVIDENCE = Path("evidence/focus_sites_20261026_audit.json")
DEFAULT_OUTPUT = Path("docs/data/focus-freshness.json")
SCHEMA = "gems88.focus-freshness.v1"
SHA = re.compile(r"[0-9a-f]{40}\Z")
STALE_AFTER_HOURS = 12


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def timestamp(value: object) -> bool:
    # Match the GitHub wire format and the browser's accepted snapshot format.
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        return parsed.tzinfo is not None
    except ValueError:
        return False


def baseline(root: Path = ROOT) -> tuple[dict[str, str], str]:
    """Read the evidence-backed HEADs. No caller can supply a smaller site list."""
    web = (root / BASELINE).read_bytes()
    evidence = (root / EVIDENCE).read_bytes()
    if web != evidence:
        raise ValueError("published historical audit differs from evidence")
    data = json.loads(web)
    if not isinstance(data, dict) or data.get("schema") != "gems88.focus-sites-audit-20261026.v1":
        raise ValueError("unexpected historical-audit schema")
    verdict = data.get("summary_verdict")
    if not isinstance(verdict, dict) or verdict.get("ok_to_submit") is not False:
        raise ValueError("historical audit cannot authorize submissions")
    rows = data.get("focus_sites")
    if not isinstance(rows, list) or len(rows) != len(SITES):
        raise ValueError("historical audit must contain exactly nine sites")
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid historical row")
        site, head = row.get("site"), row.get("inspected_repo_head_sha")
        if site not in SITES or site in result or not isinstance(head, str) or not SHA.fullmatch(head):
            raise ValueError("invalid or duplicate historical site/HEAD")
        result[site] = head
    if set(result) != set(SITES):
        raise ValueError("historical audit lacks a required site")
    return result, hashlib.sha256(web).hexdigest()


class GitHubOnlyRedirect(HTTPRedirectHandler):
    """Never forward an Actions token to a redirected third-party host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme != "https" or target.hostname != "api.github.com"
                or target.username is not None or target.password is not None
                or target.port not in (None, 443)):
            raise ValueError("GitHub API redirect left the allowed host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_head(site: str) -> tuple[str, str]:
    if site not in SITES:
        raise ValueError("unexpected focus repository")
    url = f"https://api.github.com/repos/{OWNER}/{site}/commits/HEAD"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GEMSDOE88-focus-freshness/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers, method="GET")
    with build_opener(GitHubOnlyRedirect()).open(request, timeout=12) as response:
        payload = json.load(response)
    head = payload.get("sha")
    committed = payload.get("commit", {}).get("committer", {}).get("date")
    if not isinstance(head, str) or not SHA.fullmatch(head) or not timestamp(committed):
        raise ValueError("malformed GitHub commit response")
    return head, committed


def collect(pinned: dict[str, str], digest: str, *,
            fetch: Callable[[str], tuple[str, str]] = fetch_head,
            checked_at: str | None = None) -> dict:
    """Measure revision drift only. Requests are bounded and failures are local."""
    if set(pinned) != set(SITES) or any(not isinstance(v, str) or not SHA.fullmatch(v) for v in pinned.values()):
        raise ValueError("incomplete historical HEAD baseline")
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("invalid historical-audit digest")
    checked_at = checked_at or utc_now()
    if not timestamp(checked_at):
        raise ValueError("invalid collection time")

    def one(site: str) -> dict:
        row = {
            "site": site,
            "audited_head": pinned[site],
            "current_head": None,
            "current_commit_utc": None,
            "state": "UNKNOWN",
            "source_url": f"https://api.github.com/repos/{OWNER}/{site}/commits/HEAD",
            "error": None,
        }
        try:
            head, committed = fetch(site)
            if not isinstance(head, str) or not SHA.fullmatch(head) or not timestamp(committed):
                raise ValueError("invalid fetched HEAD")
            row.update(current_head=head, current_commit_utc=committed,
                       state="UNCHANGED" if head == pinned[site] else "CHANGED")
        except HTTPError as exc:
            row["error"] = f"GitHub HTTP {exc.code}"
        except (TimeoutError, URLError):
            row["error"] = "GitHub network unavailable or timed out"
        except Exception:
            # Do not serialize exception strings, which could contain credentials
            # or arbitrary upstream text. Unrecognized failures remain UNKNOWN.
            row["error"] = "GitHub response unavailable or invalid"
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(one, SITES))
    counts = {state.lower(): sum(row["state"] == state for row in rows)
              for state in ("CHANGED", "UNCHANGED", "UNKNOWN")}
    report = {
        "schema": SCHEMA,
        "checked_at_utc": checked_at,
        "status": "COMPLETE" if counts["unknown"] == 0 else "PARTIAL",
        "source": "GitHub API repository HEAD only; no organizer request",
        "audited_snapshot": BASELINE.as_posix(),
        "audited_snapshot_sha256": digest,
        "stale_after_hours": STALE_AFTER_HOURS,
        "counts": counts,
        "sites": rows,
        "limitations": (
            "A HEAD check is not a raster, holdout, receipt, leaderboard or quota audit. "
            "Even an unchanged HEAD does not authorize a submission."
        ),
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
    }
    validate_report(report, pinned, digest)
    return report


def validate_report(report: dict, pinned: dict[str, str], digest: str) -> None:
    """Validate schema and fail-closed states without depending on assertions."""
    if (not isinstance(report, dict) or report.get("schema") != SCHEMA or not timestamp(report.get("checked_at_utc"))
            or report.get("audited_snapshot") != BASELINE.as_posix()
            or report.get("audited_snapshot_sha256") != digest
            or report.get("stale_after_hours") != STALE_AFTER_HOURS
            or report.get("ok_to_submit") is not False
            or report.get("approved_for_weekly_slot") is not False):
        raise ValueError("invalid or unsafe freshness report")
    rows = report.get("sites")
    if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
            or [r.get("site") for r in rows] != list(SITES)):
        raise ValueError("freshness report must contain the ordered nine sites")
    counts = {state.lower(): 0 for state in ("CHANGED", "UNCHANGED", "UNKNOWN")}
    for row in rows:
        site, state, head = row["site"], row.get("state"), row.get("current_head")
        if row.get("audited_head") != pinned[site]:
            raise ValueError("freshness report references the wrong audited HEAD")
        if row.get("source_url") != f"https://api.github.com/repos/{OWNER}/{site}/commits/HEAD":
            raise ValueError("untrusted freshness source")
        if state not in ("CHANGED", "UNCHANGED", "UNKNOWN"):
            raise ValueError("unknown freshness state")
        counts[state.lower()] += 1
        if state == "UNKNOWN":
            if (head is not None or row.get("current_commit_utc") is not None
                    or not isinstance(row.get("error"), str) or not row["error"]):
                raise ValueError("unknown state must not retain a successful HEAD")
        elif (not isinstance(head, str) or not SHA.fullmatch(head)
              or not timestamp(row.get("current_commit_utc")) or row.get("error") is not None
              or (state == "UNCHANGED") != (head == pinned[site])):
            raise ValueError("freshness state contradicts its HEAD")
    if report.get("counts") != counts:
        raise ValueError("freshness counts contradict rows")
    expected = "COMPLETE" if counts["unknown"] == 0 else "PARTIAL"
    if report.get("status") != expected:
        raise ValueError("freshness status contradicts rows")


def write_atomic(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    fd, name = tempfile.mkstemp(prefix=".focus-freshness-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--refresh", action="store_true", help="query only the public GitHub API")
    actions.add_argument("--check", action="store_true", help="validate the stored snapshot offline")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else root / args.output
    try:
        pinned, digest = baseline(root)
        if args.refresh:
            report = collect(pinned, digest)
            write_atomic(output, report)
        else:
            report = json.loads(output.read_text(encoding="utf-8"))
            validate_report(report, pinned, digest)
        print(json.dumps({"status": report["status"], "checked_at_utc": report["checked_at_utc"],
                          "counts": report["counts"], "ok_to_submit": False}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        # Baseline corruption prevents a new deployment. The old browser snapshot
        # will age out; never turn this error into an eligibility decision.
        print(json.dumps({"status": "ERROR", "error": str(exc), "ok_to_submit": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
