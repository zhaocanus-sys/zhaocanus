import datetime
import py_compile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_report_data
import app_report_html
import generate_app_full_report


class RecentReportRegressionTests(unittest.TestCase):
    def test_report_modules_compile(self):
        modules = [
            "generate_app_full_report.py",
            "generate_hongniang_full_report.py",
            "generate_jianxin_full_report.py",
            "generate_shop_full_report.py",
            "generate_telesale_full_report.py",
            "app_report_data.py",
            "app_report_html.py",
        ]

        for module in modules:
            with self.subTest(module=module):
                py_compile.compile(str(ROOT / module), doraise=True)

    def test_app_trend_data_computes_refund_rate_after_aggregation(self):
        rows = [
            {
                "ftime": "2026022601",
                "amt": "100",
                "refund_money": "1",
                "pay_num": "5",
                "active_members": "100",
                "order_cnt": "10",
                "order_pay": "8",
            },
            {
                "ftime": "2026022602",
                "amt": "300",
                "refund_money": "9",
                "pay_num": "15",
                "active_members": "300",
                "order_cnt": "30",
                "order_pay": "24",
            },
            {
                "ftime": "2026022701",
                "amt": "200",
                "refund_money": "8",
                "pay_num": "10",
                "active_members": "100",
                "order_cnt": "20",
                "order_pay": "10",
            },
        ]

        for builder in (
            app_report_data.build_trend_data,
            generate_app_full_report.build_trend_data,
        ):
            with self.subTest(builder=builder.__module__):
                trends = builder(rows)

                self.assertEqual(
                    [trend["dt"] for trend in trends],
                    ["2026-02-26", "2026-02-27"],
                )
                self.assertAlmostEqual(trends[0]["refund_rate"], 2.5)
                self.assertAlmostEqual(trends[1]["refund_rate"], 4.0)

    def test_app_kpi_refund_sparkline_uses_refund_rate_not_raw_amount(self):
        today = {
            "active": 200000,
            "retain_rate_1d": 45,
            "retain_rate_7d": 35,
            "pay_rate": 5,
            "pay_num": 10000,
            "arpu": 25,
            "total_rev": 250000,
            "fugou_amt": 50000,
            "fugou_pct": 20,
            "refund_rate": 4,
            "order_conv": 70,
            "order_fail": 3,
            "zhenxin_pct": 70,
            "amt_m": 1000000,
            "pay_m": 20000,
        }
        trends = [
            {"refund_rate": 1.0, "refund_money": 100000},
            {"refund_rate": 4.0, "refund_money": 1000},
        ]
        captured_values = []

        def fake_sparkline(values, **_kwargs):
            captured_values.append(list(values))
            return "<svg></svg>"

        with patch(
            "agent_system.actions.report_sparkline.sparkline_svg",
            side_effect=fake_sparkline,
        ):
            html = app_report_html.kpi_cards_html(today, {}, trends)

        self.assertIn("退款率", html)
        self.assertIn([1.0, 4.0], captured_values)
        self.assertNotIn([100000, 1000], captured_values)

    def test_app_main_fetches_today_previous_and_exact_ten_day_window(self):
        original_date = generate_app_full_report.DATE
        original_date_display = generate_app_full_report.DATE_DISPLAY
        daily_calls = []

        def fake_daily(team, date):
            daily_calls.append((team, date))
            return {"rows": [{"ftime": date, "amt": "100"}]}

        try:
            generate_app_full_report.DATE = "20260227"
            generate_app_full_report.DATE_DISPLAY = "2026-02-27"

            with patch.object(sys, "argv", ["generate_app_full_report.py"]), \
                    patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                    patch.object(generate_app_full_report, "generate_html", return_value="<html></html>"), \
                    patch.object(generate_app_full_report, "export_html", return_value="/tmp/app.html"), \
                    patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            generate_app_full_report.DATE = original_date
            generate_app_full_report.DATE_DISPLAY = original_date_display

        base = datetime.datetime.strptime("20260227", "%Y%m%d")
        ten_day_window = [
            (base - datetime.timedelta(days=delta)).strftime("%Y%m%d")
            for delta in range(9, -1, -1)
        ]
        expected = [("app", "20260227"), ("app", "20260226")]
        expected.extend(("app", date) for date in ten_day_window)

        self.assertEqual(daily_calls, expected)


if __name__ == "__main__":
    unittest.main()
