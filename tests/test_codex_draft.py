import json
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts.collect_douyin import collect
from scripts.common import ROOT, timestamp, write_json
from scripts.deduplicate_topics import topic_id
from scripts.evidence import reviewed_packages
from scripts.normalize_topics import normalize
from scripts.run_research import write_report
from scripts.stage_codex_draft import choose, stage
from scripts.validate_guides import read_guide


class DraftTests(unittest.TestCase):
    def test_dynamic_selection_and_claim_only_stage(self):
        now = timestamp("2026-11-25T01:00:00Z")
        # Synthetic observation and evidence used only to test wiring and refusal paths.
        observed = normalize(dict(platform="other", kind="community", method="manual",
            title="如何核对测试备份和家庭照片？", url="https://example.com/synthetic-observation",
            task="合成样本任务", signal_type="demand", observed_at=now))
        key = topic_id([observed])
        pack = {
            "topic_id": key, "title": "怎样核对合成备份任务中的三个可观察结果？",
            "guide_id": "howto-test-synthetic-backup", "category": "life", "subcategory": "home-and-household",
            "personas": ["unknown"], "age_groups": ["unknown"], "occupations": ["unknown"],
            "life_stages": ["unknown"], "scenarios": ["device-backup"], "region": "global",
            "difficulty": "beginner", "estimated_time": "20 分钟", "cost": "已有设备测试",
            "prerequisites": ["仅在自建虚构资料和受控工作目录中执行。"],
            "risk_level": "medium", "risk_reason": "合成例子覆盖需回退的备份操作。",
            "evidence_level": "A", "review_status": "editorial-approved", "verified_at": "2026-11-24",
            "demand_source_urls": [observed["url"]],
            "brief": dict.fromkeys(("outcome", "audience", "materials", "troubleshooting", "limits", "checklist"),
                                   "合成测试专用文本，用来检查步骤渲染与状态存在。"),
            "claims": [], "steps": [],
        }
        for number in range(1, 4):
            claim_id = f"synthetic-{number}"
            pack["claims"].append(dict(claim_id=claim_id, claim_text="合成证据记录用于测试。",
                claim_type="fact", supporting_source_ids=["apple-iphone"], support_level="direct",
                source_location="Synthetic test selector", applicable_region="global",
                applicable_version="fixture", limitations="Synthetic fixture only",
                reviewer_status="editorial-checked"))
            pack["steps"].append(dict(claim_id=claim_id, action="读取自建备份文件的测试标签。",
                                      expected="核对结果与虚构样例的标签一致。"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("data", "guides", ".github", "resources"):
                shutil.copytree(ROOT / folder, root / folder)
            for name in ("README.md", "README_EN.md"):
                shutil.copyfile(ROOT / name, root / name)
            write_json(root / "data/evidence" / f"{key}.json", pack)
            report = root / "out"
            write_report(report, "monthly", now - timedelta(days=30), now, [], [observed], [], 0,
                         packages=reviewed_packages(root))
            selection = report / "selection.json"
            self.assertEqual(choose(root, "auto", selection), [key])
            self.assertEqual(choose(root, "topic-1111111111111111", selection), [])
            with self.assertRaises(ValueError):
                stage(root, [key], {"drafts": [{"topic_id": key, "claim_order": ["synthetic-1", "synthetic-2", "invented"]}]}, date(2026, 11, 25))
            ordered = [x["claim_id"] for x in pack["claims"]]
            result = stage(root, [key], {"drafts": [{"topic_id": key, "claim_order": ordered}]}, date(2026, 11, 25))
            metadata, _ = read_guide(result[0], root)
            self.assertEqual((metadata["status"], metadata["risk_level"]), ("draft", "medium"))
            self.assertEqual(metadata["occupations"], ["unknown"])
            self.assertEqual(metadata["last_verified_at"], "2026-11-24")
            self.assertEqual(choose(root, "auto", selection), [])

    def test_stage_rejects_claims_with_invalid_source_provenance(self):
        from scripts.evidence import source_registry, validate_claims
        claim = dict(claim_id="example", claim_text="合成的事实断言用于校验。",
            claim_type="fact", supporting_source_ids=["ftc-phishing"], support_level="direct",
            source_location="Examples", applicable_region="global",
            applicable_version="fixture", limitations="Synthetic example", reviewer_status="editorial-checked")
        with self.assertRaisesRegex(ValueError, "regions"):
            validate_claims([claim], source_registry(), "global")

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
