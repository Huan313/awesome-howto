# Awesome-HowTo 首版发布报告

核验日期为 2026-11-25。仓库已公开，默认分支为 `main`。已通过 GitHub API 核对远端提交，并确认公开页面返回 HTTP 200、README 正常渲染。首次提交为 `2a515b27e321aeee68294d0fae1ea465f9980c84`。[公开仓库](https://github.com/Huan313/awesome-howto) · [首次提交](https://github.com/Huan313/awesome-howto/commit/2a515b27e321aeee68294d0fae1ea465f9980c84)

## 内容与目录

| 目录 | 首版内容 |
| --- | --- |
| `guides/` | 生活、学习、AI、数字技能、职场成长。9 篇草稿、1 篇待专业审核。含主题与人群索引 |
| `resources/` | 18 个经 GitHub API 核验的项目及五类资源入口 |
| `docs/`、`templates/` | 证据等级、研究方法、隐私与安全、贡献流程和编辑模板 |
| `data/`、`schemas/` | 人群、年龄、职业和场景词表，来源注册表，观察、选题和指南校验格式 |
| `scripts/`、`tests/` | 公开采集、去重评分、周月报告、指南和链接检查，以及相关回归测试 |
| `.agents/skills/` | 六个项目级 Codex Skills，每个含最小用例及验收条件 |
| `.github/` | 五个工作流、Dependabot、Issue 表单和 PR 模板 |

指南内容由公开来源整理，实际设备或任务演练待独立复核。防钓鱼指南处于 `review-required` 状态。原创代码采用 [MIT](../LICENSE)，原创文字采用 [CC BY 4.0](../LICENSE-CONTENT)。

## 本地检查

Python 3.12.3 虚拟环境安装固定依赖，`pip check` 和 15 项单元测试通过。10 篇指南、6 个 Skills、3 套 JSON Schema、Markdown 结构、内部链接和索引一致性通过。Actionlint 校验全部工作流。Gitleaks 检查首次暂存差异，无泄漏发现；Git diff 仅含项目交付文件。

首个提交的外链检查覆盖 66 条链接，脚本确认 61 条，0 条判定失效。其余 5 条因访问限制或连接问题由官方页面信息另行核对。已修复一条失效引用。复测公开采集时，Python 基金会旧博客源连线失败，已改用可访问的 Python Insider 官方 RSS。

## GitHub Actions 验证

| 工作流 | 触发 | 云端核验 |
| --- | --- | --- |
| Weekly topic scan | 周一 09:00，亦可手动 | 生成 20 项候选和来源状态 artifact。[周报运行](https://github.com/Huan313/awesome-howto/actions/runs/45444616442) |
| Monthly topic review | 每月 1 日 09:00，亦可手动 | 生成 5 个研究专题并复用 1 份周报快照。AI 草稿与 PR job 均跳过。[月报运行](https://github.com/Huan313/awesome-howto/actions/runs/45444756148) |
| Guide quality | Push、PR 或手动 | 测试、Schema、索引、Markdown、工作流语法、外链和 Gitleaks 通过。[质量运行](https://github.com/Huan313/awesome-howto/actions/runs/45444516959) |
| Link check | 周一 09:12，亦可手动 | 云端外链检查通过。[外链运行](https://github.com/Huan313/awesome-howto/actions/runs/45444623895) |
| Dependency review | PR，亦可指定基准手动运行 | 初次因依赖图未启用而返回 403。启用 Dependabot 提醒与依赖图后，手动和实际 Dependabot PR 重跑均通过。[手动依赖检查](https://github.com/Huan313/awesome-howto/actions/runs/45444629550) · [PR 依赖检查](https://github.com/Huan313/awesome-howto/actions/runs/45444742656) |

时区为 `Asia/Shanghai`。周报、月报和外链的云端结果来自手动触发，已核对定时配置。报告生成后上传 artifact，默认保留 45 天。Dependabot 版本更新、提醒、密钥扫描、推送保护与私密漏洞报告已核验启用。初始化结束后的内容变更走 PR，经质量及依赖检查和人工审核后合并。

## 数据源与授权

GitHub Search、Hacker News、GitHub Changelog、Python Insider 和 arXiv 已按公开方式运行。小红书目前使用公开页面的人工研究与脱敏观察导入，`read_notes` 仍列为规划。抖音默认通过人工记录，官方热点词适配器已经过模拟响应测试，真实调用等待应用通过 `hotsearch` 审批。Reddit OAuth 适配器等待获批应用凭证。X、YouTube 与 TikTok 提供经人工确认的合规观测导入。

仓库当前没有 `OPENAI_API_KEY`，`ENABLE_CODEX_AUTOGEN` 未设置。默认无密钥管线已经过两次云端手动运行验证。可选 Codex 草稿路径通过了本地结构化输出与草稿约束测试，真实模型调用和创建草稿 PR 等待显式启用。模型使用版本控制中的已审编辑简报，原始材料的联网核查在独立编辑环节进行。[来源与功能配置](automation-guide.md)

## 维护与新增指南

在仓库根目录打开 Codex，输入 `$trend-scout`、`$persona-painpoint-researcher`、`$evidence-researcher`、`$howto-author`、`$fact-safety-auditor` 或 `$repo-maintainer` 并给出具体任务。手动运行报告可在 Actions 选对应工作流和 `main` 分支，再点击 **Run workflow**。启用和关闭可选 AI 的步骤在 [自动化指南](automation-guide.md#启用或关闭-codex-草稿)。

新增 HowTo 时先去重、写研究记录、按模板起草，重建索引并打开 PR。优先为现有草稿安排独立核验，再补小红书的合规需求样本和抖音真实权限验收。[贡献步骤](../CONTRIBUTING.md) · [下一批 10 个推荐主题](../data/topic-queue/backlog.md)
