import sys
import unittest
from unittest.mock import patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_empty_call_list_returns_empty_result(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_isolates_failures(self):
        def first():
            return {"rows": [{"id": 1}]}

        def broken():
            raise RuntimeError("boom")

        def third():
            return {"rows": [{"id": 3}]}

        result = parallel_fetch([first, broken, third])

        self.assertEqual(result[0], {"rows": [{"id": 1}]})
        self.assertEqual(result[2], {"rows": [{"id": 3}]})
        self.assertEqual(result[1]["rows"], [])
        self.assertIn("boom", result[1]["error"])


class SparklineTests(unittest.TestCase):
    def test_sparkline_handles_empty_single_and_flat_series(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([100]), "")

        svg = sparkline_svg([5, 5, 5], width=30, height=12)

        self.assertIn('<svg width="30" height="12"', svg)
        self.assertIn('<polyline points="1.0,11.0 15.0,11.0 29.0,11.0"', svg)
        self.assertIn('fill="#16a34a"', svg)

    def test_extract_trend_values_returns_chronological_history_with_fallbacks(self):
        history = [
            {"date": "2026-02-27", "metrics": {"total_rev": "300"}},
            {"date": "2026-02-26", "metrics": {"total_rev": None}},
            {"date": "2026-02-25", "metrics": {"total_rev": "100"}},
        ]

        vals = extract_trend_values(history, "total_rev", today_val=400)

        self.assertEqual(vals, [100.0, 0.0, 300.0, 400.0])
        self.assertEqual(
            extract_trend_values([], "total_rev", today_val=40, prev_val=20),
            [20.0, 40.0],
        )


class AppTrendDataTests(unittest.TestCase):
    def test_app_data_trend_groups_by_day_and_computes_refund_rate(self):
        rows = [
            {
                "ftime": "20260227000000",
                "amt": "1000",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "25",
                "order_cnt": "20",
                "order_pay": "10",
            },
            {
                "ftime": "20260227120000",
                "amt": "3000",
                "pay_num": "30",
                "active_members": "100",
                "refund_money": "75",
                "order_cnt": "30",
                "order_pay": "15",
            },
        ]

        trend = app_report_data.build_trend_data(rows)

        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["dt"], "2026-02-27")
        self.assertEqual(trend[0]["amt"], 4000.0)
        self.assertEqual(trend[0]["pay_rate"], 20.0)
        self.assertEqual(trend[0]["refund_rate"], 2.5)
        self.assertEqual(trend[0]["order_conv"], 50.0)

    def test_legacy_app_trend_also_computes_refund_rate(self):
        trend = generate_app_full_report.build_trend_data(
            [
                {
                    "ftime": "20260227",
                    "amt": "2000",
                    "pay_num": "20",
                    "active_members": "200",
                    "refund_money": "100",
                }
            ]
        )

        self.assertEqual(trend[0]["refund_rate"], 5.0)


class AppReportHtmlTests(unittest.TestCase):
    def test_refund_kpi_sparkline_uses_refund_rate_not_refund_money(self):
        t = {
            "active": 1000,
            "retain_rate_1d": 40,
            "retain_rate_7d": 25,
            "pay_rate": 5,
            "pay_num": 50,
            "arpu": 100,
            "total_rev": 5000,
            "fugou_amt": 1000,
            "fugou_pct": 20,
            "refund_rate": 2.5,
            "order_conv": 75,
            "order_fail": 5,
            "zhenxin_pct": 60,
            "amt_m": 100000,
            "pay_m": 100,
        }
        p = dict(t)
        trends = [
            {
                "active_members": 900,
                "pay_rate": 4.5,
                "arpu": 90,
                "amt": 4000,
                "fugou_amt": 800,
                "refund_rate": 1.0,
                "refund_money": 1000,
                "order_conv": 70,
                "retain_1d": 38,
            },
            {
                "active_members": 1000,
                "pay_rate": 5.0,
                "arpu": 100,
                "amt": 5000,
                "fugou_amt": 1000,
                "refund_rate": 2.5,
                "refund_money": 500,
                "order_conv": 75,
                "retain_1d": 40,
            },
        ]
        calls = []

        def fake_sparkline(values, color="#3b82f6", **kwargs):
            calls.append(list(values))
            return "<svg></svg>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            app_report_html.kpi_cards_html(t, p, trends)

        self.assertIn([1.0, 2.5], calls)
        self.assertNotIn([1000, 500], calls)


class AppReportMainTests(unittest.TestCase):
    def test_main_fetches_today_prev_and_exact_ten_day_trend_window(self):
        seen_dates = []

        def fake_daily(team, date):
            self.assertEqual(team, "app")
            seen_dates.append(date)
            return {"rows": [{"amt": "1"}]}

        original_argv = sys.argv
        sys.argv = ["generate_app_full_report.py", "--date", "2026-02-27"]
        try:
            with patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                 patch.object(generate_app_full_report, "generate_html", return_value="<html></html>"), \
                 patch.object(generate_app_full_report, "export_html", return_value="/tmp/app.html"), \
                 patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            sys.argv = original_argv

        self.assertEqual(
            seen_dates,
            [
                "20260227",
                "20260226",
                "20260218",
                "20260219",
                "20260220",
                "20260221",
                "20260222",
                "20260223",
                "20260224",
                "20260225",
                "20260226",
                "20260227",
            ],
        )


if __name__ == "__main__":
    unittest.main()
