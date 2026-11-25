"""Apply source-backed metadata, classification and priority screening to resource records."""
from collections import Counter, defaultdict
import re

from scripts.curation_identity import COLLECTION_ITEM, pinned_parts
from scripts.curation_semantics import (
    AUXILIARY, DOMAINS, GUIDES, LEARNING, ROOT_TYPES, assess_risk, classify_sources, verification_level,
)
from scripts.extract_collection_items import suitable
from scripts.deduplicate_resources import github_name
from scripts.normalize_topics import clean_text
from scripts.score_resources import COLLECTIONS, assess

TITLE_PLACEHOLDER = re.compile(r"^(?:contents|table of contents|readme|目录|index|home)$", re.I)
VERSION = "2.1.1"
QUOTAS = {"howto": 35, "learning": 20, "official": 20, "indexes": 15, "auxiliary": 10}
TRIAGE_LIMITATIONS = [
    "Uses structure and source metadata. Instructional quality, completeness and applicability require review.",
    "Stars express participation and do not establish accuracy.",
]


def public_description(value):
    value = clean_text(value or "", 180)
    return value if suitable(value) else None


def evidence_lookup(search, expansion, official):
    roots = {row["metadata"]["full_name"].casefold(): row for row in expansion["roots"] if row.get("metadata")}
    repositories = {}
    queries = {}
    for page in search["pages"]:
        queries[page["id"]] = page["domain"]
        for metadata in (page["data"] or {}).get("items", []):
            repositories[metadata["full_name"].casefold()] = metadata
    for name, root in roots.items():
        repositories[name] = root["metadata"]
    entries = {}
    for item in official["entries"]:
        from scripts.resource_catalog import official_record

        observed = official_record(item)
        if observed:
            entries[observed["canonical_url"]] = item
    return roots, repositories, entries, queries


def resource_scope(row, parent):
    kind = row["resource_type"]
    method = row["provenance"]["method"]
    if row["github_metrics"]:
        if kind in AUXILIARY:
            return "tool"
        return "collection_root" if kind in ROOT_TYPES else "standalone_resource"
    if method == COLLECTION_ITEM:
        snapshot = pinned_parts(row["snapshot_url"] or row["canonical_url"])
        if snapshot and snapshot[-1]:
            return "section"
        if parent and parent["resource_type"] in LEARNING | {"tutorial"} and kind != "collection":
            return "course_unit"
        return "document"
    if method == "github-collection-link":
        return "external_resource"
    if kind in AUXILIARY:
        return "tool"
    return "collection_root" if kind in ROOT_TYPES else "standalone_resource"


def technical_record(row, root, metadata, editorial):
    upstream_title = root.get("readme_title")
    if not upstream_title or TITLE_PLACEHOLDER.fullmatch(upstream_title):
        upstream_title = None
    upstream_title = upstream_title or metadata.get("full_name", "").split("/")[-1] or None
    row["display_title"] = clean_text(editorial.get("title") or upstream_title or row["title"], 180)
    row["upstream_title"] = clean_text(upstream_title, 180) if upstream_title else None
    row["upstream_description"] = public_description(metadata.get("about"))
    evidence = []
    old = row["legacy_v2"]
    if editorial.get("summary"):
        row["curator_summary"] = editorial["summary"]
        evidence.append(editorial["evidence"])
        status = "generated-needs-review"
    elif old:
        row["curator_summary"] = old["description"]
        evidence.append("V2 registry description")
        status = "human-reviewed"
    elif row["provenance"]["method"] in {"official-entry", "gitlab-project"}:
        row["curator_summary"] = row["description"]
        evidence.append("Reviewed entry metadata from the discovery registry")
        status = "generated-needs-review"
    else:
        row["curator_summary"] = None
        status = "extracted" if row["upstream_description"] or root.get("readme_title") else "unavailable"

    if root.get("readme_title") and root.get("structure", {}).get("commit_sha"):
        from scripts.expand_awesome_indexes import ref_url

        pinned = ref_url(row["canonical_url"], root["structure"]["commit_sha"], root["readme_path"])
        evidence.append(pinned)
        row["snapshot_url"] = pinned
        row["source_url"] = pinned
    elif metadata:
        evidence.append("Public repository description or name")
    if row["provenance"]["method"] == COLLECTION_ITEM:
        evidence.append("Pinned title or file entry")
    row["summary_evidence"] = evidence
    row["summary_status"] = status
    row["summary_checked_at"] = (root.get("structure", {}).get("readme_checked_at")
                                 or row["provenance"]["last_checked_at"]) if evidence else None


