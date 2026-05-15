import unittest

from agent_system.actions.report_sparkline import (
    extract_trend_values,
    sparkline_svg,
)


class SparklineSvgTests(unittest.TestCase):
    def test_requires_at_least_two_non_null_values(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None]), "")
        self.assertEqual(sparkline_svg([12, None]), "")

    def test_flat_series_renders_without_fill_and_marks_non_decrease_green(self):
        svg = sparkline_svg([5, 5, 5], width=30, height=12, fill=False)

        self.assertIn('<svg width="30" height="12"', svg)
        self.assertIn("<polyline", svg)
        self.assertIn("<circle", svg)
        self.assertIn('fill="#16a34a"', svg)
        self.assertNotIn("<polygon", svg)

    def test_decreasing_series_marks_latest_point_red(self):
        svg = sparkline_svg([8, 4], fill=False)

        self.assertIn('fill="#dc2626"', svg)


class ExtractTrendValuesTests(unittest.TestCase):
    def test_reverses_latest_first_history_and_normalizes_missing_metrics(self):
        history = [
            {"date": "2026-02-27", "metrics": {"amt": "30"}},
            {"date": "2026-02-26", "metrics": {"amt": None}},
            {"date": "2026-02-25", "metrics": {"other": 99}},
        ]

        self.assertEqual(
            extract_trend_values(history, "amt", today_val="40", prev_val=20),
            [0.0, 0.0, 30.0, 40.0],
        )

    def test_uses_previous_value_only_when_history_is_empty(self):
        self.assertEqual(
            extract_trend_values([], "amt", today_val=40, prev_val=20),
            [20.0, 40.0],
        )


if __name__ == "__main__":
    unittest.main()
