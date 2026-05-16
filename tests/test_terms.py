import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from terms import resolve_term


class ResolveTermTests(unittest.TestCase):
    def test_uses_current_year_before_or_during_term_month(self):
        self.assertEqual(resolve_term("spring", datetime(2026, 1, 15)), "202602")
        self.assertEqual(resolve_term("summer", datetime(2026, 5, 16)), "202605")
        self.assertEqual(resolve_term("fall", datetime(2026, 8, 1)), "202608")

    def test_uses_next_year_after_term_month(self):
        self.assertEqual(resolve_term("spring", datetime(2026, 3, 1)), "202702")
        self.assertEqual(resolve_term("summer", datetime(2026, 6, 1)), "202705")
        self.assertEqual(resolve_term("fall", datetime(2026, 12, 1)), "202708")

    def test_normalizes_case_and_rejects_invalid_season(self):
        self.assertEqual(resolve_term("Fall", datetime(2026, 1, 1)), "202608")
        with self.assertRaises(ValueError):
            resolve_term("winter", datetime(2026, 1, 1))


if __name__ == "__main__":
    unittest.main()
