"""Render V2.1.1 navigation, evidence-rich review queues and audit summaries."""
from collections import Counter, defaultdict
from hashlib import sha256

from scripts.build_resource_catalog import table_csv
from scripts.curation_semantics import AUXILIARY, DOMAINS, GUIDES, LEARNING
from scripts.curate_resources import pool_key, priority_order
from scripts.run_research import escape, md_url
from scripts.score_resources import COLLECTIONS

REVIEW_COLUMNS = (
    "resource_id", "display_title", "canonical_url", "resource_type", "domain", "audience", "language", "region",
    "stars", "forks", "last_updated", "license_status", "verification_level", "triage_score", "score_evidence",
    "parent_collection", "review_reason", "suggested_action", "status",
)
AUDIT_SEED = "awesome-howto-v2.1.1-risk-audit"
GROUPS = (
    ("howto-series.md", "HowTo 系列与场景指南"),
    ("practical-guides.md", "实操指南与手册"),
    ("learning-paths-and-courses.md", "学习路径、课程与开放教材"),
    ("awesome-lists.md", "Awesome Lists 与资料索引"),
    ("official-resources.md", "官方资料与原始来源"),
    ("tools-and-communities.md", "实用工具与社区"),
    ("resource-audiences.md", "受众与职业入口"),
)


def verified_original(row):
    method = row["provenance"]["method"]
    old = row["legacy_v2"]
    return method == "official-entry" or bool(old and old.get("kind") != "github")


def show_title(row, *, snapshot=False):
    label = escape(row["display_title"])
    url = row["snapshot_url"] if snapshot and row["snapshot_url"] else row["canonical_url"]
    return f"[{label}]({md_url(url)})" if row["status"] != "broken" else label


def label(row):
    title = show_title(row, snapshot=row["resource_scope"] in {"document", "course_unit"})
    summary = row["curator_summary"] or row["upstream_description"] or "用途待核验。"
    if not row["curator_summary"] and row["upstream_description"]:
        summary = "上游简介 · " + summary
    audience = "、".join(row["audience"]) or "受众未核定"
    state = "待核验" if row["status"] in {"needs_review", "inaccessible"} else row["status"]
    assessment = row["quality_assessment"]["recommendation"]
    return (f"- {title} · {row['resource_type']} · {DOMAINS[row['primary_domain']]} · "
            f"{row['language']} / {row['region']} · {audience} · {row['skill_level']} · "
            f"许可 {row['license']['status']} · {state} / {row['verification_level']} · {assessment}。{escape(summary)}")


def section(title, rows, *, empty="本组暂无符合条件的记录。"):
    return [f"## {title}", "", *([label(row) for row in rows] or [empty]), ""]


