# Awesome-HowTo V2 交付记录

2026-11-25。V2 在 `refactor/awesome-howto-v2` 实施，以受保护的 main `f1c8ac2` 为基线。主分支基线有 10 篇指南、6 个 Skills、18 项资源。完整环境与初始 PR 状态见 [审计报告](v2-audit-report.md)。

## 架构与主要修复

公开来源发现后，拆分活动、需求与可比较趋势，聚类并生成研究任务。编辑将实际 topic_id、需求 URL、来源和主张矩阵绑定。审核后可用 Codex 选排已有步骤，脚本渲染可复核草稿。质量门禁检查结构、地区、证据与风险，再由人工审核 PR。页面仅使用已发布内容。维护者根据复查日期、失效来源和问题反馈更新。

五个一级分类扩充独立子类。身份、年龄、职业、人生阶段、场景、地区是独立维度，人群和年龄未核定时使用 unknown。增加难度、耗时、费用、最近更新和审核状态导航，中英文首页由数据生成计数。FTC 相关稿已按美国适用范围标注。

## 指南与资源

22 篇指南，20 篇草稿、2 篇待专业审核。生活 4 篇、学习 5 篇、AI 6 篇、数字技能 4 篇、职场成长 3 篇。对应占比为 18.2%、22.7%、27.3%、18.2%、13.6%。内容与出处已编辑核对，真实设备和任务演练待验证。

| 变更 | 指南 | 状态 |
| --- | --- | --- |
| 新增 | [怎样用 AI 起草成人培训练习并核验答案？](../guides/ai/ai-adult-lesson-plan.md) | draft |
| 新增 | [怎样用虚构记录测试 AI 会议纪要的准确性？](../guides/ai/ai-meeting-notes.md) | draft |
| 升级 | [怎样用 AI 设计一个可回退的重复工作提醒？](../guides/ai/automate-list-reminder.md) | draft |
| 升级 | [怎样用 Codex 检查并公开发布一个 GitHub 项目？](../guides/ai/codex-github-release.md) | draft |
| 新增 | [怎样用六个小样例检查 Codex Skill 是否正确触发？](../guides/ai/codex-skill-evaluation.md) | draft |
| 升级 | [怎样核验 AI 给出的论文和官方引用？](../guides/ai/verify-ai-citations.md) | draft |
| 新增 | [怎样在换机时验证 Google Authenticator 仍能登录？](../guides/digital/authenticator-phone-transfer.md) | expert-review |
| 升级 | [怎样让跨设备文件只有一个工作版本？](../guides/digital/cross-device-file-management.md) | draft |
| 新增 | [怎样用 Time Machine 验证 Mac 文件能恢复？](../guides/digital/mac-time-machine-restore.md) | draft |
| 新增 | [怎样安全共享一个 OneDrive 测试文件并验证撤权？](../guides/digital/onedrive-share-revoke.md) | draft |
| 新增 | [怎样用一张表解释两篇论文结论为何不同？](../guides/learning/compare-two-studies.md) | draft |
| 新增 | [怎样用一个两小时小项目验收新软件技能？](../guides/learning/learn-software-project.md) | draft |
| 升级 | [怎样读一篇论文，并判断结论能支持什么？](../guides/learning/read-research-paper.md) | draft |
| 升级 | [怎样用主动回忆和间隔复习学一项新技能？](../guides/learning/retrieval-practice.md) | draft |
| 新增 | [怎样合并 Zotero 重复条目并核验原有引文？](../guides/learning/zotero-merge-duplicates.md) | draft |
| 新增 | [更换 Android 手机前，怎样确认数据能恢复？](../guides/life/android-device-transfer.md) | draft |
| 升级 | [怎样给手机和电脑做一份能恢复的备份？](../guides/life/device-backup-restore.md) | draft |
| 新增 | [怎样用一张家庭恢复地图分工并恢复测试文件？](../guides/life/household-restore-map.md) | draft |
| 升级 | [收到可疑消息后，怎样核对账号通知的真伪？](../guides/life/phishing-message-check.md) | expert-review |
| 升级 | [怎样比较几门付费课程的内容和总投入？](../guides/work/compare-paid-courses.md) | draft |
| 新增 | [怎样用三段可核对经历准备结构化面试？](../guides/work/structured-interview-practice.md) | draft |
| 升级 | [怎样写一份让同事知道下一步的工作汇报？](../guides/work/write-project-status-update.md) | draft |

资源 53 条，含 25 个 GitHub 项目和 28 条官方／原始资料，比 V1 增加 35 条。2026-11-25 核验仓库 Stars、Forks、push、归档和 LICENSE；许可证不明确的项目仅链接。新增学习课程、基础数字技能、研究软件、家庭与消费及职业入口。[GitHub 资源](../resources/awesome-howto-projects.md) · [官方与原始资料](../resources/official-resources.md)

