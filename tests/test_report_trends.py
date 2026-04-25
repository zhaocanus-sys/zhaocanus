import re
import unittest

from agent_system.actions.report_sparkline import (
    extract_trend_values,
    sparkline_svg,
)
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html


class SparklineSvgTests(unittest.TestCase):
    def test_returns_empty_when_less_than_two_data_points(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 42, None]), "")

    def test_renders_svg_without_fill_and_marks_downward_latest_point_red(self):
        svg = sparkline_svg([10, 20, 15], width=100, height=30, color="#111111", fill=False)

        self.assertIn('<svg width="100" height="30"', svg)
        self.assertNotIn("<polygon", svg)
        self.assertIn('stroke="#111111"', svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertRegex(svg, r'<polyline points="1\.0,29\.0 50\.0,1\.0 99\.0,15\.0"')

    def test_constant_values_still_render_deterministic_points(self):
        svg = sparkline_svg([7, 7, 7], width=60, height=22)

        self.assertIn('points="1.0,21.0 30.0,21.0 59.0,21.0', svg)
        self.assertIn('cx="59.0" cy="21.0"', svg)
        self.assertIn('fill="#16a34a"', svg)


class ExtractTrendValuesTests(unittest.TestCase):
    def test_reverses_recalled_history_to_chronological_order_and_appends_today(self):
        history = [
            {"date": "20260226", "metrics": {"revenue": "300.5"}},
            {"date": "20260225", "metrics": {"revenue": 200}},
            {"date": "20260224", "metrics": {"revenue": None}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=400),
            [0.0, 200.0, 300.5, 400.0],
        )

    def test_uses_previous_value_as_baseline_only_when_history_is_empty(self):
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=120, prev_val=100),
            [100.0, 120.0],
        )
        self.assertEqual(
            extract_trend_values(
                [{"date": "20260226", "metrics": {"revenue": 90}}],
                "revenue",
                today_val=120,
                prev_val=100,
            ),
            [90.0, 120.0],
        )


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_aggregates_rows_by_day_and_calculates_rates(self):
        rows = [
            {
                "ftime": "20260227090000",
                "amt": "100",
                "pay_num": "2",
                "active_members": "100",
                "refund_money": "5",
                "retain_1d": "20",
                "order_cnt": "10",
                "order_pay": "7",
                "anchmems": "1",
                "giftmems": "4",
                "fugou_amt": "30",
            },
            {
                "ftime": "20260226090000",
                "amt": "80",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": None,
                "retain_1d": "0",
                "order_cnt": "0",
                "order_pay": "0",
                "anchmems": "2",
                "giftmems": "3",
                "fugou_amt": "10",
            },
            {
                "ftime": "20260227180000",
                "amt": "50",
                "pay_num": "1",
                "active_members": "50",
                "refund_money": "1",
                "retain_1d": "5",
                "order_cnt": "5",
                "order_pay": "3",
                "anchmems": "2",
                "giftmems": "6",
                "fugou_amt": "20",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([trend["dt"] for trend in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[0]["amt"], 80.0)
        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)
        self.assertEqual(trends[1]["amt"], 150.0)
        self.assertEqual(trends[1]["pay_num"], 3.0)
        self.assertEqual(trends[1]["active_members"], 150.0)
        self.assertEqual(trends[1]["refund_money"], 6.0)
        self.assertEqual(trends[1]["arpu"], 50.0)
        self.assertEqual(trends[1]["pay_rate"], 2.0)
        self.assertAlmostEqual(trends[1]["order_conv"], 66.66666666666666)
        self.assertEqual(trends[1]["anchmems"], 3.0)
        self.assertEqual(trends[1]["giftmems"], 10.0)
        self.assertEqual(trends[1]["fugou_amt"], 50.0)

    def test_kpi_cards_render_sparklines_from_last_ten_trend_points(self):
        today = {
            "active": 120,
            "retain_rate_1d": 40,
            "retain_rate_7d": 35,
            "pay_rate": 4,
            "pay_num": 6,
            "arpu": 20,
            "total_rev": 120,
            "fugou_amt": 30,
            "fugou_pct": 25,
            "refund_rate": 1.5,
            "order_conv": 70,
            "order_fail": 3,
            "zhenxin_pct": 50,
            "amt_m": 1000,
            "pay_m": 50,
        }
        previous = dict(today, active=100, total_rev=100)
        trends = [
            {
                "active_members": i,
                "pay_rate": i / 10,
                "arpu": i + 1,
                "amt": i * 10,
                "fugou_amt": i * 2,
                "refund_money": i,
                "order_conv": i / 2,
                "retain_1d": i / 3,
            }
            for i in range(1, 13)
        ]

        html = kpi_cards_html(today, previous, trends)

        self.assertGreaterEqual(html.count("<svg"), 8)
        self.assertIn("DAU", html)
        self.assertIn("日营收", html)
        polyline_points = re.findall(r"<polyline points=\"([^\"]+)\"", html)
        self.assertTrue(polyline_points)
        self.assertTrue(all(points.startswith("1.0,") for points in polyline_points))


if __name__ == "__main__":
    unittest.main()
