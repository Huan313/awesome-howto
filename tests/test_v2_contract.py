import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import collect_douyin, collect_reddit
from scripts.build_index import render
from scripts.build_resource_index import read_registry
from scripts.build_site import stage_site
from scripts.common import ROOT, timestamp
from scripts.ingest_social_csv import parse_rows
from scripts.migrate_guide_metadata import migrate
from scripts.normalize_topics import normalize
from scripts.score_topics import score_group, score_group_v2
from scripts.update_resource_metadata import refresh


class ContractTests(unittest.TestCase):
    def test_v2_separates_updates_and_demand_and_reports_unknowns(self):
        stamp = "2026-11-25T01:00:00Z"
        official = normalize(dict(platform="rss", kind="official", method="rss", observed_at=stamp,
            title="如何核对备份并更换 Android 手机？", url="https://example.com/official"))
        result = score_group_v2([official], [])
        self.assertEqual(result["baseline"]["score"], score_group([official], [])["score"])
        for name in ("demand", "trend", "persona_confidence", "evidence_readiness"):
            self.assertEqual(result["signals_v2"][name], "unknown")
        self.assertEqual(result["growth"], "unknown")
        self.assertEqual(result["personas"], ["unknown"])

    def test_csv_template_is_skipped_and_public_observations_are_minimal(self):
        text = (ROOT / "templates/social-observation-template.csv").read_text(encoding="utf-8")
        self.assertEqual(list(parse_rows(io.StringIO(text), "xiaohongshu")), [])
        actual = text.replace("示例·换手机前需要整理备份", "虚构测试·核对恢复")
        actual = actual.replace("unknown,true", "unknown,false").replace("000000000000000000000000,", "000000000000000000000000?xsec_token=discard,")
        records = list(parse_rows(io.StringIO(actual), "xiaohongshu"))
        self.assertEqual(len(records), 1)
        self.assertNotIn("?", records[0]["url"])
        self.assertEqual(records[0]["metrics"], {"comments": 0})
        for mutated in (actual.replace("comments,0", "forks,0"),
                        actual.replace("www.xiaohongshu.com", "www.example.com")):
            with self.assertRaises(ValueError):
                list(parse_rows(io.StringIO(mutated), "xiaohongshu"))
        with self.assertRaises(ValueError):
            list(parse_rows(io.StringIO(actual + actual.splitlines(keepends=True)[1]), "xiaohongshu"))

    def test_missing_platform_credentials_skip(self):
        now = timestamp("2026-11-25T01:00:00Z")
        with patch.dict("os.environ", {"ENABLE_DOUYIN": "true", "DOUYIN_CLIENT_TOKEN": "",
                                      "DOUYIN_CLIENT_KEY": "", "DOUYIN_CLIENT_SECRET": "",
                                      "ENABLE_REDDIT": "true", "REDDIT_ACCESS_TOKEN": ""}):
            self.assertEqual(list(collect_douyin.units({"enabled_by": "ENABLE_DOUYIN"}, now)), [])
            self.assertEqual(list(collect_reddit.units({"enabled_by": "ENABLE_REDDIT", "communities": ["all"]}, now)), [])

    def test_readme_indexes_keep_unpublished_and_dimensions_distinct(self):
        pages = render(ROOT)
        self.assertIn("暂无指南", pages["age-groups.md"])
        self.assertIn("软件开发从业者", pages["occupations.md"])
        self.assertIn("## 待专业审核", pages["review-status.md"])

    def test_pages_staging_does_not_copy_unpublished_guides(self):
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            from scripts.validate_guides import validate_repository
            entries, _ = validate_repository()
            expected = [path for path, meta in entries if meta["status"] == "published"]
            self.assertEqual(stage_site(ROOT, site), len(expected))
            staged = {path.relative_to(site / "docs") for path in (site / "docs/guides").glob("*/*.md")}
            self.assertEqual(staged, {path.relative_to(ROOT) for path in expected})
            self.assertTrue((site / "docs/resources/official-resources.md").is_file())

    def test_unknown_license_is_never_upgraded_to_copy_permission(self):
        row = next(row for row in read_registry() if row["github"] and row["github"]["license"] == "unknown")
        class Client:
            def json(self, url):
                if url.endswith("/license"):
                    return {"html_url": "https://github.com/example/repo/blob/main/LICENSE"}
                return dict(stargazers_count=1, forks_count=0, pushed_at="2026-11-25T00:00:00Z",
                            archived=False, license={"spdx_id": "NOASSERTION"})
        self.assertEqual(refresh(row, Client(), "2026-11-25")["use_mode"], "reference-only")

    def test_migration_requires_per_article_annotations(self):
        with self.assertRaises(ValueError):
            migrate({"status": "review-required"}, {"occupations": ["unknown"]})
