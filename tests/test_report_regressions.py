import sys
import unittest
from unittest.mock import patch

from agent_system.actions.api_client import parallel_fetch
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html


class ParallelFetchTests(unittest.TestCase):
    def test_empty_order_and_exception_handling(self):
        self.assertEqual(parallel_fetch([]), [])

        def fail():
            raise RuntimeError("boom")

        results = parallel_fetch([
            lambda: "first",
            fail,
            lambda: "third",
        ])

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])


class AppTrendTests(unittest.TestCase):
    def test_build_trend_data_groups_sorts_and_derives_display_rates(self):
        trends = build_trend_data([
            {
                "ftime": "20260228093000",
                "amt": "10000",
                "pay_num": "100",
                "active_members": "1000",
                "refund_money": "100",
                "retain_1d": "20",
                "retain_7d": "10",
                "mems": "200",
                "order_cnt": "50",
                "order_pay": "25",
                "fugou_amt": "2500",
            },
            {
                "ftime": "20260227093000",
                "amt": "0",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "100",
                "retain_1d": "10",
                "retain_7d": "5",
                "mems": "0",
                "order_cnt": "0",
                "order_pay": "0",
                "fugou_amt": "0",
            },
            {
                "ftime": "20260228094500",
                "amt": "90000",
                "pay_num": "300",
                "active_members": "3000",
                "refund_money": "2900",
                "retain_1d": "60",
                "retain_7d": "30",
                "mems": "600",
                "order_cnt": "50",
                "order_pay": "50",
                "fugou_amt": "7500",
            },
        ])

        self.assertEqual([t["dt"] for t in trends], ["2026-02-27", "2026-02-28"])
        zero_day, active_day = trends
        self.assertEqual(zero_day["refund_rate"], 0)
        self.assertEqual(zero_day["retain_rate_1d"], 0)
        self.assertEqual(zero_day["order_conv"], 0)
        self.assertEqual(active_day["amt"], 100000)
        self.assertEqual(active_day["pay_rate"], 10)
        self.assertEqual(active_day["refund_rate"], 3)
        self.assertEqual(active_day["retain_rate_1d"], 10)
        self.assertEqual(active_day["retain_rate_7d"], 5)
        self.assertEqual(active_day["order_conv"], 75)
        self.assertEqual(active_day["fugou_pct"], 10)

    def test_kpi_cards_use_rate_trends_not_raw_counts_or_amounts(self):
        t = {
            "active": 3000,
            "retain_rate_1d": 40.0,
            "retain_rate_7d": 20.0,
            "pay_rate": 10.0,
            "pay_num": 300,
            "arpu": 333.3,
            "total_rev": 100000,
            "fugou_amt": 10000,
            "fugou_pct": 10.0,
            "refund_rate": 3.0,
            "order_conv": 75.0,
            "order_fail": 25,
            "zhenxin_pct": 70.0,
            "amt_m": 1000000,
            "pay_m": 3000,
        }
        trends = build_trend_data([
            {
                "ftime": "20260227000000",
                "amt": "10000",
                "pay_num": "100",
                "active_members": "1000",
                "refund_money": "100",
                "retain_1d": "20",
                "retain_7d": "10",
                "mems": "200",
                "order_cnt": "100",
                "order_pay": "50",
                "fugou_amt": "1000",
            },
            {
                "ftime": "20260228000000",
                "amt": "100000",
                "pay_num": "300",
                "active_members": "3000",
                "refund_money": "3000",
                "retain_1d": "80",
                "retain_7d": "40",
                "mems": "200",
                "order_cnt": "100",
                "order_pay": "75",
                "fugou_amt": "10000",
            },
        ])
        spark_values = []

        def capture(values, *args, **kwargs):
            spark_values.append(values)
            return "<svg></svg>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=capture):
            html = kpi_cards_html(t, {}, trends=trends)

        self.assertIn("退款率", html)
        self.assertEqual(spark_values[1], [10.0, 40.0])
        self.assertEqual(spark_values[6], [1.0, 3.0])


class GenerateAppFullReportTests(unittest.TestCase):
    def test_main_fetches_exact_ten_day_trend_without_unused_duplicate(self):
        import generate_app_full_report as report

        call_dates = []

        def fake_daily(team, date):
            call_dates.append(date)
            return {"rows": [{"amt": "1"}]}

        with patch.object(report, "daily", side_effect=fake_daily), \
                patch.object(report, "generate_html", return_value="<html></html>") as gen_html, \
                patch.object(report, "export_html", return_value="/tmp/report.html"), \
                patch.object(report, "send_report_email", return_value=True), \
                patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-02-28"]):
            report.main()

        self.assertEqual(len(call_dates), 12)
        self.assertEqual(call_dates[0], "20260228")
        self.assertEqual(call_dates[1], "20260227")
        self.assertEqual(call_dates[2:], [
            "20260219", "20260220", "20260221", "20260222", "20260223",
            "20260224", "20260225", "20260226", "20260227", "20260228",
        ])
        self.assertEqual(call_dates.count("20260228"), 2)
        trend_rows = gen_html.call_args.args[2]
        self.assertEqual([row["ftime"] for row in trend_rows], call_dates[2:])

    def test_product_comparison_does_not_leak_placeholders(self):
        import generate_app_full_report as report

        today = {
            "amt": "100000",
            "pay_num": "100",
            "active_members": "1000",
            "refund_money": "1000",
            "pay_num_new": "10",
            "retain_1d": "400",
            "retain_7d": "200",
            "order_cnt": "100",
            "order_pay": "80",
            "reg_num_m": "5000",
            "pay_num_m": "1000",
            "pay_amt_m": "1000000",
            "mems": "1000",
            "zhenxin_member": "60000",
            "super_member_full": "20000",
            "live_guard": "10000",
            "super_member_plus": "4000",
            "zhenai_coin": "3000",
            "super_remind": "2000",
            "star_privilege": "700",
            "super_recommend": "200",
            "other": "100",
        }
        html = report.generate_html([today], [today], [dict(today, ftime="20260228")], "2026-02-28")

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("设计值得", html)


if __name__ == "__main__":
    unittest.main()
