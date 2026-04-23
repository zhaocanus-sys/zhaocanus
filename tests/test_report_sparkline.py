import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class SparklineSvgTests(unittest.TestCase):
    def test_returns_empty_when_less_than_two_points(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 5]), "")

    def test_generates_svg_with_fill_and_green_dot_for_upward_trend(self):
        svg = sparkline_svg([1, 3, 5], color="#123456")

        self.assertIn('<svg width="60" height="22"', svg)
        self.assertIn('<polygon points="', svg)
        self.assertIn('fill="#123456"', svg)
        self.assertIn('<polyline points="', svg)
        self.assertIn('fill="#16a34a"', svg)

    def test_generates_svg_without_fill_and_red_dot_for_downward_trend(self):
        svg = sparkline_svg([5, 2], fill=False)

        self.assertNotIn("<polygon", svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertIn('1.0,1.0 59.0,21.0', svg)

    def test_flat_values_are_supported(self):
        svg = sparkline_svg([7, 7])

        self.assertIn('1.0,21.0 59.0,21.0', svg)
        self.assertIn('fill="#16a34a"', svg)


class ExtractTrendValuesTests(unittest.TestCase):
    def test_reverses_history_order_and_appends_today_value(self):
        history_episodes = [
            {"date": "2026-03-03", "metrics": {"kpi": 20}},
            {"date": "2026-03-02", "metrics": {"kpi": 10}},
        ]

        values = extract_trend_values(history_episodes, "kpi", today_val=30)

        self.assertEqual(values, [10.0, 20.0, 30.0])

    def test_uses_zero_for_none_or_missing_metric(self):
        history_episodes = [
            {"date": "2026-03-03", "metrics": {"kpi": None}},
            {"date": "2026-03-02", "metrics": {}},
        ]

        values = extract_trend_values(history_episodes, "kpi")

        self.assertEqual(values, [0.0, 0.0])

    def test_uses_prev_value_when_history_is_empty(self):
        values = extract_trend_values([], "kpi", today_val=15, prev_val=12)

        self.assertEqual(values, [12.0, 15.0])

    def test_returns_empty_when_no_history_and_no_fallback(self):
        self.assertEqual(extract_trend_values([], "kpi"), [])


if __name__ == "__main__":
    unittest.main()
