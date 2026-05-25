import sys
import unittest
from unittest.mock import patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch


class ApiClientRegressionTests(unittest.TestCase):
    def test_parallel_fetch_handles_empty_calls(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_wraps_errors(self):
        def first():
            return {"rows": [1]}

        def second():
            raise RuntimeError("boom")

        def third():
            return {"rows": [3]}

        result = parallel_fetch([first, second, third])

        self.assertEqual(result[0], {"rows": [1]})
        self.assertEqual(result[2], {"rows": [3]})
        self.assertEqual(result[1]["rows"], [])
        self.assertIn("boom", result[1]["error"])


class AppReportTrendRegressionTests(unittest.TestCase):
    def test_main_fetches_exact_10_day_trend_window_and_stamps_ftime(self):
        calls = []
        captured = {}

        def fake_daily(team, date):
            calls.append((team, date))
            return {
                "rows": [{
                    "amt": 100,
                    "pay_num": 5,
                    "active_members": 100,
                    "refund_money": 1,
                    "retain_1d": 40,
                }]
            }

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html>ok</html>"

        argv = ["generate_app_full_report.py", "--date", "2026-02-27"]
        with patch.object(sys, "argv", argv), \
                patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
                patch.object(generate_app_full_report, "export_html", return_value="/tmp/app.html"), \
                patch.object(generate_app_full_report, "send_report_email", return_value=True):
            generate_app_full_report.main()

        expected_dates = [
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
        ]
        self.assertEqual([date for _, date in calls], expected_dates)
        self.assertTrue(all(team == "app" for team, _ in calls))
        self.assertEqual(
            [row["ftime"] for row in captured["trend_rows"]],
            expected_dates[2:],
        )
        self.assertEqual(captured["date_display"], "2026-02-27")

    def test_product_comparison_renders_real_names_not_template_placeholders(self):
        today = [{
            "amt": 1_000_000,
            "pay_num": 100,
            "active_members": 10_000,
            "refund_money": 0,
            "retain_1d": 5_000,
            "retain_7d": 4_000,
            "order_cnt": 100,
            "order_pay": 80,
            "mems": 10_000,
            "zhenxin_member": 900_000,
            "super_member_full": 50_000,
            "live_guard": 30_000,
            "super_member_plus": 15_000,
            "zhenai_coin": 4_000,
            "super_remind": 600,
            "star_privilege": 300,
            "super_recommend": 80,
            "other": 20,
        }]

        html = generate_app_full_report.generate_html(today, [], [], "2026-02-27")

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("珍心会员设计值得", html)

    def test_trend_data_and_kpi_sparkline_use_refund_rate_not_raw_refund_amount(self):
        trends = app_report_data.build_trend_data([
            {"ftime": "20260226", "amt": 10_000, "refund_money": 100},
            {"ftime": "20260227", "amt": 20_000, "refund_money": 500},
        ])
        self.assertEqual([t["refund_rate"] for t in trends], [1.0, 2.5])

        t = {
            "active": 1000,
            "retain_rate_1d": 40,
            "retain_rate_7d": 30,
            "pay_rate": 5,
            "pay_num": 50,
            "arpu": 400,
            "total_rev": 20_000,
            "fugou_amt": 0,
            "fugou_pct": 0,
            "refund_rate": 2.5,
            "order_conv": 0,
            "order_fail": 0,
            "zhenxin_pct": 50,
            "amt_m": 0,
            "pay_m": 0,
        }

        with patch("agent_system.actions.report_sparkline.sparkline_svg", return_value="") as sparkline:
            app_report_html.kpi_cards_html(t, {}, trends)

        non_empty_series = [
            call.args[0] for call in sparkline.call_args_list if call.args[0]
        ]
        self.assertIn([1.0, 2.5], non_empty_series)
        self.assertNotIn([100.0, 500.0], non_empty_series)


if __name__ == "__main__":
    unittest.main()
