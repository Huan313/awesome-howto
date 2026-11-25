import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.common import ROOT, read_yaml
from scripts.validate_catalog import (
    TOPIC_TYPES, check_catalog_diff, check_labels, read_index, resource_url, validate_catalog,
)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = read_yaml(ROOT / "data/taxonomy.yml")
        cls.policy = read_yaml(ROOT / "data/source-policy.yml")

    def test_catalog_and_topic_bank_are_consistent(self):
        result = validate_catalog(ROOT)
        self.assertEqual(len(result["pages"]), 13)
        self.assertEqual(set(result["pages"]) - set(self.taxonomy["domains"]),
                         {"howto-series", "handbooks-and-courses", "awesome-indexes"})

    def test_url_identity_ignores_tracking_and_keeps_content_keys(self):
        self.assertEqual(resource_url("https://github.com/Owner/Guide/blob/main/README.md?utm_source=x"),
                         resource_url("https://Github.com/owner/guide/"))
        self.assertNotEqual(resource_url("https://www.example.org/help?q=phone"),
                            resource_url("https://www.example.org/help?q=computer"))
        self.assertNotEqual(resource_url("https://www.example.org/help#one"),
                            resource_url("https://www.example.org/help#two"))
        with self.assertRaises(ValueError):
            resource_url("https://www.example.org/help?Access_Token=fixture")

    def test_topics_reject_misplaced_collection_types(self):
        with TemporaryDirectory() as directory:
            page = Path(directory) / "topic.md"
            page.write_text("# Topic\n\n- [Source](https://example.org/) — 有具体任务。 `Awesome List` · `中文`\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected type"):
                list(read_index(page, "learning-research", TOPIC_TYPES, self.taxonomy, self.policy))

    def test_protected_topics_require_real_scope_and_explicit_review(self):
        with self.assertRaisesRegex(ValueError, "dated human review"):
            check_labels(["HowTo", "中文", "中国大陆"], "www.nhc.gov.cn", "health-safety",
                         TOPIC_TYPES, self.taxonomy, self.policy)
        with self.assertRaisesRegex(ValueError, "approved primary source"):
            check_labels(["HowTo", "中文", "中国大陆", "高风险", "已人工复核", "核验 2026-11-25", "审核记录 #1"],
                         "www.nhc.gov.cn.example.org", "health-safety", TOPIC_TYPES, self.taxonomy, self.policy)
        self.assertEqual(check_labels(["官方入口", "中文", "中国大陆", "核验 2026-11-25"], "www.nhc.gov.cn",
                                      "health-safety", TOPIC_TYPES, self.taxonomy, self.policy),
                         ("官方入口", "中文"))

    def test_diff_guard_rejects_raw_candidates(self):
        with patch("scripts.validate_catalog.subprocess.check_output", return_value="catalog/candidates.jsonl\0"):
            with self.assertRaisesRegex(ValueError, "keep candidate data"):
                check_catalog_diff(ROOT, "a" * 40)
