---
id: "howto-codex-github-release"
title: "怎样用 Codex 检查并公开发布一个 GitHub 项目？"
category: "ai"
subcategory: "codex-and-coding-agents"
personas: ["software-engineer", "student"]
age_groups: ["unknown"]
occupations: ["software-developer"]
scenarios: ["project-release", "publish-github-project"]
region: "global"
difficulty: "beginner"
estimated_time: "30–60 分钟"
cost: "练习可免费完成"
evidence_level: "A"
content_type: "howto"
risk_level: "low"
status: "draft"
created_at: "2026-11-25"
updated_at: "2026-11-25"
review_due: "2026-12-25"
sources: ["https://learn.chatgpt.com/docs/codex/cli", "https://cli.github.com/manual/gh_repo_create", "https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository"]
life_stages: ["unknown"]
prerequisites: ["有目标仓库写权限，使用独立目录与可访问的 Git 工具。"]
last_verified_at: "2026-11-25"
version: "0.2"
execution_status: "pending"
claim_evidence: [{"claim_id": "codex-github-release-1", "claim_text": "Codex CLI 在指定项目目录运行，权限取决于环境配置。", "claim_type": "fact", "supporting_source_ids": ["codex-cli"], "support_level": "direct", "source_location": "CLI overview", "applicable_region": "global", "applicable_version": "版本以执行前为准", "limitations": "结论限于所列文档范围及版本，执行及地区限制见正文。", "reviewer_status": "editorial-checked"}, {"claim_id": "codex-github-release-2", "claim_text": "GitHub CLI 提供源目录、远端、公开性和推送参数。", "claim_type": "fact", "supporting_source_ids": ["gh-cli-create"], "support_level": "direct", "source_location": "Options / --source --remote --push", "applicable_region": "global", "applicable_version": "gh CLI", "limitations": "结论限于所列文档范围及版本，执行及地区限制见正文。", "reviewer_status": "editorial-checked"}, {"claim_id": "codex-github-release-3", "claim_text": "创建 GitHub 仓库时需确认所有者和可见性。", "claim_type": "fact", "supporting_source_ids": ["gh-repository"], "support_level": "direct", "source_location": "Creating a new repository", "applicable_region": "global", "applicable_version": "GitHub.com", "limitations": "结论限于所列文档范围及版本，执行及地区限制见正文。", "reviewer_status": "editorial-checked"}]
---

# 怎样用 Codex 检查并公开发布一个 GitHub 项目？

从单独的项目目录开始，检查内容与 GitHub 身份，再用普通首次推送发布。

## 适用人群

已经能使用命令行，并拥有 GitHub 账户的开发者或学习者。

读者标签　开发者、学生、创作者。

## 前置条件与不适用情况

安装 Git 与 GitHub CLI。Codex 可用桌面应用或 CLI，权限取决于账号和环境。已有非空远端时先检查提交历史并合并可兼容内容。

## 准备、耗时与费用

准备自己的 README、许可证和测试命令，预留 30–60 分钟。公开仓库的可用能力按 GitHub 账户设置确定。

## 操作步骤与验收

1. 在项目目录打开 Codex，请它检查 git status、测试结果和许可证。运行 gh auth status 及 gh api user --jq .login。 **验收**　登录名与目标所有者一致，发布目录里只有预期项目文件。
2. 逐项检查待提交文件、git diff --cached、忽略规则，并用本地密钥扫描检查。 **验收**　确认没有 .env、Cookie、私人资料或凭据，测试记录真实。
3. 确认目标名可用，进行首次提交。对新仓库执行 gh repo create OWNER/REPO --public --source . --remote origin --push，把 OWNER/REPO 替换为你已核对的仓库名。 **验收**　远端关联到预期 owner/repo，普通推送成功。
4. 用 gh repo view 核对公开状态、默认分支及默认分支提交，再查看 README 和 Actions。 **验收**　远端提交与本地 git rev-parse HEAD 相同，公开页面可访问。

先执行 `git rev-parse --show-toplevel` 和 `git status --short --branch`，确认看到的是目标目录和拟发布文件。新项目先由你核对公开边界，再让 Codex 运行项目自身测试。对既有项目执行 `git switch -c docs/example-change`，下次更新走 Draft PR。核对默认分支 SHA 的命令为 `gh api repos/OWNER/REPO/branches/main --jq .commit.sha`。

## 常见错误与排查

终端找不到 Codex 时，可从桌面应用打开项目或按官方 CLI 文档安装。看到非空同名仓库时，先比对历史和文件。

GitHub CLI 能读 API 但 Git 推送超时时，先核对 `git remote -v`、网络和 Git 的 CA 设置。按 GitHub 现有 HTTPS 配置处理，保留证书校验。仓库创建后推送失败时检查远端分支再用普通 push 重试。

## 风险与限制

仓库内容和公开提交历史会被第三方复制。首次提交前进行发布检查。后续变更走人工审核的 PR。

## 最简行动清单

核对目录和身份 → 测试与审查 staged diff → 常规推送 → 校验远端。

## 参考来源

- 查看 CLI 启动和用法。 [OpenAI · Codex CLI](https://learn.chatgpt.com/docs/codex/cli)（访问于 2026-11-25）。
- 核对仓库可见性、源目录、远端与推送参数。 [GitHub CLI · gh repo create](https://cli.github.com/manual/gh_repo_create)（访问于 2026-11-25）。
- 核对拥有者、可见性及创建选项。 [GitHub Docs · Creating a new repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)（访问于 2026-11-25）。

## 核验与版本

2026-11-25 核对来源与适用范围。v0.2 · 初稿，待独立复核和实际设备或任务演练。下一次复查 2026-12-25。
