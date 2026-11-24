import unittest
from scripts.score_topics import weighted_score, decision, metric_growth


class ScoringTests(unittest.TestCase):
    def test_weights(self):
        self.assertEqual(weighted_score(dict(
            demand=80, momentum=50, evidence=100, actionability=70, novelty=30,
        )), 72)

    def test_gate_applies_before_score(self):
        self.assertEqual(decision(90, high_risk=True, evidence=0, social_only=False)[0], "blocked")
        self.assertEqual(decision(90, high_risk=False, evidence=80, social_only=True)[0], "observe")
        self.assertEqual(decision(65, high_risk=False, evidence=40, social_only=False)[0], "candidate")

    def test_growth_requires_same_series_distinct_times_and_positive_baseline(self):
        old = dict(platform="douyin", url="https://www.douyin.com/hot", query="term",
                   observed_at="2026-11-25T00:00:00Z", metrics={"heat": 10})
        new = {**old, "observed_at": "2026-11-25T00:10:00Z", "metrics": {"heat": 15}}
        self.assertEqual(metric_growth([old, new])[0][-1], 50.0)
        self.assertEqual(metric_growth([old, {**new, "platform": "xiaohongshu"}]), [])
        self.assertEqual(metric_growth([old, {**new, "observed_at": old["observed_at"]}]), [])
