import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_data import build_trend_data as build_app_data_trends
from app_report_html import kpi_cards_html
from generate_app_full_report import build_trend_data as build_full_report_trends


class AppTrendAggregationTest(unittest.TestCase):
    def test_full_report_trends_group_sort_and_derive_rates(self):
        rows = [
            {"ftime": "20260227090000", "amt": "300", "pay_num": "3", "active_members": "30"},
            {"ftime": "20260225090000", "amt": "100", "pay_num": "2", "active_members": "20"},
            {"ftime": "20260227093000", "amt": "200", "pay_num": "1", "active_members": "10"},
        ]

        trends = build_full_report_trends(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-25", "2026-02-27"])
        self.assertEqual(trends[1]["amt"], 500)
        self.assertEqual(trends[1]["pay_num"], 4)
        self.assertEqual(trends[1]["active_members"], 40)
        self.assertEqual(trends[1]["arpu"], 125)
        self.assertEqual(trends[1]["pay_rate"], 10)

    def test_app_data_trends_zero_safe_conversion_metrics(self):
        rows = [
            {
                "ftime": "20260226000000",
                "amt": "0",
                "pay_num": "0",
                "active_members": "0",
                "order_cnt": "0",
                "order_pay": "0",
            },
            {
                "ftime": "20260227000000",
                "amt": "1,200",
                "pay_num": "4",
                "active_members": "100",
                "order_cnt": "20",
                "order_pay": "5",
                "fugou_amt": "300",
            },
        ]

        trends = build_app_data_trends(rows)

        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)
        self.assertEqual(trends[1]["arpu"], 300)
        self.assertEqual(trends[1]["pay_rate"], 4)
        self.assertEqual(trends[1]["order_conv"], 25)
        self.assertEqual(trends[1]["fugou_amt"], 300)


class SparklineRegressionTest(unittest.TestCase):
    def test_sparkline_requires_two_points_and_marks_downturn_red(self):
        self.assertEqual(sparkline_svg([None, 7]), "")

        svg = sparkline_svg([None, 10, 5], color="#111111")

        self.assertIn("<svg", svg)
        self.assertIn("<polyline", svg)
        self.assertIn('stroke="#111111"', svg)
        self.assertIn('fill="#dc2626"', svg)

    def test_extract_trend_values_orders_history_and_uses_baseline(self):
        history = [
            {"date": "2026-02-27", "metrics": {"total_rev": 300}},
            {"date": "2026-02-26", "metrics": {"total_rev": None}},
            {"date": "2026-02-25", "metrics": {"total_rev": 100}},
        ]

        self.assertEqual(extract_trend_values(history, "total_rev", today_val=400), [100.0, 0.0, 300.0, 400.0])
        self.assertEqual(extract_trend_values([], "total_rev", today_val=2, prev_val=1), [1.0, 2.0])


class AppKpiHtmlRegressionTest(unittest.TestCase):
    def test_kpi_cards_render_sparklines_from_trends(self):
        today = {
            "active": 200000,
            "retain_rate_1d": 40,
            "retain_rate_7d": 25,
            "pay_rate": 5,
            "pay_num": 10000,
            "arpu": 30,
            "total_rev": 300000,
            "fugou_amt": 60000,
            "fugou_pct": 20,
            "refund_rate": 1.5,
            "order_conv": 80,
            "order_fail": 20,
            "zhenxin_pct": 70,
            "amt_m": 3000000,
            "pay_m": 90000,
        }
        trends = [
            {"active_members": 180000, "pay_rate": 4, "arpu": 25, "amt": 250000, "fugou_amt": 50000, "refund_money": 2000, "order_conv": 70, "retain_1d": 80000},
            {"active_members": 200000, "pay_rate": 5, "arpu": 30, "amt": 300000, "fugou_amt": 60000, "refund_money": 1500, "order_conv": 80, "retain_1d": 90000},
        ]

        html = kpi_cards_html(today, {}, trends)

        self.assertIn("DAU", html)
        self.assertIn("订单成功率", html)
        self.assertGreaterEqual(html.count("<svg"), 8)


class ParallelFetchRegressionTest(unittest.TestCase):
    def test_parallel_fetch_handles_empty_calls(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_wraps_exceptions(self):
        def fail():
            raise RuntimeError("boom")

        results = parallel_fetch([lambda: "first", fail, lambda: "third"])

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("boom", results[1]["error"])


if __name__ == "__main__":
    unittest.main()