def apply_metadata(row, editorial, official):
    old = row["legacy_v2"]
    if editorial:
        row["resource_type"] = editorial.get("type", row["resource_type"])
        row["language"] = editorial.get("language", row["language"])
        row["skill_level"] = editorial.get("skill_level", row["skill_level"])
    if editorial.get("audience"):
        row["audience"] = list(editorial["audience"])
        evidence = [editorial["evidence"]]
    elif official.get("audience") and row["audience"]:
        evidence = ["Publisher entry target audience: " + official["url"]]
    else:
        evidence = []
    if old and not row["audience"] and old["audience"] == "一般读者及对应设备使用者":
        row["audience"] = ["general-public"]
        evidence = ["V2 registry audience: " + old["id"]]
    row["audience_evidence"] = evidence
    row["audience_confidence"] = "medium" if evidence else "low"
    row["life_stage_evidence"] = []
    row["region_evidence"] = []
    if row["region"] != "unknown":
        source = official.get("url") or (f"V2 registry limits: {old['id']}" if old else None)
        if source:
            row["region_evidence"] = [source]
    row["jurisdiction_evidence"] = list(row["region_evidence"]) if row["jurisdiction"] != "unknown" else []


def refine_metadata(rows, search, expansion, official, editorial):
    roots, metadata, official_entries, queries = evidence_lookup(search, expansion, official)
    by_id = {row["resource_id"]: row for row in rows}
    # Roots and independent URLs are resolved before collection node context is used.
    rows.sort(key=lambda row: (bool(row["parent_resource_id"]), row["resource_id"]))
    labels = {}
    for row in rows:
        method = row["provenance"]["method"]
        name = (row["source_repository"] or "").casefold()
        if not name and row["legacy_v2"] and row["legacy_v2"]["github"]:
            name = github_name(row["canonical_url"]) or ""
            row["source_repository"] = name or None
        root = roots.get(name, {}) if row["github_metrics"] else {}
        repo = metadata.get(name, {}) if row["github_metrics"] else {}
        verified = editorial.get(name, {}) if row["github_metrics"] or (
            row["legacy_v2"] and row["legacy_v2"]["github"]
        ) else {}
        public_entry = official_entries.get(row["canonical_url"], {})
        parent = by_id.get(row["parent_resource_id"])
        asserted = None
        if verified:
            asserted = (verified["domain"], verified["evidence"])
        elif public_entry and public_entry.get("platform") != "gitlab":
            asserted = (public_entry["domain"], "Reviewed official entry metadata")
        elif row["legacy_v2"]:
            asserted = (row["primary_domain"], "V2 registry category")
        apply_metadata(row, verified, public_entry)
        if public_entry.get("resource_type") in AUXILIARY:
            row["resource_type"] = public_entry["resource_type"]
        row["resource_scope"] = resource_scope(row, parent)
        technical_record(row, root, repo, verified)
        headings = " ".join(item["title"] for item in root.get("headings", [])[:12])
        descriptions = row["upstream_description"] or row["curator_summary"] or ""
        query_domains = sorted({queries[ref.rsplit(":", 1)[0]] for ref in row["provenance"]["query_refs"]
                                if ref.rsplit(":", 1)[0] in queries})
        fields = [("README H1", root.get("readme_title"), 6), ("README sections", headings, 5),
                  ("Repository description", descriptions, 5), ("Topics", " ".join(row["topics"]), 4),
                  ("Repository name" if name and repo else "Title", name.split("/")[-1] if name and repo else row["title"], 3),
                  ("File path", row["provenance"]["source_file_path"], 3)]
        parent_domain = labels.get(parent["resource_id"]) if parent else None
        category = classify_sources(sources=fields, asserted=asserted, parent=parent_domain, query_domains=query_domains)
        (row["primary_domain"], row["domains"], row["classification_confidence"],
         row["classification_status"], row["classification_evidence"], row["alternative_domains"]) = category
        labels[row["resource_id"]] = row["primary_domain"]
        row["query_domains"] = query_domains
        impact = assess_risk(title=row["display_title"], description=descriptions, headings=headings,
                             kind=row["resource_type"], official=bool(public_entry) or method == "official-entry",
                             outline=bool(root.get("outline_only")) or (parent and parent.get("requires_expert_review")))
        (row["risk_level"], row["risk_scope"], row["risk_evidence"],
         row["risk_confidence"], row["requires_expert_review"]) = impact
        if row["resource_id"] == "github-geekan-howtolivelonger":
            row["risk_level"] = "medium"
            row["risk_scope"] = "reference"
            row["risk_evidence"] = ["Multilingual longevity collection and outline. Claims require specialist verification."]
            row["requires_expert_review"] = True
        if row["resource_scope"] in {"document", "section", "course_unit"}:
            row["license_scope"] = "document"
            row["license_inherited_from"] = parent["resource_id"] if parent else None
            row["license_inheritance_status"] = "needs_review"
        else:
            row["license_scope"] = "repository" if row["github_metrics"] or (
                row["legacy_v2"] and row["legacy_v2"]["github"]
            ) else (
                "third-party-link" if row["resource_scope"] == "external_resource" else "unknown")
            row["license_inherited_from"] = None
            row["license_inheritance_status"] = "not_applicable"
        if row["schema_version"] != VERSION or row["license_inheritance_status"] != "verified":
            if row["license_scope"] == "document":
                row["license"]["content_reuse_allowed"] = False
        row["verification_level"] = verification_level(row)
        row["schema_version"] = VERSION
        if row["quality_assessment"]["review_status"] != "human-approved":
            old_grade = row["quality_assessment"]
            rating = assess(row)
            rating.update(review_status=old_grade["review_status"], recommendation=old_grade["recommendation"])
            row["quality_assessment"] = rating
        rating = row["quality_assessment"]
        row.update(score_type="structural_triage", score_confidence=rating["confidence"],
                   score_evidence=rating["evidence"], score_limitations=TRIAGE_LIMITATIONS)