def curation_indexes(resources, candidates):
    ordered = sorted(resources, key=lambda row: (row["display_title"].casefold(), row["resource_id"]))
    screened = sorted((row for row in candidates if row["screening"] == "screened"), key=priority_order)
    head = ["# 全球实用资源目录", "",
            f"当前有 {len(resources)} 条规范目录记录、{len(candidates)} 条候选。"
            f"其中 {len(screened)} 条候选达到自动结构初筛线。目录节点、独立资源和外链口径见[统计说明](../reports/RESOURCE_SCOPE_AND_COUNTS.md)。",
            "", *[f"- [{title}]({name})" for name, title in GROUPS],
            "- [自动初筛与候选](discovery-candidates.md)",
            "- [类型总导航](discovery-by-type.md)",
            ""]
    for domain, title in DOMAINS.items():
        rows = [row for row in ordered if row["primary_domain"] == domain]
        count = sum(row["primary_domain"] == domain for row in screened)
        head.extend(section(f"{title} · 目录 {len(rows)} 条 · 初筛 {count} 条", rows))
    by_type = ["# 资源类型导航", "", "各入口展示用途、受众与技术验证等级。"
               "编辑推荐等级需要人工记录，可查[发现及审核说明](../discovery/README.md)。", ""]
    by_type.extend(f"- [{title}]({name})" for name, title in GROUPS)
    by_type.extend(["- [自动初筛](discovery-candidates.md)", "", "## 规范目录类型", ""])
    by_type.extend(f"- {kind} · {count}" for kind, count in sorted(Counter(row["resource_type"] for row in ordered).items()))
    by_type.append("")
    predicates = (
        lambda r: r["resource_type"] == "howto_series" and r["resource_scope"] == "collection_root",
        lambda r: r["resource_type"] in GUIDES and r["resource_scope"] not in {"section", "course_unit"},
        lambda r: r["resource_type"] in LEARNING | {"tutorial"} and r["resource_scope"] != "section",
        lambda r: r["resource_type"] in COLLECTIONS and r["resource_scope"] != "section",
        verified_original,
        lambda r: r["resource_type"] in AUXILIARY and bool(r["curator_summary"]),
    )
    descriptions = (
        "持续维护或组织成系列的实践与场景指南。",
        "单项实作指南、手册、食谱、流程和速查资料。",
        "学习路径、课程体系、开放教材和带任务的教程。",
        "集合目录可用于发现候选。集合中的独立条目各自保留核验状态。",
        "公共机构、大学、项目官方帮助及 V2 登记的原始资料。各条记录保留适用范围与核验等级。",
        "能为明确任务提供实作用途的工具和辅助入口。",
    )
    outputs = {}
    for (file, title), match, description in zip(GROUPS, predicates, descriptions):
        body = [f"# {title}", "", description, ""]
        body.extend(section("规范目录", [row for row in ordered if match(row)]))
        if file != "official-resources.md":
            linked = [row for row in screened if match(row) and row["resource_scope"] not in {"document", "course_unit"}]
            if linked:
                body.extend(section("自动初筛样本", linked[:10]))
        outputs[file] = "\n".join(body)
    audience_index = defaultdict(list)
    for row in ordered:
        for audience in row["audience"] or ["适用人群未核定"]:
            audience_index[audience].append(row)
    audience_page = ["# 按受众与职业查找", "", "标签来自发布方说明、课程先修条件和既有注册表证据。"
                     "同一资源可在多个受众入口出现，其规范 ID 相同。", ""]
    for audience, rows in sorted(audience_index.items()):
        audience_page.extend(section(audience, rows))
    preview = ["# 自动初筛与候选", "", f"结构初筛 {len(screened)} 条。以下每个主题最多展示 5 条。"
               "候选保留原始链接与复核状态。", "",
               "[优先复核](../data/reviews/priority-review.csv) · [候选积压](../data/reviews/candidate-backlog.csv) · "
               "[全部候选 JSONL](../data/resource-catalog/candidates.jsonl)", ""]
    for domain, title in DOMAINS.items():
        preview.extend(section(title, [row for row in screened if row["primary_domain"] == domain][:5]))
    outputs.update({"discovery-index.md": "\n".join(head), "discovery-by-type.md": "\n".join(by_type),
                    "resource-audiences.md": "\n".join(audience_page), "discovery-candidates.md": "\n".join(preview)})
    return outputs


def review_row(row, by_id, reason, action):
    metrics = row["github_metrics"] or {}
    parent = by_id.get(row["parent_resource_id"], {})
    return (
        row["resource_id"], row["display_title"], row["canonical_url"], row["resource_type"], row["primary_domain"],
        "; ".join(row["audience"]), row["language"], row["region"], metrics.get("stars"), metrics.get("forks"),
        metrics.get("updated_at") or "", row["license"]["status"], row["verification_level"],
        row["quality_assessment"]["automated_score"], " | ".join(row["score_evidence"]),
        parent.get("display_title", ""), reason, action, row["screening"],
    )


