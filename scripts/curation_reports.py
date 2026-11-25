"""Report the measured curation changes and the review limitations."""
from collections import Counter, defaultdict

from scripts.curation_outputs import AUDIT_SEED
from scripts.curation_semantics import AUXILIARY, DOMAINS, GUIDES, LEARNING
from scripts.generate_discovery_report import distribution, table
from scripts.score_resources import COLLECTIONS

AUDIT_NAMES = (
    "hamidhirsi/mlops-case-study", "qhyai-bit/farmsource", "studybuddydevelopers/study-buddy-v2",
    "decade-qiu/openai-prompt-packs", "alishahryar1/free-claude-code",
    "larsmt35/haushaltsbuch-web-version", "chrisryugj/korean-law-mcp",
)


def coverage(rows):
    return {
        "total": len(rows),
        "audience": sum(bool(row["audience"]) for row in rows),
        "language": sum(row["language"] != "unknown" for row in rows),
        "region": sum(row["region"] != "unknown" for row in rows),
        "license_known": sum(row["license"]["status"] != "unknown" for row in rows),
        "license_verified": sum(row["license"]["status"] == "verified" for row in rows),
    }


def scope_counts(rows):
    counts = Counter(row["resource_scope"] for row in rows)
    return {
        "各类集合根": counts["collection_root"],
        "独立资源入口": counts["standalone_resource"],
        "独立实操指南": sum(row["resource_scope"] == "standalone_resource"
                           and row["resource_type"] == "practical_guide" for row in rows),
        "HowTo 系列": sum(row["resource_scope"] == "collection_root"
                        and row["resource_type"] == "howto_series" for row in rows),
        "手册、说明书与食谱": sum(row["resource_type"] in {"handbook", "manual", "cookbook"}
                             and row["resource_scope"] not in {"section", "course_unit"} for row in rows),
        "其他实操参考（流程、现场指南、速查）": sum(row["resource_type"] in GUIDES - {
            "practical_guide", "handbook", "manual", "cookbook"} and row["resource_scope"] != "section" for row in rows),
        "教程或课程单元": sum(row["resource_type"] == "tutorial" or row["resource_scope"] == "course_unit"
                       for row in rows if row["resource_scope"] != "section"),
        "学习路径、课程体系、课程与开放教材": sum(row["resource_type"] in LEARNING
                                        and row["resource_scope"] not in {"section", "course_unit"} for row in rows),
        "Awesome Lists、资料目录与书目": sum(row["resource_type"] in COLLECTIONS and row["resource_scope"] != "section" for row in rows),
        "章节节点": counts["section"],
        "文档节点": counts["document"],
        "外链线索": counts["external_resource"],
        "工具、社区与数据集": sum(row["resource_type"] in AUXILIARY for row in rows),
    }


