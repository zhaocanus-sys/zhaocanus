import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html


class ParallelFetchTest(unittest.TestCase):
    def test_empty_call_list_returns_empty_result(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_preserves_order_and_wraps_exceptions(self):
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


class SparklineTest(unittest.TestCase):
    def test_sparkline_requires_at_least_two_non_null_points(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 12]), "")

    def test_sparkline_handles_flat_series_and_downtrend_dot(self):
        svg = sparkline_svg([5, 5, 4], width=30, height=12, color="#111", fill=True)

        self.assertIn('<svg width="30" height="12"', svg)
        self.assertIn('<polygon points=', svg)
        self.assertIn('stroke="#111"', svg)
        self.assertIn('fill="#dc2626"', svg)

    def test_extract_trend_values_uses_history_in_chronological_order(self):
        history = [
            {"date": "2026-02-27", "metrics": {"amt": "300"}},
            {"date": "2026-02-26", "metrics": {"amt": None}},
        ]

        self.assertEqual(
            extract_trend_values(history, "amt", today_val=400, prev_val=200),
            [0.0, 300.0, 400.0],
        )

    def test_extract_trend_values_uses_previous_value_as_baseline(self):
        self.assertEqual(
            extract_trend_values([], "amt", today_val=400, prev_val=200),
            [200.0, 400.0],
        )


class AppTrendDataTest(unittest.TestCase):
    def test_build_trend_data_groups_days_and_derives_rates(self):
        rows = [
            {
                "ftime": "202602270900",
                "amt": "100",
                "pay_num": "2",
                "active_members": "40",
                "refund_money": "5",
                "retain_1d": "7",
                "order_cnt": "10",
                "order_pay": "8",
                "anchmems": "1",
                "giftmems": "3",
                "fugou_amt": "20",
            },
            {
                "ftime": "202602271800",
                "amt": "50",
                "pay_num": "1",
                "active_members": "20",
                "refund_money": "0",
                "retain_1d": "2",
                "order_cnt": "5",
                "order_pay": "4",
                "anchmems": "2",
                "giftmems": "1",
                "fugou_amt": "5",
            },
            {
                "ftime": "202602260900",
                "amt": "30",
                "pay_num": "0",
                "active_members": "0",
                "order_cnt": "0",
                "order_pay": "0",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-26", "2026-02-27"])
        latest = trends[1]
        self.assertEqual(latest["amt"], 150.0)
        self.assertEqual(latest["pay_num"], 3.0)
        self.assertEqual(latest["active_members"], 60.0)
        self.assertEqual(latest["refund_money"], 5.0)
        self.assertEqual(latest["retain_1d"], 9.0)
        self.assertEqual(latest["order_cnt"], 15.0)
        self.assertEqual(latest["order_pay"], 12.0)
        self.assertEqual(latest["anchmems"], 3.0)
        self.assertEqual(latest["giftmems"], 4.0)
        self.assertEqual(latest["fugou_amt"], 25.0)
        self.assertEqual(latest["arpu"], 50.0)
        self.assertEqual(latest["pay_rate"], 5.0)
        self.assertEqual(latest["order_conv"], 80.0)
        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)


class AppKpiCardsTest(unittest.TestCase):
    def test_kpi_cards_render_sparklines_from_trend_data(self):
        today = {
            "active": 210000,
            "retain_rate_1d": 46,
            "retain_rate_7d": 35,
            "pay_rate": 5.2,
            "pay_num": 10920,
            "arpu": 31.5,
            "total_rev": 344000,
            "fugou_amt": 45000,
            "fugou_pct": 13.1,
            "refund_rate": 1.8,
            "order_conv": 72,
            "order_fail": 120,
            "zhenxin_pct": 60,
            "amt_m": 9000000,
            "pay_m": 100000,
        }
        previous = dict(today, active=200000, total_rev=330000)
        trends = [
            {
                "active_members": 190000 + day * 1000,
                "pay_rate": 4.0 + day / 10,
                "arpu": 25 + day,
                "amt": 300000 + day * 1000,
                "fugou_amt": 40000 + day * 100,
                "refund_money": 9000 + day,
                "order_conv": 60 + day,
                "retain_1d": 40 + day / 10,
            }
            for day in range(10)
        ]

        html = kpi_cards_html(today, previous, trends)

        self.assertIn("<svg", html)
        self.assertIn("DAU", html)
        self.assertIn("订单成功率", html)
        self.assertGreaterEqual(html.count("<svg"), 8)


if __name__ == "__main__":
    unittest.main()
