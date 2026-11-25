"""Build the V2.1 resource catalog, indexes and audit queues from saved evidence."""
import argparse
import csv
import hashlib
import io
import json
import subprocess
from collections import Counter
from pathlib import Path

from scripts.build_resource_index import read_registry
from scripts.common import ROOT, SHANGHAI, read_json, read_yaml, timestamp, write_text
from scripts.discover_github import CONFIG, add_arguments
from scripts.generate_discovery_report import reports
from scripts.resource_catalog import DOMAIN_LABELS, assemble
from scripts.run_research import escape, md_url
from scripts.score_resources import COLLECTIONS, PRACTICAL
from scripts.validate_catalog import CATALOG, read_lines, validate_records

VERIFIED = {"active", "redirected", "archived"}


def lines(rows):
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)


def table_csv(fields, rows):
    def spreadsheet_text(cell):
        value = str(cell if cell is not None else "")
        return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value

    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(fields)
    writer.writerows([spreadsheet_text(cell) for cell in row] for row in rows)
    return stream.getvalue()


def label(row):
    title = escape(row["title"])
    if row["status"] in VERIFIED:
        title = f"[{title}]({md_url(row['canonical_url'])})"
    grade = row["quality_assessment"]["recommendation"]
    return (f"- {title} · {row['resource_type']} · {DOMAIN_LABELS[row['primary_domain']]} · "
            f"{row['language']} / {row['region']} · {', '.join(row['audience']) or '受众未核定'} · "
            f"{row['skill_level']} · {row['license']['status']} · {grade}。{escape(row['description'])}")


def indexes(resources, candidates):
    screened = [row for row in candidates if row["screening"] == "screened"]
    roots = sorted([*resources, *screened], key=lambda row: (row["primary_domain"], row["title"].casefold()))
    head = ["# 资源发现与分类目录", "",
            f"规范目录 {len(resources)} 条，待审候选 {len(candidates)} 条。候选中 {len(screened)} 条达到自动初筛线。",
            "旧 V2 编辑状态保存在原始注册表和 V2.1 的 legacy_v2 字段。新核验入口标为 reference-only。",
            "", "[HowTo 系列](howto-series.md) · [Awesome Lists](awesome-lists.md) · "
            "[类型、受众和难度](discovery-by-type.md) · [自动初筛](discovery-candidates.md) · "
            "[发现报告](../reports/RESOURCE_DISCOVERY_V2.1_REPORT.md)", ""]
    series = ["# HowTo 系列与手册", "",
              "以下入口来自规范目录。具体子项和来源位置见机器可读关系，来源的使用限制需单独核验。", ""]
    series.extend(label(row) for row in resources if row["resource_type"] in PRACTICAL)
    awesome = ["# Awesome Lists 与其他索引集合", "",
               "合集可以帮助定位资料。核验集合存在不等于核验了它的每条外链。", "", "## 规范目录", ""]
    awesome.extend(label(row) for row in resources if row["resource_type"] in COLLECTIONS)
    awesome.extend(["", "## 候选 Awesome Lists", ""])
    indexes_to_show = [r for r in roots if r["screening"] == "screened" and r["resource_type"] == "awesome_list"][:25]
    awesome.extend(label(row) for row in indexes_to_show)
    types = ["# 按类型、受众和难度浏览", "",
             "主目录按类型分开。受众与难度只展示已知标签，缺少证据的记录留作未核定。", ""]
    for kind in sorted({r["resource_type"] for r in resources}):
        types.extend([f"## {kind}", "", *[label(r) for r in resources if r["resource_type"] == kind], ""])
    for title, key in [("已知受众", "audience"), ("已知难度", "skill_level")]:
        types.extend([f"## {title}", ""])
        present = [r for r in resources if r[key] and r[key] != "unknown"]
        types.extend([label(r) for r in present] or ["暂无注明的资料。"])
        types.append("")
    types.extend(["## 特殊分组", "",
                  "- [Awesome 索引与目录](awesome-lists.md)",
                  "- [官方文档和原始来源](official-resources.md)",
                  "- 工具与社区入口保留其类型，可在 [机器可读目录](../data/resource-catalog/resources.jsonl) 按类型读取。",
                  "", "## 编辑推荐等级", "",
                  "新发现入口采用 reference-only 或 needs-review。Flagship、Recommended、Niche 留待有记录的人审。",
                  "候选从 [自动初筛](discovery-candidates.md) 进入独立复核。", ""])
    preview = ["# 自动初筛队列", "",
               f"共有 {len(screened)} 条初筛记录。每个主题最多显示 8 条，完整候选数据含未入初筛项。",
               "展示分数属于机器初筛，标签保持 needs-review。",
               "", "[完整候选 JSONL](../data/resource-catalog/candidates.jsonl) · "
               "[人工复核 CSV](../data/reviews/manual-review-queue.csv)", ""]
    for domain, title in DOMAIN_LABELS.items():
        domain_resources = [row for row in resources if row["primary_domain"] == domain]
        domain_screened = [row for row in screened if row["primary_domain"] == domain]
        head.extend([f"## {title}", "", f"目录 {len(domain_resources)} 条，自动初筛 {len(domain_screened)} 条。", "",
                     *[label(row) for row in domain_resources], ""])
        preview.extend([f"## {title}", "", f"自动初筛 {len(domain_screened)} 条。", "",
                        *[label(row) for row in sorted(domain_screened, key=lambda r: (
                            -r["quality_assessment"]["automated_score"], r["resource_id"]))[:8]], ""])
    return {"discovery-index.md": "\n".join(head), "howto-series.md": "\n".join(series),
            "awesome-lists.md": "\n".join(awesome), "discovery-by-type.md": "\n".join(types),
            "discovery-candidates.md": "\n".join(preview)}