def review_outputs(catalog, priority, backlog, edges, unresolved):
    by_id = {row["resource_id"]: row for row in catalog}
    by_repository = {row["source_repository"].casefold(): row for row in catalog if row["github_metrics"]}
    published = [row for row in catalog if row["screening"] == "catalogued"]
    grouped = defaultdict(list)
    for row in catalog:
        if row["license"]["status"] == "verified" and row["license_inheritance_status"] != "needs_review":
            continue
        name = (row["source_repository"] or "").casefold()
        if name and name in by_repository:
            grouped[by_repository[name]["resource_id"]].append(row)

    def queue(rows, reason, action):
        return table_csv(REVIEW_COLUMNS, (
            review_row(row, by_id, reason(row), action) for row in rows
        ))

    risk = [row for row in catalog if row["requires_expert_review"]]
    risk.sort(key=lambda row: ({"high": 0, "medium": 1, "unknown": 2, "low": 3}[row["risk_level"]], row["resource_id"]))
    metadata = []
    for row in published + priority:
        missing = [key for key in ("language", "region", "resource_type") if row[key] == "unknown"]
        if row["license"]["status"] == "unknown":
            missing.append("license")
        if not row["audience"]:
            missing.append("audience")
        if row["primary_domain"] == "unclassified":
            missing.append("primary_domain")
        if missing:
            metadata.append((row, tuple(missing)))
    duplicate = [(e["from_id"], e["type"], e["to_id"], e["evidence"],
                  "核对上游、版本和适用范围，记录保留或合并理由") for e in edges if not e["verified"]]
    duplicate.extend((resource_id, "identity_needs_review", "", url, "核对默认分支、固定提交和路径后建立映射")
                     for resource_id, url in unresolved)
    files = {
        "priority-review.csv": queue(priority, lambda row: pool_key(row), "打开原始资料，核对范围、步骤与实例，再填写人工审核"),
        "candidate-backlog.csv": queue(backlog, lambda row: (
            "需要专业核验" if row["requires_expert_review"] else row["classification_status"]),
            "核对独立可达性和主题证据，完善来源记录"),
        "high-risk-review.csv": queue(risk, lambda row: (
            f"{row['risk_level']} / {row['risk_scope']} / {row['jurisdiction']} · " + " | ".join(row["risk_evidence"])),
            "由专业人员核对行为影响、发布方、适用辖区及版本"),
        "metadata-review.csv": table_csv(REVIEW_COLUMNS, (
            review_row(row, by_id, ", ".join(missing), "读取目标受众或许可说明，补充可追溯依据") for row, missing in metadata
        )),
        "duplicate-review.csv": table_csv(("from_id", "relation", "to_id", "evidence", "suggested_action"), sorted(duplicate)),
        "license-root-review.csv": table_csv((*REVIEW_COLUMNS, "items_needing_review", "license_scopes"), (
            (*review_row(by_id[key], by_id, "仓库级许可和子路径适用范围待确认",
                         "检查 LICENSE、文件头、第三方材料与子路径许可"), len(items),
             " | ".join(f"{scope}={count}" for scope, count in sorted(Counter(row["license_scope"] for row in items).items())))
            for key, items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))
        )),
    }
    counts = {"priority": len(priority), "backlog": len(backlog), "expert_review": len(risk),
              "metadata": len(metadata), "license_roots": len(grouped), "duplicate": len(duplicate)}
    return {f"data/reviews/{key}": value for key, value in files.items()}, counts


def sample_key(resource_id):
    return sha256(f"{AUDIT_SEED}|{resource_id}".encode()).hexdigest()


def risk_sample(old_rows, rows, id_map):
    refined = {row["resource_id"]: row for row in rows}
    old_high = sorted((row for row in old_rows if row["risk_level"] == "high"),
                      key=lambda row: sample_key(row["resource_id"]))[:50]
    ids = {id_map[row["resource_id"]] for row in old_high}
    known = [row for row in rows if row["risk_level"] != "high" and row["resource_id"] not in ids]
    # Deliberately inspect both impact-adjacent and general records to look for missed decisions.
    strata = ([row for row in known if row["requires_expert_review"]],
              [row for row in known if not row["requires_expert_review"]])
    non_high = [row for group in strata for row in sorted(group, key=lambda r: sample_key(r["resource_id"]))[:25]]
    high = sorted((row for row in rows if row["risk_level"] == "high"),
                  key=lambda row: sample_key(row["resource_id"]))[:50]
    return ([("baseline-high", old["resource_id"], refined[id_map[old["resource_id"]]]) for old in old_high] +
            [("current-non-high", row["resource_id"], row) for row in non_high] +
            [("current-high", row["resource_id"], row) for row in high])
