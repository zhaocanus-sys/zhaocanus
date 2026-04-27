import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class SparklineSvgTest(unittest.TestCase):
    def test_requires_at_least_two_non_null_values(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 10, None]), "")

    def test_renders_constant_series_without_dividing_by_zero(self):
        svg = sparkline_svg([5, 5, 5], width=60, height=22)

        self.assertIn('<svg width="60" height="22"', svg)
        self.assertIn('<polyline points="1.0,21.0 30.0,21.0 59.0,21.0"', svg)
        self.assertIn('<circle cx="59.0" cy="21.0" r="2" fill="#16a34a"', svg)

    def test_marks_decreasing_final_point_red_and_can_disable_fill(self):
        svg = sparkline_svg([10, 5], width=20, height=10, color="#123456", fill=False)

        self.assertNotIn("<polygon", svg)
        self.assertIn('stroke="#123456"', svg)
        self.assertIn('<circle cx="19.0" cy="9.0" r="2" fill="#dc2626"', svg)

    def test_ignores_missing_values_when_plotting(self):
        svg = sparkline_svg([None, 1, None, 3], width=20, height=10)

        self.assertIn('<polyline points="1.0,9.0 19.0,1.0"', svg)
        self.assertIn('<circle cx="19.0" cy="1.0" r="2" fill="#16a34a"', svg)


class ExtractTrendValuesTest(unittest.TestCase):
    def test_reverses_recall_results_into_chronological_order_and_appends_today(self):
        history = [
            {"date": "2026-02-27", "metrics": {"revenue": "300.5"}},
            {"date": "2026-02-26", "metrics": {"revenue": 200}},
            {"date": "2026-02-25", "metrics": {"revenue": None}},
        ]

        values = extract_trend_values(history, "revenue", today_val=400)

        self.assertEqual(values, [0.0, 200.0, 300.5, 400.0])

    def test_uses_previous_value_as_baseline_when_history_is_empty(self):
        values = extract_trend_values([], "revenue", today_val=120, prev_val=100)

        self.assertEqual(values, [100.0, 120.0])

    def test_does_not_add_previous_value_when_history_exists(self):
        values = extract_trend_values(
            [{"date": "2026-02-26", "metrics": {"revenue": 80}}],
            "revenue",
            today_val=120,
            prev_val=100,
        )

        self.assertEqual(values, [80.0, 120.0])


if __name__ == "__main__":
    unittest.main()
