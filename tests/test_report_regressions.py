import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html


class ReportRegressionTests(unittest.TestCase):
    def test_build_trend_data_aggregates_rows_by_day_and_handles_zero_denominators(self):
        rows = [
            {
                "ftime": "20260227090000",
                "amt": "100",
                "pay_num": "2",
                "active_members": "10",
                "refund_money": "5",
                "retain_1d": "3",
                "order_cnt": "4",
                "order_pay": "2",
                "anchmems": "1",
                "giftmems": "2",
                "fugou_amt": "30",
            },
            {
                "ftime": "20260227120000",
                "amt": "50",
                "pay_num": "1",
                "active_members": "5",
                "refund_money": "0",
                "retain_1d": "2",
                "order_cnt": "1",
                "order_pay": "1",
                "anchmems": "3",
                "giftmems": "4",
                "fugou_amt": "20",
            },
            {
                "ftime": "20260228090000",
                "amt": "10",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "1",
                "retain_1d": "0",
                "order_cnt": "0",
                "order_pay": "0",
            },
        ]

        trend = build_trend_data(rows)

        self.assertEqual([day["dt"] for day in trend], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trend[0]["amt"], 150)
        self.assertEqual(trend[0]["pay_num"], 3)
        self.assertEqual(trend[0]["active_members"], 15)
        self.assertEqual(trend[0]["refund_money"], 5)
        self.assertEqual(trend[0]["retain_1d"], 5)
        self.assertEqual(trend[0]["order_cnt"], 5)
        self.assertEqual(trend[0]["order_pay"], 3)
        self.assertEqual(trend[0]["anchmems"], 4)
        self.assertEqual(trend[0]["giftmems"], 6)
        self.assertEqual(trend[0]["fugou_amt"], 50)
        self.assertEqual(trend[0]["arpu"], 50)
        self.assertEqual(trend[0]["pay_rate"], 20)
        self.assertEqual(trend[0]["order_conv"], 60)
        self.assertEqual(trend[1]["arpu"], 0)
        self.assertEqual(trend[1]["pay_rate"], 0)
        self.assertEqual(trend[1]["order_conv"], 0)

    def test_kpi_cards_html_embeds_sparklines_for_available_trends(self):
        current = {
            "active": 180000,
            "retain_rate_1d": 42.0,
            "retain_rate_7d": 28.0,
            "pay_rate": 4.0,
            "pay_num": 7200,
            "arpu": 35.0,
            "total_rev": 252000,
            "fugou_amt": 45000,
            "fugou_pct": 17.9,
            "refund_rate": 1.2,
            "order_conv": 75.0,
            "order_fail": 25,
            "zhenxin_pct": 72.0,
            "amt_m": 1230000,
            "pay_m": 36000,
        }
        previous = {"active": 170000, "total_rev": 240000}
        trends = [
            {
                "active_members": 160000 + i,
                "pay_rate": 3.5 + i * 0.1,
                "arpu": 30 + i,
                "amt": 220000 + i * 1000,
                "fugou_amt": 30000 + i * 500,
                "refund_money": 100 + i,
                "order_conv": 65 + i,
                "retain_1d": 36 + i,
            }
            for i in range(10)
        ]

        html = kpi_cards_html(current, previous, trends)

        self.assertIn("DAU", html)
        self.assertIn("日营收", html)
        self.assertGreaterEqual(html.count("<svg"), 8)
        self.assertIn('width="60"', html)
        self.assertIn("stroke=", html)

    def test_sparkline_svg_handles_flat_and_descending_series(self):
        flat = sparkline_svg([5, 5, 5], color="#123456")
        descending = sparkline_svg([3, 2, 1], fill=False)

        self.assertIn("<svg", flat)
        self.assertIn('fill="#16a34a"', flat)
        self.assertIn('stroke="#123456"', flat)
        self.assertIn('fill="#dc2626"', descending)
        self.assertNotIn("<polygon", descending)

    def test_sparkline_svg_requires_two_values_after_filtering_none(self):
        self.assertEqual(sparkline_svg([None, 10]), "")
        self.assertIn("<svg", sparkline_svg([None, 10, 12]))

    def test_extract_trend_values_uses_history_oldest_to_newest_with_fallbacks(self):
        history = [
            {"metrics": {"revenue": 300}},
            {"metrics": {"revenue": None}},
            {"metrics": {"revenue": "100"}},
        ]

        values = extract_trend_values(history, "revenue", today_val=400, prev_val=200)

        self.assertEqual(values, [100.0, 0.0, 300.0, 400.0])
        self.assertEqual(extract_trend_values([], "revenue", today_val=400, prev_val=200), [200.0, 400.0])

    def test_parallel_fetch_preserves_call_order(self):
        calls = [lambda: "first", lambda: "second", lambda: "third"]

        self.assertEqual(parallel_fetch(calls), ["first", "second", "third"])

    def test_parallel_fetch_converts_exceptions_to_api_error_shape(self):
        def raises():
            raise RuntimeError("boom")

        result = parallel_fetch([lambda: {"rows": [1]}, raises])

        self.assertEqual(result[0], {"rows": [1]})
        self.assertEqual(result[1]["rows"], [])
        self.assertEqual(result[1]["row_count"], 0)
        self.assertEqual(result[1]["columns"], [])
        self.assertIn("boom", result[1]["error"])

    def test_parallel_fetch_accepts_empty_call_list(self):
        self.assertEqual(parallel_fetch([]), [])


if __name__ == "__main__":
    unittest.main()
