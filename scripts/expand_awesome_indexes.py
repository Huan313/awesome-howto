"""Expand safe collection structures with GitHub Contents and Git Trees BFS."""
import argparse
import hashlib
import json
import posixpath
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote, urljoin, urlsplit

from scripts.common import read_yaml
from scripts.deduplicate_resources import canonical_url, github_name
from scripts.discover_github import (
    CONFIG, add_arguments, atomic_json, build_client, checked_at, encoded_repo, repo_metadata,
)
from scripts.extract_collection_items import parse_document, suitable, translation_language

DOCUMENT = re.compile(r"\.(?:md|mdx|rst|ipynb)$", re.I)
TOC = re.compile(r"(?:^|/)(?:readme|toc|summary|index|contents|contributing)\.(?:md|rst)$", re.I)
LICENSE_NAME = re.compile(r"^(?:license|copying|copyright)(?:[_.-].*)?$", re.I)
DIRNAME = re.compile(r"(?:^|/)(?:docs|guides?|book|wiki|tutorials?|examples?|chapters?|lessons?|en|zh)(?:/|$)", re.I)
SKIP_PATH = re.compile(r"(?:^|/)(?:assets|.github|.git|screenshots|media|node_modules|vendor|tests?)(?:/|$)", re.I)
ADMIN_DOC = re.compile(r"(?:^|/)(?:contributing|support|license|copying|code[-_]of[-_]conduct|security)\.", re.I)
FORK_PARENTS = {"jlevy/the-art-of-command-line", "practical-tutorials/project-based-learning"}
FORMAT_HINT = re.compile(r"awesome|guide|tutorial|manual|handbook|course|curriculum|checklist|learn|book|"
                         r"实践|手册|教程|指南|课程|食谱", re.I)


def ref_url(repo, commit, path, anchor=""):
    link = f"{repo}/blob/{commit}/" + quote(path, safe="/")
    return link + ("#" + quote(anchor, safe="-_") if anchor else "")


def file_list(payload):
    # Exclude large binaries, code and private data. Tree hashes and filtered path lists are sufficient.
    allowed = []
    for item in payload["tree"]:
        path = item["path"]
        if item["type"] == "blob" and len(path) < 240 and not SKIP_PATH.search(path) and suitable(path):
            if DOCUMENT.search(path) or ("/" not in path and LICENSE_NAME.fullmatch(path)):
                allowed.append(path)
    return {"paths": sorted(allowed)[:6000], "matched_count": len(allowed),
            "truncated": payload["truncated"] or len(allowed) > 6000}


def license_metadata(payload):
    return {"spdx_id": (payload.get("license") or {}).get("spdx_id"),
            "url": payload.get("html_url"), "path": payload.get("path")}


def structure(client, name, meta, rules):
    prefix = "repos/" + encoded_repo(name)
    branch = quote(meta["default_branch"], safe="")
    commit = client.get(f"{prefix}/commits/{branch}", lambda item: {
        "sha": item["sha"], "tree_sha": item["commit"]["tree"]["sha"],
    })
    if commit["status"] != "ok":
        return {"status": "commit-unavailable", "http": commit["http"], "items": []}
    sha = commit["data"]["sha"]
    tree = client.get(f"{prefix}/git/trees/{commit['data']['tree_sha']}?recursive=1", file_list)
    root_url = canonical_url(meta["url"])
    readme = client.get(f"{prefix}/readme?ref={sha}", lambda item: parse_document(item, root_url))
    docs = [readme["data"]] if readme["data"] else []
    paths = (tree["data"] or {}).get("paths", [])
    index_paths = [path for path in paths if TOC.search(path) and ("/" not in path or DIRNAME.search(path))
                   and all(path != doc["path"] for doc in docs)]
    index_paths.sort(key=lambda path: (path.count("/"), path.casefold()))
    statuses = []
    for path in index_paths[:max(0, rules["max_documents_per_repository"] - len(docs))]:
        lookup = client.get(f"{prefix}/contents/{quote(path, safe='/')}?ref={sha}",
                            lambda item: parse_document(item, root_url))
        if lookup["data"]:
            docs.append(lookup["data"])
        statuses.append({"path": path, "http": lookup["http"], "status": lookup["status"]})
    return {"status": "ok" if tree["data"] and docs else "partial", "commit_sha": sha,
            "tree_http": tree["http"], "readme_http": readme["http"], "documents": docs,
            "toc_checks": statuses, "tree_truncated": (tree["data"] or {}).get("truncated"),
            "paths": paths, "license_files": [path for path in paths if LICENSE_NAME.fullmatch(path)]}


