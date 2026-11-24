"""Check guide schemas, editorial structure, taxonomy and repository metadata."""
import argparse
import re
import unicodedata
from datetime import date
from pathlib import Path

from markdown_it import MarkdownIt

from scripts.common import ROOT, read_yaml, validate, validator
from scripts.normalize_topics import public_url

SECTIONS = (
    "适用人群", "前置条件与不适用情况", "准备、耗时与费用", "操作步骤与验收",
    "常见错误与排查", "风险与限制", "最简行动清单", "参考来源", "核验与版本",
)
SKILLS = {
    "trend-scout", "persona-painpoint-researcher", "evidence-researcher",
    "howto-author", "fact-safety-auditor", "repo-maintainer",
}
MARKDOWN = MarkdownIt("commonmark")


def split_frontmatter(path):
    content = path.read_text(encoding="utf-8")
    parts = content.split("\n---\n", 1)
    if len(parts) != 2 or not parts[0].startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    return parts[0][4:], parts[1].strip()


def links(markdown):
    def walk(tokens):
        for token in tokens:
            if token.type in {"link_open", "image"}:
                yield token.attrGet("href") or token.attrGet("src")
            if token.children:
                yield from walk(token.children)
    return walk(MARKDOWN.parse(markdown))


def validate_guide(metadata):
    validate("guide", metadata)
    if not (date.fromisoformat(metadata["created_at"]) <= date.fromisoformat(metadata["updated_at"])
            < date.fromisoformat(metadata["review_due"])):
        raise ValueError("dates must satisfy created_at <= updated_at < review_due")
    for url in metadata["sources"]:
        public_url(url)
    if {"0-12", "13-17"} & set(metadata["age_groups"]) and metadata["risk_level"] != "high":
        raise ValueError("guides targeting minors need high-risk review")
    if "0-12" in metadata["age_groups"] and not {"parent", "caregiver"} & set(metadata["personas"]):
        raise ValueError("guides for ages 0–12 must address a guardian")


def read_guide(path):
    from scripts.common import parse_yaml

    header, body = split_frontmatter(path)
    metadata = parse_yaml(header)
    validate_guide(metadata)
    titles = re.findall(r"^# (.+)$", body, re.M)
    if titles != [metadata["title"]]:
        raise ValueError("expected one H1 matching title")
    section_titles = re.findall(r"^## (.+)$", body, re.M)
    if tuple(title for title in section_titles if title in SECTIONS) != SECTIONS:
        raise ValueError("required headings are missing, repeated or out of order")
    for title in SECTIONS:
        section = body.split(f"\n## {title}\n", 1)[1].split("\n## ", 1)[0].strip()
        if len(section) < 10:
            raise ValueError(f"section needs concrete content: {title}")
    reference = body.split("\n## 参考来源\n", 1)[1].split("\n## ", 1)[0]
    if set(metadata["sources"]) - set(links(reference)):
        raise ValueError("each metadata source must appear in the reference section")
    return metadata, body


def validate_repository(root=ROOT):
    personas = read_yaml(root / "data/personas.yaml")["personas"]
    scenarios = read_yaml(root / "data/scenarios.yaml")
    taxonomy = read_yaml(root / "data/topic-taxonomy.yaml")
    findings, guides, identifiers, titles = [], [], set(), set()
    for path in sorted((root / "guides").glob("*/*.md")):
        try:
            metadata, _ = read_guide(path)
            if path.parent.name != metadata["category"] or path.stem != metadata["id"].removeprefix("howto-"):
                raise ValueError("category or ID does not match the path")
            title = unicodedata.normalize("NFKC", metadata["title"]).casefold()
            if metadata["id"] in identifiers or title in titles:
                raise ValueError("duplicate ID or title")
            if set(metadata["personas"] + metadata["occupations"]) - personas.keys():
                raise ValueError("unknown persona or occupation")
            if set(metadata["scenarios"]) - set(taxonomy[metadata["category"]]["scenarios"]):
                raise ValueError("scenario does not belong to this category")
            if set(metadata["scenarios"]) - scenarios.keys():
                raise ValueError("unknown scenario")
            identifiers.add(metadata["id"])
            titles.add(title)
            guides.append((path, metadata))
            if date.fromisoformat(metadata["review_due"]) < date.today():
                findings.append(f"复查已到期：{path.relative_to(root)}")
        except ValueError as error:
            raise ValueError(f"{path.relative_to(root)}: {error}") from error
    if not guides:
        raise ValueError("no guides found")
    return guides, findings


def repo_files(root=ROOT):
    excluded = {".venv", ".git", "__pycache__", "out", ".pytest_cache"}
    for directory, children, files in root.walk():
        children[:] = sorted(name for name in children if name not in excluded)
        for file in sorted(files):
            yield directory / file


def validate_files(root=ROOT):
    names = {
        "auth.json", "hosts.yml", "credentials", "id_rsa", "id_ed25519", "config.local.toml",
    }
    for path in repo_files(root):
        if path.is_symlink():
            raise ValueError(f"symbolic link requires review: {path.relative_to(root)}")
        if (path.name in names or path.name.startswith((".env", "Cookie"))
                or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".har"}):
            raise ValueError(f"sensitive filename: {path.relative_to(root)}")
        if path.suffix in {".yml", ".yaml"}:
            read_yaml(path)
        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            if not content.endswith("\n") or re.search(r"[\x00-\x08\x0b-\x1f]", content):
                raise ValueError(f"invalid Markdown text: {path.relative_to(root)}")
    for kind in ("guide", "topic", "source"):
        validator(kind)
    paths = {path.parent.name: path for path in (root / ".agents/skills").glob("*/SKILL.md")}
    if set(paths) != SKILLS:
        raise ValueError("missing or unexpected project skills")
    from scripts.common import parse_yaml
    for name, path in paths.items():
        raw, body = split_frontmatter(path)
        metadata = parse_yaml(raw)
        if (metadata.get("name") != name or not isinstance(metadata.get("description"), str)
                or not metadata["description"].strip() or len(metadata["description"]) > 200
                or not all(section in body for section in (
                    "## 输入与目标", "## 流程与输出", "## 失败与安全", "## 示例与验收",
                ))):
            raise ValueError(f"invalid skill: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    validate_files(args.root)
    guides, notices = validate_repository(args.root)
    for notice in notices:
        print(notice)
    print(f"Validated {len(guides)} guides, {len(SKILLS)} skills and 3 schemas.")


if __name__ == "__main__":
    main()
