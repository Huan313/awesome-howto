"""Check public Markdown entries, source policy and the independent topic bank."""
import argparse
import csv
import re
import subprocess
from collections import Counter
from datetime import date
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

from scripts.common import ROOT, read_yaml
from scripts.normalize_topics import public_url

COLLECTIONS = {
    "howto-series": {"HowTo 系列"},
    "handbooks-and-courses": {"手册", "课程", "学习路径"},
    "awesome-indexes": {"Awesome List"},
}
TOPIC_TYPES = {"HowTo", "参考", "官方入口"}
BANK_COLUMNS = (
    "topic_id", "topic", "domain", "target_audience", "pain_point", "discovery_source",
    "source_url", "verified_resources", "content_angle", "evergreen_or_trend", "status", "notes",
)
ENTRY = re.compile(
    r"- \[(?P<title>[^\[\]\r\n]+)\]\((?P<url>https://[^\s()]+)\) — "
    r"(?P<summary>[^`\r\n]+?)\s*(?P<labels>`[^`\r\n]+`(?: · `[^`\r\n]+`)+)"
)
REVIEW_ID = re.compile(r"审核记录 #[1-9][0-9]*\Z")
TOPIC_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
TRACKING = {"ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid"}
PRIVATE_QUERY = {"token", "access_token", "auth", "api_key", "key", "password", "session", "signature"}


def resource_url(value):
    """Keep meaningful content parameters and section fragments in identity."""
    public_url(value)
    parts = urlsplit(value)
    host = parts.hostname
    assert host is not None
    query = parse_qsl(parts.query, keep_blank_values=True)
    if any(key.casefold() in PRIVATE_QUERY for key, _ in query):
        raise ValueError("resource URL contains a private query key")
    visible = [(key, val) for key, val in query
               if key.casefold() not in TRACKING and not key.casefold().startswith("utm_")]
    path = unquote(parts.path).rstrip("/") or "/"
    if host == "github.com":
        pieces = path.strip("/").split("/", 2)
        if len(pieces) >= 2:
            owner, repository, *rest = pieces
            if rest and rest[0].casefold() in {"blob/main/readme.md", "blob/master/readme.md"} and not parts.fragment:
                rest = []
            path = "/" + "/".join((owner.casefold(), repository.casefold().removesuffix(".git"), *rest))
    return host, path, urlencode(sorted(visible)), unquote(parts.fragment)


def official_host(host, policy):
    approved = policy["public_entry_hosts"]
    return host in approved["exact"] or any(
        host == suffix or host.endswith("." + suffix) for suffix in approved["gov_suffixes"]
    )


def check_labels(labels, host, domain, kinds, taxonomy, policy):
    kind, language, *details = labels
    if kind not in kinds or kind not in taxonomy["types"] or language not in taxonomy["languages"]:
        raise ValueError("unexpected type or language for this page")
    if len(set(labels)) != len(labels):
        raise ValueError("repeated resource label")
    rule = policy["high_risk"]
    risk_flag, approval = rule["required_labels"]
    date_prefix = rule["date_label"] + " "
    dates = [tag.removeprefix(date_prefix) for tag in details if tag.startswith(date_prefix)]
    reviews = [tag for tag in details if REVIEW_ID.fullmatch(tag)]
    regions = [tag for tag in details if tag in taxonomy["regions"]]
    known = set(regions) | {date_prefix + value for value in dates} | set(reviews) | {risk_flag, approval}
    if set(details) - known or len(regions) > 1 or len(dates) > 1 or len(reviews) > 1:
        raise ValueError("unexpected or ambiguous resource metadata")
    if dates and date.fromisoformat(dates[0]).isoformat() != dates[0]:
        raise ValueError("date must use YYYY-MM-DD")
    if kind == "官方入口":
        if not official_host(host, policy) or not regions or not dates:
            raise ValueError("official entry needs an official host, region and check date")
    if risk_flag in details or (domain in policy["protected_topics"] and kind != "官方入口"):
        if not ({risk_flag, approval, rule["region"]} <= set(details) and dates and reviews):
            raise ValueError("high-risk content requires mainland-China scope and dated human review")
        if not official_host(host, policy):
            raise ValueError("high-risk content requires an approved primary source")
    elif approval in details or reviews:
        raise ValueError("human review label requires a high-risk entry")
    return kind, language


def read_index(path, domain, kinds, taxonomy, policy):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if sum(line.startswith("# ") for line in lines) != 1 or not lines or not lines[0].startswith("# "):
        raise ValueError(f"{path.name}: expected one top-level title")
    if sum(line.startswith("## ") for line in lines) > 5 or any(line.startswith("### ") for line in lines):
        raise ValueError(f"{path.name}: keep entries under at most five second-level sections")
    for number, line in enumerate(lines, 1):
        if not line.startswith(("- ", "* ", "+ ")):
            continue
        match = ENTRY.fullmatch(line)
        try:
            if not match:
                raise ValueError("expected one resource per line with a direct link, use and labels")
            labels = match["labels"][1:-1].split("` · `")
            url = resource_url(match["url"])
            kind, language = check_labels(labels, url[0], domain, kinds, taxonomy, policy)
        except ValueError as error:
            raise ValueError(f"{path.name}:{number}: {error}") from error
        yield url, kind, language, number


