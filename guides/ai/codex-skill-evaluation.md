---
id: "howto-codex-skill-evaluation"
title: "怎样用六个小样例检查 Codex Skill 是否正确触发？"
category: "ai"
subcategory: "agent-skills"
personas: ["software-engineer","researcher"]
age_groups: ["unknown"]
occupations: ["software-developer"]
life_stages: ["unknown"]
scenarios: ["evaluate-ai"]
region: "global"
difficulty: "beginner"
estimated_time: "40–60 分钟"
cost: "环境及模型用量按实际计"
prerequisites: ["准备受控项目中的 Skill 和不含真实资料的测试文件。执行前记录版本、授权范围和网络条件。"]
risk_level: "low"
status: "draft"
evidence_level: "A"
content_type: "howto"
created_at: "2026-11-25"
updated_at: "2026-11-25"
last_verified_at: "2026-11-25"
review_due: "2027-02-25"
version: "0.1"
execution_status: "pending"
sources: ["https://developers.openai.com/blog/eval-skills","https://learn.chatgpt.com/docs/build-skills"]
claim_evidence: [{"claim_id":"codex-skill-evaluation-1","claim_text":"OpenAI 建议用可复跑情景、期望行为和评分标准评估 Skill。","claim_type":"fact","supporting_source_ids":["openai-eval-skills"],"support_level":"direct","source_location":"End-to-end evals / examples","applicable_region":"global","applicable_version":"发布文档版本","limitations":"结论限于所列文档范围及版本，执行及地区限制见正文。","reviewer_status":"editorial-checked"},{"claim_id":"codex-skill-evaluation-2","claim_text":"项目技能通过描述与 SKILL.md 表达用途和执行流程。","claim_type":"fact","supporting_source_ids":["openai-skills"],"support_level":"direct","source_location":"Create a skill / Run a skill","applicable_region":"global","applicable_version":"当前 Codex 文档","limitations":"结论限于所列文档范围及版本，执行及地区限制见正文。","reviewer_status":"editorial-checked"}]
---

# 怎样用六个小样例检查 Codex Skill 是否正确触发？

对两个版本使用同样用例排序和评分标准，保留失败样例。 本稿记录了资料核对，操作待实测。

## 适用人群

准备受控项目中的 Skill 和不含真实资料的测试文件。执行前记录版本、授权范围和网络条件。

## 前置条件与不适用情况

结果因运行器、版本和上下文而变。测试材料禁止含真实凭据，避免使用会修改外部资源的用例。

## 准备、耗时与费用

表格含 `输入｜应触发｜预期文件｜禁止副作用｜证据`。从两条正例、两条负例、两条边界用例开始。 预计 40–60 分钟，环境及模型用量按实际计。

## 操作步骤与验收

1. 写正例「用本 Skill 检查虚构 CSV」，负例「将示例翻译成中文」，边界例「文件不存在」。每例定义 observable 结果。 **验收**　每个用例都能判定触发正确与否，明确输出路径和失败表现。
2. 在新对话分别执行，用临时项目检查实际创建或修改的文件。记录 Codex 版本和权限。 **验收**　日志与 diff 可定位；只在预期目录出现测试输出。
3. 改动 description 后同条件重跑。比较触发、内容和安全边界各项通过率。 **验收**　对两个版本使用同样用例排序和评分标准，保留失败样例。

## 常见错误与排查

只有一次成功时增补同义表达和无关请求。无法读取预期文件时核对项目技能发现路径及运行权限。

## 风险与限制

结果因运行器、版本和上下文而变。测试材料禁止含真实凭据，避免使用会修改外部资源的用例。 关键条件无法确认时停止并保留原始数据。

## 最简行动清单

定义六个样例 → 固定环境 → 比对输出和副作用 → 复测。

## 参考来源

- OpenAI 建议用可复跑情景、期望行为和评分标准评估 Skill。 定位 End-to-end evals / examples。[OpenAI · Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)（2026-11-25 核对）。
- 项目技能通过描述与 SKILL.md 表达用途和执行流程。 定位 Create a skill / Run a skill。[OpenAI · Build skills](https://learn.chatgpt.com/docs/build-skills)（2026-11-25 核对）。

## 核验与版本

2026-11-25 核对列出的文档范围。v0.1，实际设备或任务演练待核验。下次复查 2027-02-25。
