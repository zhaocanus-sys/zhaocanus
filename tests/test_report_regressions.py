# -*- coding: utf-8 -*-
import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html, trend_bars_html


class ParallelFetchTests(unittest.TestCase):
    def test_empty_call_list_returns_empty_results(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_preserves_call_order_and_wraps_exceptions(self):
        def first():
            return {"rows": [1]}

        def failing():
            raise RuntimeError("boom")

        def third():
            return {"rows": [3]}

        results = parallel_fetch([first, failing, third])

        self.assertEqual(results[0], {"rows": [1]})
        self.assertEqual(results[2], {"rows": [3]})
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("boom", results[1]["error"])


class AppTrendAggregationTests(unittest.TestCase):
    def test_build_trend_data_sorts_days_and_aggregates_rates(self):
        rows = [
            {
                "ftime": "20260302090000",
                "amt": "1,000",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "20",
                "retain_1d": "30",
                "order_cnt": "20",
                "order_pay": "10",
                "anchmems": "2",
                "giftmems": "3",
                "fugou_amt": "200",
            },
            {
                "ftime": "20260301090000",
                "amt": "500",
                "pay_num": "5",
                "active_members": "50",
                "refund_money": "5",
                "retain_1d": "10",
                "order_cnt": "10",
                "order_pay": "8",
                "anchmems": "1",
                "giftmems": "1",
                "fugou_amt": "100",
            },
            {
                "ftime": "20260302120000",
                "amt": "2,000",
                "pay_num": "20",
                "active_members": "200",
                "refund_money": "30",
                "retain_1d": "40",
                "order_cnt": "30",
                "order_pay": "15",
                "anchmems": "4",
                "giftmems": "6",
                "fugou_amt": "300",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([trend["dt"] for trend in trends], ["2026-03-01", "2026-03-02"])
        self.assertEqual(trends[1]["amt"], 3000.0)
        self.assertEqual(trends[1]["pay_num"], 30.0)
        self.assertEqual(trends[1]["arpu"], 100.0)
        self.assertEqual(trends[1]["pay_rate"], 10.0)
        self.assertEqual(trends[1]["order_conv"], 50.0)
        self.assertEqual(trends[1]["fugou_amt"], 500.0)

    def test_build_trend_data_handles_zero_denominators(self):
        trends = build_trend_data([
            {
                "ftime": "20260302",
                "amt": "100",
                "pay_num": "0",
                "active_members": "0",
                "order_cnt": "0",
                "order_pay": "0",
            }
        ])

        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)


class ReportSparklineTests(unittest.TestCase):
    def test_sparkline_requires_two_points_and_marks_downtrend(self):
        self.assertEqual(sparkline_svg([42]), "")

        svg = sparkline_svg([10, None, 5], color="#123456", fill=False)

        self.assertIn('<svg width="60" height="22"', svg)
        self.assertIn('stroke="#123456"', svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertNotIn("<polygon", svg)

    def test_extract_trend_values_uses_history_then_today(self):
        history = [
            {"date": "2026-03-02", "metrics": {"amt": "300"}},
            {"date": "2026-03-01", "metrics": {"amt": None}},
        ]

        self.assertEqual(
            extract_trend_values(history, "amt", today_val="400", prev_val="200"),
            [0.0, 300.0, 400.0],
        )
        self.assertEqual(
            extract_trend_values([], "amt", today_val="400", prev_val="200"),
            [200.0, 400.0],
        )


class AppReportHtmlTests(unittest.TestCase):
    def test_kpi_cards_render_sparklines_only_when_trend_has_signal(self):
        today = {
            "active": 120000,
            "retain_rate_1d": 40.0,
            "retain_rate_7d": 20.0,
            "pay_rate": 4.0,
            "pay_num": 4800,
            "arpu": 25.0,
            "total_rev": 120000.0,
            "fugou_amt": 30000.0,
            "fugou_pct": 25.0,
            "refund_rate": 1.5,
            "order_conv": 60.0,
            "order_fail": 40,
            "zhenxin_pct": 70.0,
            "amt_m": 300000.0,
            "pay_m": 10000,
        }
        previous = dict(today, active=100000, total_rev=100000.0)

        html = kpi_cards_html(today, previous, [
            {"active_members": 100000, "amt": 100000, "pay_rate": 3.5, "arpu": 20.0},
            {"active_members": 120000, "amt": 120000, "pay_rate": 4.0, "arpu": 25.0},
        ])

        self.assertIn("<svg", html)
        self.assertIn("DAU", html)
        self.assertIn("▲20.0%", html)

    def test_trend_bars_render_last_ten_days_and_highlight_today(self):
        trends = [
            {"dt": f"2026-03-{day:02d}", "amt": day * 10000, "pay_rate": day, "order_conv": 50}
            for day in range(1, 12)
        ]

        html = trend_bars_html(trends, "2026-03-11")

        self.assertNotIn("03-01", html)
        self.assertIn("03-02", html)
        self.assertIn("03-11", html)
        self.assertIn("background:#0f172a", html)


if __name__ == "__main__":
    unittest.main()
