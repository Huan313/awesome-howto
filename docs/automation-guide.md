# 自动化与本地运行

## 本地运行

需要 Python 3.12。先创建虚拟环境并在自己的终端激活，再执行以下命令。

```console
python -m venv .venv
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m scripts.validate_guides
python -m scripts.build_index --check
python -m scripts.validate_catalog
python -m scripts.check_links --external --strict
python -m scripts.run_research weekly --output out/weekly-research
python -m scripts.run_research monthly --history out/weekly-research --output out/monthly-research
```

修改指南后用 `python -m scripts.build_index` 重建两个索引。链接检查记录 HTTP 404/410 与无法自动验证的项目。默认输出在 `out/`，其中的报告和快照可按需要脱敏后归档。

## 本地 Codex Skills

从本仓库根目录打开 Codex。输入 `$` 后选择 Skill，或直接写出名称和具体任务。旧版 Skill 的内容在[历史归档](../archive/legacy-v1/README.md)。

| 调用 | 用途 |
| --- | --- |
| [`$howto-resource-scout`](../.agents/skills/howto-resource-scout/SKILL.md) | 按任务查找原始资源 |
| [`$howto-resource-auditor`](../.agents/skills/howto-resource-auditor/SKILL.md) | 核对内容、地区、许可和重复 |
| [`$content-bank-scout`](../.agents/skills/content-bank-scout/SKILL.md) | 收集可追溯的选题线索和公开来源 |

## GitHub Actions

| 工作流 | 上海时间与入口 | 产出 |
| --- | --- | --- |
| [Weekly topic scan](../.github/workflows/weekly-topic-scan.yml) | 手动 | 旧版七日研究和候选 artifact |
| [Monthly topic review](../.github/workflows/monthly-topic-review.yml) | 手动 | 旧版三十日专题计划，可复用周报 artifact |
| [Guide quality](../.github/workflows/guide-quality.yml) | push、PR 或手动 | 测试、目录格式、PR 路径、链接和敏感信息检查 |
| [Link check](../.github/workflows/link-check.yml) | 周一 09:12；可手动 | 外链状态报告 |
| [Dependency review](../.github/workflows/dependency-review.yml) | PR 或指定基准手动运行 | 依赖差异和严重性门禁 |

定时器使用 IANA `Asia/Shanghai`。GitHub 可能延迟调度。打开仓库 **Actions**，选中工作流后点 **Run workflow**，选择默认分支。从运行详情页下载报告 artifact，保留期 45 天。周报与月报默认仅上传 artifact，审核者可另行归档；全体公开采集失败会留下诊断并使运行失败。参阅 [GitHub 工作流语法](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)。

公开仓库连续 60 天没有活动时，GitHub 会停用定时工作流。可从 Actions 页重新启用。[管理工作流](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)

## 来源配置

| 来源 | 当前接入 | 适用边界 |
| --- | --- | --- |
| GitHub、Hacker News、RSS | 默认启用 | GitHub Search、HN Firebase API、GitHub Changelog、Python 与 arXiv RSS；窗口与失败见报告 |
| 小红书 | 公开页面人工查阅，或批准的最小化观察导入 | OAuth 首期仅开放 `basic_info`，`read_notes` 在规划中 |
| 抖音 | 默认人工导入；可启用应用授权热点 API | `hotsearch` 需要平台审核与对应应用权限 |
| Reddit | 已批准客户端可用 OAuth adapter | 默认关闭；权限和令牌需由平台批准和维护 |
| X、YouTube、TikTok | 公开、经授权导出的人工记录 | 只导入平台条款允许再发布的聚合观察 |

### 小红书、抖音与其他人工观测

在 `data/source-cache/<platform>/observations.json` 写入 JSON 数组。每项填写 `platform`、公开 HTTPS `url`、自己概括的 `title`、`observed_at`（带时区的 ISO 8601 时间），并可加 `query`、允许发布的 `metrics` 和明确的 `topic_key`。默认方法为 `manual`，授权导出用 `authorized-export`。

先运行 `python -m scripts.ingest_manual_social_sources xiaohongshu INPUT.json --output out/xiaohongshu-observations.json`。人工检查公开性和隐私后，再选取可提交项。采集器移除追踪参数，个别小红书笔记可能因此仍需登录，遇到这种情况可改用公开聚合入口或留作私下线索。API、授权导出与转载分别审批。参阅 [小红书授权范围文档](https://openaccount.xiaohongshu.com/docs/scope)。

### 抖音应用权限

在抖音开放平台创建或选择移动／网站应用，提交「查询热点视频」能力申请，确认获批范围包含 `hotsearch`。通过 GitHub **Settings → Secrets and variables → Actions** 添加 `DOUYIN_CLIENT_KEY`、`DOUYIN_CLIENT_SECRET`，再设变量 `ENABLE_DOUYIN=true`。工作流在任务进程内申请短期 client token，仅调用实时热点词接口。已有短期 client token 的本地测试可临时设 `DOUYIN_CLIENT_TOKEN`。令牌不落盘，运行人员须确认获准再发布的字段与用途。关闭时将变量设为 `false`。参阅 [查询热点视频能力](https://developer.open-douyin.com/capacity-center-page/capacity-detail/7180573594794065975)、[实时热点词接口](https://open.douyin.com/platform/resource/docs/openapi/data-open-service/hot-video-data/get-current-hot-words/) 和 [Client Token](https://open.douyin.com/platform/resource/docs/openapi/account-permission/client-token)。

### Reddit

获得外部 Data API 审批后，设置变量 `ENABLE_REDDIT=true` 与 Secret `REDDIT_ACCESS_TOKEN`。过期令牌由获批应用维护者更新。清单在 [来源注册表](../data/sources.yaml)。参阅 [Reddit 开发者 FAQ](https://developers.reddit.com/docs/guides/faq)。

## 启用或关闭 Codex 草稿

默认无 API Key，公开采集和报告保持运行。想试用草稿时，添加 Repository Secret `OPENAI_API_KEY` 和 Repository Variable `ENABLE_CODEX_AUTOGEN=true`。如选择让 GITHUB_TOKEN 创建 Draft PR，在 **Settings → Actions → General → Workflow permissions** 启用 **Allow GitHub Actions to create and approve pull requests**；仓库工作流只执行创建。部分由机器人创建的 PR 检查可能需要维护者批准运行。参阅 [GitHub Actions 仓库权限设置](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)。

月报成功后，从版本控制中的 [编辑简报](../data/editorial-briefs.yaml) 选择相关类别里的首个低风险选题，或在手动运行时指定已批准的简报。未命中或已存在同题指南会跳过。Codex 使用隔离 job 的已核验摘要与固定输出格式。报告、外部网页、帖子、评论和 PR 标题不进入模型提示。模型步骤在 job 末尾并使用 workspace-write 与 drop-sudo。接收结果的另一 job 使用独立工作区，校验结构、来源、链接、指南状态和密钥后创建草稿 PR。模型启用路径支持从简报生成初稿，联网原文研究由编辑流程另行完成。参阅 [OpenAI Codex Action](https://github.com/openai/codex-action)。

暂停时将变量设为 `false`，并按需删除 Secret。轮换密钥时先关闭开关，替换仓库 Secret，撤销旧密钥，再启用并手动验证。只在仓库 Secret 中填写密钥，避免在 Issues、工作流文件或日志中粘贴。
