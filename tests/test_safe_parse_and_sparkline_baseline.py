"""Regression coverage for API parsers and sparkline empty-history baseline.

safe_float / safe_int sit under all five report aggregators. Comma
amounts, percent strings, and invalid cells must stay finite defaults
or every KPI/DoD card can go NaN.

extract_trend_values leftover (not locked as primary in PR #112):
empty recall + prev_val is the documented 2-point fallback; None
metric cells coerce to 0; recall DESC is reversed into time order.

sparkline leftover (not locked as primary in PR #64/#112): fewer than
two finite points stay empty; a flat last==prev dot is green; fill=False
omits the under-curve polygon.

Does not retest PR #112 missing-key / history-ignores-prev_val /
today_val=None, or downtrend red / fill polygon / mixed-None render.
Does not import generate_telesale_full_report (illegal f-string on main).

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.actions.api_client import safe_float, safe_int
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class SafeParseTests(unittest.TestCase):
    def test_safe_float_strips_comma_percent_and_whitespace(self):
        self.assertEqual(1234.5, safe_float("1,234.5"))
        self.assertEqual(12.5, safe_float("12.5%"))
        self.assertEqual(8.0, safe_float("  8.0 "))
        self.assertEqual(1234.5, safe_float("1,234.50%"))
        self.assertEqual(42.0, safe_float(42))

    def test_safe_float_none_and_invalid_use_default(self):
        self.assertEqual(0.0, safe_float(None))
        self.assertEqual(3.5, safe_float(None, 3.5))
        self.assertEqual(0.0, safe_float(""))
        self.assertEqual(0.0, safe_float("abc"))
        self.assertEqual(-1.0, safe_float("n/a", -1.0))
        self.assertEqual(0.0, safe_float("—"))

    def test_safe_int_truncates_after_same_cleanup(self):
        self.assertEqual(1234, safe_int("1,234.9"))
        self.assertEqual(12, safe_int("12.9%"))
        self.assertEqual(0, safe_int(None))
        self.assertEqual(7, safe_int("x", 7))
        self.assertEqual(3, safe_int(3.9))


class SparklineExtractBaselineTests(unittest.TestCase):
    def test_empty_history_uses_prev_val_as_baseline(self):
        self.assertEqual([10.0], extract_trend_values([], "revenue", prev_val=10))
        self.assertEqual(
            [10.0, 12.0],
            extract_trend_values([], "revenue", today_val=12, prev_val=10),
        )
        self.assertEqual([12.0], extract_trend_values([], "revenue", today_val=12))
        self.assertEqual([], extract_trend_values([], "revenue"))

    def test_none_metric_coerces_to_zero_and_reverses_desc_recall(self):
        history = [
            {"date": "2026-08-28", "metrics": {"revenue": 20}},
            {"date": "2026-08-27", "metrics": {"revenue": None}},
            {"date": "2026-08-26", "metrics": {"revenue": 10}},
        ]
        self.assertEqual(
            [10.0, 0.0, 20.0, 22.0],
            extract_trend_values(history, "revenue", today_val=22),
        )

    def test_sparkline_needs_two_finite_points(self):
        self.assertEqual("", sparkline_svg([]))
        self.assertEqual("", sparkline_svg([5]))
        self.assertEqual("", sparkline_svg([None, None]))

    def test_flat_series_dot_is_green_and_fill_false_omits_polygon(self):
        html = sparkline_svg([10, 10], fill=False)
        self.assertIn("#16a34a", html)
        self.assertNotIn("#dc2626", html)
        self.assertNotIn("<polygon", html)
        self.assertIn("<polyline", html)


if __name__ == "__main__":
    unittest.main()
