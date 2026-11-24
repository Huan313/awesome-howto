import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts.collect_douyin import collect
from scripts.common import ROOT, timestamp
from scripts.stage_codex_draft import choose, stage
from scripts.validate_guides import read_guide


class DraftTests(unittest.TestCase):
    def test_staging_no_model_metadata_and_no_overwrite(self):
        text = "使用自行构造的测试条目验证结果并记录异常。"
        draft = dict.fromkeys(("intro", "audience", "prerequisites", "materials",
                               "troubleshooting", "limits", "checklist"), text)
        draft["steps"] = [{"action": text, "check": text}] * 3
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("data", "guides", ".github"):
                shutil.copytree(ROOT / folder, root / folder)
            selection = root / "selection.json"
            selection.write_text(json.dumps({"categories": ["learning"]}), encoding="utf-8")
            topic = choose(root, "auto", selection)
            self.assertEqual(topic, "zotero-deduplicate-library")
            with self.assertRaises(ValueError):
                stage(root, topic, {**draft, "status": "published"}, date(2026, 11, 25))
            result = stage(root, topic, draft, date(2026, 11, 25))
            self.assertEqual(read_guide(result)[0]["status"], "draft")
            self.assertEqual(choose(root, "auto", selection), "")
            with self.assertRaises(ValueError):
                stage(root, topic, draft, date(2026, 11, 25))

    def test_douyin_reads_official_heat_field_without_live_credentials(self):
        class StubClient:
            def json(self, url, headers):
                self.url, self.headers = url, headers
                return {"data": {"error_code": 0, "list": [{"sentence": "备份测试", "hot_level": 123}]}}
        client = StubClient()
        with patch.dict(os.environ, {"DOUYIN_CLIENT_TOKEN": "test-value"}):
            rows = list(collect(client, timestamp("2026-11-25T00:00:00Z")))
        self.assertEqual(client.url, "https://open.douyin.com/hotsearch/sentences/")
        self.assertEqual(client.headers["access-token"], "test-value")
        self.assertEqual(rows[0]["metrics"], {"heat": 123})