def local_path(href, doc, meta, commit):
    parts = urlsplit(href)
    if parts.query:
        return None
    if parts.scheme or parts.netloc:
        if parts.netloc not in {"github.com", "www.github.com"}:
            return None
        segments = unquote(parts.path.strip("/")).split("/", 4)
        if (len(segments) != 5 or "/".join(segments[:2]).casefold() != meta["full_name"].casefold()
                or segments[2] not in {"blob", "tree"} or segments[3] not in {commit, meta["default_branch"]}):
            return None
        path = segments[-1]
    else:
        value = unquote(parts.path)
        path = (posixpath.normpath(value.lstrip("/")) if value.startswith("/") else
                posixpath.normpath(posixpath.join(posixpath.dirname(doc), value)))
    return path if not path.startswith("../") and path != ".." else None


def collection_items(meta, info, rules):
    if not info.get("documents"):
        return [], None
    commit = info["commit_sha"]
    repo = canonical_url(meta["url"])
    paths = set(info["paths"])
    local, external = {}, {}
    shapes = []
    for doc in info["documents"]:
        for heading in doc["headings"]:
            if ADMIN_DOC.search(doc["path"]):
                continue
            path, anchor = doc["path"], heading["anchor"]
            url = ref_url(repo, commit, path, anchor)
            local.setdefault(url, {"url": url, "title": heading["title"], "path": path, "mode": "heading"})
            shapes.append(heading["title"].casefold())
        for link in doc["links"]:
            path = local_path(link["href"], doc["path"], meta, commit)
            if path in paths and DOCUMENT.search(path) and not ADMIN_DOC.search(path):
                url = ref_url(repo, commit, path)
                local.setdefault(url, {"url": url, "title": link["label"], "path": path,
                                       "mode": "document", "translation": translation_language(link, path)})
                continue
            target = urljoin(ref_url(repo, commit, doc["path"]), link["href"])
            try:
                url = canonical_url(target)
            except (ValueError, UnicodeError):
                continue
            if not suitable(url + " " + link["label"]):
                continue
            name = github_name(url)
            if (name and name.casefold() == meta["full_name"].casefold()) or (
                not name and url.startswith(repo + "/")
            ):
                continue
            if translation_language(link) or FORMAT_HINT.search(link["label"] + " " + url):
                external.setdefault(url, {"url": url, "title": link["label"], "path": doc["path"],
                                          "mode": "external", "translation": translation_language(link)})
    for path in sorted(paths):
        if (DOCUMENT.search(path) and not TOC.search(path) and not ADMIN_DOC.search(path)
                and (DIRNAME.search(path) or path.count("/") > 0)):
            title = re.sub(r"[-_]+", " ", posixpath.basename(path).rsplit(".", 1)[0])
            if len(title) > 4 and suitable(title):
                url = ref_url(repo, commit, path)
                local.setdefault(url, {"url": url, "title": title, "path": path, "mode": "tree"})
    files_first = sorted(local.values(), key=lambda row: row["mode"] not in {"document", "tree"})
    external_first = sorted(external.values(), key=lambda row: (
        not bool(re.search(r"awesome|handbook|manual|curriculum|course", row["url"], re.I)), row["url"]))
    fingerprint = hashlib.sha256("\n".join(shapes).encode()).hexdigest() if len(shapes) >= 7 else None
    return files_first[:rules["max_local_items"]] + external_first[:rules["max_external_items"]], fingerprint