def pool_key(row):
    kind, scope = row["resource_type"], row["resource_scope"]
    if scope == "section":
        return None
    if row["provenance"]["method"] == "official-entry" and row["verification_level"] == "public_page_reachable":
        return "official"
    if scope == "course_unit":
        return "learning"
    if kind == "howto_series" or kind in GUIDES:
        return "howto"
    if kind in LEARNING | {"tutorial"} or scope == "course_unit":
        return "learning"
    if kind in COLLECTIONS:
        return "indexes"
    if kind in AUXILIARY:
        return "auxiliary"
    return None


def priority_order(row):
    root_priority = {"content_reviewed": 4, "expert_reviewed": 4, "structure_inspected": 3, "document_exists": 2,
                     "public_page_reachable": 2, "repository_exists": 1, "metadata_only": 0}
    return (-root_priority[row["verification_level"]], -row["quality_assessment"]["automated_score"], row["resource_id"])


def triage_eligible(row):
    if not pool_key(row) or row["status"] not in {"active", "redirected"}:
        return False
    if row["requires_expert_review"] or row["risk_level"] == "high" or (row["github_metrics"] or {}).get("fork"):
        return False
    if row["primary_domain"] == "unclassified" or row["verification_level"] == "metadata_only":
        return False
    return row["quality_assessment"]["automated_score"] >= (20 if pool_key(row) == "auxiliary" else 24)


def prioritize(rows, limit):
    assigned = [row for row in rows if row["screening"] == "catalogued"]
    candidates = [row for row in rows if row["screening"] != "catalogued"]
    groups = defaultdict(lambda: defaultdict(list))
    for row in candidates:
        row["screening"] = "needs_review"
        if triage_eligible(row):
            groups[pool_key(row)][row["primary_domain"]].append(row)

    result, counts = [], {}
    for bucket, ratio in QUOTAS.items():
        by_domain = groups[bucket]
        for items in by_domain.values():
            items.sort(key=priority_order)
        portion = limit * ratio // 100
        selected = []
        for index in range(max(map(len, by_domain.values()), default=0)):
            for domain in DOMAINS:
                domain_rows = by_domain.get(domain, [])
                if len(selected) < portion and index < len(domain_rows):
                    selected.append(domain_rows[index])
        counts[bucket] = {"target": portion, "eligible": sum(map(len, by_domain.values())), "selected": len(selected)}
        result.extend(selected)
    for row in result:
        row["screening"] = "screened"
    remaining = sorted((row for row in candidates if row["screening"] != "screened"), key=priority_order)
    return assigned, result, remaining, counts