## 研究、来源与 Skills

V1 的启发式基线随每个选题输出。V2 分开需求、同指标趋势、人群、证据、可执行性、空白和风险；样本、域名、日期、覆盖率与置信度可复算。官方公告或社交热度不会单独增加解决方案证据。默认报告日期窗口与周一／每月一日 09:00 上海时间保持一致，输出 Markdown、完整 selection JSON、当前／历史引用与研究包 artifact。长期归档可由维护者提取脱敏摘要创建 PR。

GitHub、HN、RSS 已实跑，新增 NIST Feed。本地无密钥试跑记录一项匿名 GitHub 查询 403。首次云端月报记录五项匿名 GitHub 查询限流，报告仍完成。工作流随后改用 GitHub 自动签发的只读短期令牌，局部失败仍逐源记录。小红书 CSV/JSON 已有模板、URL 和指标校验，等待真实合规样本。抖音具备模拟响应验收，实接需要 hotsearch 审批。Reddit 缺获批 Token 时跳过。其他站点用官方资料或脱敏记录。[来源矩阵](source-coverage-matrix.md) · [来源与 Secrets 设置](automation-guide.md)

升级原六个 Skills，新增 `topic-to-howto-pipeline` 和 `resource-curator`。各有适用条件、输入、输出、权限、失败条件与验收。可选模型模式需要 `OPENAI_API_KEY` 和 `ENABLE_CODEX_AUTOGEN=true`，按实际审核证据最多生成三篇可审阅草稿。实测覆盖无密钥路径及合成证据包；真实模型与草稿 PR 作业等待授权。

## 站点、验证和发布状态

MkDocs 本地 strict 构建通过并产生搜索索引。现有指南仍待审核，站点生成官方资料、资源目录和导航。GitHub Pages 设置仍待启用。[站点设置](pages-guide.md)

本地已运行 Python 单测（24 项）、指南 Schema、指南及资源索引、Actionlint、MkDocs 与实采周月报告。无密钥周报选出 17 项，月报选出 5 项并复用上一周报快照。内部链接零失败。外链脚本覆盖 104 个 URL，91 个成功，13 个因访问限制或连接问题未能自动确认，未判定失效链接。49 条来源登记的首次扫描中，35 条由脚本确认，14 条因网络或访问限制未自动确认。面试指南后续改用公开可访问的 MIT 职业中心原文。暂存差异经 Gitleaks 扫描无泄漏发现。

基线开放 Dependabot #1–#5 涉及 jsonschema-specifications、attrs、jsonschema、markdown-it-py 和 rpds-py，PR 保持待维护者处理。#3 日志确认单独更新 jsonschema 时与基线的 rpds-py 锁定版本冲突。应先联动检查这两个包的兼容性。V2 另行验证基线锁定依赖和独立的站点依赖。[依赖 PR](https://github.com/Huan313/awesome-howto/pulls)

## GitHub 交付

实施提交 `b7b2c36f491fb4ad042046e520fa8abf52d6dc37` 已推送至 `refactor/awesome-howto-v2`。分支上的 V2 周度／月度均已手动实跑。周报产出 20 项，月报产出 5 项并复用 1 份 V2 周报，有 0 项获编辑批准可写。Codex 和生成草稿 PR 作业均按无授权状态跳过。质量和依赖检查通过。

[Draft PR #6](https://github.com/Huan313/awesome-howto/pull/6) · [质量检查](https://github.com/Huan313/awesome-howto/actions/runs/45526312487) · [依赖检查](https://github.com/Huan313/awesome-howto/actions/runs/45526312512) · [云端周报](https://github.com/Huan313/awesome-howto/actions/runs/45526350119) · [云端月报](https://github.com/Huan313/awesome-howto/actions/runs/45526624553)

限流修复提交 `3fe834c46bbb59e4596629e761cd13fe09915c4a` 在同一分支复跑。周报 20 项，月报 5 项，复跑两次的 GitHub Search 均为 9/9，月报 5 个专题均含历史引用。质量及依赖检查已通过。[复跑周报](https://github.com/Huan313/awesome-howto/actions/runs/45527070647) · [复跑月报](https://github.com/Huan313/awesome-howto/actions/runs/45527064966) · [修复后 PR 质量检查](https://github.com/Huan313/awesome-howto/actions/runs/45527073078)

本地复核命令为 `python -m unittest discover -s tests`、`python -m scripts.validate_guides`、`python -m scripts.build_index --check`、`python -m scripts.build_resource_index --check`、`python -m scripts.check_links --external --strict` 和 `python -m scripts.build_site`。工作流语法用 Actionlint 验证，提交前用 Gitleaks 扫描暂存差异。

定时任务将在 V2 进入默认分支后采用新实现。Pages 需要维护者启用。现有指南都需要继续核验，抖音、Reddit 和可选 Codex 路径分别等待审批或密钥。
