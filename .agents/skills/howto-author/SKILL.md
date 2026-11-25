---
name: howto-author
description: "把已核验的研究记录写成分步中文指南，补齐先决条件、验收和 frontmatter。"
---

# howto-author

## 触发条件

有原始证据包且需要可操作步骤时使用。证据缺失只写研究缺口。

## 输入与目标

证据矩阵、目标读者、地区、版本、风险等级及相似指南。

## 流程与输出

先比对 `guides/index.md`。按 `templates/howto-template.md` 把一个任务写清。每一步都有读者可观察的结果，用 `data/` 词表填写标签。列出费用、时间、排查和停止条件。引用靠近主张；参考区包含元数据的每个链接。用 `python -m scripts.validate_guides` 和 `python -m scripts.build_index` 检查结果。

## 失败与安全

没有足够来源时只交候选或研究记录。把虚构示例标清，未经实测不可声称实测，未获独立审核按 draft 或 review-required 标记。

## 示例与验收

输入 `$howto-author 根据已核验的备份研究记录更新手机备份草稿`。只交一份 `guides/life/` 草稿，新增步骤需可验收；当前仓库运行 `python -m unittest discover -s tests -p test_guide_schema.py`。

## V2 文件、权限和验收

以 `templates/howto-template.md`、`schemas/guide.schema.json` 和审核证据包为输入。更新既有稿须保留原 ID。

写入 `guides/<category>/`，每一步有输入及验收。未经演练标记 pending。运行 `python -m scripts.build_index` 和 `python -m scripts.validate_guides`。

回归命令 `python -m unittest discover -s tests -p test_guide_schema.py`。
