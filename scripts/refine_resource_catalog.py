"""Build a source-backed curation release from saved observations and a Git baseline."""
import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from scripts.build_resource_catalog import lines, table_csv
from scripts.build_resource_index import read_registry
from scripts.common import ROOT, read_json, read_yaml, write_text
from scripts.curation_identity import migrate_rows
from scripts.curation_outputs import curation_indexes, review_outputs, risk_sample
from scripts.curation_reports import coverage, reports
from scripts.curate_resources import VERSION, prioritize, refine_metadata
from scripts.discover_github import CONFIG
from scripts.resource_catalog import assemble
from scripts.validate_catalog import CATALOG, read_lines, validate_migrations, validate_records

RUN = "data/curation-runs/v2.1.1"
HISTORICAL = "data/discovery-runs/2026-11-25/manifest.json"


def historical_file(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT).decode("utf-8")


def catalog_at(revision):
    return [json.loads(line) for name in ("resources", "candidates")
            for line in historical_file(revision, f"{CATALOG}/{name}.jsonl").splitlines() if line]


def baseline_summary(rows, edges, previous):
    return {**previous["counts"], "catalogued": sum(row["screening"] == "catalogued" for row in rows),
            "screened": sum(row["screening"] == "screened" for row in rows),
            "candidates": sum(row["screening"] != "catalogued" for row in rows),
            "relations": len(edges), "risk": dict(Counter(row["risk_level"] for row in rows)),
            "screened_types": dict(Counter(row["resource_type"] for row in rows if row["screening"] == "screened")),
            "editorial_scores": sum(row["quality_assessment"]["editorial_score"] is not None for row in rows),
            "coverage": coverage([row for row in rows if row["screening"] == "catalogued"])}


def snapshot_manifest(base, old, edges, previous, search, expansion, official, platform_observations, rejected):
    pages = search["pages"]
    roots = expansion["roots"]
    covered = {(p["id"], p["page"], p["checked_at"]) for p in previous["search_pages"]}
    return {
        "schema_version": VERSION, "baseline_revision": base,
        "baseline_counts": baseline_summary(old, edges, previous),
        "search": {"groups": len({p["id"] for p in pages}), "pages": len(pages),
                   "successful": sum(p["status"] == "ok" for p in pages),
                   "cached_baseline_pages": sum((p["id"], p["page"], p["checked_at"]) in covered for p in pages),
                   "hits": sum(len((p["data"] or {}).get("items", [])) for p in pages),
                   "incomplete": sum(bool((p["data"] or {}).get("incomplete")) for p in pages),
                   "empty": sum(p["status"] == "ok" and not (p["data"] or {}).get("items") for p in pages),
                   "finished_at": search["finished_at"]},
        "search_pages": [{**{k: p[k] for k in ("id", "language", "domain", "page", "checked_at", "http", "status", "executed_expression")},
                          "count": len((p["data"] or {}).get("items", []))} for p in pages],
        "expansion": {"routes": len(roots), "resolved": sum(row["fetch_status"] == "ok" for row in roots),
                      "deepest": max(row["depth"] + bool(row["items"]) for row in roots),
                      "items": sum(len(row["items"]) for row in roots), "finished_at": expansion["finished_at"]},
        "repository_routes": [{"repository": r["repository"], "via": r["via"], "level": r["depth"], "items": len(r["items"]),
                               "status": r["fetch_status"], "type_hint": r["resource_type"], "limitation": r.get("limitation"),
                               "outline_only": bool(r.get("outline_only")), "commit": r.get("structure", {}).get("commit_sha")}
                              for r in roots],
        "official_link_evidence": {"reused": len(official["entries"]), "origin": HISTORICAL},
        "platforms": {platform: [{k: v for k, v in result.items() if k != "candidates"} for result in results]
                      for platform, results in platform_observations.items()},
        "filtered_observations": dict(rejected),
    }


