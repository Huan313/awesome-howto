"""Build guide indexes and README counts from reviewed frontmatter."""
import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_resource_index import read_registry
from scripts.common import ROOT, read_yaml, write_text
from scripts.validate_guides import validate_repository

STATUS = {
    "idea": "选题", "needs-research": "待研究", "draft": "草稿", "editorial-review": "编辑审核",
    "expert-review": "待专业审核", "published": "已发布", "needs-update": "待更新", "retired": "已归档",
}
DIMENSIONS = {
    "people": ("按人群找指南", "personas"),
    "age-groups": ("按年龄浏览", "age_groups"),
    "occupations": ("按职业浏览", "occupations"),
    "life-stages": ("按人生阶段浏览", "life_stages"),
    "scenarios": ("按场景浏览", "scenarios"),
    "regions": ("按地区浏览", "region"),
    "difficulty": ("按难度浏览", "difficulty"),
    "time": ("按耗时浏览", "estimated_time"),
    "cost": ("按费用浏览", "cost"),
    "review-status": ("按审核状态浏览", "status"),
}
TIME_LABELS = {"short": "30 分钟以内", "medium": "31–60 分钟", "long": "60 分钟以上", "unknown": "未核定"}
COST_LABELS = {"free": "免费可练习", "depends": "按环境计费或需现有设备", "unknown": "未核定"}


def time_band(description):
    match = re.search(r"(\d+)(?:[–—-](\d+))?\s*(分钟|小时)", description)
    if not match:
        return "long" if "两小时" in description else "unknown"
    minutes = int(match[2] or match[1]) * (60 if match[3] == "小时" else 1)
    return "short" if minutes <= 30 else "medium" if minutes <= 60 else "long"


def cost_band(description):
    if description in {"unknown", "pending"}:
        return "unknown"
    return "free" if "免费" in description and not any(
        word in description for word in ("账号", "账户", "存储", "额外", "许可", "取决")) else "depends"


def render(root, entries=None, *, site=False):
    if entries is None:
        entries, _ = validate_repository(root)
    taxonomy = read_yaml(root / "data/topic-taxonomy.yaml")
    by_persona = read_yaml(root / "data/personas.yaml")
    labels = {
        "category": {key: data["label"] for key, data in taxonomy.items()},
        "personas": by_persona["personas"],
        "age_groups": {key: "未核定" if key == "unknown" else key for key in by_persona["age_groups"]},
        "occupations": read_yaml(root / "data/occupations.yaml"),
        "life_stages": read_yaml(root / "data/life-stages.yaml"),
        "scenarios": read_yaml(root / "data/scenarios.yaml"),
        "region": read_yaml(root / "data/regions.yaml"),
        "difficulty": {"beginner": "入门", "intermediate": "进阶", "advanced": "高级"},
        "estimated_time": TIME_LABELS, "cost": COST_LABELS, "status": STATUS,
    }
    result = {}
    nav = " · ".join([f"[{title}]({name}.md)" for name, (title, _) in DIMENSIONS.items()]
                    + ["[最近更新](recent.md)"])

    def item(path, guide):
        link = path.relative_to(root / "guides").as_posix()
        return f"- [{guide['title']}]({link}) · {STATUS[guide['status']]} · {guide['estimated_time']}"

    def grouped(title, field):
        groups = defaultdict(list)
        for path, guide in entries:
            values = guide[field]
            if field == "estimated_time":
                values = time_band(values)
            if field == "cost":
                values = cost_band(values)
            for value in values if isinstance(values, list) else [values]:
                groups[value].append(item(path, guide))
        lines = [f"# {title}", "", "[主题总览](index.md)" if field != "category" else nav, ""]
        if field == "category":
            lines.extend(["[返回首页](" + ("../index.md" if site else "../README.md") + ")", ""])
        for value, label in labels[field].items():
            lines.extend([f"## {label}", "", *(groups[value] or ["暂无指南。"]), ""])
        return "\n".join(lines)

    result["index.md"] = grouped("按主题找指南", "category")
    for name, (title, field) in DIMENSIONS.items():
        result[f"{name}.md"] = grouped(title, field)
    newest = sorted(entries, key=lambda row: (row[1]["updated_at"], row[0].name), reverse=True)
    result["recent.md"] = "\n".join(["# 最近更新", "", "[主题总览](index.md)", "",
                                      *[f"{item(path, guide)} · {guide['updated_at']}" for path, guide in newest],
                                      *([] if newest else ["暂无指南。"]), ""])
    return result


def expected_files(root):
    entries, _ = validate_repository(root)
    result = {root / "guides" / path: value for path, value in render(root, entries).items()}
    counts = Counter(guide["status"] for _, guide in entries)
    resources = len(read_registry(root))
    en = {"idea": "ideas", "needs-research": "needs research", "draft": "drafts", "editorial-review": "editorial review",
          "expert-review": "expert review", "published": "published", "needs-update": "needs update",
          "retired": "retired"}
    summaries = {
        "README.md": f"**{len(entries)} 篇指南** · " +
        "、".join(f"{count} 篇{STATUS[status]}" for status, count in sorted(counts.items())) +
        f" · **{resources} 条资源**",
        "README_EN.md": f"**{len(entries)} guides** · " +
        ", ".join(f"{count} {en[status]}" for status, count in sorted(counts.items())) +
        f" · **{resources} resources**",
    }
    for name, summary in summaries.items():
        path = root / name
        marker = r"(?s)<!-- begin:counts -->.*?<!-- end:counts -->"
        replacement = f"<!-- begin:counts -->\n{summary}\n<!-- end:counts -->"
        value, found = re.subn(marker, lambda _: replacement, path.read_text(encoding="utf-8"))
        if found != 1:
            raise ValueError(f"expected one generated count block in {name}")
        result[path] = value
    return result


def write_indexes(root=ROOT, *, check=False):
    for path, content in expected_files(root).items():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise ValueError(f"{path.name} is stale; run python -m scripts.build_index")
        else:
            write_text(path, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    write_indexes(args.root, check=args.check)
    print("Guide indexes and README counts verified." if args.check else "Guide indexes and README counts rebuilt.")


if __name__ == "__main__":
    main()
