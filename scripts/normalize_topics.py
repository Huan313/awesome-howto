"""Normalize trusted metadata and minimize data retained from external sources."""
import hashlib
import html
import ipaddress
import re
import unicodedata
from urllib.parse import parse_qs, quote, unquote, urlsplit, urlunsplit

from scripts.common import stamp, validate

METRICS = {"stars", "forks", "points", "comments", "heat", "likes", "views", "saves"}
SOCIAL = {"xiaohongshu", "douyin", "reddit", "x", "youtube", "tiktok"}
SOCIAL_HOSTS = {
    "xiaohongshu": ("xiaohongshu.com",),
    "douyin": ("douyin.com", "open-douyin.com"),
    "reddit": ("reddit.com",),
    "x": ("x.com", "twitter.com"),
    "youtube": ("youtube.com", "youtu.be"),
    "tiktok": ("tiktok.com",),
}
PRIVATE_PATH = re.compile(r"/(?:user|users|profile|profiles|login|signin|oauth|oauth2|account)(?:/|$)", re.I)
SENSITIVE_TEXT = re.compile(
    r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|\b(?:\+?86[- ]?)?1[3-9]\d{9}\b"
    r"|\b(?:gh[opusr]_[A-Z0-9]{20,}|github_pat_[A-Z0-9_]{20,}|sk-(?:proj-)?[A-Z0-9_-]{20,})\b"
)


def clean_text(value, limit):
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]*>", " ", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Cf")
    value = SENSITIVE_TEXT.sub("[已省略]", value)
    return " ".join(value.split())[:limit]


def public_url(value):
    parts = urlsplit(value)
    host = parts.hostname or ""
    if (parts.scheme != "https" or not host or parts.username or parts.password
            or parts.port not in (None, 443) or "." not in host
            or host.endswith((".local", ".internal", ".test", ".invalid", ".localhost"))
            or not re.fullmatch(r"[a-z0-9.-]+", host) or PRIVATE_PATH.search(unquote(parts.path))
            or re.search(r"[\s<>\\]", value)):
        raise ValueError("URL must be a public HTTPS content URL")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("literal IP is not a content URL")
    path = parts.path.rstrip("/") or "/"
    if (host == "x.com" or host.endswith(".x.com") or host == "twitter.com"
            or host.endswith(".twitter.com")):
        if match := re.search(r"/status/(\d+)", path):
            host, path = "x.com", "/i/web/status/" + match[1]
        else:
            raise ValueError("use a public X post URL")
    if (host == "tiktok.com" or host.endswith(".tiktok.com")) and "/@" in path:
        raise ValueError("use an aggregate TikTok URL without an account identifier")
    # Preserve public identifiers required by these canonical content URLs.
    query = ""
    params = parse_qs(parts.query)
    if (host == "youtube.com" or host.endswith(".youtube.com")) and path == "/watch":
        video = params.get("v", [""])[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
            raise ValueError("invalid YouTube video ID")
        query = "v=" + video
    if host == "news.ycombinator.com" and path == "/item":
        item_id = params.get("id", [""])[0]
        if not re.fullmatch(r"\d{1,18}", item_id):
            raise ValueError("invalid Hacker News item ID")
        query = "id=" + item_id
    return urlunsplit(("https", host, quote(path, safe="/:@!$&'*+,;=-._~%"), query, ""))


def fingerprint(prefix, value):
    return f"{prefix}-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def normalize(raw):
    platform = raw["platform"]
    method = raw["method"]
    observed = stamp(raw["observed_at"])
    url = public_url(raw["url"])
    if platform in SOCIAL_HOSTS:
        host = urlsplit(url).hostname
        if not any(host == domain or host.endswith("." + domain) for domain in SOCIAL_HOSTS[platform]):
            raise ValueError("URL does not match the declared platform")
    title = clean_text(raw["title"], 180)
    query = clean_text(raw.get("query") or title, 120)
    record = {
        "source_id": fingerprint("src", f"{platform}|{url}|{query.casefold()}|{observed}"),
        "platform": platform,
        "kind": "social" if platform in SOCIAL or method in {"manual", "authorized-export"} else raw.get("kind", "community"),
        "title": title,
        "url": url,
        "observed_at": observed,
        "event_at": stamp(raw.get("event_at") or observed),
        "event_basis": raw.get("event_basis", "observed"),
        "query": query,
        "method": method,
        "metrics": {
            key: value for key, value in raw.get("metrics", {}).items()
            if key in METRICS and type(value) is int and value >= 0
        },
    }
    if raw.get("topic_key"):
        record["topic_key"] = raw["topic_key"]
    validate("source", record)
    return record
