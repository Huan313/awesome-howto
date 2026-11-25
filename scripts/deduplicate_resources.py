"""Normalize resource URLs and index identity without conflating versions or forks."""
import hashlib
import ipaddress
import re
import unicodedata
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

TRACKING = {"ref", "source", "fbclid", "gclid", "spm", "si", "xsec_token", "token", "access_token",
            "auth", "password", "api_key", "apikey", "client_secret", "session", "sessionid", "sig", "signature"}
REPO_SEGMENT = re.compile(r"[\w.-]+\Z", re.ASCII)


def canonical_url(value, *, default_branch=None, pages_aliases=None):
    parts = urlsplit(value.strip())
    host = (parts.hostname or "").encode("idna").decode("ascii").lower()
    if not host or "." not in host or parts.scheme not in {"http", "https"} or parts.username or parts.password:
        raise ValueError("expected a public web URL")
    if parts.port not in {None, 80, 443} or host.endswith((".local", ".internal", ".test", ".localhost")):
        raise ValueError("not a public hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("literal IP destinations are excluded")
    path = parts.path.rstrip("/") or "/"
    parameters = [
        (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING
    ]
    anchor = parts.fragment
    if host in {"github.com", "www.github.com"}:
        host = "github.com"
        pieces = unquote(path.strip("/")).split("/")
        if len(pieces) >= 2 and all(REPO_SEGMENT.fullmatch(piece) and piece not in {".", ".."} for piece in pieces[:2]):
            owner, repo = pieces[0].casefold(), pieces[1].casefold().removesuffix(".git")
            rest = pieces[2:]
            parts_are_root_readme = (len(rest) == 3 and rest[0] == "blob" and
                                     rest[1] in {"main", "master", default_branch} and
                                     rest[2].casefold() in {"readme.md", "readme.rst"})
            if parts_are_root_readme and anchor in {"", "readme"}:
                rest = []
            if anchor == "readme" and not rest:
                anchor = ""
            path = "/" + "/".join(quote(piece, safe="") for piece in [owner, repo, *rest])
    result = urlunsplit((parts.scheme, host, path, urlencode(parameters, doseq=True), anchor))
    if pages_aliases and result in pages_aliases:
        return pages_aliases[result]
    return result


def github_name(url):
    parts = urlsplit(url)
    segments = unquote(parts.path.strip("/")).split("/")
    if parts.netloc != "github.com" or len(segments) != 2 or parts.query or parts.fragment:
        return None
    if not all(REPO_SEGMENT.fullmatch(item) and item not in {".", ".."} for item in segments):
        return None
    return "/".join(segments)


def normalized_title(title):
    value = unicodedata.normalize("NFKC", title).casefold()
    return "".join(char for char in value if char.isalnum())


def stable_id(url, repository_id=None):
    if repository_id:
        return f"gh-{repository_id}"
    return "resource-" + hashlib.sha256(url.encode()).hexdigest()[:20]