def preserve_prior(prior, rows, ledger):
    current = {row["resource_id"]: row for row in rows}
    aliases = {entry["old_resource_id"]: entry["resource_id"] for entry in ledger}
    for previous in prior:
        key = previous["resource_id"]
        record = current.get(aliases.get(key, key))
        if not record:
            raise ValueError(f"resource lost during refinement: {key}")
        if previous["legacy_v2"] != record["legacy_v2"]:
            raise ValueError(f"legacy editorial snapshot changed: {key}")
        editorial = previous["quality_assessment"]
        if editorial["review_status"] == "human-approved" and editorial != record["quality_assessment"]:
            raise ValueError(f"human-approved assessment changed: {key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", help="exact Git commit of the V2.1 baseline")
    parser.add_argument("--output", type=Path, default=ROOT / "out/resource-curation", help="saved acquisition evidence")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    published_run = ROOT / RUN / "manifest.json"
    baseline = args.baseline or (read_json(published_run)["baseline_revision"] if published_run.exists() else "")
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        parser.error("provide the exact baseline commit with --baseline on first run")

    search, expansion, official = (read_json(args.output / name) for name in ("search.json", "expansion.json", "links.json"))
    platform_file = args.output / "platform-probes.json"
    platforms = read_json(platform_file) if platform_file.exists() else {}
    legacy = read_registry(ROOT)
    rules = read_yaml(CONFIG / "discovery-rules.yaml")
    editorial = read_yaml(CONFIG / "curation-evidence.yaml")
    prior = catalog_at(baseline)
    prior_edges = [json.loads(line) for line in historical_file(baseline, f"{CATALOG}/resource-relations.jsonl").splitlines() if line]
    previous_run = json.loads(historical_file(baseline, HISTORICAL))
    derived = assemble(legacy, search, expansion, official, 5000, rules["screened_limit"])
    previous_migrations = []
    primary, linked = prior, prior_edges
    ledger_path = ROOT / RUN / "id-migrations.jsonl"
    if ledger_path.exists():
        previous_migrations = list(read_lines(ledger_path))
        primary = [row for name in ("resources", "candidates") for row in read_lines(ROOT / CATALOG / f"{name}.jsonl")]
        linked = list(read_lines(ROOT / CATALOG / "resource-relations.jsonl"))
    rows, edges, ledger, unresolved, id_map = migrate_rows(
        primary, list(derived.rows.values()), [*linked, *derived.edges.values()], previous_migrations,
    )
    id_map.update((entry["old_resource_id"], entry["resource_id"]) for entry in ledger)
    preserve_prior(prior, rows, ledger)
    refine_metadata(rows, search, expansion, official, editorial)
    preserve_prior(primary, rows, ledger)
    resources, priority, backlog, quotas = prioritize(rows, rules["screened_limit"])
    candidates = priority + backlog
    resources.sort(key=lambda r: r["resource_id"])
    candidates.sort(key=lambda r: r["resource_id"])
    edges.sort(key=lambda edge: (edge["from_id"], edge["type"], edge["to_id"]))
    ledger.sort(key=lambda entry: entry["old_resource_id"])
    run = snapshot_manifest(baseline, prior, prior_edges, previous_run, search, expansion, official, platforms, derived.rejected)
    run["record_counts"] = validate_records(resources, candidates, edges, legacy)
    validate_migrations(rows, ledger)
    run["screened_by_pool"] = quotas
    run["scope"] = dict(sorted(Counter(row["resource_scope"] for row in rows).items()))
    queues, counts = review_outputs(rows, priority, backlog, edges, unresolved)
    run["review_queues"] = counts

    sample = risk_sample(prior, rows, id_map)
    verdict_file = CONFIG / "risk-audit-v2.1.1.yaml"
    verdicts = read_yaml(verdict_file) if verdict_file.exists() else {}
    sample_ids = {key for _, key, _ in sample}
    if args.publish and (len(sample) < 100 or set(verdicts) != sample_ids):
        parser.error("complete the reproducible risk sample before publishing")
    audit_values = []
    for group, key, row in sample:
        audit = verdicts.get(key, {})
        audit_values.append((group, key, row["resource_id"], row["display_title"], row["canonical_url"],
                             row["risk_level"], row["risk_scope"], audit.get("verdict"), audit.get("reason"),
                             row["upstream_description"] or row["curator_summary"] or "",
                             " | ".join(row["risk_evidence"])))
    audit_csv = table_csv(("sample", "sample_id", "resource_id", "title", "source", "level", "scope", "verdict",
                           "reason", "observed_summary", "risk_evidence"), audit_values)
    target = ROOT if args.publish else args.output / "catalog"
    outputs = {
        f"{CATALOG}/resources.jsonl": lines(resources), f"{CATALOG}/candidates.jsonl": lines(candidates),
        f"{CATALOG}/resource-relations.jsonl": lines(edges), f"{RUN}/id-migrations.jsonl": lines(ledger),
        f"{RUN}/manifest.json": json.dumps(run, ensure_ascii=False, indent=2) + "\n",
        f"{RUN}/risk-sample.csv": audit_csv,
    }
    outputs.update(queues)
    outputs.update({f"resources/{k}": v for k, v in curation_indexes(resources, candidates).items()})
    outputs.update(reports(prior, resources, candidates, priority, edges, ledger, unresolved, counts, quotas, sample, verdicts, run))
    for name, content in outputs.items():
        write_text(target / name, content.rstrip("\n") + "\n")
    print(run["record_counts"], "screened:", len(priority), "migrations:", len(ledger), "scope:", run["scope"])


if __name__ == "__main__":
    main()