def reports(old, resources, candidates, priority, relations, ledger, unresolved, counts, quotas, sample, verdicts, manifest):
    rows = resources + candidates
    old_catalog = [row for row in old if row["screening"] == "catalogued"]
    base = manifest["baseline_counts"]
    search = manifest["search"]
    expansion = manifest["expansion"]
    present = {row["primary_domain"] for row in priority}
    missing = "、".join(label for key, label in DOMAINS.items() if key not in present and key != "unclassified")
    pages_by_topic = defaultdict(list)
    for page in manifest["search_pages"]:
        pages_by_topic[page["domain"]].append(page)
    output = {}
    output["RESOURCE_CURATION_V2.1.1_REPORT.md"] = [
        "# 资源策展 V2.1.1", "",
        f"基准提交 {manifest['baseline_revision']}。规范目录 {base['catalogued']} 条，候选 {base['candidates']} 条，"
        f"结构初筛 {base['screened']} 条。基线记录来自 Git 快照和历史采集清单。",
        f"精修后规范目录 {len(resources)} 条，候选 {len(candidates)} 条，结构初筛 {len(priority)} 条。"
        f"新增人工评分 {sum(row['quality_assessment']['editorial_score'] is not None for row in rows) - base['editorial_scores']} 条。", "",
        f"GitHub 查询 {search['groups']} 组，{search['pages']} 页，成功 {search['successful']} 页，"
        f"其中 {search['cached_baseline_pages']} 页复用原始观测。检索返回 {search['hits']} 个观察，"
        f"{search['incomplete']} 页标为不完整，{search['empty']} 页返回空结果。",
        f"递归核验 {expansion['resolved']}/{expansion['routes']} 条入口路线，最大深度 {expansion['deepest']}，"
        f"抽取 {expansion['items']} 个目录观察。记录目录上限、逐主题选择与个别安全边界。",
        f"GitLab {len(manifest['platforms'].get('gitlab', []))} 组公开搜索共返回 "
        f"{sum(item['count'] or 0 for item in manifest['platforms'].get('gitlab', []))} 项 API 排名样本。"
        "其中包括应用源码与不相关项目，结果作为平台覆盖证据。"
        f"Codeberg HTTP 状态 {distribution(str(row['http']) for row in manifest['platforms'].get('codeberg', []))}。",
        f"官方及已知平台入口复用历史探测 {manifest['official_link_evidence']['reused']} 条。新覆盖明细见运行清单。",
        f"当前优先队列主题缺口为 {missing or '无'}。健康、财务和法律同样保留官方参考与独立专业复核。",
        "", "## 按主题核对查询语言", "",
        table(("主题", "实际检索语言", "成功页", "返回记录"), [
            (DOMAINS[topic], "、".join(sorted({p["language"] for p in pages})),
             sum(p["status"] == "ok" for p in pages), sum(p["count"] for p in pages))
            for topic, pages in pages_by_topic.items()
        ]),
        "", "语言分布来自查询式和实际返回记录。单个多语查询结果中的作品语言仍按资源证据填写。",
        "", "## 审计明细", "",
        "- [稳定 ID 与快照](RESOURCE_ID_STABILITY_REPORT.md) · [资源口径与数量](RESOURCE_SCOPE_AND_COUNTS.md)",
        "- [分类样本](RESOURCE_CLASSIFICATION_AUDIT.md) · [风险抽查](RESOURCE_RISK_AUDIT.md)",
        "- [受众覆盖](RESOURCE_AUDIENCE_COVERAGE.md) · [复核队列](RESOURCE_REVIEW_QUEUE_REPORT.md)",
        "- [采集记录](../data/curation-runs/v2.1.1/manifest.json) · [历史 V2.1 运行](../data/discovery-runs/2026-11-25/manifest.json)", "",
    ]
    original_ids = {r["resource_id"] for r in old}
    output["RESOURCE_ID_STABILITY_REPORT.md"] = [
        "# 稳定资源身份与快照", "",
        f"保留了 {len(old)} 条基线记录的身份或映射。共输出 {len(ledger)} 条旧 ID 到稳定 ID 的迁移记录，"
        f"其中 {sum(entry['old_resource_id'] in original_ids for entry in ledger)} 条来自基线。"
        f"有 {len(unresolved)} 条固定提交记录无法确认默认分支映射，保留原记录并排入复核。", "",
        "稳定子项身份由 GitHub 仓库、默认分支、路径和片段组成。根仓库既有 ID 保留，新增根记录优先使用 GitHub repository ID。",
        "固定提交的 snapshot_url 与 source_url 保存证据定位。snapshots 保留此前来源 URL 和提交。旧 ID 还可在 identity_aliases 查询。",
        "翻译、不同路径与片段、发布版本、辖区和 Fork 维持独立身份。迁移记录的 supersedes 指向退役旧 ID。",
        "", "[旧 ID 映射](../data/curation-runs/v2.1.1/id-migrations.jsonl) · [疑似重复复核](../data/reviews/duplicate-review.csv)", "",
    ]
    scope = scope_counts(rows)
    directory_scope, candidate_scope, priority_scope = map(scope_counts, (resources, candidates, priority))
    output["RESOURCE_SCOPE_AND_COUNTS.md"] = [
        "# 资源范围与统计口径", "",
        f"{len(rows)} 条是规范化记录。目录观察、章节节点、候选外链和关系边单独计量。"
        f"当前有 {len(relations)} 条关系，其中 {sum(edge['type']=='child_of' for edge in relations)} 条为父子关系。",
        "", "## 范围", "",
        f"所有记录的互斥 scope 分布为 {distribution(row['resource_scope'] for row in rows)}。",
        "", table(("统计项", "规范目录", "候选", "已初筛候选", "合计"), [
            (label, directory_scope[label], candidate_scope[label], priority_scope[label], value)
            for label, value in scope.items()
        ]),
        "", "表中功能细类可能交叉。初筛列属于候选子集。目录旧人工字段保存在 legacy_v2。"
        "章节标题与外链线索只作导航证据。", "",
        f"初筛类型 {distribution(row['resource_type'] for row in priority)}。",
        f"目录类型 {distribution(row['resource_type'] for row in resources)}。", "",
    ]
    comparison = {(row["source_repository"] or "").casefold(): row for row in rows if row["github_metrics"]}
    before = {(row["source_repository"] or "").casefold(): row for row in old if row["github_metrics"]}
    output["RESOURCE_CLASSIFICATION_AUDIT.md"] = [
        "# 分类与已知误判复查", "",
        "有文本证据时优先使用 README、发布方简介和主题。仓库名、路径与父集合提供补充。"
        "查询主题只保留为发现出处。没有明确证据或出现同权冲突时使用 unclassified。",
        "", table(("样本", "V2.1 归类", "本轮主题", "本轮风险", "证据"), [
            (name, before[name]["primary_domain"], comparison[name]["primary_domain"], comparison[name]["risk_level"],
             " / ".join(comparison[name]["classification_evidence"]))
            for name in AUDIT_NAMES if name in comparison and name in before
        ]),
        "", f"分类状态 {distribution(row['classification_status'] for row in rows)}。"
        f"主题分布 {distribution(row['primary_domain'] for row in rows)}。", "",
        "主题词模型用于排序和查阅。混合领域、只有通用 README 的仓库及搜索结果标题仍需人工判读。", "",
    ]
    old_cover, cover = coverage(old_catalog), coverage(resources)
    fields = {"audience": "已知受众", "language": "已知语言", "region": "已知地区",
              "license_known": "有许可证状态记录", "license_verified": "许可已核验"}
    output["RESOURCE_AUDIENCE_COVERAGE.md"] = [
        "# 受众、语言、地区与许可覆盖", "",
        "受众采用上游用途说明、课程先修条件或原 V2 注册表。语言使用实际来源、语言导航或翻译证据。"
        "缺少证据时保留空值或 unknown。",
        "", table(("规范目录覆盖", "V2.1 基线", "V2.1.1"), [
            (label, f"{old_cover[key]}/{old_cover['total']} ({old_cover[key] / old_cover['total']:.1%})",
             f"{cover[key]}/{cover['total']} ({cover[key] / cover['total']:.1%})") for key, label in fields.items()
        ]),
        "", f"当前规范目录许可分布 {distribution(row['license']['status'] for row in resources)}。",
        "许可已核验描述仓库声明及文件证据。子路径、第三方资料和单独授权对象保留独立状态。",
        "", "[受众索引](../resources/resource-audiences.md) · [元数据复核](../data/reviews/metadata-review.csv)", "",
    ]
    output["RESOURCE_REVIEW_QUEUE_REPORT.md"] = [
        "# 人工复核队列", "",
        "结构初筛按资料类型分池。每个池内按已知主题轮换，并以技术核验和结构分排序。",
        "", table(("类型池", "参考配额", "符合门槛", "实取"), [
            (name, item["target"], item["eligible"], item["selected"]) for name, item in quotas.items()
        ]),
        "", f"优先审核 {counts['priority']} 条，候选积压 {counts['backlog']} 条，"
        f"按仓库归并的许可任务 {counts['license_roots']} 条，"
        f"元数据任务 {counts['metadata']} 条，疑似重复及身份任务 {counts['duplicate']} 条。",
        f"初筛中 Awesome Lists 占 {sum(row['resource_type'] == 'awesome_list' for row in priority)}/{len(priority)}。"
        "官方已核验来源进入规范目录。官方候选可达性未核验时保留原链接和待核验状态。",
        "", "[优先复核](../data/reviews/priority-review.csv) · [较后候选](../data/reviews/candidate-backlog.csv) · "
        "[仓库许可](../data/reviews/license-root-review.csv) · [疑似重复](../data/reviews/duplicate-review.csv)", "",
    ]
    strata = defaultdict(Counter)
    missed_gate = 0
    for group, key, row in sample:
        decision = verdicts.get(key, {}).get("verdict", "未标注")
        strata[group][decision] += 1
        if group == "current-non-high" and decision == "decision" and not row["requires_expert_review"]:
            missed_gate += 1
    old_false_positive = sum(strata["baseline-high"][kind] for kind in ("ordinary", "software", "reference"))
    output["RESOURCE_RISK_AUDIT.md"] = [
        "# 风险筛查审计", "",
        f"基线风险分布 {distribution(row['risk_level'] for row in old)}。"
        f"本轮风险分布 {distribution(row['risk_level'] for row in rows)}。"
        f"专业核验队列 {counts['expert_review']} 条，含高影响决策、潜在决策支持和证据不足的入口。",
        "", "风险判断采用产品功能和来源证据，主题用于导航。记账软件与资料目录可列为低风险或参考。"
        "来源显示临床决策、个性化法律意见或投资建议功能时触发专业复核。", "",
        "## 可复现的抽查", "",
        f"按 SHA256({AUDIT_SEED}|resource_id) 排序。抽取基线高风险 50 条与当前非高风险 50 条。"
        "非高风险样本分别从已进入专家队列及其他资源各选 25 条。"
        "复查本轮高风险记录，当前数量少于 50 时全查。"
        "抽查限于公开元数据与结构，无法判定时记为 uncertain。", "",
        table(("样本层", "抽查结果"), [(group, distribution(result)) for group, result in strata.items()]),
        "", f"基线 50 条样本中有 {old_false_positive} 条依据可见用途属于旧版高风险误报。"
        f"当前非高风险样本中有 {strata['current-non-high']['decision']} 条值得复核为决策支持，"
        f"其中 {missed_gate} 条尚未进入专业队列。",
        "", "旧高风险层中的 ordinary、software 或 reference 为元数据可见的旧误报。"
        "非高风险层中的 decision 为潜在漏报，仍需按原始输出和部署情境核对。",
        "", "[逐条抽查](../data/curation-runs/v2.1.1/risk-sample.csv) · [专业复核队列](../data/reviews/high-risk-review.csv)", "",
    ]
    return {f"reports/{name}": "\n".join(body) for name, body in output.items()}