def make_manifest(search, expanded, official, catalog, platform_probes):
    roots, pages = expanded["roots"], search["pages"]
    rows = list(catalog.rows.values())
    start = min(search["started_at"], expanded["started_at"],
                *(item["probe"]["checked_at"] for item in official["entries"]))
    end = max(search["finished_at"], expanded["finished_at"],
              *(item["probe"]["checked_at"] for item in official["entries"]))
    date = timestamp(start).astimezone(SHANGHAI).date().isoformat()
    run_dir = f"data/discovery-runs/{date}"
    previous_manifest = ROOT / run_dir / "manifest.json"
    previous = read_json(previous_manifest) if previous_manifest.is_file() else {}
    base_revision = previous.get("base_revision") if previous.get("started_at") == start else None
    if not base_revision:
        base_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    script_hashes = {}
    for name in ("discover_github", "expand_awesome_indexes", "extract_collection_items", "resource_catalog",
                 "check_resource_links", "score_resources", "deduplicate_resources", "build_resource_catalog",
                 "validate_catalog", "generate_discovery_report"):
        path = ROOT / "scripts" / f"{name}.py"
        script_hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    seed = [row for row in roots if row["group"] in {"requested-index", "added-index", "requested-series"}]
    return {
        "started_at": start, "finished_at": end, "path": "../" + run_dir + "/manifest.json",
        "base_revision": base_revision, "scripts_sha256": script_hashes, "depth_limit": expanded["depth_limit"],
        "counts": {
            "query_groups": len({row["id"] for row in pages}),
            "search_hits": sum(len((row["data"] or {}).get("items", [])) for row in pages),
            "search_pages_ok": sum(row["status"] == "ok" for row in pages),
            "search_pages_incomplete": sum(bool((row["data"] or {}).get("incomplete")) for row in pages),
            "seed_routes": len(seed), "seed_ok": sum(row["fetch_status"] == "ok" for row in seed),
            "index_seed_ok": sum(row["fetch_status"] == "ok" and row["group"].endswith("-index") for row in seed),
            "added_index_ok": sum(row["fetch_status"] == "ok" and row["group"] == "added-index" for row in seed),
            "deepest": max((row["depth"] + bool(row["items"]) for row in roots), default=0),
            "extracted_items": sum(len(row["items"]) for row in roots),
            "children": sum(edge["type"] == "child_of" for edge in catalog.edges.values()),
            "raw_count": catalog.raw_count, "duplicates": len(catalog.events),
        },
        "search_pages": [{**{key: row[key] for key in ("id", "language", "domain", "executed_expression",
                          "sort", "page", "status", "http", "checked_at")},
                          "returned": len((row["data"] or {}).get("items", [])),
                          "incomplete_results": (row["data"] or {}).get("incomplete")} for row in pages],
        "repository_routes": [{
            "repository": row["repository"], "depth": row["depth"], "group": row["group"], "http": row["http"],
            "checked_at": row["checked_at"], "items": len(row["items"]),
            "structure_status": row.get("structure", {}).get("status", "metadata-only"),
            "tree_truncated": row.get("structure", {}).get("tree_truncated"),
            "license_http": row.get("license_http"), "commit": row.get("structure", {}).get("commit_sha"),
            "limitation": row.get("limitation"),
        } for row in roots],
        "link_observations": [{"title": row["title"], "url": row["url"], **row["probe"],
                               "project_metadata": row.get("visible_metadata")} for row in official["entries"]],
        "languages": dict(Counter(row["language"] for row in rows)),
        "risk": dict(Counter(row["risk_level"] for row in rows)),
        "excluded": dict(catalog.rejected),
        "platform_probes": platform_probes,
    }


