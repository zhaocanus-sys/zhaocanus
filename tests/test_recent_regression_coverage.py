import sys
import unittest
from unittest.mock import call, patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_empty_call_list_returns_empty_result(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_isolates_exceptions(self):
        def ok(value):
            return {"rows": [value]}

        def bad():
            raise RuntimeError("boom")

        results = parallel_fetch([
            lambda: ok("first"),
            bad,
            lambda: ok("third"),
        ])

        self.assertEqual(results[0], {"rows": ["first"]})
        self.assertEqual(results[2], {"rows": ["third"]})
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])


class AppTrendAggregationTests(unittest.TestCase):
    def test_build_trend_data_aggregates_days_and_computes_derived_rates(self):
        rows = [
            {
                "ftime": "20260301",
                "amt": "1000",
                "refund_money": "10",
                "pay_num": "10",
                "active_members": "100",
                "order_cnt": "20",
                "order_pay": "10",
            },
            {
                "ftime": "20260301",
                "amt": "2000",
                "refund_money": "50",
                "pay_num": "20",
                "active_members": "100",
                "order_cnt": "30",
                "order_pay": "20",
            },
            {
                "ftime": "20260302",
                "amt": "0",
                "refund_money": "5",
                "pay_num": "0",
                "active_members": "0",
                "order_cnt": "0",
                "order_pay": "0",
            },
        ]

        for build_trend_data in (
            app_report_data.build_trend_data,
            generate_app_full_report.build_trend_data,
        ):
            with self.subTest(module=build_trend_data.__module__):
                trends = build_trend_data(rows)

                self.assertEqual([t["dt"] for t in trends], ["2026-03-01", "2026-03-02"])
                self.assertEqual(trends[0]["amt"], 3000)
                self.assertEqual(trends[0]["refund_money"], 60)
                self.assertEqual(trends[0]["arpu"], 100)
                self.assertEqual(trends[0]["pay_rate"], 15)
                self.assertEqual(trends[0]["refund_rate"], 2)
                self.assertEqual(trends[1]["refund_rate"], 0)


class AppKpiSparklineTests(unittest.TestCase):
    def test_refund_kpi_uses_refund_rate_history_not_refund_amount_history(self):
        today = {
            "active": 1000,
            "retain_rate_1d": 40,
            "retain_rate_7d": 30,
            "pay_rate": 5,
            "pay_num": 50,
            "arpu": 20,
            "total_rev": 10000,
            "fugou_amt": 2000,
            "fugou_pct": 20,
            "refund_rate": 3,
            "order_conv": 80,
            "order_fail": 2,
            "zhenxin_pct": 50,
            "amt_m": 30000,
            "pay_m": 150,
        }
        prev = {**today, "total_rev": 9000, "active": 900}
        trends = [
            {
                "active_members": 900,
                "pay_rate": 4,
                "arpu": 18,
                "amt": 9000,
                "fugou_amt": 1000,
                "refund_money": 900,
                "refund_rate": 1.0,
                "order_conv": 70,
                "retain_1d": 35,
            },
            {
                "active_members": 1000,
                "pay_rate": 5,
                "arpu": 20,
                "amt": 10000,
                "fugou_amt": 2000,
                "refund_money": 300,
                "refund_rate": 3.0,
                "order_conv": 80,
                "retain_1d": 40,
            },
        ]
        captured = []

        def fake_sparkline(values, **kwargs):
            captured.append(list(values))
            return f"<spark>{','.join(str(v) for v in values)}</spark>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            html = app_report_html.kpi_cards_html(today, prev, trends)

        self.assertIn("退款率", html)
        self.assertIn([1.0, 3.0], captured)
        self.assertNotIn([900, 300], captured)


class AppReportMainTests(unittest.TestCase):
    def test_main_fetches_exact_previous_today_and_ten_day_trend_window(self):
        captured = {}

        def fake_daily(team, date):
            return {"rows": [{"amt": 1, "ftime": date}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_dates"] = [row["ftime"] for row in trend_rows]
            captured["date_display"] = date_display
            return "<html>ok</html>"

        original_argv = sys.argv[:]
        try:
            sys.argv = ["generate_app_full_report.py", "--date", "2026-03-10"]
            with patch.object(generate_app_full_report, "daily", side_effect=fake_daily) as daily_mock, \
                 patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
                 patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
                 patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            sys.argv = original_argv
            generate_app_full_report.DATE = "20260227"
            generate_app_full_report.DATE_DISPLAY = "2026-02-27"

        expected_dates = [
            "20260310",
            "20260309",
            "20260301",
            "20260302",
            "20260303",
            "20260304",
            "20260305",
            "20260306",
            "20260307",
            "20260308",
            "20260309",
            "20260310",
        ]
        self.assertEqual(daily_mock.call_args_list, [call("app", d) for d in expected_dates])
        self.assertEqual(captured["trend_dates"], expected_dates[2:])
        self.assertEqual(captured["date_display"], "2026-03-10")


class SparklineHelperTests(unittest.TestCase):
    def test_sparkline_ignores_none_and_marks_downward_last_point_red(self):
        svg = sparkline_svg([None, 10, 5], width=30, height=12)

        self.assertIn("<svg", svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertIn("1.0,1.0 29.0,11.0", svg)

    def test_extract_trend_values_is_chronological_and_uses_previous_fallback(self):
        history = [
            {"date": "2026-03-02", "metrics": {"revenue": 20}},
            {"date": "2026-03-01", "metrics": {"revenue": 10}},
        ]

        self.assertEqual(extract_trend_values(history, "revenue", today_val=30), [10.0, 20.0, 30.0])
        self.assertEqual(extract_trend_values([], "revenue", today_val=30, prev_val=25), [25.0, 30.0])


if __name__ == "__main__":
    unittest.main()
