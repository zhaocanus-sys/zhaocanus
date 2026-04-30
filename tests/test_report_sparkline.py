import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class SparklineSvgTest(unittest.TestCase):
    def test_returns_empty_when_less_than_two_points(self):
        self.assertEqual("", sparkline_svg([]))
        self.assertEqual("", sparkline_svg([42]))
        self.assertEqual("", sparkline_svg([None, 42]))

    def test_renders_constant_values_without_divide_by_zero(self):
        svg = sparkline_svg([5, 5, 5], width=60, height=22, color="#123456")

        self.assertIn('<svg width="60" height="22"', svg)
        self.assertIn('stroke="#123456"', svg)
        self.assertIn('fill="#123456"', svg)
        self.assertIn('fill="#16a34a"', svg)
        self.assertIn('points="1.0,21.0 30.0,21.0 59.0,21.0"', svg)

    def test_marks_last_point_red_when_latest_value_declines(self):
        svg = sparkline_svg([10, 20, 15], fill=False)

        self.assertNotIn("<polygon", svg)
        self.assertIn('fill="#dc2626"', svg)


class ExtractTrendValuesTest(unittest.TestCase):
    def test_uses_history_in_chronological_order_and_appends_today(self):
        history = [
            {"date": "2026-02-27", "metrics": {"pay_amt": "30"}},
            {"date": "2026-02-26", "metrics": {"pay_amt": 20}},
            {"date": "2026-02-25", "metrics": {"pay_amt": None}},
        ]

        values = extract_trend_values(history, "pay_amt", today_val=40)

        self.assertEqual([0.0, 20.0, 30.0, 40.0], values)

    def test_prev_value_is_baseline_only_when_history_is_empty(self):
        self.assertEqual(
            [10.0, 15.0],
            extract_trend_values([], "pay_amt", today_val=15, prev_val=10),
        )

        self.assertEqual(
            [3.0, 4.0],
            extract_trend_values(
                [{"metrics": {"pay_amt": 3}}],
                "pay_amt",
                today_val=4,
                prev_val=999,
            ),
        )


if __name__ == "__main__":
    unittest.main()
