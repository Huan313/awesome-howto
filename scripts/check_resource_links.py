"""Probe reviewed official entries and record redirects and access restrictions."""
import argparse
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from scripts.check_links import require_public
from scripts.common import Client, FetchError, read_json, read_yaml
from scripts.deduplicate_resources import canonical_url
from scripts.discover_github import CONFIG, add_arguments, atomic_json, checked_at

AGENT = "AwesomeHowToResourceDiscovery"
GITLAB = [
    ("inkscape/inkscape", "Inkscape", "creative-hobby", "tool", "矢量图形绘制工具的公开项目入口。"),
    ("graphviz/graphviz", "Graphviz", "digital-life", "tool", "图形结构布局工具的官方开发仓库。"),
    ("fdroid/fdroid-website", "F-Droid website", "digital-life", "resource_directory", "F-Droid 文档与应用目录的公开站点源码。"),
]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(opener, url, method, max_read=0):
    require_public(url)
    headers = {"User-Agent": AGENT}
    if method == "GET" and not max_read:
        headers["Range"] = "bytes=0-511"
    with opener.open(Request(url, method=method, headers=headers), timeout=7) as reply:
        return reply.status, reply.headers, reply.read(max_read) if max_read else b""


def request_url(url):
    normalized = urlsplit(canonical_url(url))
    path = normalized.path
    if urlsplit(url).path.endswith("/") and not path.endswith("/"):
        path += "/"
    return urlunsplit(normalized._replace(path=path, fragment=""))


def robots(opener, url):
    site = urlsplit(url)
    target = f"{site.scheme}://{site.netloc}/robots.txt"
    for _ in range(3):
        try:
            response, _, text = request(opener, target, "GET", 200_000)
        except HTTPError as error:
            location = error.headers.get("Location")
            error.close()
            if error.code == 404:
                return True, "no robots.txt"
            if error.code in {301, 302, 303, 307, 308} and location:
                try:
                    target = request_url(urljoin(target, location))
                except ValueError:
                    return False, "invalid robots redirect"
                continue
            return False, f"robots HTTP {error.code}"
        except (URLError, ValueError, OSError, HTTPException) as error:
            return False, f"robots {type(error).__name__}"
        if response == 200:
            parser = RobotFileParser()
            parser.parse(text.decode("utf-8", errors="replace").splitlines())
            return parser.can_fetch(AGENT, url), "robots.txt checked"
        return False, f"robots HTTP {response}"
    return False, "robots redirect limit"


def probe(url):
    original = request_url(url)
    current = original
    observed = {"checked_at": checked_at(), "http": None, "redirect_target": None,
                "status": "needs_review", "method": "https", "reason": "unverified"}
    opener = build_opener(NoRedirect())
    visited = {current}
    for _ in range(4):
        allowed, reason = robots(opener, current)
        if not allowed:
            return {**observed, "status": "inaccessible", "reason": reason}
        for method in ("HEAD", "GET"):
            try:
                code, _, _ = request(opener, current, method)
            except HTTPError as error:
                code = error.code
                target = error.headers.get("Location")
                error.close()
                if method == "HEAD" and code in {400, 405, 501}:
                    continue
                if code in {301, 302, 303, 307, 308} and target:
                    try:
                        new_url = request_url(urljoin(current, target))
                    except ValueError:
                        return {**observed, "http": code, "reason": "invalid redirect destination"}
                    if new_url in visited or urlsplit(new_url).path.lower().endswith((".pdf", ".zip", ".epub")):
                        return {**observed, "http": code, "reason": "redirect loop or binary destination"}
                    visited.add(new_url)
                    current = new_url
                    observed["redirect_target"] = current
                    break
                return {**observed, "http": code, "status": "needs_review" if code in {404, 410} else "inaccessible",
                        "reason": f"HTTP {code}" + (" requires independent recheck" if code in {404, 410} else "")}
            except (URLError, ValueError, OSError, HTTPException) as error:
                return {**observed, "status": "inaccessible", "reason": type(error).__name__}
            else:
                return {**observed, "http": code, "status": "redirected" if current != original else "active",
                        "reason": reason}
    return {**observed, "reason": "redirect limit"}


def gitlab(entry):
    from urllib.parse import quote

    slug, title, domain, kind, description = entry
    path = quote(slug, safe="")
    client = Client(timeout=8, attempts=2)
    try:
        payload = client.json(f"https://gitlab.com/api/v4/projects/{path}")
        if payload.get("visibility") != "public":
            raise ValueError("GitLab result is not public")
        project_id, web_url = payload["id"], payload["web_url"]
    except (FetchError, KeyError, TypeError, ValueError) as error:
        reason = str(error) if isinstance(error, FetchError) else type(error).__name__
        return {"title": title, "url": "https://gitlab.com/" + slug, "domain": domain,
                "probe": {"status": "inaccessible", "reason": reason, "http": None,
                          "redirect_target": None, "method": "gitlab-api", "checked_at": checked_at()}}
    archived = payload.get("archived")
    return {"title": title, "url": web_url, "domain": domain, "platform": "gitlab",
            "publisher": slug.split("/")[0], "resource_type": kind, "description": description,
            "language": "unknown", "region": "unknown", "audience": [], "skill_level": "unknown",
            "visible_metadata": {"project_id": project_id, "last_activity_at": payload.get("last_activity_at"),
                                 "archived": archived, "default_branch": payload.get("default_branch")},
            "probe": {"status": "archived" if archived else "active", "http": 200,
                      "reason": "public project metadata", "method": "gitlab-api",
                      "redirect_target": None, "checked_at": checked_at()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    items = [row for row in read_yaml(CONFIG / "official-entries.yaml") if
             (not args.domains or row["domain"] in args.domains) and
             (not args.languages or row["language"] in args.languages)]
    if args.dry_run:
        print(f"{len(items)} official probes and {len(GITLAB)} GitLab route(s).")
        return
    def cached_probe(item):
        path = args.output / "link-cache" / (hashlib.sha256(item["url"].encode()).hexdigest() + ".json")
        if args.resume and not args.refresh_cache and path.is_file():
            return {**item, "probe": read_json(path)}
        result = probe(item["url"])
        atomic_json(path, result)
        return {**item, "probe": result}

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(cached_probe, items))
        projects = list(pool.map(gitlab, [entry for entry in GITLAB if not args.domains or entry[2] in args.domains]))
    atomic_json(args.output / "links.json", {"entries": rows + projects})
    for entry in rows + projects:
        print(entry["title"], entry["probe"]["status"], entry["probe"]["reason"])


if __name__ == "__main__":
    main()
