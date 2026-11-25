import csv
import io
import unittest
from copy import deepcopy

from scripts.curate_resources import refine_metadata, resource_scope, technical_record
from scripts.curation_identity import child_urls, migrate_rows
from scripts.curation_outputs import REVIEW_COLUMNS, curation_indexes, review_outputs, show_title
from scripts.curation_semantics import assess_risk, classify_sources
from scripts.resource_catalog import github_record, health, record
from scripts.validate_catalog import validate_migrations

DATE = "2026-11-25T01:23:00Z"
REPO = "owner/guide"
ROOT = "https://github.com/" + REPO


def parent():
    metadata = {
        "repository_id": 20, "full_name": REPO, "url": ROOT, "default_branch": "main",
        "created_at": DATE, "updated_at": DATE, "pushed_at": DATE, "archived": False,
        "fork": False, "topics": [], "stars": 10, "forks": 1, "open_issues": 1,
    }
    return github_record(metadata, "learning-study", "howto_series", DATE, origin="github-search")


def child(sha, path="README.md", anchor="#readme", when=DATE):
    url = f"{ROOT}/blob/{sha}/{path}{anchor}"
    entry = record(url, "Step by step", "learning-study", "practical_guide", when,
                   method="github-collection-item", link=health("active", when, "git-tree"),
                   description="Fixture", path=path, source_url=url.split("#")[0], commit=sha)
    entry["source_repository"] = REPO
    return entry


