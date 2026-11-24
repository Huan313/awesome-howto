import unittest
from scripts.normalize_topics import normalize, public_url


class SourceTests(unittest.TestCase):
    def test_manual_sources_drop_private_fields_and_tracking(self):
        stamp = "2026-11-25T01:00:00Z"
        item = normalize(dict(platform="xiaohongshu", title="<b>硬盘备份</b>",
                              url="https://www.xiaohongshu.com/explore/123?xsec_token=private",
                              method="manual", observed_at=stamp, author="hidden",
                              metrics={"likes": 3, "unknown": 9}))
        self.assertEqual(item["url"], "https://www.xiaohongshu.com/explore/123")
        self.assertEqual(item["title"], "硬盘备份")
        self.assertEqual(item["metrics"], {"likes": 3})
        self.assertNotIn("author", item)
        self.assertEqual(item["event_at"], stamp)

    def test_private_hosts_and_login_are_rejected(self):
        for value in ["http://github.com/a", "https://127.0.0.1/x", "https://user:pass@github.com/a",
                      "https://foo.local/foo", "https://www.xiaohongshu.com/user/profile/a"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                public_url(value)

    def test_content_identifiers_survive_tracking_removal(self):
        self.assertEqual(public_url("https://news.ycombinator.com/item?id=123&tracking=private"),
                         "https://news.ycombinator.com/item?id=123")
        self.assertEqual(public_url("https://www.youtube.com/watch?v=abcdefghijk&si=private"),
                         "https://www.youtube.com/watch?v=abcdefghijk")