def inspect_root(client, item, rules, can_expand):
    name = item["repository"]
    prefix = "repos/" + encoded_repo(name)
    result = client.get(prefix, repo_metadata)
    meta = result["data"]
    if not meta:
        return {**item, "fetch_status": result["status"], "http": result["http"],
                "checked_at": result["checked_at"], "items": []}
    legal = client.get(prefix + "/license", license_metadata)
    acquired = {**item, "metadata": meta, "fetch_status": "ok", "http": result["http"],
                "checked_at": result["checked_at"], "license_check": legal["data"],
                "license_http": legal["http"], "items": []}
    if not can_expand or not item["expand"] or not meta["default_branch"]:
        return acquired
    details = structure(client, name, meta, rules)
    entries, fingerprint = collection_items(meta, details, rules)
    return {**acquired, "items": entries, "fingerprint": fingerprint,
            "structure": {k: v for k, v in details.items() if k not in {"documents", "paths"}},
            "headings": [heading for doc in details.get("documents", []) for heading in doc["headings"][:15]]}


def expand(client, seeds, args, rules):
    queue = [{**seed, "depth": 0, "via": None} for seed in seeds]
    seen = {row["repository"].casefold() for row in queue}
    returned = []
    remaining = rules["repository_expansions"]
    cap = min(args.max_depth, rules["max_depth"])
    for depth in range(cap + 1):
        if not queue:
            break
        if depth:
            queue = queue[:8]
        batch = []
        for item in queue:
            take = bool(remaining and item["expand"] and depth < cap)
            batch.append((item, take))
            remaining -= int(take)
        with ThreadPoolExecutor(max_workers=rules["concurrency"]) as workers:
            results = list(workers.map(lambda pair: inspect_root(client, pair[0], rules, pair[1]), batch))
        returned.extend(results)
        queue = []
        for result in results:
            for item in result["items"]:
                name = github_name(item["url"])
                if (name and depth + 1 < cap and name not in seen
                        and "awesome" in name.split("/")[1] and suitable(name)):
                    seen.add(name)
                    queue.append({"repository": name, "depth": depth + 1, "expand": True,
                                  "via": result["metadata"]["url"], "group": "recursive",
                                  "domain": result["domain"], "language": None, "resource_type": "awesome_list"})
    return returned


def inspect_forks(client, roots, rules):
    for root in roots:
        if root["repository"].casefold() not in FORK_PARENTS or root["fetch_status"] != "ok":
            continue
        prefix = "repos/" + encoded_repo(root["repository"])
        listing = client.get(prefix + "/forks?sort=stargazers&per_page=2",
                             lambda repos: [repo["full_name"] for repo in repos])
        for name in listing["data"] or []:
            item = {"repository": name, "depth": 0, "via": None, "expand": False,
                    "group": "relationship-probe", "domain": root["domain"],
                    "language": None, "resource_type": root["resource_type"]}
            yield inspect_root(client, item, rules, False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    seeds = [row for row in read_yaml(CONFIG / "seed-indexes.yaml") if
             (not args.domains or row["domain"] in args.domains) and
             (not args.languages or row["language"] in args.languages)]
    if args.dry_run:
        print(json.dumps({"seed_count": len(seeds), "depth": args.max_depth}))
        return
    client, rules = build_client(args)
    started = checked_at()
    results = expand(client, seeds, args, rules)
    results += list(inspect_forks(client, results, rules))
    atomic_json(args.output / "expansion.json", {"started_at": started, "finished_at": checked_at(),
                                               "depth_limit": args.max_depth, "roots": results})
    print(f"{len(results)} repository routes, {sum(row['fetch_status'] == 'ok' for row in results)} resolved.")
    if args.verbose:
        for row in results:
            print(row["repository"], row["depth"], row["http"], len(row["items"]))


if __name__ == "__main__":
    main()
