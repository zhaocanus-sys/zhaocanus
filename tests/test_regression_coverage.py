import time
import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_data import build_trend_data as build_app_trend_data
from app_report_html import kpi_cards_html
from generate_app_full_report import build_trend_data as build_full_report_trend_data


def _daily_row(day, **overrides):
    row = {
        "ftime": day,
        "amt": "0",
        "pay_num": "0",
        "active_members": "0",
        "refund_money": "0",
        "retain_1d": "0",
        "order_cnt": "0",
        "order_pay": "0",
        "anchmems": "0",
        "giftmems": "0",
        "fugou_amt": "0",
    }
    row.update(overrides)
    return row


class AppTrendDataTests(unittest.TestCase):
    def test_app_trend_data_groups_sorts_and_derives_rates(self):
        rows = [
            _daily_row("20260228", amt="300", pay_num="3", active_members="30", order_cnt="4", order_pay="2"),
            _daily_row("20260227", amt="100", pay_num="2", active_members="10", order_cnt="5", order_pay="5"),
            _daily_row("20260227", amt="50", pay_num="1", active_members="5", order_cnt="5", order_pay="0"),
        ]

        trends = build_app_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trends[0]["amt"], 150)
        self.assertEqual(trends[0]["pay_num"], 3)
        self.assertEqual(trends[0]["active_members"], 15)
        self.assertEqual(trends[0]["arpu"], 50)
        self.assertEqual(trends[0]["pay_rate"], 20)
        self.assertEqual(trends[0]["order_conv"], 50)
        self.assertEqual(trends[1]["arpu"], 100)

    def test_app_trend_data_keeps_zero_denominators_safe(self):
        trends = build_app_trend_data([
            _daily_row("20260227", amt="100", pay_num="0", active_members="0", order_cnt="0", order_pay="0")
        ])

        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)

    def test_full_report_trend_builder_remains_compatible(self):
        trends = build_full_report_trend_data([
            _daily_row("20260227", amt="1,200", pay_num="4", active_members="100", refund_money="25"),
            _daily_row("20260227", amt="300", pay_num="1", active_members="50", refund_money="5"),
        ])

        self.assertEqual(len(trends), 1)
        self.assertEqual(trends[0]["dt"], "2026-02-27")
        self.assertEqual(trends[0]["amt"], 1500)
        self.assertEqual(trends[0]["pay_num"], 5)
        self.assertEqual(trends[0]["active_members"], 150)
        self.assertEqual(trends[0]["refund_money"], 30)
        self.assertEqual(trends[0]["arpu"], 300)
        self.assertAlmostEqual(trends[0]["pay_rate"], 5 / 150 * 100)


class SparklineRenderingTests(unittest.TestCase):
    def _kpi_totals(self):
        return {
            "active": 200000,
            "retain_rate_1d": 45.0,
            "retain_rate_7d": 40.0,
            "pay_rate": 5.0,
            "pay_num": 10000,
            "arpu": 30.0,
            "total_rev": 300000.0,
            "fugou_amt": 60000.0,
            "fugou_pct": 20.0,
            "refund_rate": 1.5,
            "order_conv": 75.0,
            "order_fail": 25,
            "zhenxin_pct": 60.0,
            "amt_m": 9000000.0,
            "pay_m": 300000,
        }

    def test_kpi_cards_render_sparklines_for_recent_trend_metrics(self):
        trends = [
            {
                "active_members": 100 + i,
                "pay_rate": 2 + i,
                "arpu": 20 + i,
                "amt": 1000 + i,
                "fugou_amt": 100 + i,
                "refund_money": 5 + i,
                "order_conv": 50 + i,
                "retain_1d": 30 + i,
            }
            for i in range(12)
        ]

        html = kpi_cards_html(self._kpi_totals(), {"active": 190000, "total_rev": 280000}, trends)

        self.assertEqual(html.count("<svg"), 8)
        self.assertIn("DAU", html)
        self.assertIn("日营收", html)
        self.assertIn("订单成功率", html)

    def test_sparkline_handles_sparse_values_and_marks_downward_trend(self):
        svg = sparkline_svg([None, 10, 5], fill=False)

        self.assertIn("<svg", svg)
        self.assertNotIn("<polygon", svg)
        self.assertIn('fill="#dc2626"', svg)

    def test_extract_trend_values_uses_previous_value_when_history_empty(self):
        vals = extract_trend_values([], "total_rev", today_val=200, prev_val=100)

        self.assertEqual(vals, [100.0, 200.0])


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_empty_call_list_returns_empty_list(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_call_order(self):
        def slow():
            time.sleep(0.02)
            return "slow"

        def fast():
            return "fast"

        self.assertEqual(parallel_fetch([slow, fast]), ["slow", "fast"])

    def test_parallel_fetch_converts_exceptions_to_error_payloads(self):
        def boom():
            raise RuntimeError("network unavailable")

        result = parallel_fetch([lambda: {"rows": [1]}, boom])

        self.assertEqual(result[0], {"rows": [1]})
        self.assertIn("network unavailable", result[1]["error"])
        self.assertEqual(result[1]["rows"], [])
        self.assertEqual(result[1]["row_count"], 0)
        self.assertEqual(result[1]["columns"], [])


if __name__ == "__main__":
    unittest.main()
