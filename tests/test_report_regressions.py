import sys
import unittest
from unittest.mock import patch


class ParallelFetchTests(unittest.TestCase):
    def test_empty_call_list_returns_empty_result(self):
        from agent_system.actions.api_client import parallel_fetch

        self.assertEqual(parallel_fetch([]), [])


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_derives_rate_metrics_by_day(self):
        from app_report_data import build_trend_data

        rows = [
            {
                "ftime": "20260227",
                "amt": 200,
                "pay_num": 4,
                "active_members": 40,
                "refund_money": 20,
                "retain_1d": 12,
                "mems": 30,
                "order_cnt": 10,
                "order_pay": 7,
                "fugou_amt": 50,
            },
            {
                "ftime": "20260226",
                "amt": 0,
                "pay_num": 0,
                "active_members": 0,
                "refund_money": 5,
                "retain_1d": 0,
                "mems": 0,
                "order_cnt": 0,
                "order_pay": 0,
                "fugou_amt": 0,
            },
            {
                "ftime": "20260227",
                "amt": 300,
                "pay_num": 6,
                "active_members": 60,
                "refund_money": 5,
                "retain_1d": 8,
                "mems": 20,
                "order_cnt": 10,
                "order_pay": 8,
                "fugou_amt": 25,
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([day["dt"] for day in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[0]["refund_rate"], 0)
        self.assertEqual(trends[0]["retain_rate_1d"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)

        latest = trends[1]
        self.assertEqual(latest["amt"], 500)
        self.assertEqual(latest["refund_money"], 25)
        self.assertAlmostEqual(latest["refund_rate"], 5.0)
        self.assertAlmostEqual(latest["retain_rate_1d"], 40.0)
        self.assertAlmostEqual(latest["pay_rate"], 10.0)
        self.assertAlmostEqual(latest["order_conv"], 75.0)


class AppKpiSparklineTests(unittest.TestCase):
    def test_kpi_sparklines_use_rate_metrics_not_raw_counts(self):
        import app_report_html

        t = {
            "active": 1000,
            "retain_rate_1d": 40.0,
            "retain_rate_7d": 25.0,
            "pay_rate": 6.0,
            "pay_num": 60,
            "arpu": 33.0,
            "total_rev": 1980.0,
            "fugou_amt": 250.0,
            "fugou_pct": 12.6,
            "refund_rate": 4.56,
            "order_conv": 80.0,
            "order_fail": 5,
            "zhenxin_pct": 60.0,
            "amt_m": 100000.0,
            "pay_m": 3000,
        }
        p = dict(t, active=900, total_rev=1800.0)
        trends = [
            {
                "active_members": 900,
                "retain_1d": 300,
                "retain_rate_1d": 30.0,
                "pay_rate": 5.0,
                "arpu": 30.0,
                "amt": 1800.0,
                "fugou_amt": 200.0,
                "refund_money": 987.0,
                "refund_rate": 9.87,
                "order_conv": 70.0,
            },
            {
                "active_members": 1000,
                "retain_1d": 400,
                "retain_rate_1d": 40.0,
                "pay_rate": 6.0,
                "arpu": 33.0,
                "amt": 1980.0,
                "fugou_amt": 250.0,
                "refund_money": 456.0,
                "refund_rate": 4.56,
                "order_conv": 80.0,
            },
        ]
        captured = []

        def fake_sparkline(values, **kwargs):
            captured.append(tuple(values))
            return "<svg></svg>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            html = app_report_html.kpi_cards_html(t, p, trends)

        self.assertIn("退款率", html)
        self.assertIn((9.87, 4.56), captured)
        self.assertIn((30.0, 40.0), captured)
        self.assertNotIn((987.0, 456.0), captured)
        self.assertNotIn((300, 400), captured)


class GenerateAppFullReportTests(unittest.TestCase):
    def test_main_fetches_today_prev_and_exact_ten_day_trend_window(self):
        import generate_app_full_report as report

        called_dates = []
        captured_trend_rows = []

        def fake_daily(team, date):
            called_dates.append(date)
            return {"rows": [{"amt": 1000, "pay_num": 10, "active_members": 100}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured_trend_rows.extend(trend_rows)
            self.assertEqual(date_display, "2026-02-27")
            self.assertEqual(today_rows[0]["amt"], 1000)
            self.assertEqual(prev_rows[0]["pay_num"], 10)
            return "<html></html>"

        with patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-02-27"]), \
             patch.object(report, "daily", side_effect=fake_daily), \
             patch.object(report, "generate_html", side_effect=fake_generate_html), \
             patch.object(report, "export_html", return_value="/tmp/report.html"), \
             patch.object(report, "send_report_email", return_value=True):
            report.main()

        expected_window = [
            "20260218", "20260219", "20260220", "20260221", "20260222",
            "20260223", "20260224", "20260225", "20260226", "20260227",
        ]
        self.assertEqual(called_dates, ["20260227", "20260226"] + expected_window)
        self.assertEqual([row["ftime"] for row in captured_trend_rows], expected_window)

    def test_product_compare_reason_interpolates_real_product_names(self):
        import generate_app_full_report as report

        row = {
            "amt": 1000000,
            "pay_num": 100,
            "active_members": 1000,
            "refund_money": 10000,
            "pay_num_new": 20,
            "retain_1d": 500,
            "retain_7d": 300,
            "order_cnt": 120,
            "order_pay": 100,
            "reg_num_m": 10000,
            "pay_num_m": 3000,
            "pay_amt_m": 5000000,
            "mems": 1000,
            "pay_amt": 1000000,
            "zhenxin_member": 500000,
            "super_member_full": 200000,
            "live_guard": 100000,
            "super_member_plus": 90000,
            "zhenai_coin": 50000,
            "super_remind": 30000,
            "star_privilege": 20000,
            "super_recommend": 10000,
            "other": 1000,
        }

        html = report.generate_html([row], [dict(row, amt=900000)], [dict(row, ftime="20260227")], "2026-02-27")

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("珍心会员设计值得珍爱币借鉴", html)


if __name__ == "__main__":
    unittest.main()
