"""Build a MkDocs site with only reviewed, published guides."""
import shutil
import subprocess
import sys
import tempfile

from scripts.build_index import DIMENSIONS, render
from scripts.build_resource_index import outputs
from scripts.common import ROOT, write_json, write_text
from scripts.validate_guides import validate_repository


def published_guides(root=ROOT):
    entries, _ = validate_repository(root)
    return [(path, metadata) for path, metadata in entries if metadata["status"] == "published"]


def stage_site(root, destination):
    docs = destination / "docs"
    entries = published_guides(root)
    for path, _ in entries:
        target = docs / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    for name, content in render(root, entries, site=True).items():
        write_text(docs / "guides" / name, content)
    for name, content in outputs(root, site=True).items():
        write_text(docs / "resources" / name, content)
    navigation = "\n".join(f"- [{title}](guides/{slug}.md)" for slug, (title, _) in DIMENSIONS.items())
    message = f"{len(entries)} 篇指南完成审查并进入站点。" if entries else "当前可先查官方文档和资源目录。指南经审核后会进入本站。"
    write_text(docs / "index.md", f"""# 我想解决什么问题

学习新技能、整理数字文件或找到官方说明。使用页面顶部搜索，或从适合你的维度进入。

{message}

- [按主题找指南](guides/index.md)
{navigation}
- [最近更新](guides/recent.md)
- [官方与原始资料](resources/official-resources.md)
- [GitHub 项目资源](resources/awesome-howto-projects.md)
""")
    return len(entries)


def main():
    workspace = ROOT / "out"
    workspace.mkdir(exist_ok=True)
    site = workspace / "site"
    if workspace.is_symlink() or site.is_symlink() or workspace.resolve() != ROOT / "out":
        raise SystemExit("site output must be the repository-generated out directory")
    with tempfile.TemporaryDirectory(dir=workspace, prefix="pages-src-") as temp:
        from pathlib import Path

        directory = Path(temp)
        count = stage_site(ROOT, directory)
        config = {
            "site_name": "Awesome-HowTo", "site_description": "生活、学习、AI 与职场技能",
            "docs_dir": str(directory / "docs"), "site_dir": str(site),
            "theme": {"name": "mkdocs", "locale": "zh_CN", "navigation_depth": 2},
            "plugins": [{"search": {"lang": ["zh", "en"]}}],
            "nav": [{"首页": "index.md"}, {"指南": [{"主题": "guides/index.md"},
                    *[{title: f"guides/{slug}.md"} for slug, (title, _) in DIMENSIONS.items()],
                    {"最近更新": "guides/recent.md"}]},
                    {"资源": [{"官方资料": "resources/official-resources.md"},
                              {"GitHub 项目": "resources/awesome-howto-projects.md"},
                              *[{section.capitalize(): f"resources/{section}-resources.md"}
                                for section in ("life", "learning", "ai", "digital", "work")]]}],
        }
        if count:
            config["nav"].append({"指南条目": [path.relative_to(ROOT).as_posix()
                                               for path, _ in published_guides()]})
        config_path = directory / "mkdocs.yml"
        write_json(config_path, config)
        subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict", "-f", str(config_path)],
                       check=True)
    print(f"Pages site built with {count} reviewed guide(s).")


if __name__ == "__main__":
    main()
