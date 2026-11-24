---
name: repo-maintainer
description: "检查仓库结构、索引、重复稿、链接和发布准备，整理 PR 与维护记录。"
---

# repo-maintainer

## 输入与目标

当前 diff、指南索引、质量命令、适用许可证和 PR 范围。

## 流程与输出

运行 `python -m unittest discover -s tests`、`python -m scripts.validate_guides`、`python -m scripts.build_index --check` 和 `python -m scripts.check_links`。检查来源、报告状态、重复主题和许可证。按 `docs/publishing-guide.md` 输出 PR 摘要、验证记录、待补项和 changelog 候选。

## 失败与安全

对失败记录具体验收项，链接失效时先核对等价性。检查可能泄密的文件，在发布前消除发现。按授权进行 Git 操作，后续 PR 由人工审核。

## 示例与验收

输入 `$repo-maintainer 检查这次新增文本并写 PR 摘要`。故意省略重建索引时，`python -m scripts.build_index --check` 应报告索引过期。
