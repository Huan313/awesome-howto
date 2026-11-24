"""Check Markdown paths and anchors. Optionally record external HTTP outcomes."""
import argparse
import ipaddress
import re
import socket
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.common import ROOT, USER_AGENT, write_text
from scripts.validate_guides import MARKDOWN, links, repo_files


def slug(text):
    text = unicodedata.normalize("NFC", text).lower()
    return "".join(char for char in text if (
        char in " _-" or unicodedata.category(char)[0] in {"L", "N", "M"}
    )).strip().replace(" ", "-")


@lru_cache
def anchors(path):
    parsed = MARKDOWN.parse(path.read_text(encoding="utf-8"))
    result = set()
    for index, token in enumerate(parsed):
        if token.type != "heading_open":
            continue
        heading = parsed[index + 1]
        base = slug("".join(child.content for child in heading.children or []
                            if child.type in {"text", "code_inline", "image"}))
        name, number = base, 1
        while name in result:
            name = f"{base}-{number}"
            number += 1
        result.add(name)
    return result


def inspect(root):
    invalid, external = [], defaultdict(set)
    for path in repo_files(root):
        if path.suffix != ".md":
            continue
        for url in set(links(path.read_text(encoding="utf-8"))):
            if not url:
                continue
            parts = urlsplit(url)
            path_label = path.relative_to(root).as_posix()
            if parts.scheme in {"https", "http"}:
                external[parts._replace(fragment="").geturl()].add(path_label)
                continue
            if parts.scheme == "mailto":
                continue
            if parts.netloc or parts.scheme:
                invalid.append((path_label, url, "unsupported link scheme"))
                continue
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
            if not target.is_relative_to(root) or not target.exists():
                invalid.append((path_label, url, "missing or outside repository"))
                continue
            if target.is_dir():
                target = target / "README.md"
            if parts.fragment and (not target.is_file() or target.suffix != ".md"
                                   or unquote(parts.fragment) not in anchors(target)):
                invalid.append((path_label, url, "missing Markdown anchor"))
    return sorted(invalid), external


def require_public(url):
    parts = urlsplit(url)
    if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username
            or parts.password or parts.port not in (None, 80, 443)):
        raise ValueError("non-public URL")
    addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    if not all(ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("non-global destination")


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_public(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def http_status(url):
    try:
        require_public(url)
        opener = build_opener(PublicRedirect())
        request = Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
        try:
            with opener.open(request, timeout=9) as reply:
                return "ok", str(reply.status)
        except HTTPError as error:
            error.close()
            if error.code not in {400, 403, 404, 405, 406, 410, 501}:
                raise
        request = Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-511"})
        with opener.open(request, timeout=9) as reply:
            return "ok", str(reply.status)
    except HTTPError as error:
        error.close()
        return ("dead" if error.code in {404, 410} else "unverified"), f"HTTP {error.code}"
    except (URLError, OSError, ValueError) as error:
        return "unverified", type(error).__name__


def github_api_url(url):
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/")
    if parts.netloc != "github.com" or parts.query or len(segments) < 2:
        return None
    owner, repo, *rest = segments
    if not all(re.fullmatch(r"[\w.-]+", segment, flags=re.ASCII) for segment in (owner, repo)):
        return None
    base = f"https://api.github.com/repos/{owner}/{repo}"
    if not rest:
        return base
    if len(rest) >= 3 and rest[0] == "blob":
        path = quote(unquote("/".join(rest[2:])), safe="/")
        if any(segment in {".", ".."} for segment in path.split("/")):
            return None
        return f"{base}/contents/{path}?" + urlencode({"ref": unquote(rest[1])})
    return None


def check_external(url):
    api = github_api_url(url)
    if api:
        status, detail = http_status(api)
        if status == "ok":
            return status, f"GitHub API {detail}"
    return http_status(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external", action="store_true")
    parser.add_argument("--strict", action="store_true", help="fail on confirmed HTTP 404 or 410")
    parser.add_argument("--report", default="out/link-check.md")
    args = parser.parse_args()
    invalid, external = inspect(ROOT)
    report = ["# 链接检查", "", "## 内部链接", ""]
    report.extend(f"- {path} → {url} · {reason}" for path, url, reason in invalid)
    if not invalid:
        report.append("所有可解析的内部 Markdown 路径与锚点通过。")
    counts = Counter()
    if args.external:
        report.extend(["", "## 外部链接", "", "404/410 标为失效。其他访问问题单独人工确认。", ""])
        jobs = sorted(external)
        with ThreadPoolExecutor(max_workers=6) as executor:
            for url, (status, detail) in zip(jobs, executor.map(check_external, jobs)):
                counts[status] += 1
                sources = ", ".join(sorted(external[url]))
                report.append(f"- {status} · {detail} · <{url}> · {sources}")
    write_text(ROOT / args.report, "\n".join(report) + "\n")
    print(f"Internal failures: {len(invalid)}. External: {dict(counts)}. Report: {args.report}")
    if invalid or (args.strict and counts["dead"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
