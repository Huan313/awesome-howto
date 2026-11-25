"""Bounded GitHub search and structural metadata collection using gh auth."""
import argparse
import hashlib
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from urllib.parse import quote, urlencode, urlsplit

from scripts.common import ROOT, read_json, read_yaml, stamp, write_json
from scripts.normalize_topics import clean_text

REPO = re.compile(r"[\w.-]+/[\w.-]+\Z", re.ASCII)
CONFIG = ROOT / "discovery"
DEFAULT_OUTPUT = ROOT / "out" / "resource-discovery"


def checked_at():
    return stamp(datetime.now(timezone.utc))


def atomic_json(path, value):
    scratch = path.with_suffix(".pending")
    write_json(scratch, value)
    scratch.replace(path)


def encoded_repo(name):
    if not REPO.fullmatch(name) or any(word in {".", ".."} for word in name.split("/")):
        raise ValueError("invalid GitHub repository name")
    return "/".join(quote(part, safe="") for part in name.split("/"))


def repo_metadata(item):
    """Select public repository metadata, not owner profiles or raw API payloads."""
    if item.get("private") or (item.get("visibility") not in {None, "public"}) or not item.get("full_name"):
        return None
    parent = item.get("parent") or {}
    return {
        "repository_id": item["id"], "full_name": item["full_name"], "url": item["html_url"],
        "homepage": item.get("homepage") or None,
        "about": clean_text(item.get("description") or "", 180),
        "topics": [clean_text(word, 46) for word in item.get("topics", [])[:32]],
        "stars": item["stargazers_count"], "forks": item["forks_count"],
        "open_issues": item.get("open_issues_count"), "created_at": item.get("created_at"),
        "pushed_at": item.get("pushed_at"), "updated_at": item.get("updated_at"),
        "license_spdx": (item.get("license") or {}).get("spdx_id"),
        "archived": bool(item.get("archived")), "default_branch": item.get("default_branch"),
        "fork": bool(item.get("fork")), "parent_url": parent.get("html_url"),
    }


