# V2 审计基线

2026-11-25 核验了公开仓库、受保护的 main、工作区和 GitHub 账号。基线为 [f1c8ac2](https://github.com/Huan313/awesome-howto/commit/f1c8ac2046c092fa329a12300e60b4c0a3696797)，远端递归树有 127 个条目。本地工作区干净，以 fast-forward 同步后创建 `refactor/awesome-howto-v2`。Windows 10.0.26200、Python 3.12.3、Git 2.47.0、GitHub CLI 2.97.0、桌面内置 Codex CLI 0.171.0-alpha.13.2。

| 基线 | 优先修复 |
| --- | --- |
| 10 篇指南、6 个 Skills、18 个资源 | 补操作、验收和互相独立的读者维度 |
| 人群索引只有 persona，职业复制 persona | 独立词表、逐篇迁移、复查与地区校验 |
| 月报 selection 只有类别，草稿使用预设简报 | 保留完整 topic_id、观测引用和审核证据 |
| 评分把来源类型当作证据强度 | 保留旧分并列做对照，实现独立信号和置信度 |
| 三路 RSS、GitHub 和 HN，社交源多为手工 | 扩充经过核验的官方入口和脱敏导入 |
| Markdown 导航，Pages 查询返回 404 | 实现可本地生成的审核后站点 |
| 周报、月报和 CI 已在基线主分支实跑成功 | 保留既有定时并测试 V2 契约 |

五个 Dependabot PR 开放。#1 jsonschema-specifications、#2 attrs、#3 jsonschema、#4 markdown-it-py、#5 rpds-py。基线查询时 #4 的质量和依赖检查均通过，#3 两类检查失败，#1、#2、#5 质量通过但旧依赖检查失败。详见 [开放 PR](https://github.com/Huan313/awesome-howto/pulls)。

## 实施顺序

先迁移内容契约和原有指南，再扩来源、资源和导航。以真实观测检验评分与月报，从版本控制中匹配已审核证据。无密钥时发布报告 artifact。Pages 构建仅收录已发布指南。所有改动经过独立 Draft PR。
