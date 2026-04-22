import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class SparklineSvgTests(unittest.TestCase):
    def test_returns_empty_when_less_than_two_points(self):
        self.assertEqual(sparkline_svg([None, 5, None]), "")

    def test_upward_trend_uses_green_dot_and_fill_polygon(self):
        svg = sparkline_svg([1, 2, 3], color="#123456")
        self.assertIn("<svg", svg)
        self.assertIn("<polygon", svg)
        self.assertIn('fill="#16a34a"', svg)
        self.assertIn('stroke="#123456"', svg)

    def test_downward_trend_uses_red_dot_and_can_disable_fill(self):
        svg = sparkline_svg([3, 2, 1], fill=False)
        self.assertIn("<svg", svg)
        self.assertNotIn("<polygon", svg)
        self.assertIn('fill="#dc2626"', svg)


class ExtractTrendValuesTests(unittest.TestCase):
    def test_history_is_reversed_to_time_order_and_today_is_appended(self):
        history = [
            {"date": "2026-02-27", "metrics": {"amt": 300}},
            {"date": "2026-02-26", "metrics": {"amt": 200}},
        ]
        vals = extract_trend_values(history, "amt", today_val=350)
        self.assertEqual(vals, [200.0, 300.0, 350.0])

    def test_uses_prev_value_when_history_is_empty(self):
        vals = extract_trend_values([], "amt", today_val=120, prev_val=100)
        self.assertEqual(vals, [100.0, 120.0])

    def test_none_metric_is_normalized_to_zero(self):
        history = [{"date": "2026-02-27", "metrics": {"amt": None}}]
        vals = extract_trend_values(history, "amt", today_val=5)
        self.assertEqual(vals, [0.0, 5.0])


if __name__ == "__main__":
    unittest.main()
