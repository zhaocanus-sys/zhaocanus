import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class TestSparklineSvg(unittest.TestCase):
    def test_returns_empty_svg_when_less_than_two_values(self):
        self.assertEqual(sparkline_svg([1]), "")
        self.assertEqual(sparkline_svg([None]), "")

    def test_ignores_none_values_and_renders_svg(self):
        svg = sparkline_svg([None, 1, None, 2], width=60, height=22)

        self.assertTrue(svg.startswith('<svg width="60" height="22"'))
        self.assertIn("<polyline", svg)
        self.assertIn("<circle", svg)

    def test_colors_last_dot_green_when_trend_is_up_or_flat(self):
        up_svg = sparkline_svg([1, 2])
        flat_svg = sparkline_svg([2, 2])

        self.assertIn('fill="#16a34a"', up_svg)
        self.assertIn('fill="#16a34a"', flat_svg)

    def test_colors_last_dot_red_when_trend_is_down(self):
        svg = sparkline_svg([2, 1])

        self.assertIn('fill="#dc2626"', svg)

    def test_disable_fill_removes_polygon(self):
        svg = sparkline_svg([1, 2], fill=False)

        self.assertNotIn("<polygon", svg)
        self.assertIn("<polyline", svg)


class TestExtractTrendValues(unittest.TestCase):
    def test_extracts_values_in_time_order_and_appends_today(self):
        # recall() returns episodes from newest to oldest in current implementation.
        episodes = [
            {"date": "2026-03-03", "metrics": {"kpi": 30}},
            {"date": "2026-03-02", "metrics": {"kpi": 20}},
            {"date": "2026-03-01", "metrics": {"kpi": 10}},
        ]

        values = extract_trend_values(episodes, "kpi", today_val=40)

        self.assertEqual(values, [10.0, 20.0, 30.0, 40.0])

    def test_converts_none_history_to_zero(self):
        episodes = [{"date": "2026-03-01", "metrics": {"kpi": None}}]

        values = extract_trend_values(episodes, "kpi")

        self.assertEqual(values, [0.0])

    def test_uses_prev_value_as_fallback_when_history_empty(self):
        values = extract_trend_values([], "kpi", today_val=12, prev_val=10)

        self.assertEqual(values, [10.0, 12.0])

    def test_without_today_or_prev_returns_empty_list(self):
        values = extract_trend_values([], "kpi")

        self.assertEqual(values, [])


if __name__ == "__main__":
    unittest.main()
