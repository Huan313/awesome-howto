# 自动化与本地运行

## 本地运行

需要 Python 3.12。先创建虚拟环境并在自己的终端激活，再执行以下命令。

```console
python -m venv .venv
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m scripts.validate_guides
python -m scripts.build_index --check
python -m scripts.check_links --external --strict
python -m scripts.run_research weekly --output out/weekly-research
python -m scripts.run_research monthly --history out/weekly-research --output out/monthly-research
```

修改指南后用 `python -m scripts.build_index` 重建两个索引。链接检查记录 HTTP 404/410 与无法自动验证的项目。默认输出在 `out/`，其中的报告和快照可按需要脱敏后归档。

## 本地 Codex Skills

从本仓库根目录打开 Codex 桌面项目或 Codex CLI。输入 `$` 后选择 Skill，或直接写出名称加任务。CLI 批处理前，先在你的终端用 `codex --version` 和 `codex login status` 核对安装与认证；例如 `codex exec '$repo-maintainer 检查当前变更'`。普通终端找不到 Codex 时仍可在 Desktop 中使用项目级 Skill。参阅 [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) 和 [Skill 构建文档](https://learn.chatgpt.com/docs/build-skills)。

| 调用 | 用途 |
| --- | --- |
| [`$trend-scout`](../.agents/skills/trend-scout/SKILL.md) | 扫描七天或三十天候选话题 |
| [`$persona-painpoint-researcher`](../.agents/skills/persona-painpoint-researcher/SKILL.md) | 核验某类读者在实际场景中的痛点 |
| [`$evidence-researcher`](../.agents/skills/evidence-researcher/SKILL.md) | 为核心主张核对原始证据 |
| [`$howto-author`](../.agents/skills/howto-author/SKILL.md) | 从证据矩阵写出可验收步骤 |
| [`$fact-safety-auditor`](../.agents/skills/fact-safety-auditor/SKILL.md) | 检查事实、安全、版权和隐私 |
| [`$repo-maintainer`](../.agents/skills/repo-maintainer/SKILL.md) | 复核测试、索引、变更和 PR |
| [`$topic-to-howto-pipeline`](../.agents/skills/topic-to-howto-pipeline/SKILL.md) | 从当期选题与证据创建草稿 |
| [`$resource-curator`](../.agents/skills/resource-curator/SKILL.md) | 核对资源、许可和受众 |

## GitHub Actions

| 工作流 | 上海时间与入口 | 产出 |
| --- | --- | --- |
| [Weekly topic scan](../.github/workflows/weekly-topic-scan.yml) | 周一 09:00；可手动 | 七日候选、来源状态、队列与结构化观测 |
| [Monthly topic review](../.github/workflows/monthly-topic-review.yml) | 每月 1 日 09:00；可手动 | 三十日专题计划；复用可取得的已成功周报快照 |
| [Guide quality](../.github/workflows/guide-quality.yml) | push、PR 或手动 | 测试、Schema、Markdown、索引、链接以及 Gitleaks |
| [Link check](../.github/workflows/link-check.yml) | 周一 09:12；可手动 | 外链状态报告 |
| [Dependency review](../.github/workflows/dependency-review.yml) | PR 或指定基准手动运行 | 依赖差异和严重性门禁 |

定时器使用 IANA `Asia/Shanghai`。GitHub 可能延迟调度。打开仓库 **Actions**，选中工作流后点 **Run workflow**，选择默认分支。从运行详情页下载报告 artifact，保留期 45 天。周报与月报默认仅上传 artifact，审核者可另行归档；全体公开采集失败会留下诊断并使运行失败。Actions 向 GitHub Search 使用其自动签发的只读短期令牌，本地无配置时用匿名公开搜索。参阅 [GitHub 工作流语法](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)。

公开仓库连续 60 天没有活动时，GitHub 会停用定时工作流。可从 Actions 页重新启用。[管理工作流](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)

## 来源配置

| 来源 | 当前接入 | 适用边界 |
| --- | --- | --- |
| GitHub、Hacker News、RSS | 默认启用 | GitHub Search、HN Firebase API、GitHub Changelog、Python、NIST 与 arXiv RSS；窗口与失败见报告 |
| 小红书 | 公开页面人工查阅，或批准的最小化观察导入 | OAuth 首期仅开放 `basic_info`，`read_notes` 在规划中 |
| 抖音 | 默认人工导入；可启用应用授权热点 API | `hotsearch` 需要平台审核与对应应用权限 |
| Reddit | 已批准客户端可用 OAuth adapter | 默认关闭；权限和令牌需由平台批准和维护 |
| X、YouTube、TikTok | 公开、经授权导出的人工记录 | 只导入平台条款允许再发布的聚合观察 |

### 小红书、抖音与其他人工观测

在 `data/source-cache/<platform>/observations.json` 写入 JSON 数组。每项填写 `platform`、公开 HTTPS `url`、自己概括的 `title`、`observed_at`（带时区的 ISO 8601 时间），并可加 `query`、允许发布的 `metrics` 和明确的 `topic_key`。默认方法为 `manual`，授权导出用 `authorized-export`。

先运行 `python -m scripts.ingest_manual_social_sources xiaohongshu INPUT.json --output out/xiaohongshu-observations.json`。人工检查公开性和隐私后，再选取可提交项。采集器移除追踪参数，个别小红书笔记可能因此仍需登录，遇到这种情况可改用公开聚合入口或留作私下线索。API、授权导出与转载分别审批。参阅 [小红书授权范围文档](https://openaccount.xiaohongshu.com/docs/scope)。

小红书还支持 [CSV](../templates/social-observation-template.csv) 和 [JSON](../templates/social-observation-template.json)。执行 `python -m scripts.ingest_social_csv xiaohongshu INPUT.csv --output out/xiaohongshu-observations.json`，核对 URL、指标单位和样本限制。标记 example 的条目跳过。分支手动试跑使用公开源。

### 抖音应用权限

在抖音开放平台创建或选择移动／网站应用，提交「查询热点视频」能力申请，确认获批范围包含 `hotsearch`。通过 GitHub **Settings → Secrets and variables → Actions** 添加 `DOUYIN_CLIENT_KEY`、`DOUYIN_CLIENT_SECRET`，再设变量 `ENABLE_DOUYIN=true`。工作流在任务进程内申请短期 client token，仅调用实时热点词接口。已有短期 client token 的本地测试可临时设 `DOUYIN_CLIENT_TOKEN`。令牌不落盘，运行人员须确认获准再发布的字段与用途。关闭时将变量设为 `false`。参阅 [查询热点视频能力](https://developer.open-douyin.com/capacity-center-page/capacity-detail/7180573594794065975)、[实时热点词接口](https://open.douyin.com/platform/resource/docs/openapi/data-open-service/hot-video-data/get-current-hot-words/) 和 [Client Token](https://open.douyin.com/platform/resource/docs/openapi/account-permission/client-token)。

### Reddit

获得外部 Data API 审批后，设置变量 `ENABLE_REDDIT=true` 与 Secret `REDDIT_ACCESS_TOKEN`。过期令牌由获批应用维护者更新。清单在 [来源注册表](../data/sources.yaml)。参阅 [Reddit 开发者 FAQ](https://developers.reddit.com/docs/guides/faq)。

## 启用或关闭 Codex 草稿

默认无 API Key，公开采集和报告保持运行。想试用草稿时，添加 Repository Secret `OPENAI_API_KEY` 和 Repository Variable `ENABLE_CODEX_AUTOGEN=true`。如选择让 GITHUB_TOKEN 创建 Draft PR，在 **Settings → Actions → General → Workflow permissions** 启用 **Allow GitHub Actions to create and approve pull requests**；仓库工作流只执行创建。部分由机器人创建的 PR 检查可能需要维护者批准运行。参阅 [GitHub Actions 仓库权限设置](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)。

月报以 selection.json 中的具体 topic_id 匹配已审证据包与真实需求 URL。手动可在 draft_topic 输入实际 topic_id、auto 或 none。默认 auto 最多选择三项。证据不完整时照常上传研究计划。历史简报留作人工参考。

模型在隔离 job 里选择和排序已审主张，渲染脚本依据证据填写资料、字段和出处。原始观察、Issue 和评论不进入模型指令。Codex 用 workspace-write 和 drop-sudo，并放在 job 末尾。另一 job 做质量与密钥检查，建立待人工审核的 Draft PR。含 Secret 的作业只在默认分支可用。[证据包](../data/evidence/README.md)

暂停时将变量设为 `false`，并按需删除 Secret。轮换密钥时先关闭开关，替换仓库 Secret，撤销旧密钥，再启用并手动验证。只在仓库 Secret 中填写密钥，避免在 Issues、工作流文件或日志中粘贴。
