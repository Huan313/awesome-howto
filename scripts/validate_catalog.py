"""Validate the checked-in resource graph and legacy preservation."""
import argparse
import json
from pathlib import Path

from scripts.build_resource_index import read_registry
from scripts.common import ROOT, validate
from scripts.deduplicate_resources import canonical_url
from scripts.score_resources import eligible

CATALOG = "data/resource-catalog"


def read_lines(path):
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError as error:
                    raise ValueError(f"invalid JSONL at {path.name}:{number}") from error


def validate_records(resources, candidates, relations, legacy):
    rows, urls, repos = {}, set(), set()
    for row in resources + candidates:
        validate("resource-catalog", row)
        key, url = row["resource_id"], row["canonical_url"]
        if key in rows or url in urls or canonical_url(url) != url or url in row["aliases"]:
            raise ValueError(f"duplicate or noncanonical identity: {key}")
        if row["github_metrics"]:
            repo_id = row["github_metrics"]["repository_id"]
            if repo_id in repos:
                raise ValueError(f"duplicate GitHub repository ID: {key}")
            repos.add(repo_id)
        urls.add(url)
        rows[key] = row
        if row["primary_domain"] not in row["domains"]:
            raise ValueError(f"primary domain missing: {key}")
        if row["license"]["status"] != "verified" and row["license"]["content_reuse_allowed"]:
            raise ValueError(f"unverified license grants reuse: {key}")
        if row["status"] != row["link_check"]["status"]:
            raise ValueError(f"contradictory link status: {key}")
        rating = row["quality_assessment"]
        if rating["automated_score"] != sum(rating["score_breakdown"].values()):
            raise ValueError(f"automated score is not reproducible: {key}")
        if rating["editorial_score"] is not None and rating["review_status"] != "human-approved":
            raise ValueError(f"editorial rating has no human approval: {key}")
        if row["screening"] == "screened" and not eligible(row):
            raise ValueError(f"screened record does not meet the triage gate: {key}")
        if row["child_item_count"] != len(row["child_resource_ids"]):
            raise ValueError(f"child count mismatch: {key}")
    if any(row["screening"] != "catalogued" for row in resources) or any(
        row["screening"] == "catalogued" for row in candidates
    ):
        raise ValueError("catalogued resources and candidates must remain separate")
    for existing in legacy:
        if existing["id"] not in rows or rows[existing["id"]]["legacy_v2"] != existing:
            raise ValueError(f"legacy grade or resource lost: {existing['id']}")
    edges = set()
    for relation in relations:
        validate("resource-relation", relation)
        source, kind, target = relation["from_id"], relation["type"], relation["to_id"]
        item = source, kind, target
        if source not in rows or target not in rows or source == target or item in edges:
            raise ValueError(f"missing or duplicate relation: {item}")
        edges.add(item)
    children = {(child, "child_of", key) for key, row in rows.items() for child in row["child_resource_ids"]}
    if children != {edge for edge in edges if edge[1] == "child_of"}:
        raise ValueError("parent/child indexes and edges differ")
    for key, row in rows.items():
        parent = row["parent_resource_id"]
        if parent and (key, "child_of", parent) not in children:
            raise ValueError(f"primary parent edge missing: {key}")
        seen = {key}
        while parent:
            if parent in seen:
                raise ValueError(f"primary parent cycle: {key}")
            seen.add(parent)
            parent = rows[parent]["parent_resource_id"]
    return {"catalogued": len(resources), "candidates": len(candidates), "relations": len(relations)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root
    data = root / CATALOG
    result = validate_records(list(read_lines(data / "resources.jsonl")),
                              list(read_lines(data / "candidates.jsonl")),
                              list(read_lines(data / "resource-relations.jsonl")), read_registry(root))
    print("Resource graph validated:", result)


if __name__ == "__main__":
    main()
