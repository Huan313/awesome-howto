"""Explainable triage. Automated scores convey inspection evidence only."""
from datetime import date
import math

WEIGHTS = {"content": 25, "credibility": 25, "actionability": 20,
           "maintenance": 15, "community": 10, "metadata": 5}
PRACTICAL = {"howto_series", "practical_guide", "handbook", "manual", "cookbook", "playbook",
             "field_guide", "tutorial", "learning_path", "curriculum", "course", "cheatsheet", "book"}
COLLECTIONS = {"awesome_list", "resource_directory", "collection", "bibliography"}


def assess(row):
    github = row["github_metrics"] or {}
    verified = row["status"] in {"active", "redirected", "archived"}
    method = row["link_check"]["method"]
    structure = row["structure"]
    archived = row["status"] == "archived"
    publisher = row["publisher"]
    last_push = github.get("pushed_at")
    inspected = structure["headings"] or structure["local_items"]
    content = min(13, 4 + inspected // 3) if inspected else 3 if row["resource_type"] != "unknown" else 0
    actionability = 10 if row["resource_type"] in PRACTICAL and (inspected or method == "git-tree") else (
        6 if row["resource_type"] in PRACTICAL | COLLECTIONS | {"official_reference"} else 0)
    credibility = 19 if row["provenance"]["method"] == "official-entry" and verified else (
        8 if verified and (github or method == "git-tree") else 1 if publisher else 0)
    if last_push and not archived:
        age = (date.fromisoformat(row["provenance"]["last_checked_at"][:10])
               - date.fromisoformat(last_push[:10])).days
        maintenance = 12 if age <= 90 else 8 if age <= 365 else 3
    else:
        maintenance = 4 if verified and not archived else 0
    community = min(6, round(math.log10(1 + github.get("stars", 0)))) if github else 0
    metadata = sum(bool(value) for value in (
        publisher, row["language"] != "unknown", row["region"] != "unknown",
        row["license"]["status"] == "verified", row["resource_type"] != "unknown",
    ))
    scores = dict(content=content, credibility=credibility, actionability=actionability,
                  maintenance=maintenance, community=community, metadata=metadata)
    evidence = [method] if verified else []
    if inspected:
        evidence.append(f"structural headings={structure['headings']}; local items={structure['local_items']}")
    if last_push:
        evidence.append("GitHub API push timestamp")
    if github:
        evidence.append("GitHub participation snapshot, capped at six points")
    return {"automated_score": sum(scores.values()), "editorial_score": None,
            "score_breakdown": scores, "evidence": evidence,
            "confidence": "medium" if verified and (inspected or credibility == 19) else "low",
            "limitations": ["Inspection uses structure and metadata. Full instructional quality was not rated."],
            "review_status": "needs_review",
            "recommendation": "needs-review"}


def eligible(row):
    rating = row["quality_assessment"]
    return (row["status"] in {"active", "redirected"} and row["risk_level"] != "high"
            and not (row["github_metrics"] or {}).get("fork")
            and row["resource_type"] in PRACTICAL | COLLECTIONS | {"official_reference", "wiki"}
            and rating["score_breakdown"]["actionability"] >= 6
            and rating["automated_score"] >= 25)
