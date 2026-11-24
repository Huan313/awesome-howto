import unittest
from scripts.deduplicate_topics import cluster


class DeduplicationTests(unittest.TestCase):
    def test_titles_and_topic_keys(self):
        observations = [
            dict(source_id="a", title="如何备份 iPhone？", topic_key="iphone-backup"),
            dict(source_id="b", title="给 iPhone 建立备份", topic_key="iphone-backup"),
            dict(source_id="c", title="用 Zotero 整理参考文献"),
            dict(source_id="d", title="如何备份 iPhone"),
        ]
        groups = [{item["source_id"] for item in group} for group in cluster(observations)]
        self.assertCountEqual(groups, [{"a", "b", "d"}, {"c"}])

    def test_short_unrelated_titles_do_not_collide(self):
        groups = cluster([dict(source_id="a", title="AI"), dict(source_id="b", title="AI 课程")])
        self.assertEqual(len(groups), 2)

    def test_unrelated_douyin_hot_words_share_a_board_url(self):
        items = [dict(source_id=name, title=name, url="https://www.douyin.com/hot", platform="douyin")
                 for name in ("如何备份手机", "如何读论文")]
        self.assertEqual(len(cluster(items)), 2)
