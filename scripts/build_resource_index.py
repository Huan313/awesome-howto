"""Generate the public resource catalog from its reviewed registry."""
import argparse
from collections import defaultdict

from scripts.common import ROOT, read_yaml, validate, write_text
from scripts.normalize_topics import public_url

REGISTRY = "resources/resource-registry.yaml"
GROUPS = {
    "life-howto": "生活与日常 HowTo", "cooking-household": "烹饪与家庭",
    "health-safety": "健康素养与安全", "learning-study": "学习与课程",
    "career-work": "职业与工作", "digital-security": "数字技能与安全",
    "ai-everyone": "大众 AI", "ai-engineering": "AI 开发与工程",
    "agent-skills": "Agent Skills 与 Codex", "research-productivity": "研究与生产力",
    "official-documentation": "官方文档",
}
SECTIONS = {
    "life": {"life-howto", "cooking-household", "health-safety"},
    "learning": {"learning-study", "research-productivity"},
    "ai": {"ai-everyone", "ai-engineering", "agent-skills", "official-documentation"},
    "digital": {"digital-security"},
    "work": {"career-work"},
}


def read_registry(root=ROOT):
    rows = read_yaml(root / REGISTRY)
    ids, urls = set(), set()
    for item in rows:
        validate("resource", item)
        public_url(item["url"])
        if item["id"] in ids or item["url"] in urls:
            raise ValueError("duplicate resource ID or URL")
        ids.add(item["id"])
        urls.add(item["url"])
        github = item["github"]
        if (item["kind"] == "github") != bool(github):
            raise ValueError("GitHub entries require GitHub metadata")
        if github and github["license_url"]:
            public_url(github["license_url"])
        if github and (github["license"] == "unknown" or github["license_url"] is None):
            if item["editorial_grade"] != "license-unclear" or item["use_mode"] != "reference-only":
                raise ValueError("license-unclear repositories must be link-only references")
    return rows


def render(title, rows):
    intro = ("下列等级是编辑判断。Stars 和 Forks 表示 GitHub 公开参与度。"
             "官方资料按原文适用范围使用，第三方内容遵守原许可。")
    result = [f"# {title}", "", f"共 {len(rows)} 条。{intro}", ""]
    indexed = defaultdict(list)
    for row in rows:
        indexed[row["category"]].append(row)
    for kind, label in GROUPS.items():
        if not indexed[kind]:
            continue
        result.extend([f"## {label}", ""])
        for row in indexed[kind]:
            detail = ""
            entry = row["github"]
            if entry:
                state = "已归档" if entry["archived"] else "未归档"
                license = f"[{entry['license']}]({entry['license_url']})" if entry["license_url"] else entry["license"]
                detail = (f" Stars {entry['stars']}，Forks {entry['forks']}，"
                          f"push {entry['pushed_at']}，{state}，许可证 {license}。")
            result.extend([
                f"- [{row['title']}]({row['url']}) · {row['editorial_grade']} / {row['use_mode']}。"
                f"{row['description']} 受众为{row['audience']}。{detail} 核验 {row['checked_at']}。",
                f"  可借鉴 {row['borrow']} 限制 {row['limitations']}",
            ])
        result.append("")
    return "\n".join(result)


def outputs(root=ROOT, *, site=False):
    rows = read_registry(root)
    out = {
        "awesome-howto-projects.md": render("GitHub HowTo 项目资源", [row for row in rows if row["github"]]),
    }
    if site or not (root / "data/curation-runs/v2.1.1/manifest.json").is_file():
        out["official-resources.md"] = render("官方与原始资料", [row for row in rows if not row["github"]])
    for name, groups in SECTIONS.items():
        out[f"{name}-resources.md"] = render(f"{name.title()} 资源", [row for row in rows if row["category"] in groups])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in outputs().items():
        path = ROOT / "resources" / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"stale resource index: {name}")
        else:
            write_text(path, content)
    print(f"{len(read_registry())} resources validated.")


if __name__ == "__main__":
    main()
