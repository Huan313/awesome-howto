---
name: evidence-researcher
description: "为 HowTo 的关键论断寻找原始来源并报告适用范围、证据冲突和证据缺口。"
---

# evidence-researcher

## 触发条件

需要为步骤核验原始证据时触发，只有社交线索时先留下待补证据。

## 输入与目标

问题、地区、操作版本、待核事实和研究截止日期。用 `templates/research-record-template.md` 记录。

## 流程与输出

先把主张拆成可核对的陈述。按 `docs/evidence-grading.md` 查官方说明、研究原文、系统综述和专业指南。记录实际文档段落、研究设计、适用地区、发布日期和访问日期。输出 claim–evidence 对照表及冲突、限制、待补证据。

## 失败与安全

无法打开原文时注明可访问范围。引用同一材料的多个页面不算独立证据。避免复制长文本。高风险题先看 `docs/safety-policy.md`，不足时停止生成操作建议。

## 示例与验收

输入 `$evidence-researcher 核对 File History 能否恢复较早版本`。测试样例使用 Microsoft File History 文档，将产品适用范围和版本恢复段落关联到具体主张。

## V2 文件、权限和验收

读 `research/<topic_id>.json`、`data/source-registry.yaml` 和 `schemas/evidence.schema.json`。仅在获准访问的原始材料上定位章节和版本。

依据 `templates/evidence-matrix-template.csv` 填写事实、推断、建议与未知，经人工编辑后写入 `data/evidence/topic-….json`。

回归命令 `python -m unittest discover -s tests -p test_codex_draft.py`。
