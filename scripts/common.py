"""Shared paths, serialization, schema validation and bounded HTTP reads."""
import json
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")
USER_AGENT = "Awesome-HowTo/0.1 (+https://github.com/Huan313/awesome-howto)"
MAX_RESPONSE = 4 * 1024 * 1024


class StrictLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in keys:
                raise ValueError("duplicate YAML key")
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def parse_yaml(content):
    return yaml.load(content, Loader=StrictLoader)


def read_yaml(path):
    return parse_yaml(path.read_text(encoding="utf-8"))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path, payload):
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if result.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def stamp(value):
    return timestamp(value).isoformat(timespec="seconds").replace("+00:00", "Z")


@lru_cache
def validator(kind):
    schema = read_json(ROOT / "schemas" / f"{kind}.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate(kind, payload):
    error = next(validator(kind).iter_errors(payload), None)
    if error:
        field = ".".join(map(str, error.absolute_path)) or "record"
        # Omit values. Validation failures can contain private input data.
        raise ValueError(f"{kind}: {field} failed {error.validator}")


class FetchError(Exception):
    """A transport failure safe to record in a public report."""


class SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlsplit(req.full_url), urlsplit(newurl)
        if (old.scheme, old.netloc) != (new.scheme, new.netloc):
            raise FetchError("cross-origin redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, delay=0.18, timeout=10, attempts=3):
        self.delay = delay
        self.timeout = timeout
        self.attempts = attempts
        self.opener = build_opener(SameHostRedirect())
        self.last_request = 0.0

    def get(self, url, headers=None, data=None):
        request = Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
        for attempt in range(self.attempts):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            retry_after = 0
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    data = response.read(MAX_RESPONSE + 1)
                    if len(data) > MAX_RESPONSE:
                        raise FetchError("oversize response")
                    return data
            except HTTPError as error:
                reason = f"HTTP {error.code}"
                retryable = error.code in (408, 429, 500, 502, 503, 504)
                raw_delay = error.headers.get("Retry-After", "")
                retry_after = int(raw_delay) if raw_delay.isdecimal() and len(raw_delay) < 8 else 0
                error.close()
                if not retryable or retry_after > 20:
                    raise FetchError(reason) from None
            except (URLError, TimeoutError, OSError) as error:
                reason = type(error).__name__
            if attempt + 1 < self.attempts:
                time.sleep(max(retry_after, 2**attempt))
        raise FetchError(reason)

    def json(self, url, headers=None, data=None):
        try:
            return json.loads(self.get(url, headers, data))
        except (ValueError, UnicodeError):
            raise FetchError("invalid JSON response") from None