class CurationRefinementTests(unittest.TestCase):
    def test_commit_changes_snapshot_and_keeps_stable_identity(self):
        first = child("a" * 40)
        second = child("b" * 40, when="2026-11-26T01:23:00Z")
        rows, _, ledger, unresolved, ids = migrate_rows([parent(), first], [second], [])
        self.assertEqual(ids[first["resource_id"]], ids[second["resource_id"]])
        row = next(row for row in rows if row["resource_id"] == ids[first["resource_id"]])
        self.assertEqual(row["canonical_url"], ROOT + "/blob/main/README.md#readme")
        self.assertEqual(row["snapshot_url"], second["canonical_url"])
        self.assertEqual(row["source_url"], second["canonical_url"])
        self.assertEqual({item["commit_sha"] for item in row["snapshots"]}, {"a" * 40, "b" * 40})
        self.assertEqual(len(ledger), 2)
        self.assertEqual(unresolved, [])
        validate_migrations(rows, ledger)
        again, _, again_ledger, _, _ = migrate_rows(rows, [second], [], ledger)
        self.assertEqual(again, rows)
        self.assertEqual(again_ledger, ledger)

    def test_distinct_path_anchor_and_version_keep_distinct_ids(self):
        children = [child("a" * 40, path, anchor) for path, anchor in (
            ("README.md", "#readme"), ("README.md", "#steps"),
            ("docs/v1/tutorial.md", ""), ("docs/v2/tutorial.md", ""),
            ("README-fr.md", ""),
        )]
        rows, _, _, _, _ = migrate_rows([parent(), *children], [], [])
        self.assertEqual(len({r["resource_id"] for r in rows}), 6)
        self.assertEqual(len({r["canonical_url"] for r in rows}), 6)
        url, _ = child_urls(children[2]["canonical_url"], REPO, "release/current")
        self.assertIn("/blob/release%2Fcurrent/docs/v1/", url)

    def test_unproven_default_branch_stays_pinned_for_review(self):
        entry = child("a" * 40)
        rows, _, ledger, unresolved, _ = migrate_rows([entry], [], [])
        self.assertEqual(rows[0]["canonical_url"], entry["canonical_url"])
        self.assertEqual(ledger, [])
        self.assertEqual(unresolved, [(entry["resource_id"], entry["canonical_url"])])

    def test_verified_repository_link_is_idempotent(self):
        linked = record(ROOT, "Original resource", "learning-study", "collection", DATE,
                        method="github-collection-link", link=health("needs_review", DATE, "collection-link"),
                        description="Fixture")
        rows, _, _, _, _ = migrate_rows([linked], [parent()], [])
        self.assertEqual(rows[0]["resource_id"], linked["resource_id"])
        self.assertEqual(rows[0]["latest_url"], ROOT)
        self.assertEqual(rows[0]["link_check"]["method"], "github-api")
        self.assertEqual(rows[0]["status"], "active")
        repeated, _, _, _, _ = migrate_rows(rows, [parent()], [])
        self.assertEqual(rows, repeated)

    def test_query_is_provenance_and_weak_or_tied_evidence_is_unclassified(self):
        a = classify_sources(sources=[("Repository description", "MLOps with model deployment", 5)],
                             query_domains=["health-safety"])
        self.assertEqual(a[0], "ai-engineering")
        self.assertEqual(classify_sources(sources=[("Title", "Untitled project", 3)],
                                          query_domains=["finance-law-consumer"])[0], "unclassified")
        self.assertEqual(classify_sources(sources=[("Title", "Linux interview", 3)])[3], "needs-review")

    def test_classification_regressions_from_public_metadata(self):
        for name, description, query, expected in (
            ("FarmSource", "Agricultural supply and farmers marketplace", "health-safety", "professional"),
            ("Study Buddy", "", "finance-law-consumer", "learning-study"),
            ("OpenAI Prompt Packs", "Prompt Packs guide", "health-safety", "ai-everyone"),
            ("free Claude Code", "Claude Code configuration", "finance-law-consumer", "ai-engineering"),
            ("Haushaltsbuch", "Expense tracking app", "health-safety", "finance-law-consumer"),
            ("Korean Law MCP", "MCP server for Korean law statutes and citations", "ai-engineering", "ai-engineering"),
        ):
            with self.subTest(name=name):
                fields = [("Repository name", name, 3), ("Repository description", description, 5)]
                self.assertEqual(classify_sources(sources=fields, query_domains=[query])[0], expected)

    def test_risk_depends_on_function_and_evidence(self):
        self.assertEqual(assess_risk(title="Budget tracker", description="Expense tracking app")[0], "low")
        self.assertEqual(assess_risk(title="Medical paper index", description="Search index of medical literature")[0], "low")
        self.assertEqual(assess_risk(title="Korean law MCP", description="MCP server for Korean law statutes and citations")[1],
                         "reference")
        self.assertEqual(assess_risk(title="Clinical service")[0], "unknown")
        for description in ("Clinical decision support for patients", "Produces personalized legal advice",
                            "Offers personalized investment recommendations"):
            with self.subTest(description=description):
                risk = assess_risk(title="Example application", description=description)
                self.assertEqual(risk[0], "high")
                self.assertTrue(risk[-1])

    def test_prefer_readme_title_and_keep_short_upstream_description(self):
        row = parent()
        upstream = "An information source describing the repository."
        root = {"readme_title": "Practical collection", "readme_path": "README.md", "structure": {"commit_sha": "a" * 40}}
        technical_record(row, root, {"about": upstream, "full_name": REPO}, {})
        self.assertEqual(row["display_title"], "Practical collection")
        self.assertEqual(row["upstream_description"], upstream)
        self.assertEqual(row["summary_status"], "extracted")
        technical_record(row, root, {"about": "abc " * 100, "full_name": REPO},
                         {"summary": "按主题查找指南。", "evidence": "READMe navigation"})
        self.assertLessEqual(len(row["upstream_description"]), 180)
        self.assertEqual(row["curator_summary"], "按主题查找指南。")

    def test_indices_keep_course_out_of_series_and_candidate_link_clickable(self):
        rows, _, _, _, _ = migrate_rows([parent()], [], [])
        refine_metadata(rows, {"pages": []}, {"roots": []}, {"entries": []}, {})
        series = rows[0]
        course = deepcopy(series)
        course.update(display_title="Example Course", resource_type="course", canonical_url="https://example.org/course",
                      status="needs_review")
        self.assertIn("https://example.org/course", show_title(course))
        pages = curation_indexes([series, course], [])
        self.assertNotIn("Example Course", pages["howto-series.md"])
        self.assertIn("Example Course", pages["learning-paths-and-courses.md"])
        section_row = child("a" * 40)
        section_row["snapshot_url"] = section_row["canonical_url"]
        self.assertEqual(resource_scope(section_row, series), "section")

    def test_queues_have_evidence_and_inheritance_requires_review(self):
        root = parent()
        entry = child("a" * 40)
        entry["license"].update(status="verified", content_reuse_allowed=True)
        edge = {"from_id": entry["resource_id"], "type": "child_of", "to_id": root["resource_id"],
                "evidence": "fixture", "verified": True}
        rows, edges, _, _, _ = migrate_rows([root, entry], [], [edge])
        refine_metadata(rows, {"pages": []}, {"roots": []}, {"entries": []}, {})
        document = next(row for row in rows if row["parent_resource_id"])
        self.assertFalse(document["license"]["content_reuse_allowed"])
        self.assertEqual(document["license_inheritance_status"], "needs_review")
        queues, _ = review_outputs(rows, [], rows, edges, [])
        output = csv.DictReader(io.StringIO(queues["data/reviews/candidate-backlog.csv"]))
        self.assertEqual(tuple(output.fieldnames), REVIEW_COLUMNS)
        self.assertTrue(next(output)["suggested_action"])


if __name__ == "__main__":
    unittest.main()
