import sys
import unittest
from unittest.mock import patch

from agent_system.actions.api_client import parallel_fetch
import generate_app_full_report as app_report


def _app_daily_row(date="20260310", **overrides):
    row = {
        "ftime": date,
        "amt": 1_000_000,
        "pay_num": 10_000,
        "active_members": 200_000,
        "refund_money": 10_000,
        "pay_num_new": 1_000,
        "retain_1d": 80_000,
        "retain_7d": 40_000,
        "order_cnt": 20_000,
        "order_pay": 10_000,
        "reg_num_m": 50_000,
        "pay_num_m": 30_000,
        "pay_amt_m": 20_000_000,
        "mems": 200_000,
        "pay_amt": 1_000_000,
        "zhenxin_member": 900_000,
        "super_member_full": 70_000,
        "live_guard": 20_000,
        "super_member_plus": 5_000,
        "zhenai_coin": 2_000,
        "super_remind": 1_000,
        "star_privilege": 800,
        "super_recommend": 500,
        "other": 200,
    }
    row.update(overrides)
    return row


class AppReportRegressionTests(unittest.TestCase):
    def test_build_trend_data_groups_by_ftime_and_handles_zero_denominators(self):
        trends = app_report.build_trend_data([
            {
                "ftime": "20260302",
                "amt": "100",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "5",
                "retain_1d": "0",
            },
            {
                "ftime": "20260301",
                "amt": "200",
                "pay_num": "4",
                "active_members": "20",
                "refund_money": "3",
                "retain_1d": "8",
            },
            {
                "ftime": "20260301",
                "amt": "100",
                "pay_num": "6",
                "active_members": "30",
                "refund_money": "2",
                "retain_1d": "7",
            },
        ])

        self.assertEqual([t["dt"] for t in trends], ["2026-03-01", "2026-03-02"])
        self.assertEqual(trends[0]["amt"], 300)
        self.assertEqual(trends[0]["pay_num"], 10)
        self.assertEqual(trends[0]["active_members"], 50)
        self.assertEqual(trends[0]["refund_money"], 5)
        self.assertEqual(trends[0]["retain_1d"], 15)
        self.assertEqual(trends[0]["arpu"], 30)
        self.assertEqual(trends[0]["pay_rate"], 20)
        self.assertEqual(trends[1]["arpu"], 0)
        self.assertEqual(trends[1]["pay_rate"], 0)

    def test_generate_app_html_interpolates_product_comparison_names(self):
        html = app_report.generate_html(
            [_app_daily_row()],
            [],
            [],
            "2026-03-10",
        )

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("设计值得", html)
        self.assertIn("珍心会员设计值得", html)

    def test_app_main_fetches_exact_ten_day_trend_window(self):
        calls = []

        def fake_daily(team, date):
            calls.append((team, date))
            return {"rows": [_app_daily_row(date=date)]}

        old_date = app_report.DATE
        old_date_display = app_report.DATE_DISPLAY
        try:
            with patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-03-10"]), \
                 patch.object(app_report, "daily", side_effect=fake_daily), \
                 patch.object(app_report, "export_html", return_value="/tmp/app.html"), \
                 patch.object(app_report, "send_report_email", return_value=True):
                app_report.main()
        finally:
            app_report.DATE = old_date
            app_report.DATE_DISPLAY = old_date_display

        expected_dates = [
            "20260310",  # today
            "20260309",  # previous day
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
        self.assertEqual([team for team, _ in calls], ["app"] * len(expected_dates))
        self.assertEqual([date for _, date in calls], expected_dates)


class ApiClientRegressionTests(unittest.TestCase):
    def test_parallel_fetch_empty_list_and_index_ordered_error_result(self):
        def raise_error():
            raise RuntimeError("boom")

        self.assertEqual(parallel_fetch([]), [])

        results = parallel_fetch([
            lambda: "first",
            raise_error,
            lambda: "third",
        ])

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("boom", results[1]["error"])


if __name__ == "__main__":
    unittest.main()
