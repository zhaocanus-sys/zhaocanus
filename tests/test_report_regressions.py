import sys
import unittest
from unittest.mock import patch

from agent_system.actions.api_client import parallel_fetch
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html


class ParallelFetchTests(unittest.TestCase):
    def test_empty_calls_return_empty_list_and_errors_stay_in_position(self):
        self.assertEqual(parallel_fetch([]), [])

        def boom():
            raise RuntimeError("network down")

        results = parallel_fetch([
            lambda: {"rows": [{"id": 1}]},
            boom,
            lambda: {"rows": [{"id": 3}]},
        ])

        self.assertEqual(results[0], {"rows": [{"id": 1}]})
        self.assertEqual(results[2], {"rows": [{"id": 3}]})
        self.assertIn("network down", results[1]["error"])
        self.assertEqual(results[1]["rows"], [])


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_sorts_groups_and_derives_display_rates(self):
        trends = build_trend_data([
            {
                "ftime": "20260228",
                "amt": "0",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "5",
                "retain_1d": "0",
                "retain_7d": "0",
                "mems": "0",
                "order_cnt": "0",
                "order_pay": "0",
            },
            {
                "ftime": "20260227",
                "amt": "1000",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "20",
                "retain_1d": "40",
                "retain_7d": "20",
                "mems": "200",
                "order_cnt": "50",
                "order_pay": "25",
                "fugou_amt": "100",
            },
            {
                "ftime": "20260227",
                "amt": "500",
                "pay_num": "5",
                "active_members": "50",
                "refund_money": "10",
                "retain_1d": "20",
                "retain_7d": "10",
                "mems": "100",
                "order_cnt": "10",
                "order_pay": "5",
                "fugou_amt": "50",
            },
        ])

        self.assertEqual([day["dt"] for day in trends], ["2026-02-27", "2026-02-28"])
        first = trends[0]
        self.assertEqual(first["amt"], 1500)
        self.assertEqual(first["pay_num"], 15)
        self.assertEqual(first["active_members"], 150)
        self.assertEqual(first["fugou_amt"], 150)
        self.assertEqual(first["arpu"], 100)
        self.assertEqual(first["pay_rate"], 10)
        self.assertEqual(first["refund_rate"], 2)
        self.assertEqual(first["retain_rate_1d"], 20)
        self.assertEqual(first["retain_rate_7d"], 10)
        self.assertEqual(first["order_conv"], 50)

        second = trends[1]
        self.assertEqual(second["refund_rate"], 0)
        self.assertEqual(second["retain_rate_1d"], 0)
        self.assertEqual(second["order_conv"], 0)


class AppKpiSparklineTests(unittest.TestCase):
    def test_rate_cards_use_derived_rate_trends_not_raw_counts_or_amounts(self):
        today = {
            "active": 200000,
            "retain_rate_1d": 6.0,
            "retain_rate_7d": 4.0,
            "pay_rate": 5.0,
            "pay_num": 10000,
            "arpu": 30.0,
            "total_rev": 300000,
            "fugou_amt": 50000,
            "fugou_pct": 16.7,
            "refund_rate": 2.0,
            "order_conv": 70.0,
            "order_fail": 30,
            "zhenxin_pct": 60.0,
            "amt_m": 9000000,
            "pay_m": 300000,
        }
        prev = {"active": 190000, "total_rev": 280000}
        trends = [
            {
                "active_members": 190000,
                "pay_rate": 4.5,
                "arpu": 29.0,
                "amt": 280000,
                "fugou_amt": 45000,
                "refund_money": 100,
                "refund_rate": 1.0,
                "order_conv": 65.0,
                "retain_1d": 50,
                "retain_rate_1d": 5.0,
            },
            {
                "active_members": 200000,
                "pay_rate": 5.0,
                "arpu": 30.0,
                "amt": 300000,
                "fugou_amt": 50000,
                "refund_money": 200,
                "refund_rate": 2.0,
                "order_conv": 70.0,
                "retain_1d": 60,
                "retain_rate_1d": 6.0,
            },
        ]

        with patch("agent_system.actions.report_sparkline.sparkline_svg") as spark:
            spark.side_effect = lambda values, **_: "<spark>{}</spark>".format(
                ",".join(str(v) for v in values)
            )
            html = kpi_cards_html(today, prev, trends)

        spark_values = [tuple(call.args[0]) for call in spark.call_args_list]
        self.assertIn((1.0, 2.0), spark_values)
        self.assertIn((5.0, 6.0), spark_values)
        self.assertNotIn((100, 200), spark_values)
        self.assertNotIn((50, 60), spark_values)
        self.assertIn("<spark>1.0,2.0</spark>", html)
        self.assertIn("<spark>5.0,6.0</spark>", html)


class AppReportMainTests(unittest.TestCase):
    def test_main_fetches_today_prev_and_exact_ten_day_trend_without_duplicate_daily(self):
        import generate_app_full_report as report

        original_argv = sys.argv[:]
        sys.argv = ["generate_app_full_report.py", "--date", "2026-03-02"]
        expected_trend_dates = [
            "20260221",
            "20260222",
            "20260223",
            "20260224",
            "20260225",
            "20260226",
            "20260227",
            "20260228",
            "20260301",
            "20260302",
        ]

        def fake_daily(team, date):
            return {"rows": [{"amt": "1", "pay_num": "1", "active_members": "1"}]}

        try:
            with patch.object(report, "daily", side_effect=fake_daily) as daily_mock, \
                    patch.object(report, "generate_html", return_value="<html/>") as html_mock, \
                    patch.object(report, "export_html", return_value="/tmp/app.html"), \
                    patch.object(report, "send_report_email", return_value=True):
                report.main()
        finally:
            sys.argv = original_argv

        call_dates = [call.args[1] for call in daily_mock.call_args_list]
        self.assertEqual(call_dates[:2], ["20260302", "20260301"])
        self.assertEqual(call_dates[2:], expected_trend_dates)
        self.assertEqual(len(call_dates), 12)
        self.assertEqual(call_dates.count("20260302"), 2)

        trend_rows = html_mock.call_args.args[2]
        self.assertEqual([row["ftime"] for row in trend_rows], expected_trend_dates)


if __name__ == "__main__":
    unittest.main()
