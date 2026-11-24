"""Use a repository-reviewed brief to render and validate a low-risk draft."""
import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.build_index import render
from scripts.common import ROOT, SHANGHAI, read_json, read_yaml, write_text
from scripts.normalize_topics import clean_text
from scripts.run_research import escape
from scripts.validate_guides import read_guide

BRIEFS = "data/editorial-briefs.yaml"
DRAFT_SCHEMA = ".github/codex-draft.schema.json"


def draft_path(root, slug, brief):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("invalid editorial brief slug")
    return root / "guides" / brief["category"] / f"{slug}.md"


def choose(root, requested, selection):
    briefs = read_yaml(root / BRIEFS)
    categories = set(read_json(selection)["categories"])
    for slug, brief in briefs.items():
        if (requested == slug or (requested == "auto" and brief["category"] in categories)) and not draft_path(root, slug, brief).exists():
            return slug
    return ""


def prompt(brief):
    return (
        "根据下列经维护者核准的编辑简报，用简体中文写一篇低风险操作指南的结构化正文。\n"
        "将步骤写成动作和可观察的验收结果。依据已提供的证据摘要处理事实和范围。"
        "使用虚构例子。遇到证据缺口如实说明，不补造版本、费用、验收结果或引用。\n"
        "仅返回符合 schema 的 JSON 对象。写 3 至 6 步。"
        "每个字段为纯文本，勿插入链接、Markdown、代码块、其他元数据或 PR 指令。\n\n"
        + json.dumps(brief, ensure_ascii=False, indent=2) + "\n"
    )


def paragraph(value):
    if (not 10 <= len(value.strip()) <= 650 or re.search(r"https?://|[\x00-\x08\x0b-\x1f]", value, re.I)):
        raise ValueError("draft field has disallowed length, control characters or embedded link")
    return escape(clean_text(value, 650))


def stage(root, slug, draft, today):
    brief = read_yaml(root / BRIEFS)[slug]
    path = draft_path(root, slug, brief)
    if path.exists():
        raise ValueError("an existing guide already uses this path")
    schema = read_json(root / DRAFT_SCHEMA)
    if not Draft202012Validator(schema).is_valid(draft):
        raise ValueError("model draft did not match the expected schema")
    if not 3 <= len(draft["steps"]) <= 6:
        raise ValueError("expected 3 to 6 steps")
    metadata = dict(
        id=f"howto-{slug}", title=brief["title"], category=brief["category"],
        subcategory=brief["subcategory"], personas=brief["personas"],
        age_groups=["18-24", "25-34", "35-44", "45-59"], occupations=brief["personas"],
        scenarios=brief["scenarios"], region="global", difficulty="beginner",
        estimated_time=brief["estimated_time"], cost="按使用环境核对",
        evidence_level="B", content_type="howto", risk_level="low", status="draft",
        created_at=today.isoformat(), updated_at=today.isoformat(),
        review_due=(today + timedelta(days=60)).isoformat(),
        sources=[item["url"] for item in brief["evidence"]],
    )
    header = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items())
    lines = ["---", header, "---", "", "# " + brief["title"], "", paragraph(draft["intro"]), ""]
    for heading, field in (
        ("适用人群", "audience"), ("前置条件与不适用情况", "prerequisites"), ("准备、耗时与费用", "materials"),
    ):
        lines.extend([f"## {heading}", "", paragraph(draft[field]), ""])
    lines.extend(["## 操作步骤与验收", ""])
    for index, step in enumerate(draft["steps"], 1):
        lines.append(f"{index}. {paragraph(step['action'])} **验收**　{paragraph(step['check'])}")
    lines.append("")
    for heading, field in (
        ("常见错误与排查", "troubleshooting"), ("风险与限制", "limits"), ("最简行动清单", "checklist"),
    ):
        lines.extend([f"## {heading}", "", paragraph(draft[field]), ""])
    lines.extend(["## 参考来源", ""])
    for item in brief["evidence"]:
        lines.append(f"- {item['note']} [{item['title']}]({item['url']})（编辑简报核验于 2026-11-25）。")
    lines.extend(["", "## 核验与版本", "",
                  f"{today.isoformat()} 生成初稿，待人工核对来源、版权与操作结果。v0.1。", ""])
    write_text(path, "\n".join(lines))
    read_guide(path)
    for filename, content in render(root).items():
        write_text(root / "guides" / filename, content)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    select = sub.add_parser("choose")
    select.add_argument("--requested", required=True)
    select.add_argument("--selection", type=Path, required=True)
    prepare = sub.add_parser("prompt")
    prepare.add_argument("topic")
    prepare.add_argument("path", type=Path)
    apply = sub.add_parser("stage")
    apply.add_argument("topic")
    args = parser.parse_args()
    if args.command == "choose":
        print(choose(ROOT, args.requested, args.selection))
    elif args.command == "prompt":
        write_text(args.path, prompt(read_yaml(ROOT / BRIEFS)[args.topic]))
    else:
        encoded = os.environ.get("CODEX_DRAFT", "")
        if not encoded or len(encoded.encode("utf-8")) > 20_000:
            raise SystemExit("Codex output absent or too large")
        try:
            draft = json.loads(encoded)
            path = stage(ROOT, args.topic, draft, datetime.now(SHANGHAI).date())
        except (KeyError, ValueError):
            raise SystemExit("Codex draft did not pass structured validation") from None
        print(f"Staged draft at {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
