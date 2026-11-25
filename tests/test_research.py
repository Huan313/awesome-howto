import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.common import read_json
from scripts.normalize_topics import normalize
from scripts.run_research import during_window, load_history, write_report


class ResearchTests(unittest.TestCase):
    def test_window_requires_both_event_and_observation(self):
        now = datetime(2026, 11, 25, 1, tzinfo=timezone.utc)
        recent = dict(event_at=now - timedelta(days=1), observed_at=now)
        start = now - timedelta(days=7)
        self.assertTrue(during_window(recent, start, now))
        self.assertFalse(during_window({**recent, "event_at": start - timedelta(seconds=1)}, start, now))

    def test_report_round_trip_and_risk_exclusion(self):
        now = datetime(2026, 11, 25, 1, tzinfo=timezone.utc)
        common = dict(observed_at=now, method="rss", platform="rss", kind="official")
        records = [
            normalize(dict(common, title="如何备份家庭照片和旧手机", url="https://www.microsoft.com/backup")),
            normalize(dict(common, title="绕过验证码", url="https://github.com/public/example")),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            start = now - timedelta(days=7)
            selected = write_report(root, "weekly", start, now, [], records, [], 0)
            self.assertEqual(len(selected), 1)
            selection = read_json(root / 'selection.json')
            self.assertEqual(selection['topics'][0]['source_refs'], [records[0]['source_id']])
            self.assertEqual(selection['topics'][0]['research_status'], 'needs-research')
            matrix = next((root / "evidence").glob("*.json"))
            self.assertEqual(read_json(matrix)["claims"], [])
            self.assertEqual(read_json(matrix)["review_status"], "pending")
            cache = root / "source-cache/observations.json"
            self.assertEqual(len(read_json(cache)), 1)
            items, count = load_history([cache], start, now)
            self.assertEqual((items, count), ([records[0]], 1))
