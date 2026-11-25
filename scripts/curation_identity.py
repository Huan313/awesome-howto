"""Migrate collection identities while retaining pinned evidence and old IDs."""
from copy import deepcopy
import re
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from scripts.deduplicate_resources import canonical_url, stable_id

COMMIT = re.compile(r"[0-9a-f]{40}\Z")
COLLECTION_ITEM = "github-collection-item"


def pinned_parts(url):
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/", 4)
    if (parts.hostname != "github.com" or len(segments) != 5 or segments[2] != "blob"
            or not COMMIT.fullmatch(segments[3]) or parts.query):
        return None
    repo = "/".join(segments[:2]).casefold()
    return repo, segments[3], unquote(segments[4]), parts.fragment


def child_urls(snapshot_url, repository, branch):
    pinned = pinned_parts(snapshot_url)
    if not pinned or pinned[0] != repository.casefold() or not branch:
        raise ValueError("snapshot and branch metadata must identify the same repository")
    _, _, path, fragment = pinned
    latest = urlunsplit(("https", "github.com", f"/{pinned[0]}/blob/{quote(branch, safe='')}/{quote(path, safe='/')}",
                         "", fragment))
    return canonical_url(latest, collapse_readme=False), snapshot_url


def migration_candidate(row, branches):
    snapshot = row.get("snapshot_url") or row["canonical_url"]
    pinned = pinned_parts(snapshot)
    if row["provenance"]["method"] != COLLECTION_ITEM:
        return None
    repo = (row["source_repository"] or "").casefold()
    commit = row["provenance"]["source_commit_sha"]
    if not pinned or pinned[:2] != (repo, commit) or not branches.get(repo):
        return None
    return child_urls(snapshot, repo, branches[repo])


def migrate_rows(old_rows, observations, relations, prior_migrations=()):
    rows, url_ids, id_map = {}, {}, {}
    history = {entry["old_resource_id"]: deepcopy(entry) for entry in prior_migrations}
    possible_collisions = []
    branches = {row["github_metrics"]["full_name"].casefold(): row["github_metrics"]["default_branch"]
                for row in [*old_rows, *observations] if row["github_metrics"]}
    for row in [*old_rows, *observations]:
        current = deepcopy(row)
        key, url = current["resource_id"], current["canonical_url"]
        provenance = current["provenance"]
        urls = migration_candidate(current, branches)
        current.setdefault("identity_aliases", [])
        current.setdefault("latest_url", None)
        current.setdefault("snapshot_url", None)
        current.setdefault("source_url", provenance["source_url"])
        current.setdefault("snapshots", [])
        if urls:
            latest, snapshot = urls
            new_id = stable_id(latest)
            current["latest_url"] = latest
            current["snapshot_url"] = snapshot
            current["source_url"] = snapshot
            current["canonical_url"] = latest
            current["aliases"] = sorted((set(current["aliases"]) | {snapshot}) - {latest})
            observation = {
                "url": snapshot, "observed_source_url": provenance["source_url"],
                "commit_sha": provenance["source_commit_sha"],
            }
            if observation not in current["snapshots"]:
                current["snapshots"] = sorted([*current["snapshots"], observation],
                                              key=lambda entry: (entry["url"], entry["observed_source_url"]))
            if key != new_id:
                current["identity_aliases"] = sorted(set(current["identity_aliases"] + [key]))
                history[key] = {
                    "old_resource_id": key, "resource_id": new_id, "relation": "supersedes",
                    "old_canonical_url": url, "canonical_url": latest, "snapshot_url": snapshot,
                    "source_url": provenance["source_url"], "source_commit_sha": provenance["source_commit_sha"],
                    "evidence": "Same repository, default-branch file path and fragment; verified pinned source",
                }
            url, current["resource_id"] = latest, new_id
        elif provenance["method"] == COLLECTION_ITEM and pinned_parts(url):
            possible_collisions.append((key, url))
        elif current["github_metrics"]:
            current["latest_url"] = url

        resolved = url_ids.get(url, current["resource_id"])
        id_map[key] = resolved
        if resolved not in rows:
            rows[resolved] = current
            url_ids[url] = resolved
        else:
            merge_observation(rows[resolved], current)
    for entry in history.values():
        entry["resource_id"] = id_map.get(entry["resource_id"], entry["resource_id"])
    combined = {}
    for edge in relations:
        src, dst = id_map.get(edge["from_id"], edge["from_id"]), id_map.get(edge["to_id"], edge["to_id"])
        if src == dst:
            continue
        key = src, edge["type"], dst
        if key not in combined or edge["verified"]:
            combined[key] = {**edge, "from_id": src, "to_id": dst}
    possible_collisions = sorted({(id_map[old], url) for old, url in possible_collisions})
    reconnect_parents(rows, combined)
    return list(rows.values()), list(combined.values()), list(history.values()), possible_collisions, id_map


def merge_observation(row, new):
    same_identity = row["canonical_url"] == new["canonical_url"]
    if not same_identity:
        raise ValueError("different canonical URLs share a stable resource ID")
    for field in ("aliases", "identity_aliases", "alternative_titles"):
        row[field] = sorted(set(row[field]) | set(new[field]))
    row["snapshots"] = [entry for _, entry in sorted({(entry["url"], entry["observed_source_url"]): entry
                                                     for entry in row["snapshots"] + new["snapshots"]}.items())]
    reviewed = row["quality_assessment"]["review_status"] == "human-approved"
    if new["snapshot_url"] and (not row["snapshot_url"] or
                               new["provenance"]["last_checked_at"] > row["provenance"]["last_checked_at"]):
        for field in ("snapshot_url", "source_url", "latest_url", "link_check", "status", "provenance"):
            row[field] = new[field]
    if not reviewed and new["structure"]["headings"] > row["structure"]["headings"]:
        row["structure"] = new["structure"]
    metrics = new["github_metrics"]
    if metrics and (not row["github_metrics"] or
                    metrics["metadata_checked_at"] > row["github_metrics"]["metadata_checked_at"]):
        for field in ("source_repository", "github_metrics", "publisher", "topics"):
            row[field] = new[field]
        row["latest_url"] = row["canonical_url"]
        if not reviewed and new["license"]["status"] in {"verified", "mixed"}:
            row["license"] = new["license"]
    if metrics and new["link_check"]["method"] == "github-api" and (
        row["link_check"]["method"] == "collection-link"
        or new["link_check"]["checked_at"] > row["link_check"]["checked_at"]
    ):
        row["link_check"] = new["link_check"]
        row["status"] = new["status"]
        row["provenance"]["last_checked_at"] = new["link_check"]["checked_at"]
    if not row["legacy_v2"] and new["legacy_v2"]:
        raise ValueError("legacy snapshot must be the primary observation")


def reconnect_parents(rows, edges):
    original = {key: set(row["child_resource_ids"]) for key, row in rows.items()}
    for row in rows.values():
        row["parent_resource_id"] = None
        row["child_resource_ids"] = []
    for (src, kind, dst), _ in sorted(edges.items()):
        if kind != "child_of":
            continue
        rows[dst]["child_resource_ids"].append(src)
        if not rows[src]["parent_resource_id"] or src in original[dst]:
            rows[src]["parent_resource_id"] = dst
    for row in rows.values():
        row["child_resource_ids"].sort()
        row["child_item_count"] = len(row["child_resource_ids"])