def build_outputs(catalog, manifest):
    rows = sorted(catalog.rows.values(), key=lambda row: row["resource_id"])
    resources = [row for row in rows if row["screening"] == "catalogued"]
    candidates = [row for row in rows if row["screening"] != "catalogued"]
    relations = [catalog.edges[key] for key in sorted(catalog.edges)]
    files = {f"{CATALOG}/resources.jsonl": lines(resources), f"{CATALOG}/candidates.jsonl": lines(candidates),
             f"{CATALOG}/resource-relations.jsonl": lines(relations)}
    run_dir = manifest["path"].removeprefix("../").removesuffix("/manifest.json")
    files[f"{run_dir}/manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    files[f"{run_dir}/duplicate-events.jsonl"] = lines(catalog.events)
    headers = ("resource_id", "title", "url", "domain", "status", "reason")
    def queue(subset, reason):
        return table_csv(headers, ((r["resource_id"], r["title"], r["canonical_url"], r["primary_domain"],
                                    r["screening"], reason(r)) for r in subset))
    files["data/reviews/manual-review-queue.csv"] = queue(candidates, lambda r: (
        "结构和来源需独立审阅" if r["screening"] == "screened" else "待核验链接、主题或范围"))
    files["data/reviews/license-review.csv"] = queue(
        [r for r in rows if r["license"]["status"] != "verified"], lambda r: r["license"]["status"])
    files["data/reviews/high-risk-review.csv"] = queue(
        [r for r in rows if r["risk_level"] == "high"], lambda r: f"核对权威来源及辖区 {r['jurisdiction']}")
    files["data/reviews/duplicate-review.csv"] = table_csv(
        ("from_id", "relation", "to_id", "evidence"),
        ((r["from_id"], r["type"], r["to_id"], r["evidence"]) for r in relations if not r["verified"]))
    files.update({f"resources/{key}": value for key, value in indexes(resources, candidates).items()})
    files.update({f"reports/{key}": value for key, value in reports(catalog, manifest).items()})
    return files, resources, candidates, relations


def validate_indexes(root):
    folder = root / CATALOG
    resources = list(read_lines(folder / "resources.jsonl"))
    candidates = list(read_lines(folder / "candidates.jsonl"))
    for name, content in indexes(resources, candidates).items():
        existing = (root / "resources" / name).read_text(encoding="utf-8")
        if existing.rstrip("\n") != content.rstrip("\n"):
            raise ValueError(f"stale discovery index: {name}")


def preserve_published(target, resources):
    path = target / CATALOG / "resources.jsonl"
    if not path.is_file():
        return
    current = {row["resource_id"]: row for row in resources}
    for prior in read_lines(path):
        key = prior["resource_id"]
        if key not in current:
            raise ValueError(f"publish would remove an existing catalog resource: {key}")
        assessment = prior["quality_assessment"]
        if assessment["review_status"] == "human-approved" and assessment != current[key]["quality_assessment"]:
            raise ValueError(f"publish would change a human assessment: {key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument("--publish", action="store_true", help="write checked-in outcomes")
    parser.add_argument("--check", action="store_true", help="check saved Markdown indexes without network")
    args = parser.parse_args()
    if args.check:
        validate_indexes(ROOT)
        print("V2.1 discovery indexes verified.")
        return
    if args.dry_run:
        print("Read search.json, expansion.json and links.json. No files will be changed.")
        return
    search, expansion, official = (read_json(args.output / name) for name in
                                   ("search.json", "expansion.json", "links.json"))
    legacy = read_registry(ROOT)
    rules = read_yaml(CONFIG / "discovery-rules.yaml")
    catalog = assemble(legacy, search, expansion, official, args.limit, rules["screened_limit"])
    probe_file = args.output / "platform-probes.json"
    manifest = make_manifest(search, expansion, official, catalog, read_json(probe_file) if probe_file.is_file() else {})
    files, resources, candidates, relations = build_outputs(catalog, manifest)
    print(validate_records(resources, candidates, relations, legacy))
    target = ROOT if args.publish else args.output / "catalog"
    preserve_published(target, resources)
    for path, data in files.items():
        write_text(target / path, data.rstrip("\n") + "\n")
    print("Screened:", sum(row["screening"] == "screened" for row in candidates), "output:", target)


if __name__ == "__main__":
    main()