def validate_bank(path, domains, registered, policy):
    ids = set()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != BANK_COLUMNS:
            raise ValueError("topic bank header does not match the documented fields")
        for row in reader:
            if None in row or not all(row.values()):
                raise ValueError(f"topic bank line {reader.line_num}: incomplete row")
            topic_id = row["topic_id"]
            if not TOPIC_ID.fullmatch(topic_id) or topic_id in ids:
                raise ValueError(f"topic bank line {reader.line_num}: invalid or duplicate topic ID")
            ids.add(topic_id)
            if row["domain"] not in domains or row["status"] not in policy["states"]:
                raise ValueError(f"{topic_id}: unknown topic or review state")
            if row["evergreen_or_trend"] not in {"evergreen", "trend"}:
                raise ValueError(f"{topic_id}: invalid time scope")
            resource_url(row["source_url"])
            for reference in row["verified_resources"].split(" | "):
                if resource_url(reference) not in registered:
                    raise ValueError(f"{topic_id}: verified resource is absent from the formal catalog")
    return len(ids)


def validate_catalog(root):
    taxonomy = read_yaml(root / "data/taxonomy.yml")
    policy = read_yaml(root / "data/source-policy.yml")
    domains = taxonomy["domains"]
    registered = {}
    counts, by_type, languages = {}, Counter(), Counter()
    archive = "archive/legacy-v3-0/"
    paths = [(f"{archive}catalog/{name}.md", name, TOPIC_TYPES) for name in domains]
    paths += [(f"{archive}collections/{name}.md", name, kinds) for name, kinds in COLLECTIONS.items()]
    for path, domain, kinds in paths:
        count = 0
        for key, kind, language, line in read_index(root / path, domain, kinds, taxonomy, policy):
            if key in registered:
                raise ValueError(f"{path}:{line}: duplicate resource, first listed in {registered[key]}")
            registered[key] = f"{path}:{line}"
            count += 1
            by_type[kind] += 1
            languages[language] += 1
        counts[domain] = count
    migrated = set()
    for name in ("official-sources", "recommended-projects", "policy-sources"):
        path = root / "references" / f"{name}.md"
        for key, _, _, line in read_index(path, name, set(taxonomy["types"]), taxonomy, policy):
            if key in migrated or key not in registered:
                raise ValueError(f"{path.name}:{line}: expected a unique retained source")
            migrated.add(key)
    guides = sorted((root / "howto").glob("*/*/*.md"))
    if {guide.parent.parent.name for guide in guides} != {"digital-life", "ai-productivity", "life-mind"}:
        raise ValueError("missing a focused guide section")
    for guide in guides:
        body = guide.read_text(encoding="utf-8")
        for heading in ("适用与准备", "基础档", "成功检查", "证据与核验"):
            if f"\n## {heading}\n" not in body:
                raise ValueError(f"{guide.name}: missing {heading}")
    return {"pages": counts, "types": dict(by_type), "languages": dict(languages),
            "focused_guides": len(guides), "retained_sources": len(migrated),
            "topics": validate_bank(root / "content-bank/topics.csv", domains, registered, policy)}


def check_catalog_diff(root, base):
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("PR base must be a full Git SHA")
    paths = subprocess.check_output(
        ["git", "diff", "--name-only", "-z", "--diff-filter=ACMR", f"{base}...HEAD"], cwd=root, text=True
    ).split("\0")
    domains = read_yaml(root / "data/taxonomy.yml")["domains"]
    allowed = {f"catalog/{name}.md" for name in domains} | {f"collections/{name}.md" for name in COLLECTIONS}
    allowed |= {"people/README.md", "content-bank/README.md", "content-bank/topics.csv", "content-bank/topic-schema.md",
                "data/source-policy.yml", "data/taxonomy.yml"}
    public_prefixes = ("catalog/", "collections/", "people/", "content-bank/")
    private_prefixes = ("local-studio/", "out/", "reports/", "data/reviews/", "data/discovery-runs/")
    for path in paths:
        if path.startswith(private_prefixes) or path.endswith((".jsonl", ".ndjson")):
            raise ValueError(f"keep candidate data and run logs out of the PR: {path}")
        if path.startswith(public_prefixes) and path not in allowed:
            raise ValueError(f"unexpected file in the public catalog: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="check changed PR paths against this exact base commit")
    options = parser.parse_args()
    if options.base:
        check_catalog_diff(ROOT, options.base)
    result = validate_catalog(ROOT)
    print(f"Validated {sum(result['types'].values())} catalog resources and {result['topics']} topic bank records.")
    print("Pages:", result["pages"])
    print("Types:", result["types"])
    print("Languages:", result["languages"])
    print("Focused guides:", result["focused_guides"], "Retained sources:", result["retained_sources"])


if __name__ == "__main__":
    main()
