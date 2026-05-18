import unittest
from unittest.mock import patch

import app_report_data
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch


def app_daily_row(**overrides):
    row = {
        "amt": 211000,
        "pay_num": 100,
        "active_members": 2000,
        "refund_money": 1000,
        "pay_num_new": 30,
        "retain_1d": 900,
        "retain_7d": 600,
        "order_cnt": 200,
        "order_pay": 120,
        "reg_num_m": 3000,
        "pay_num_m": 500,
        "pay_amt_m": 900000,
        "mems": 3000,
        "zhenxin_member": 90000,
        "super_member_full": 50000,
        "live_guard": 30000,
        "super_member_plus": 20000,
        "zhenai_coin": 10000,
        "super_remind": 5000,
        "star_privilege": 3000,
        "super_recommend": 2000,
        "other": 1000,
        "pay_amt": 211000,
        "fugou_amt": 50000,
        "anchmems": 10,
        "giftmems": 50,
    }
    row.update(overrides)
    return row


class ParallelFetchRegressionTest(unittest.TestCase):
    def test_parallel_fetch_empty_calls_returns_empty_list(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_converts_errors(self):
        def fail():
            raise RuntimeError("boom")

        results = parallel_fetch([lambda: "first", fail, lambda: "third"])

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])


class AppTrendRegressionTest(unittest.TestCase):
    def test_app_report_data_groups_by_ftime_sorts_and_handles_zero_denominators(self):
        trends = app_report_data.build_trend_data([
            app_daily_row(ftime="20260302000000", amt=50, pay_num=0, active_members=0,
                          order_cnt=0, order_pay=0, fugou_amt=5),
            app_daily_row(ftime="20260301000000", amt=100, pay_num=5, active_members=100,
                          order_cnt=10, order_pay=4, fugou_amt=10),
            app_daily_row(ftime="20260301000000", amt=200, pay_num=5, active_members=100,
                          order_cnt=10, order_pay=6, fugou_amt=15),
        ])

        self.assertEqual([day["dt"] for day in trends], ["2026-03-01", "2026-03-02"])
        self.assertEqual(trends[0]["amt"], 300)
        self.assertEqual(trends[0]["pay_num"], 10)
        self.assertEqual(trends[0]["arpu"], 30)
        self.assertEqual(trends[0]["pay_rate"], 5)
        self.assertEqual(trends[0]["order_conv"], 50)
        self.assertEqual(trends[0]["fugou_amt"], 25)
        self.assertEqual(trends[1]["arpu"], 0)
        self.assertEqual(trends[1]["pay_rate"], 0)
        self.assertEqual(trends[1]["order_conv"], 0)

    def test_generate_app_full_report_renders_product_names_not_placeholders(self):
        html = generate_app_full_report.generate_html(
            [app_daily_row()],
            [app_daily_row(amt=200000, pay_num=100, active_members=2000)],
            [app_daily_row(ftime="20260309000000"), app_daily_row(ftime="20260310000000")],
            "2026-03-10",
        )

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("珍心会员设计值得珍爱币借鉴", html)

    def test_generate_app_main_fetches_exact_ten_day_trend_window(self):
        requested_dates = []
        original_date = generate_app_full_report.DATE
        original_display = generate_app_full_report.DATE_DISPLAY

        def fake_daily(team, date):
            self.assertEqual(team, "app")
            requested_dates.append(date)
            return {"rows": [app_daily_row(ftime=date)]}

        try:
            with patch.object(generate_app_full_report.sys, "argv",
                              ["generate_app_full_report.py", "--date", "2026-03-10"]), \
                 patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                 patch.object(generate_app_full_report, "generate_html", return_value="<html></html>") as html_mock, \
                 patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
                 patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            generate_app_full_report.DATE = original_date
            generate_app_full_report.DATE_DISPLAY = original_display

        self.assertEqual(
            requested_dates,
            ["20260310", "20260309"]
            + [f"202603{day:02d}" for day in range(1, 11)],
        )
        _, _, trend_rows, date_display = html_mock.call_args.args
        self.assertEqual(date_display, "2026-03-10")
        self.assertEqual([row["ftime"] for row in trend_rows],
                         [f"202603{day:02d}" for day in range(1, 11)])


if __name__ == "__main__":
    unittest.main()
