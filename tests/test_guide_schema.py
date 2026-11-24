import unittest
from scripts.validate_guides import validate_guide, validate_repository


class GuideTests(unittest.TestCase):
    def test_checked_in_guides(self):
        guides = validate_repository()[0]
        self.assertGreaterEqual(len(guides), 8)

    def test_high_risk_cannot_be_published(self):
        valid = validate_repository()[0][0][1]
        with self.assertRaises(ValueError):
            validate_guide({**valid, "risk_level": "high", "status": "published"})
        with self.assertRaises(ValueError):
            validate_guide({**valid, "review_due": "2025-01-01"})
