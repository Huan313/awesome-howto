# Awesome-HowTo V3.1 执行报告

2026-11-25。继续使用原仓库与 [PR #8](https://github.com/Huan313/awesome-howto/pull/8) 的 `codex/awesome-howto-v3-foundation` 分支。本地基线备份为 `backup/v3-1-before-focus-20261125`。PR 页记录最新提交、远端检查及合并状态。

## 公开仓库

| 文件范围 | 交付 |
| --- | --- |
| 首页、AGENTS、贡献与变更说明 | 面向年轻人的数字生活、AI 与效率、生活与成长指南，按问题浏览，采用一题三证与三档解法。 |
| [专题指南](../howto/README.md)与 [references](../references/recommended-projects.md) | 四篇新指南。按项目、官方与政策入口保留 24 条已有资源，并承接已有语言、地区和核验标注。 |
| [历史目录](../archive/legacy-v3-0/README.md) | 按原文件归档 V3.0 的 60 条资源、集合、人群入口、旧模板与三项旧 Skill。保留 V1 指南、许可证、历史研究数据和既有工作流。 |
| 模板、政策与选题字段 | HowTo、研究、实操核验及社交转写模板，配套更新编辑、证据、安全和自动化说明。 |
| [.agents/skills](../.agents/skills/topic-scout/SKILL.md) | `topic-scout`、`howto-writer`、`howto-auditor`。分别用微信换机需求、Windows 存储保守写法和 PDF 合成样本作案例。 |
| validators 与测试 | 验证新专题和原条目迁移。拒绝版本控制内的 `local-studio/` 路径，新增回归测试。 |

[迁移审计](V3_1_FOCUS_RESET_AUDIT.md)记录分支基线和兼容性。旧周报和月报继续支持手动触发。

## 本地交付与核验范围

本地生产中心完成 15 个候选选题、三个完整审稿包和五种布局示例。已找到并核对用户提供的猫咪母版。离线命令支持新建内容、校验、渲染、预览导出和发布状态门禁。各篇配有七张图文卡片及一张视频封面，共 24 张 PNG 和同数可编辑 SVG。三篇均为 `NEEDS_HUMAN_REVIEW`，发布就绪为 0。

- Windows 存储清理核对微软官方资料，验证 Windows 版本和磁盘空间读取。真实清理及前后对比待验证。
- 微信聊天记录核对终端厂商资料和一条公开需求。当前微信客户端菜单、备份覆盖和恢复待用合成聊天实测。
- AI 读 PDF 核对工具资料，用自制 PDF 验证页序、证据和缺失项。模型问答待真实运行。
- 私人素材保持在本地忽略范围。社交内容的审稿、必要实操和平台裁切需维护者确认。

## 工程检查

本地 21 项单元测试通过。指南、Schema、三项 Skill、索引和目录检查通过。Markdown 内链失败 0。网络链接检查确认 131 个可访问、7 个待人工核验、0 个确认失效。待核验项出现 HTTP 403、访问受限或请求超时等情况。Actionlint 和提交差异检查随 PR 验证。
