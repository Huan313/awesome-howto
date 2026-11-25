"""Render discovery and compliance reports from the recorded public evidence."""
from collections import Counter

from scripts.common import SHANGHAI, timestamp

SERIES = (
    ("github.com/practical-tutorials/project-based-learning", "按编程语言组织项目练习，外链保留来源集合。"),
    ("github.com/ebookfoundation/free-programming-books", "多语书目入口，可分别核对语言版本及原始资源。"),
    ("www.moneysense.gov.sg/managing-your-money", "可明确定位到新加坡的公共财务教育入口。"),
    ("www.nhs.uk/live-well", "按健康生活主题查找英国公共医疗机构的原始资料。"),
    ("www.w3.org/WAI/tutorials", "按无障碍任务查找标准机构的教程。"),
    ("capd.mit.edu/resources/interview-primer", "大学职业中心的面试资料，区分常见面试场景。"),
    ("docs.blender.org/manual/en/latest", "按版本、工具和工作环节浏览的官方手册。"),
    ("ocw.mit.edu/", "按学科查找大学开放课程，便于逐门核对版本和许可。"),
    ("www.nasa.gov/reference/systems-engineering-handbook", "工程机构的原始手册入口，可按术语和流程查阅。"),
    ("github.com/microsoft/ai-for-beginners", "按单元组织 AI 基础课程及习题，便于核对受众。"),
)

LOW_STAR_EXAMPLES = {
    "awesome-german/websites": "按语言程度整理德语学习网站，补充非英语学习入口。",
    "adamxweb/awesome-aussie": "按澳大利亚开发的软件和服务整理，可复查区域数字生态。",
    "autogeoai4sci/awesome-autonomous-geoai": "集中索引自主地理空间 AI 资料，便于查找专业候选。",
}


def fmt(value):
    return str(value if value is not None else "unknown").replace("|", r"\|").replace("\n", " ")


def distribution(values):
    counts = values if isinstance(values, Counter) else Counter(values)
    return "、".join(f"{name} {count}" for name, count in sorted(counts.items())) or "无记录"


def window(value):
    return timestamp(value).astimezone(SHANGHAI).isoformat(timespec="seconds")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
                      *["| " + " | ".join(fmt(value) for value in row) + " |" for row in rows]])


