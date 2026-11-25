"""Shared validation for editorial sources, claim matrices and reviewed briefs."""
from pathlib import Path

from scripts.common import ROOT, read_json, read_yaml, validate
from scripts.normalize_topics import public_url

AUTHORITATIVE = {"official", "primary-research", "systematic-review", "institution"}


def source_registry(root=ROOT):
    by_id = {}
    urls = set()
    for entry in read_yaml(root / "data/source-registry.yaml"):
        validate("source-registry", entry)
        public_url(entry["url"])
        if entry["source_id"] in by_id or entry["url"] in urls:
            raise ValueError("duplicate source registry ID or URL")
        by_id[entry["source_id"]] = entry
        urls.add(entry["url"])
    return by_id


def validate_claims(claims, registry, region, *, ready=False):
    ids = set()
    urls = set()
    for claim in claims:
        if claim["claim_id"] in ids:
            raise ValueError("duplicate claim ID")
        ids.add(claim["claim_id"])
        if claim["applicable_region"] not in {region, "global", "unknown"}:
            raise ValueError("claim and artifact regions differ")
        try:
            entries = [registry[key] for key in claim["supporting_source_ids"]]
        except KeyError as error:
            raise ValueError("claim source missing from registry") from error
        sourced = any(row["enabled"] and row["source_type"] in AUTHORITATIVE for row in entries)
        if claim["claim_type"] == "fact":
            if not sourced or claim["support_level"] == "unsupported":
                raise ValueError("fact needs traceable non-social support")
            if any(row["region"] not in {"global", claim["applicable_region"]} for row in entries):
                raise ValueError("fact source and claim regions differ")
            if ready and claim["support_level"] != "direct":
                raise ValueError("eligible factual claims require direct support")
        if ready and claim["reviewer_status"] not in {"editorial-checked", "expert-approved"}:
            raise ValueError("evidence needs editorial review")
        urls.update(entry["url"] for entry in entries)
    return urls


def load_package(path: Path, registry):
    packet = read_json(path)
    validate("evidence", packet)
    if path.stem != packet["topic_id"]:
        raise ValueError("evidence filename must match topic_id")
    known = {claim["claim_id"] for claim in packet["claims"]}
    identifiers = [step["claim_id"] for step in packet["steps"]]
    if set(identifiers) - known or len(identifiers) != len(set(identifiers)):
        raise ValueError("steps must cite unique claims from the matrix")
    review = packet["review_status"] == "editorial-approved"
    validate_claims(packet["claims"], registry, packet["region"], ready=review)
    if review and (not packet["demand_source_urls"] or packet["verified_at"] == "pending"
                   or packet["evidence_level"] in {"C", "pending"} or len(identifiers) < 3
                   or packet["region"] == "unknown" or packet["category"] == "unknown"
                   or packet["subcategory"] == "unknown" or packet["difficulty"] == "unknown"):
        raise ValueError("approved evidence needs demand provenance, scope, date and three supported steps")
    if review:
        attached = {claim["claim_id"]: claim for claim in packet["claims"]}
        for step_id in identifiers:
            claim = attached[step_id]
            if (claim["support_level"] != "direct"
                    or not any(registry[key]["source_type"] in AUTHORITATIVE and registry[key]["enabled"]
                               for key in claim["supporting_source_ids"])):
                raise ValueError("each approved step needs direct authoritative support")
    return packet


def reviewed_packages(root=ROOT):
    registry = source_registry(root)
    return {path.stem: load_package(path, registry)
            for path in sorted((root / "data/evidence").glob("topic-*.json"))}


def matching_package(topic, observations, packages):
    packet = packages.get(topic["topic_id"])
    if packet is None or packet["review_status"] != "editorial-approved":
        return None
    if set(packet["demand_source_urls"]).intersection(
        row["url"] for row in observations if row.get("signal_type") == "demand"
    ):
        return packet
    return None

def pending_package(topic, demand_evidence):
    """Create an explicit, unreviewed matrix for the research queue."""
    packet = {
        "topic_id": topic["topic_id"], "title": topic["title"],
        "guide_id": (topic["existing_guide"] if topic["existing_guide"] != "none"
                     else "howto-" + topic["topic_id"]),
        "category": "unknown" if topic["category"] == "unclassified" else topic["category"],
        "subcategory": "unknown", "personas": topic["personas"], "age_groups": ["unknown"],
        "occupations": ["unknown"], "life_stages": ["unknown"], "scenarios": topic["scenarios"],
        "region": topic["region"], "difficulty": "unknown", "estimated_time": "unknown",
        "cost": "unknown", "prerequisites": ["pending"], "risk_level": topic["risk"],
        "risk_reason": topic["risk_reason"], "evidence_level": "pending", "review_status": "pending",
        "verified_at": "pending", "demand_source_urls": sorted({row["url"] for row in demand_evidence}),
        "brief": dict.fromkeys(("outcome", "audience", "materials", "troubleshooting", "limits", "checklist"),
                                "pending"),
        "claims": [], "steps": [],
    }
    validate("evidence", packet)
    return packet
