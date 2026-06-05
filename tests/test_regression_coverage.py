import datetime
import unittest
from unittest.mock import patch

from agent_system.actions.api_client import parallel_fetch
import agent_system.actions.report_sparkline as report_sparkline
import app_report_data
import app_report_html
import generate_app_full_report


def _app_metrics(**overrides):
    metrics = {
        "active": 100000,
        "retain_rate_1d": 40.0,
        "retain_rate_7d": 25.0,
        "pay_rate": 4.0,
        "pay_num": 4000,
        "arpu": 25.0,
        "total_rev": 100000.0,
        "fugou_amt": 20000.0,
        "fugou_pct": 20.0,
        "refund_rate": 2.0,
        "order_conv": 70.0,
        "order_fail": 30,
        "zhenxin_pct": 70.0,
        "amt_m": 900000.0,
        "pay_m": 30000,
    }
    metrics.update(overrides)
    return metrics


def _full_app_row(**overrides):
    row = {
        "amt": 100000,
        "pay_num": 4000,
        "active_members": 100000,
        "refund_money": 1000,
        "pay_num_new": 800,
        "retain_1d": 400,
        "retain_7d": 250,
        "order_cnt": 1000,
        "order_pay": 700,
        "reg_num_m": 50000,
        "pay_num_m": 30000,
        "pay_amt_m": 900000,
        "mems": 1000,
        "zhenxin_member": 70000,
        "super_member_full": 15000,
        "live_guard": 5000,
        "super_member_plus": 2000,
        "zhenai_coin": 1000,
        "super_remind": 500,
        "star_privilege": 100,
        "super_recommend": 50,
        "other": 0,
    }
    row.update(overrides)
    return row


class RegressionCoverageTest(unittest.TestCase):
    def test_parallel_fetch_handles_empty_order_and_exceptions(self):
        self.assertEqual(parallel_fetch([]), [])

        results = parallel_fetch([lambda: "first", lambda: "second"])
        self.assertEqual(results, ["first", "second"])

        def boom():
            raise RuntimeError("upstream failed")

        ok, failed = parallel_fetch([lambda: {"rows": [1]}, boom])
        self.assertEqual(ok, {"rows": [1]})
        self.assertEqual(failed["rows"], [])
        self.assertIn("upstream failed", failed["error"])

    def test_app_trend_data_computes_rate_metrics_per_day(self):
        trends = app_report_data.build_trend_data([
            {
                "ftime": "20260302",
                "amt": 10000,
                "pay_num": 100,
                "active_members": 1000,
                "refund_money": 100,
                "retain_1d": 400,
                "order_cnt": 50,
                "order_pay": 25,
                "anchmems": 2,
                "giftmems": 3,
                "fugou_amt": 2000,
            },
            {
                "ftime": "20260302",
                "amt": 5000,
                "pay_num": 50,
                "active_members": 500,
                "refund_money": 200,
                "retain_1d": 150,
                "order_cnt": 50,
                "order_pay": 50,
                "anchmems": 1,
                "giftmems": 1,
                "fugou_amt": 1000,
            },
            {
                "ftime": "20260301",
                "amt": 0,
                "pay_num": 0,
                "active_members": 0,
                "refund_money": 99,
                "order_cnt": 0,
                "order_pay": 0,
            },
        ])

        self.assertEqual([trend["dt"] for trend in trends], ["2026-03-01", "2026-03-02"])
        self.assertEqual(trends[0]["refund_rate"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)
        self.assertEqual(trends[1]["amt"], 15000)
        self.assertAlmostEqual(trends[1]["refund_rate"], 2.0)
        self.assertAlmostEqual(trends[1]["pay_rate"], 10.0)
        self.assertAlmostEqual(trends[1]["order_conv"], 75.0)

    def test_app_kpi_refund_sparkline_uses_refund_rate_not_refund_amount(self):
        captured_values = []

        def fake_sparkline(values, width=60, height=22, color="#3b82f6", fill=True):
            captured_values.append(list(values))
            rendered = ",".join(f"{float(v):.1f}" for v in values)
            return f'<svg data-values="{rendered}"></svg>'

        trends = [
            {"refund_rate": 1.0, "refund_money": 1000.0},
            {"refund_rate": 5.0, "refund_money": 5000.0},
        ]

        with patch.object(report_sparkline, "sparkline_svg", side_effect=fake_sparkline):
            html = app_report_html.kpi_cards_html(_app_metrics(), {}, trends)

        refund_card = html.split("退款率", 1)[1].split("订单成功率", 1)[0]
        self.assertIn('data-values="1.0,5.0"', refund_card)
        self.assertNotIn('data-values="1000.0,5000.0"', refund_card)
        self.assertIn([1.0, 5.0], captured_values)

    def test_generate_app_main_fetches_exact_ten_day_window_and_tags_ftime(self):
        original_date = generate_app_full_report.DATE
        original_display = generate_app_full_report.DATE_DISPLAY
        calls = []
        captured = {}

        def fake_daily(team, date):
            calls.append((team, date))
            return {"rows": [{"source_date": date, "amt": 1}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html>ok</html>"

        try:
            with patch.object(generate_app_full_report.sys, "argv", [
                "generate_app_full_report.py", "--date", "2026-03-05"
            ]), patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
                patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
                patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            generate_app_full_report.DATE = original_date
            generate_app_full_report.DATE_DISPLAY = original_display

        base = datetime.datetime.strptime("20260305", "%Y%m%d")
        trend_dates = [
            (base - datetime.timedelta(days=delta)).strftime("%Y%m%d")
            for delta in range(9, -1, -1)
        ]
        expected_dates = ["20260305", "20260304"] + trend_dates
        self.assertEqual(calls, [("app", date) for date in expected_dates])
        self.assertEqual(captured["date_display"], "2026-03-05")
        self.assertEqual([row["ftime"] for row in captured["trend_rows"]], trend_dates)
        self.assertEqual([row["source_date"] for row in captured["trend_rows"]], trend_dates)

    def test_generate_app_product_comparison_interpolates_product_names(self):
        html = generate_app_full_report.generate_html(
            [_full_app_row()],
            [_full_app_row(amt=90000, refund_money=900)],
            [_full_app_row(ftime="20260305")],
            "2026-03-05",
        )

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("设计值得", html)


if __name__ == "__main__":
    unittest.main()
