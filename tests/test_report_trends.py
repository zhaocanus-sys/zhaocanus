import re
import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_data import build_trend_data as build_app_trend_data
from app_report_html import kpi_cards_html
from generate_app_full_report import build_trend_data as build_full_app_trend_data


class SparklineSvgTests(unittest.TestCase):
    def test_returns_empty_when_less_than_two_values(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 8, None]), "")

    def test_filters_none_values_and_marks_rising_trend_green(self):
        svg = sparkline_svg([None, 10, 15, None, 20], width=80, height=24, color="#123456")

        self.assertIn('<svg width="80" height="24"', svg)
        self.assertIn('stroke="#123456"', svg)
        self.assertIn('fill="#16a34a"', svg)

        polyline = re.search(r"<polyline points=\"([^\"]+)\"", svg).group(1)
        self.assertEqual(len(polyline.split()), 3)

    def test_marks_declining_trend_red_and_can_disable_fill(self):
        svg = sparkline_svg([30, 20, 10], fill=False)

        self.assertNotIn("<polygon", svg)
        self.assertIn('fill="#dc2626"', svg)

    def test_constant_values_still_render_without_division_by_zero(self):
        svg = sparkline_svg([5, 5, 5])

        self.assertIn("<polyline", svg)
        self.assertIn("<circle", svg)
        self.assertIn("1.0,21.0 30.0,21.0 59.0,21.0", svg)


class TrendExtractionTests(unittest.TestCase):
    def test_extract_trend_values_preserves_chronological_order_and_fallback(self):
        episodes = [
            {"date": "2026-02-28", "metrics": {"revenue": 300}},
            {"date": "2026-02-27", "metrics": {"revenue": None}},
            {"date": "2026-02-26", "metrics": {"revenue": 100}},
        ]

        vals = extract_trend_values(episodes, "revenue", today_val=400)

        self.assertEqual(vals, [100.0, 0.0, 300.0, 400.0])
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=20, prev_val=10),
            [10.0, 20.0],
        )


class AppTrendDataTests(unittest.TestCase):
    def test_build_app_trend_data_aggregates_rows_by_day_and_computes_rates(self):
        rows = [
            {
                "ftime": "20260228090000",
                "amt": "100",
                "pay_num": "4",
                "active_members": "200",
                "refund_money": "2",
                "retain_1d": "80",
                "order_cnt": "10",
                "order_pay": "5",
                "fugou_amt": "25",
            },
            {
                "ftime": "20260227090000",
                "amt": "50",
                "pay_num": "2",
                "active_members": "100",
                "refund_money": "1",
                "retain_1d": "30",
                "order_cnt": "8",
                "order_pay": "4",
                "fugou_amt": "10",
            },
            {
                "ftime": "20260228120000",
                "amt": "200",
                "pay_num": "6",
                "active_members": "300",
                "refund_money": "3",
                "retain_1d": "120",
                "order_cnt": "10",
                "order_pay": "10",
                "fugou_amt": "50",
            },
        ]

        trends = build_app_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trends[1]["amt"], 300.0)
        self.assertEqual(trends[1]["pay_num"], 10.0)
        self.assertEqual(trends[1]["active_members"], 500.0)
        self.assertEqual(trends[1]["fugou_amt"], 75.0)
        self.assertEqual(trends[1]["arpu"], 30.0)
        self.assertEqual(trends[1]["pay_rate"], 2.0)
        self.assertEqual(trends[1]["order_conv"], 75.0)

    def test_full_app_report_trend_data_matches_daily_aggregation_contract(self):
        rows = [
            {"ftime": "20260227", "amt": "1000", "pay_num": "10", "active_members": "200"},
            {"ftime": "20260227", "amt": "500", "pay_num": "5", "active_members": "50"},
            {"ftime": "20260228", "amt": "3000", "pay_num": "30", "active_members": "300"},
        ]

        trends = build_full_app_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trends[0]["amt"], 1500.0)
        self.assertEqual(trends[0]["arpu"], 100.0)
        self.assertEqual(trends[0]["pay_rate"], 6.0)


class AppKpiCardsSparklineTests(unittest.TestCase):
    def test_kpi_cards_render_sparklines_from_last_ten_trend_points(self):
        today = {
            "active": 1200,
            "retain_rate_1d": 42.0,
            "retain_rate_7d": 25.0,
            "pay_rate": 5.5,
            "pay_num": 66,
            "arpu": 36.0,
            "total_rev": 240000.0,
            "fugou_amt": 60000.0,
            "fugou_pct": 25.0,
            "refund_rate": 1.5,
            "refund": 3600.0,
            "order_conv": 75.0,
            "order_fail": 5,
            "zhenxin_pct": 70.0,
            "amt_m": 1200000.0,
            "pay_m": 400,
        }
        previous = {"active": 1000, "total_rev": 200000.0}
        trends = [
            {
                "active_members": i * 100,
                "pay_rate": float(i),
                "arpu": 20.0 + i,
                "amt": i * 10000,
                "fugou_amt": i * 1000,
                "refund_money": i * 100,
                "order_conv": 50.0 + i,
                "retain_1d": i * 10,
            }
            for i in range(1, 12)
        ]

        html = kpi_cards_html(today, previous, trends)

        self.assertEqual(html.count("<svg"), 8)
        self.assertIn("1.0,21.0 7.4,18.8", html)
        self.assertIn("59.0,1.0", html)
        self.assertNotIn("1.0,21.0 6.8,19.0", html)


if __name__ == "__main__":
    unittest.main()
