import base64
import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.build_resource_catalog import lines, preserve_published
from scripts.check_resource_links import probe
from scripts.deduplicate_resources import canonical_url
from scripts.expand_awesome_indexes import collection_items
from scripts.extract_collection_items import parse_document
from scripts.resource_catalog import Catalog, assemble, declared_mirrors, github_record, legal_record
from scripts.score_resources import eligible
from scripts.validate_catalog import CATALOG, validate_records

DATE = "2026-11-25T01:23:00Z"


def metadata(name, key, *, fork=False, parent=None, about="A practical reference"):
    return {
        "repository_id": key, "full_name": name, "url": f"https://github.com/{name}",
        "about": about, "topics": [], "default_branch": "main", "license_spdx": None,
        "stars": 3, "forks": 1, "open_issues": 0, "created_at": DATE, "pushed_at": DATE,
        "updated_at": DATE, "archived": False, "fork": fork, "parent_url": parent,
    }


def github_row(meta):
    return github_record(meta, "digital-life", "practical_guide", DATE, origin="github-search")


class ResourceDiscoveryTests(unittest.TestCase):
    def test_url_preserves_versions_and_normalizes_tracking(self):
        self.assertEqual(canonical_url("HTTPS://GitHub.COM/Owner/Guide/blob/main/README.md?utm_medium=a#readme"),
                         "https://github.com/owner/guide")
        self.assertEqual(canonical_url("https://example.com/guide/?version=2&api_key=x"),
                         "https://example.com/guide?version=2")
        self.assertNotEqual(canonical_url("https://github.com/owner/guide/blob/v1/README.md"),
                            canonical_url("https://github.com/owner/guide/blob/v2/README.md"))

    def test_collection_keeps_translations_and_drops_prose(self):
        markdown = """# Guide
[简体中文版](README-zh.md) · [Deutsch](README-de.md) · [English](README.md)

## Prepare
Private fixture prose that should stay outside discovery outputs.

[Contributing](CONTRIBUTING.md)
"""
        payload = {"path": "README.md", "encoding": "base64", "size": len(markdown.encode()),
                   "content": base64.b64encode(markdown.encode()).decode()}
        repo = metadata("owner/guide", 8)
        extracted = parse_document(payload, repo["url"])
        self.assertNotIn("Private fixture prose", json.dumps(extracted))
        items, _ = collection_items(repo, {"documents": [extracted], "commit_sha": "f" * 40,
                                          "paths": ["README-zh.md", "README-de.md", "CONTRIBUTING.md"]},
                                    {"max_local_items": 10, "max_external_items": 10})
        translations = {row["path"]: row.get("translation") for row in items}
        self.assertEqual(translations["README-zh.md"], "zh-CN")
        self.assertEqual(translations["README-de.md"], "de")
        self.assertNotIn("CONTRIBUTING.md", translations)

    def test_repo_id_alias_and_fork_have_distinct_identities(self):
        graph = Catalog({})
        owner = graph.add(github_row(metadata("author/guide", 8)))
        renamed = graph.add(github_row(metadata("author/new-guide", 8)))
        fork = graph.add(github_row(metadata("translator/guide", 9, fork=True)))
        self.assertEqual(owner, renamed)
        self.assertNotEqual(owner, fork)
        self.assertEqual(graph.rows[owner]["aliases"], ["https://github.com/author/new-guide"])
        self.assertEqual(graph.events[0]["basis"], "github-repository-id")
        self.assertFalse(eligible(graph.rows[fork]))

    def test_mirror_retains_both_endpoints(self):
        graph = Catalog({})
        mirror = metadata("author/mirror", 8, about="Project source code mirror")
        upstream = metadata("author/upstream", 9)
        source, target = graph.add(github_row(mirror)), graph.add(github_row(upstream))
        declared_mirrors(graph, [{"fetch_status": "ok", "metadata": mirror}], [
            {"url": upstream["url"], "mirror_repository": mirror["url"], "source_evidence": "https://example.com/"},
        ])
        self.assertEqual(len(graph.rows), 2)
        self.assertTrue(graph.edges[source, "mirror_of", target]["verified"])

    def test_slash_redirect_resolves(self):
        headers = Message()
        headers["Location"] = "/guide/"
        redirect = HTTPError("https://example.com/guide", 301, "Moved", headers, None)
        with patch("scripts.check_resource_links.robots", return_value=(True, "robots checked")):
            with patch("scripts.check_resource_links.request", side_effect=[redirect, (200, {}, b"")]) as request:
                result = probe("https://example.com/guide")
        self.assertEqual(result["status"], "redirected")
        self.assertEqual(request.call_args.args[1], "https://example.com/guide/")

    def test_assembly_is_repeatable_and_editorial_score_remains_empty(self):
        pages = {"pages": [{"data": {"items": [metadata("author/manual", 8)]}, "domain": "digital-life",
                            "checked_at": DATE, "id": "fixture-guide", "page": 1}]}
        args = ([], pages, {"roots": []}, {"entries": []}, 50, 10)
        graph = assemble(*args)
        rows = list(graph.rows.values())
        self.assertEqual(lines(rows), lines(assemble(*args).rows.values()))
        self.assertEqual(validate_records([], rows, [], [])["candidates"], 1)
        self.assertIsNone(rows[0]["quality_assessment"]["editorial_score"])
        self.assertFalse(legal_record()["content_reuse_allowed"])

    def test_publish_guard_preserves_existing_resources_and_human_review(self):
        row = github_row(metadata("author/guide", 8))
        row["quality_assessment"]["review_status"] = "human-approved"
        with tempfile.TemporaryDirectory() as folder:
            catalog = Path(folder) / CATALOG
            catalog.mkdir(parents=True)
            (catalog / "resources.jsonl").write_text(lines([row]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "remove an existing"):
                preserve_published(Path(folder), [])
            changed = dict(row, quality_assessment={**row["quality_assessment"], "editorial_score": 80})
            with self.assertRaisesRegex(ValueError, "change a human"):
                preserve_published(Path(folder), [changed])


if __name__ == "__main__":
    unittest.main()
