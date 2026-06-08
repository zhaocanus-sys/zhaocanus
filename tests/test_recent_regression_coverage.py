import sys
import unittest
from unittest.mock import patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions import api_client


def app_daily_row(**overrides):
    row = {
        "amt": "300000",
        "pay_num": "10000",
        "active_members": "200000",
        "refund_money": "6000",
        "pay_num_new": "1200",
        "retain_1d": "90000",
        "retain_7d": "70000",
        "order_cnt": "1000",
        "order_pay": "720",
        "reg_num_m": "800000",
        "pay_num_m": "160000",
        "pay_amt_m": "9000000",
        "mems": "200000",
        "zhenxin_member": "90000",
        "super_member_full": "80000",
        "live_guard": "70000",
        "super_member_plus": "20000",
        "zhenai_coin": "15000",
        "super_remind": "2000",
        "star_privilege": "1500",
        "super_recommend": "1000",
        "other": "800",
        "pay_amt": "300000",
    }
    row.update(overrides)
    return row


class ApiClientRegressionTests(unittest.TestCase):
    def test_parallel_fetch_handles_empty_order_and_exceptions(self):
        self.assertEqual(api_client.parallel_fetch([]), [])

        calls = [
            lambda: {"rows": ["first"]},
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            lambda: {"rows": ["third"]},
        ]
        results = api_client.parallel_fetch(calls)

        self.assertEqual(results[0], {"rows": ["first"]})
        self.assertEqual(results[2], {"rows": ["third"]})
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])


class AppTrendRegressionTests(unittest.TestCase):
    def test_build_trend_data_groups_sorts_and_derives_refund_rate(self):
        rows = [
            {
                "ftime": "20260228",
                "amt": "200",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "10",
                "order_cnt": "10",
                "order_pay": "8",
            },
            {
                "ftime": "20260227",
                "amt": "0",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "50",
                "order_cnt": "0",
                "order_pay": "0",
            },
            {
                "ftime": "20260228",
                "amt": "100",
                "pay_num": "5",
                "active_members": "100",
                "refund_money": "20",
                "order_cnt": "5",
                "order_pay": "3",
            },
        ]

        trends = app_report_data.build_trend_data(rows)

        self.assertEqual([d["dt"] for d in trends], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trends[0]["refund_rate"], 0)
        self.assertEqual(trends[1]["amt"], 300)
        self.assertEqual(trends[1]["refund_money"], 30)
        self.assertEqual(trends[1]["refund_rate"], 10)
        self.assertEqual(trends[1]["arpu"], 20)
        self.assertEqual(trends[1]["pay_rate"], 7.5)
        self.assertEqual(trends[1]["order_conv"], 11 / 15 * 100)

    def test_kpi_refund_sparkline_uses_rate_not_raw_refund_amount(self):
        metric = {
            "active": 200000,
            "retain_rate_1d": 45,
            "retain_rate_7d": 35,
            "pay_rate": 5,
            "pay_num": 10000,
            "arpu": 30,
            "total_rev": 300000,
            "fugou_amt": 60000,
            "fugou_pct": 20,
            "refund_rate": 5,
            "order_conv": 70,
            "order_fail": 300,
            "zhenxin_pct": 30,
            "amt_m": 9000000,
            "pay_m": 160000,
        }
        trends = [
            {
                "active_members": 100,
                "pay_rate": 4,
                "arpu": 30,
                "amt": 1000,
                "fugou_amt": 100,
                "refund_money": 100,
                "refund_rate": 20,
                "order_conv": 60,
                "retain_1d": 30,
            },
            {
                "active_members": 110,
                "pay_rate": 5,
                "arpu": 31,
                "amt": 2000,
                "fugou_amt": 200,
                "refund_money": 200,
                "refund_rate": 5,
                "order_conv": 70,
                "retain_1d": 35,
            },
        ]
        captured = []

        def fake_sparkline(values, **kwargs):
            captured.append((tuple(values), kwargs.get("color")))
            return "<sparkline/>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            html = app_report_html.kpi_cards_html(metric, {}, trends)

        self.assertIn("<sparkline/>", html)
        self.assertIn(((20, 5), "#dc2626"), captured)
        self.assertNotIn(((100, 200), "#dc2626"), captured)


class GenerateAppFullReportRegressionTests(unittest.TestCase):
    def test_main_fetches_exact_ten_day_trend_window_without_extra_current_request(self):
        calls = []
        captured = {}

        def fake_daily(team, date):
            calls.append((team, date))
            return {"rows": [{"amt": "1"}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html>ok</html>"

        old_date = generate_app_full_report.DATE
        old_date_display = generate_app_full_report.DATE_DISPLAY
        try:
            with patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-03-05"]), \
                    patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                    patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
                    patch.object(generate_app_full_report, "export_html", return_value="/tmp/app.html"), \
                    patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            generate_app_full_report.DATE = old_date
            generate_app_full_report.DATE_DISPLAY = old_date_display

        trend_window = [
            "20260224", "20260225", "20260226", "20260227", "20260228",
            "20260301", "20260302", "20260303", "20260304", "20260305",
        ]
        self.assertEqual([d for _, d in calls], ["20260305", "20260304"] + trend_window)
        self.assertEqual(calls.count(("app", "20260305")), 2)
        self.assertEqual([r["ftime"] for r in captured["trend_rows"]], trend_window)
        self.assertEqual(captured["date_display"], "2026-03-05")

    def test_product_comparison_renders_names_without_placeholder_leakage(self):
        html = generate_app_full_report.generate_html(
            [app_daily_row()],
            [app_daily_row(amt="250000")],
            [app_daily_row(ftime="20260227")],
            "2026-02-27",
        )

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("设计值得", html)
        self.assertIn("珍心会员", html)


if __name__ == "__main__":
    unittest.main()