class GitHub:
    def __init__(self, cache, *, resume=False, refresh=False, search_spacing=2.35):
        self.cache = cache
        self.resume = resume
        self.refresh = refresh
        self.search_spacing = search_spacing
        self.next_request = {}
        self.lock = Lock()

    def throttle(self, group):
        delay = self.search_spacing if group == "search" else .28
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_request.get(group, 0.0))
            self.next_request[group] = slot + delay
        time.sleep(max(0.0, slot - now))

    def get(self, endpoint, project, *, key=None):
        host = urlsplit(endpoint)
        if host.scheme or host.netloc or endpoint.startswith("/") or ".." in host.path.split("/"):
            raise ValueError("expected a relative GitHub API endpoint")
        cache = self.cache / (hashlib.sha256((key or endpoint).encode()).hexdigest() + ".json")
        # Only a caller-projected response is ever persisted. Raw READMEs are transient.
        previous = read_json(cache) if cache.is_file() else None
        if self.resume and not self.refresh and previous and previous["status"] == "ok":
            return previous
        headers = []
        if self.refresh and previous and previous["status"] == "ok":
            for field, header in (("etag", "If-None-Match"), ("last_modified", "If-Modified-Since")):
                if previous.get(field):
                    headers += ["--header", f"{header}: {previous[field]}"]
        initial = {"endpoint": endpoint, "checked_at": checked_at(), "data": None}
        for attempt in range(3):
            self.throttle("search" if endpoint.startswith("search/") else "core")
            try:
                reply = subprocess.run(
                    ["gh", "api", "--hostname", "github.com", "--include", *headers, endpoint],
                    capture_output=True, encoding="utf-8", errors="replace", timeout=25, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                status, fields, body = None, {}, ""
            else:
                raw_headers, _, body = reply.stdout.replace("\r\n", "\n").partition("\n\n")
                code = re.search(r"HTTP/\S+\s+(\d{3})", raw_headers)
                status = int(code[1]) if code else None
                fields = dict(
                    (first.lower(), rest.strip())
                    for line in raw_headers.splitlines()[1:]
                    if (line.find(":") > 0)
                    for first, rest in [line.split(":", 1)]
                )
            if status == 304 and previous:
                result = {**previous, "checked_at": checked_at(), "http": 304}
                break
            if status == 200:
                try:
                    data = project(json.loads(body))
                except (KeyError, TypeError, ValueError):
                    result = {**initial, "status": "invalid-response", "http": status}
                else:
                    result = {**initial, "status": "ok", "http": status, "data": data,
                              "etag": fields.get("etag"), "last_modified": fields.get("last-modified")}
                break
            limited = status == 429 or (status == 403 and (
                fields.get("x-ratelimit-remaining") == "0" or "retry-after" in fields))
            result = {**initial, "status": "rate-limited" if limited else "unavailable", "http": status}
            if attempt == 2 or (not limited and status not in {None, 500, 502, 503, 504}):
                break
            delay = 2 ** attempt
            retry_after = fields.get("retry-after", "")
            reset_at = fields.get("x-ratelimit-reset", "")
            if retry_after.isdecimal():
                delay = max(delay, int(retry_after))
            elif limited and reset_at.isdecimal():
                delay = max(delay, int(reset_at) - int(time.time()) + 2)
            if delay > 60:
                break
            time.sleep(delay)
        atomic_json(cache, result)
        return result


def search_page(client, query, page, page_size, since):
    expression = f"{query['expression']} is:public"
    if since:
        expression += " pushed:>=" + since
    endpoint = "search/repositories?" + urlencode({
        "q": expression, "sort": query["sort"], "order": "desc",
        "per_page": page_size, "page": page,
    })

    def project(payload):
        return {
            "total_count": payload["total_count"], "incomplete": payload["incomplete_results"],
            "items": [item for raw in payload["items"] if (item := repo_metadata(raw))],
        }

    reply = client.get(endpoint, project)
    return {**query, "executed_expression": expression, "page": page, **reply}


def discover(client, queries, *, pages, page_size, since, concurrency):
    def run(query):
        results = []
        for page in range(1, min(query.get("pages", pages), 3) + 1):
            item = search_page(client, query, page, page_size, since)
            results.append(item)
            data = item["data"]
            if not data or data["total_count"] <= page * page_size:
                break
        return results

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        return [item for pages in pool.map(run, queries) for item in pages]


def csv_set(value):
    return {item.strip() for item in value.split(",") if item.strip()}


def add_arguments(parser):
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=2500, help="candidate record ceiling")
    parser.add_argument("--max-depth", type=int, choices=range(4), default=3)
    parser.add_argument("--domains", type=csv_set, default=set())
    parser.add_argument("--languages", type=csv_set, default=set())
    parser.add_argument("--since", type=date.fromisoformat)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")


def search_configuration(args):
    matrix = read_yaml(CONFIG / "query-matrix.yaml")
    queries = [row for row in matrix["queries"] if
               (not args.domains or row["domain"] in args.domains) and
               (not args.languages or row["language"] in args.languages)]
    if args.limit < 1:
        raise ValueError("--limit must be positive")
    if not queries:
        raise ValueError("no configured query matches these filters")
    return matrix, queries


def build_client(args):
    rules = read_yaml(CONFIG / "discovery-rules.yaml")
    return GitHub(args.output / "cache", resume=args.resume, refresh=args.refresh_cache,
                  search_spacing=rules["search_spacing_seconds"]), rules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    matrix, queries = search_configuration(args)
    if args.dry_run:
        print(json.dumps({"queries": queries, "pages": matrix["pages"], "since": str(args.since)}, ensure_ascii=False))
        return
    client, rules = build_client(args)
    started = checked_at()
    reports = discover(client, queries, pages=matrix["pages"], page_size=matrix["page_size"],
                       since=args.since.isoformat() if args.since else None, concurrency=rules["concurrency"])
    atomic_json(args.output / "search.json", {"started_at": started, "finished_at": checked_at(), "pages": reports})
    failures = sum(row["status"] != "ok" for row in reports)
    print(f"{len(queries)} groups, {len(reports)} attempted pages, {failures} unsuccessful pages.")
    if args.verbose:
        for item in reports:
            print(item["id"], item["page"], item["http"],
                  len((item["data"] or {}).get("items", [])))
    if failures == len(reports):
        raise SystemExit("All GitHub searches failed; see the checkpoint.")


if __name__ == "__main__":
    main()
