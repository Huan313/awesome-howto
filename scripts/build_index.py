"""Build deterministic guide indexes by topic and audience."""
import argparse
from collections import defaultdict
from pathlib import Path

from scripts.common import ROOT, read_yaml, write_text
from scripts.validate_guides import validate_repository

STATUS = {"draft": "草稿", "review-required": "待专业审核", "stable": "稳定",
          "published": "已发布", "retired": "已归档"}


def render(root):
    entries, _ = validate_repository(root)
    taxonomy = read_yaml(root / "data/topic-taxonomy.yaml")
    personas = read_yaml(root / "data/personas.yaml")["personas"]
    grouped, by_persona = defaultdict(list), defaultdict(list)
    for path, guide in entries:
        link = path.relative_to(root / "guides").as_posix()
        entry = f"- [{guide['title']}]({link}) · {STATUS[guide['status']]} · {guide['estimated_time']}"
        grouped[guide["category"]].append(entry)
        for persona in guide["personas"]:
            by_persona[persona].append(entry)
    topic = ["# 按主题找指南", "", "[按人群浏览](people.md) · [返回首页](../README.md)", ""]
    for category, metadata in taxonomy.items():
        topic.extend([f"## {metadata['label']}", "", *grouped[category], ""])
    people = ["# 按人群找指南", "", "[按主题浏览](index.md) · [人群词表](../docs/persona-taxonomy.md)", ""]
    for persona, name in personas.items():
        if by_persona[persona]:
            people.extend([f"## {name}", "", *by_persona[persona], ""])
    return {"index.md": "\n".join(topic), "people.md": "\n".join(people)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in render(args.root).items():
        path = args.root / "guides" / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"{name} is stale. Run python -m scripts.build_index")
        else:
            write_text(path, content)
    print("Guide indexes verified." if args.check else "Guide indexes rebuilt.")


if __name__ == "__main__":
    main()
