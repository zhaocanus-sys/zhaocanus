import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class SparklineSvgTests(unittest.TestCase):
    def test_returns_empty_when_less_than_two_values(self):
        self.assertEqual(sparkline_svg([None, 3, None]), "")
        self.assertEqual(sparkline_svg([1]), "")

    def test_renders_green_dot_for_upward_or_flat_trend(self):
        svg = sparkline_svg([1, None, 2, 2], color="#123456")
        self.assertIn('<svg width="60" height="22"', svg)
        self.assertIn('<polygon points="', svg)
        self.assertIn('stroke="#123456"', svg)
        self.assertIn('fill="#16a34a"', svg)

    def test_renders_red_dot_for_downward_trend_without_fill(self):
        svg = sparkline_svg([10, 5], fill=False)
        self.assertIn('<polyline points="', svg)
        self.assertNotIn("<polygon", svg)
        self.assertIn('fill="#dc2626"', svg)


class ExtractTrendValuesTests(unittest.TestCase):
    def test_extracts_values_in_reversed_episode_order_and_appends_today(self):
        history = [
            {"metrics": {"kpi": "10"}},
            {"metrics": {"kpi": "20"}},
            {"metrics": {"kpi": None}},
        ]
        values = extract_trend_values(history, "kpi", today_val=99)
        self.assertEqual(values, [0.0, 20.0, 10.0, 99.0])

    def test_uses_prev_value_when_history_is_empty(self):
        values = extract_trend_values([], "kpi", today_val=5, prev_val=3)
        self.assertEqual(values, [3.0, 5.0])


if __name__ == "__main__":
    unittest.main()
