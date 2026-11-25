---
name: howto-auditor
description: 检查来源、事实、实操、版权和可读性，对风险与发布状态给出可复核结果。
---

# howto-auditor

## 输入与目标

指南、原始链接、执行记录、本地图片和审核目标。

## 流程与输出

复核来源时效、设备版本、步骤、证据、版权、隐私、语言与图文一致。输出 PASS、NEEDS_REVISION、NEEDS_HUMAN_REVIEW 或 REJECT，并列出证据和下一次核验条件。

## 失败与安全

高风险须人工复核。没有端到端记录时跳过 DEVICE_TESTED 标签。审批和发布是不同的操作。

## 示例与验收

PDF 模型样例。合成文件能定位原文但未实际调用 Kimi，应保留 NEEDS_HUMAN_REVIEW，要求对照指定页码和不存在的字段。
