"""Create claim-backed drafts from selected, repository-reviewed topic packages."""
import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.build_index import write_indexes
from scripts.common import ROOT, SHANGHAI, read_json, write_text
from scripts.evidence import reviewed_packages, source_registry
from scripts.migrate_guide_metadata import markdown
from scripts.run_research import escape
from scripts.validate_guides import validate_guide, validate_repository

DRAFT_SCHEMA = ".github/codex-draft.schema.json"
TOPIC = re.compile(r"topic-[a-f0-9]{16}\Z")


def guide_path(root, packet):
    return root / "guides" / packet["category"] / (packet["guide_id"].removeprefix("howto-") + ".md")


def choose(root, requested, selection):
    if requested == "none":
        return []
    if requested != "auto" and not TOPIC.fullmatch(requested):
        raise ValueError("requested topic must be auto, none or a topic_id")
    payload = read_json(selection)
    if payload.get("schema_version") != 2:
        raise ValueError("requires version 2 selection")
    selected, used = [], set()
    packages = reviewed_packages(root)
    for entry in payload["topics"]:
        topic = entry["topic"]
        key = topic["topic_id"]
        packet = packages.get(key)
        demand = {row["url"] for row in entry["demand_evidence"] if row["source_id"] in topic["demand_refs"]}
        if (requested not in {"auto", key} or not packet or entry["research_status"] != "editorial-approved"
                or packet["review_status"] != "editorial-approved" or topic["risk"] == "high"
                or packet["risk_level"] == "high" or topic["existing_guide"] != "none"
                or not demand.intersection(packet["demand_source_urls"])):
            continue
        path = guide_path(root, packet)
        if not path.exists() and path not in used:
            selected.append(key)
            used.add(path)
    return selected[:3]


def selected_packages(root, ids):
    if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or len(set(ids)) != len(ids):
        raise ValueError("expected one to three distinct topics")
    approved = reviewed_packages(root)
    result = {}
    for key in ids:
        packet = approved.get(key)
        if (not packet or packet["review_status"] != "editorial-approved" or packet["risk_level"] == "high"
                or guide_path(root, packet).exists()):
            raise ValueError("only new low/medium-risk reviewed packages are eligible")
        result[key] = packet
    if len({guide_path(root, packet) for packet in result.values()}) != len(result):
        raise ValueError("selected topics point to the same guide path")
    return result


def make_prompt(packages):
    trusted = [{k: packet[k] for k in ("topic_id", "title", "brief", "claims", "steps")}
               for packet in packages.values()]
    return ("为每个已审简报选择并排序至少三个已有步骤，用 claim_order 返回对应 claim_id。"
            "优先按前置、操作、结果和验证的依赖排序。只能引用此 topic 下的 ID。"
            "只输出 JSON，不新增事实、引用、元数据或专业审查结论。\n\n"
            + json.dumps(trusted, ensure_ascii=False, indent=2) + "\n")


def render_draft(packet, order, registry, today):
    steps = {step["claim_id"]: step for step in packet["steps"]}
    if not 3 <= len(order) <= 12 or len(set(order)) != len(order) or set(order) - steps.keys():
        raise ValueError("draft must use at least three distinct supported step claims")
    claims = [claim for claim in packet["claims"] if claim["claim_id"] in order]
    source_ids = list(dict.fromkeys(key for c in claims for key in c["supporting_source_ids"]))
    urls = [registry[key]["url"] for key in source_ids]
    keys = ("title", "category", "subcategory", "personas", "age_groups", "occupations",
            "life_stages", "scenarios", "region", "difficulty", "estimated_time", "cost",
            "prerequisites", "risk_level", "evidence_level")
    metadata = {key: packet[key] for key in keys}
    metadata.update(id=packet["guide_id"], content_type="howto", status="draft", execution_status="pending",
                    version="0.1", created_at=today.isoformat(), updated_at=today.isoformat(),
                    last_verified_at=packet["verified_at"], review_due=(today + timedelta(days=60)).isoformat(),
                    sources=urls, claim_evidence=claims)
    brief = packet["brief"]
    lines = [f"# {packet['title']}", "", escape(brief["outcome"]), ""]
    for heading, text in (
        ("适用人群", brief["audience"]), ("前置条件与不适用情况", "；".join(packet["prerequisites"])),
        ("准备、耗时与费用", f"{brief['materials']}。预计 {packet['estimated_time']}，{packet['cost']}"),
    ):
        lines.extend([f"## {heading}", "", escape(text), ""])
    lines.extend(["## 操作步骤与验收", ""])
    for index, key in enumerate(order, 1):
        step = steps[key]
        lines.append(f"{index}. {escape(step['action'])} **验收**　{escape(step['expected'])}（证据 {key}）。")
    lines.append("")
    for heading, field in (("常见错误与排查", "troubleshooting"), ("风险与限制", "limits"),
                           ("最简行动清单", "checklist")):
        lines.extend([f"## {heading}", "", escape(brief[field]), ""])
    lines.extend(["## 参考来源", ""])
    for key in source_ids:
        source = registry[key]
        loc = "、".join(c["source_location"] for c in claims if key in c["supporting_source_ids"])
        lines.append(f"- {escape(loc)}。[{escape(source['title'])}]({source['url']})（访问于 {source['accessed_at']}）。")
    lines.extend(["", "## 核验与版本", "",
                  f"{packet['verified_at']} 核对简报来源。v0.1 草稿，执行效果和适用范围待人工复查。"])
    return metadata, markdown(metadata, "\n".join(lines))


def stage(root, ids, draft, today):
    packages = selected_packages(root, ids)
    if not Draft202012Validator(read_json(root / DRAFT_SCHEMA)).is_valid(draft):
        raise ValueError("model output does not match the draft schema")
    outputs = {item["topic_id"]: item["claim_order"] for item in draft["drafts"]}
    if len(outputs) != len(draft["drafts"]) or outputs.keys() != packages.keys():
        raise ValueError("model output must cover exactly the requested topics")
    registry = source_registry(root)
    pending = {}
    for key, packet in packages.items():
        metadata, content = render_draft(packet, outputs[key], registry, today)
        validate_guide(metadata, root, registry)
        pending[guide_path(root, packet)] = content
    created = []
    try:
        for path, content in pending.items():
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                created.append(path)
                stream.write(content)
        validate_repository(root)
    except (OSError, ValueError):
        for path in created:
            path.unlink()
        raise
    write_indexes(root)
    return created


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    select = sub.add_parser("choose")
    select.add_argument("--requested", default="auto")
    select.add_argument("--selection", type=Path, required=True)
    prepare = sub.add_parser("prompt")
    prepare.add_argument("topics")
    prepare.add_argument("path", type=Path)
    apply = sub.add_parser("stage")
    apply.add_argument("topics")
    args = parser.parse_args()
    if args.command == "choose":
        print(json.dumps(choose(ROOT, args.requested, args.selection), separators=(",", ":")))
    elif args.command == "prompt":
        write_text(args.path, make_prompt(selected_packages(ROOT, json.loads(args.topics))))
    else:
        encoded = os.environ.get("CODEX_DRAFT", "")
        if not encoded or len(encoded.encode("utf-8")) > 20_000:
            raise SystemExit("Codex output absent or too large")
        try:
            created = stage(ROOT, json.loads(args.topics), json.loads(encoded), datetime.now(SHANGHAI).date())
        except (KeyError, TypeError, ValueError):
            raise SystemExit("Codex draft did not pass evidence validation") from None
        print(f"Staged {len(created)} reviewed topic draft(s).")


if __name__ == "__main__":
    main()
