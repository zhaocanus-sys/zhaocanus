import sys
import time
import unittest
from unittest.mock import patch

from agent_system.actions.api_client import parallel_fetch
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html
import generate_app_full_report


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_handles_empty_order_and_exceptions(self):
        self.assertEqual(parallel_fetch([]), [])

        def slow_success():
            time.sleep(0.02)
            return {"rows": ["first"]}

        def fast_success():
            return {"rows": ["second"]}

        def failing_call():
            raise RuntimeError("boom")

        results = parallel_fetch([slow_success, fast_success, failing_call])

        self.assertEqual(results[0], {"rows": ["first"]})
        self.assertEqual(results[1], {"rows": ["second"]})
        self.assertEqual(results[2]["rows"], [])
        self.assertEqual(results[2]["row_count"], 0)
        self.assertIn("boom", results[2]["error"])


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_sorts_groups_and_derives_rate_metrics(self):
        rows = [
            {
                "ftime": "20260302",
                "amt": 1000,
                "pay_num": 10,
                "active_members": 100,
                "refund_money": 50,
                "retain_1d": 20,
                "retain_7d": 10,
                "mems": 40,
                "order_cnt": 20,
                "order_pay": 14,
                "fugou_amt": 100,
            },
            {
                "ftime": "20260301",
                "amt": 0,
                "pay_num": 0,
                "active_members": 0,
                "refund_money": 10,
                "retain_1d": 5,
                "retain_7d": 3,
                "mems": 0,
                "order_cnt": 0,
                "order_pay": 0,
            },
            {
                "ftime": "20260302-extra",
                "amt": 500,
                "pay_num": 5,
                "active_members": 50,
                "refund_money": 25,
                "retain_1d": 10,
                "retain_7d": 5,
                "mems": 20,
                "order_cnt": 10,
                "order_pay": 7,
                "fugou_amt": 50,
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([tr["dt"] for tr in trends], ["2026-03-01", "2026-03-02"])
        self.assertEqual(trends[0]["refund_rate"], 0)
        self.assertEqual(trends[0]["retain_rate_1d"], 0)
        self.assertEqual(trends[0]["retain_rate_7d"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)

        latest = trends[1]
        self.assertEqual(latest["amt"], 1500)
        self.assertEqual(latest["refund_money"], 75)
        self.assertEqual(latest["retain_1d"], 30)
        self.assertEqual(latest["mems"], 60)
        self.assertAlmostEqual(latest["refund_rate"], 5.0)
        self.assertAlmostEqual(latest["retain_rate_1d"], 50.0)
        self.assertAlmostEqual(latest["retain_rate_7d"], 25.0)
        self.assertAlmostEqual(latest["pay_rate"], 10.0)
        self.assertAlmostEqual(latest["order_conv"], 70.0)


class AppHtmlSparklineTests(unittest.TestCase):
    def test_kpi_sparklines_use_same_rate_metric_as_displayed_card(self):
        t = {
            "active": 1000,
            "retain_rate_1d": 45.0,
            "retain_rate_7d": 25.0,
            "pay_rate": 6.0,
            "pay_num": 60,
            "arpu": 30.0,
            "total_rev": 1800.0,
            "fugou_amt": 300.0,
            "fugou_pct": 16.7,
            "refund_rate": 2.5,
            "order_conv": 70.0,
            "order_fail": 3,
            "zhenxin_pct": 60.0,
            "amt_m": 30000.0,
            "pay_m": 900,
        }
        p = dict(t, active=900, total_rev=1600.0)
        trends = [
            {
                "active_members": 900,
                "pay_rate": 5.0,
                "arpu": 25.0,
                "amt": 1600.0,
                "fugou_amt": 200.0,
                "refund_money": 100.0,
                "refund_rate": 1.5,
                "order_conv": 65.0,
                "retain_1d": 350,
                "retain_rate_1d": 35.0,
            },
            {
                "active_members": 1000,
                "pay_rate": 6.0,
                "arpu": 30.0,
                "amt": 1800.0,
                "fugou_amt": 300.0,
                "refund_money": 999.0,
                "refund_rate": 2.5,
                "order_conv": 70.0,
                "retain_1d": 450,
                "retain_rate_1d": 45.0,
            },
        ]
        calls = []

        def fake_sparkline(values, **kwargs):
            calls.append(list(values))
            return "<svg></svg>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            kpi_cards_html(t, p, trends)

        self.assertIn([1.5, 2.5], calls)
        self.assertIn([35.0, 45.0], calls)
        self.assertNotIn([100.0, 999.0], calls)
        self.assertNotIn([350, 450], calls)


class AppFullReportMainTests(unittest.TestCase):
    def test_main_fetches_exact_ten_day_trend_window_and_stamps_ftime(self):
        original_date = generate_app_full_report.DATE
        original_display = generate_app_full_report.DATE_DISPLAY
        captured = {}
        calls = []

        def fake_daily(team, date):
            calls.append((team, date))
            return {"rows": [{"source_date": date}], "row_count": 1}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html></html>"

        try:
            with patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-03-02"]), \
                 patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                 patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
                 patch.object(generate_app_full_report, "export_html", return_value="/tmp/app.html"), \
                 patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            generate_app_full_report.DATE = original_date
            generate_app_full_report.DATE_DISPLAY = original_display

        expected_trend_dates = [
            "20260221", "20260222", "20260223", "20260224", "20260225",
            "20260226", "20260227", "20260228", "20260301", "20260302",
        ]
        self.assertEqual(captured["date_display"], "2026-03-02")
        self.assertEqual(len(calls), 12)
        self.assertEqual(calls[:2], [("app", "20260302"), ("app", "20260301")])
        self.assertEqual([date for _, date in calls[2:]], expected_trend_dates)
        self.assertEqual([row["ftime"] for row in captured["trend_rows"]], expected_trend_dates)
        self.assertEqual([row["source_date"] for row in captured["trend_rows"]], expected_trend_dates)


if __name__ == "__main__":
    unittest.main()