def reports(catalog, manifest):
    rows = list(catalog.rows.values())
    registry = [row for row in rows if row["screening"] == "catalogued"]
    candidates = [row for row in rows if row["screening"] != "catalogued"]
    screened = [row for row in candidates if row["screening"] == "screened"]
    edges = list(catalog.edges.values())
    c = manifest["counts"]
    roots, pages = manifest["repository_routes"], manifest["search_pages"]
    platform_probe = "、".join(f"{name} {outcome}" for name, outcome in manifest["platform_probes"].items())
    verified = []
    for fragment, reason in SERIES:
        row = next((r for r in registry if r["canonical_url"].casefold() == "https://" + fragment.casefold() and
                    r["status"] in {"active", "redirected"} and not r["legacy_v2"]), None)
        if row:
            verified.append(f"- [{row['title']}]({row['canonical_url']})。{reason}")
    low = [r for r in screened if r["github_metrics"] and r["github_metrics"]["stars"] < 50
           and (r["source_repository"] or "").casefold() in LOW_STAR_EXAMPLES]
    intro = [
        "# V2.1 全球资源发现记录", "",
        f"运行窗口 {window(manifest['started_at'])} 至 {window(manifest['finished_at'])}（UTC+08）。"
        f"改进基线 {manifest['base_revision']}。脚本版本摘要见 [运行清单]({manifest['path']})。",
        "", "来源包括 GitHub REST Repository Search、GitHub Contents / Git Trees 和官方站点核验。"
        "GitLab 项目核验见链接报告。", "",
        *([f"补充平台探测 {platform_probe}。", ""] if platform_probe else []),
        f"GitHub 查询组 {c['query_groups']}，执行 {len(pages)} 个分页请求，返回 {c['search_hits']} 条命中。"
        f"成功 {c['search_pages_ok']} 页，标记 incomplete_results {c['search_pages_incomplete']} 页。",
        f"配置种子 {c['seed_routes']}，API 核验成功 {c['seed_ok']}。"
        f"其中索引种子成功 {c['index_seed_ok']}，补充索引种子成功 {c['added_index_ok']}。",
        f"BFS 深度上限 {manifest['depth_limit']}，实际最深 {c['deepest']}。"
        f"抽取 {c['extracted_items']} 个目录观察，建立 {c['children']} 条父子边。",
        f"纳入规范化的原始观察 {c['raw_count']} 条，含旧注册表和补充入口。"
        f"合并 {c['duplicates']} 条重复观察，唯一记录 {len(rows)} 条。"
        f"其中目录 {len(registry)} 条、候选 {len(candidates)} 条，自动初筛 {len(screened)} 条。人工新评分 0 条。",
        "", "## 类型、主题与语言", "",
        f"目录类型分布：{distribution(r['resource_type'] for r in registry)}。",
        f"候选类型分布：{distribution(r['resource_type'] for r in candidates)}。",
        f"初筛类型分布：{distribution(r['resource_type'] for r in screened)}。",
        f"初筛主题分布：{distribution(r['primary_domain'] for r in screened)}。",
        f"目录地域分布：{distribution(r['region'] for r in registry)}。",
        f"候选语言分布：{distribution(r['language'] for r in candidates)}。",
        "", "## 本轮新增并核验的入口", "", *verified,
        "", "## 低 Stars 待审样本", "",
        *[f"- [{r['title']}]({r['canonical_url']}) · {r['github_metrics']['stars']} Stars。"
          f"采集 {r['github_metrics']['metadata_checked_at']}。"
          f"{LOW_STAR_EXAMPLES[r['source_repository'].casefold()]}" for r in low],
        *([] if low else ["本轮未列出经抽样复核的低星案例。"]),
        "", "## 排除及后续", "",
        f"排除观察：{distribution(catalog.rejected)}。",
        "下一轮优先补非英语生活资源、按司法辖区的消费与劳动公开目录，以及无需账号即可查阅的低星行业手册。",
        "", "[覆盖与种子](RESOURCE_COVERAGE_GAP_REPORT.md) · [自动初筛](RESOURCE_QUALITY_REPORT.md) · "
        "[关系与去重](RESOURCE_DUPLICATION_REPORT.md) · [许可证](LICENSE_AND_COMPLIANCE_REPORT.md) · "
        "[链接核验](LINK_HEALTH_REPORT.md)", "",
    ]
    quality = [
        "# 资源质量初筛", "",
        "评分权重为内容 25、可信度 25、可操作性 20、维护 15、社区 10、元数据 5。"
        "仅检查目录结构时，内容最高计 13 分，社区项最高计 6 分。人工编辑分保留为空，"
        "旧审核字段原样保存。初筛按主题轮流取可核查候选。",
        "", f"初筛 {len(screened)} 项，剩余待审候选 {len(candidates) - len(screened)} 项。",
        f"高风险主题 {sum(r['risk_level'] == 'high' for r in rows)} 项，单独核验，自动初筛为零。",
        "", table(["样本", "类型", "自动分", "证据"], [
            (r["title"], r["resource_type"], r["quality_assessment"]["automated_score"],
             " / ".join(r["quality_assessment"]["evidence"])) for r in sorted(
                screened, key=lambda row: (-row["quality_assessment"]["automated_score"], row["resource_id"]))[:12]
        ]),
        "", "[人工审核队列](../data/reviews/manual-review-queue.csv) · [高风险队列](../data/reviews/high-risk-review.csv)", "",
    ]
    coverage = [
        "# 覆盖与缺口", "",
        "覆盖明确的搜索表达式、分页和官方入口，仍欠缺一般网页目录、需登录内容和大量非英语官方资料。",
        "部分种子仅核验元数据，深度遍历有单仓配额。健康与财务类保留官方入口和专项审核队列。",
        "", "## 实际查询与分页", "",
        table(["组", "检索语言", "页数", "成功页", "实际返回数", "表达式"], [
            (group, items[0]["language"], len(items), sum(x["status"] == "ok" for x in items),
             sum(x["returned"] for x in items), items[0]["executed_expression"])
            for group in sorted({item["id"] for item in pages})
            if (items := [item for item in pages if item["id"] == group])
        ]),
        "", "## 入口审计", "",
        table(["入口", "层级", "HTTP", "结构", "目录观察", "范围"], [
            (r["repository"], r["depth"], r["http"], r["structure_status"], r["items"], r["limitation"] or "—") for r in roots
        ]),
        "", "[完整查询矩阵](../discovery/query-matrix.yaml) · [运行清单](" + manifest["path"] + ")", "",
    ]
    duplicate = [
        "# 去重和关系", "",
        f"规范 URL 与 GitHub 仓库 ID 共合并 {c['duplicates']} 条重复观察。"
        "不同版本、翻译和 Fork 保留独立记录。仅目录指纹或名称、简介相似时提交复核。",
        f"关系分布：{distribution(edge['type'] for edge in edges)}。",
        f"候选关系待独立确认 {sum(not edge['verified'] for edge in edges)} 条。",
        "", "[别名合并日志](" + manifest["path"].replace("manifest.json", "duplicate-events.jsonl") + ") · "
        "[疑似重复复核](../data/reviews/duplicate-review.csv)", "",
    ]
    license = [
        "# 许可证与合规", "",
        f"许可证状态：{distribution(r['license']['status'] for r in rows)}。",
        "API 的 SPDX 与已查到的文件路径一起记录。对子资源保留单独核验，父仓库许可仅提供核对入口。"
        "已识别的 NC 与 ND 限制保留原 SPDX。",
        "高风险主题仅供定位来源，逐项核验发布机构、辖区、日期、版本和风险。",
        "", "[许可证复核队列](../data/reviews/license-review.csv) · [高风险复核队列](../data/reviews/high-risk-review.csv)", "",
    ]
    link = [
        "# 链接核验", "",
        f"记录状态：{distribution(r['status'] for r in rows)}。",
        "GitHub API 200 表示有公开项目元数据。固定 Git 提交的文件或解析标题使用结构证据。"
        "被集合引用但未独立访问的外链保留 needs_review。robots 限制、403、429 与超时单独记载。",
        "404/410 仍需独立复查。重定向只有到达公开成功响应时才记为已核验。",
        "", table(["入口", "状态", "HTTP", "方式", "重定向或限制"], [
            (r["title"], r["status"], r["http"], r["method"], r["redirect_target"] or r["reason"])
            for r in manifest["link_observations"]
        ]), "",
    ]
    return dict(zip(("RESOURCE_DISCOVERY_V2.1_REPORT.md", "RESOURCE_QUALITY_REPORT.md",
                     "RESOURCE_COVERAGE_GAP_REPORT.md", "RESOURCE_DUPLICATION_REPORT.md",
                     "LICENSE_AND_COMPLIANCE_REPORT.md", "LINK_HEALTH_REPORT.md"),
                    map("\n".join, (intro, quality, coverage, duplicate, license, link))))
