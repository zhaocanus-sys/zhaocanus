import datetime
import sys
import unittest
from unittest import mock


class ApiClientRegressionTest(unittest.TestCase):
    def test_parallel_fetch_handles_empty_order_and_errors(self):
        from agent_system.actions.api_client import parallel_fetch

        self.assertEqual(parallel_fetch([]), [])

        def boom():
            raise RuntimeError("network unavailable")

        results = parallel_fetch([
            lambda: {"name": "first"},
            boom,
            lambda: {"name": "third"},
        ])

        self.assertEqual(results[0], {"name": "first"})
        self.assertEqual(results[2], {"name": "third"})
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("network unavailable", results[1]["error"])


class AppTrendRegressionTest(unittest.TestCase):
    def test_build_trend_data_sorts_groups_and_derives_rates(self):
        from app_report_data import build_trend_data

        trends = build_trend_data([
            {
                "ftime": "20260227",
                "amt": "0",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "10",
                "order_cnt": "0",
                "order_pay": "0",
            },
            {
                "ftime": "20260226",
                "amt": "1,000",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "20",
                "order_cnt": "50",
                "order_pay": "25",
            },
            {
                "ftime": "20260226",
                "amt": "500",
                "pay_num": "5",
                "active_members": "50",
                "refund_money": "10",
                "order_cnt": "10",
                "order_pay": "5",
            },
        ])

        self.assertEqual([row["dt"] for row in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[0]["amt"], 1500.0)
        self.assertEqual(trends[0]["pay_rate"], 10.0)
        self.assertEqual(trends[0]["order_conv"], 50.0)
        self.assertEqual(trends[0]["refund_rate"], 2.0)
        self.assertEqual(trends[1]["refund_rate"], 0)

    def test_kpi_refund_sparkline_uses_refund_rate_not_refund_amount(self):
        from app_report_html import kpi_cards_html

        metric = {
            "active": 100,
            "pay_num": 10,
            "retain_rate_1d": 20.0,
            "retain_rate_7d": 10.0,
            "pay_rate": 10.0,
            "arpu": 30.0,
            "total_rev": 300.0,
            "fugou_amt": 20.0,
            "fugou_pct": 6.7,
            "refund_rate": 1.5,
            "order_conv": 80.0,
            "order_fail": 2,
            "zhenxin_pct": 50.0,
            "amt_m": 1000.0,
            "pay_m": 40,
        }
        captured_values = []

        def fake_sparkline(values, **_kwargs):
            captured_values.append(list(values))
            return "<svg></svg>"

        with mock.patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            html = kpi_cards_html(
                metric,
                {},
                [
                    {"refund_rate": 1.0, "refund_money": 1000.0},
                    {"refund_rate": 2.0, "refund_money": 9000.0},
                ],
            )

        self.assertIn("退款率", html)
        self.assertEqual(captured_values, [[1.0, 2.0]])


class GenerateAppFullReportRegressionTest(unittest.TestCase):
    def _app_row(self, date="20260227", **overrides):
        row = {
            "ftime": date,
            "amt": 100000,
            "pay_num": 100,
            "active_members": 1000,
            "refund_money": 1000,
            "pay_num_new": 30,
            "retain_1d": 400,
            "retain_7d": 250,
            "order_cnt": 100,
            "order_pay": 80,
            "reg_num_m": 500,
            "pay_num_m": 300,
            "pay_amt_m": 300000,
            "mems": 1000,
            "pay_amt": 100000,
            "zhenxin_member": 60000,
            "super_member_full": 20000,
            "live_guard": 10000,
            "super_member_plus": 5000,
            "zhenai_coin": 3000,
            "super_remind": 1000,
            "star_privilege": 500,
            "super_recommend": 300,
            "other": 200,
        }
        row.update(overrides)
        return row

    def test_product_comparison_interpolates_product_names(self):
        from generate_app_full_report import generate_html

        html = generate_html(
            [self._app_row()],
            [self._app_row("20260226", amt=90000)],
            [self._app_row("20260226"), self._app_row("20260227")],
            "2026-02-27",
        )

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("设计值得", html)
        self.assertIn("珍心会员设计值得", html)

    def test_main_fetches_exact_ten_trend_days_without_duplicate_current_day(self):
        import generate_app_full_report as report

        captured = {}

        def fake_daily(team, date):
            return {"rows": [self._app_row(date=date)], "row_count": 1}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html>ok</html>"

        with mock.patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "20260227"]), \
             mock.patch.object(report, "daily", side_effect=fake_daily) as daily_mock, \
             mock.patch.object(report, "generate_html", side_effect=fake_generate_html), \
             mock.patch.object(report, "export_html", return_value="/tmp/app.html"), \
             mock.patch.object(report, "send_report_email", return_value=True):
            report.main()

        expected_trend_dates = [
            (datetime.date(2026, 2, 27) - datetime.timedelta(days=delta)).strftime("%Y%m%d")
            for delta in range(9, -1, -1)
        ]
        actual_calls = [call.args for call in daily_mock.call_args_list]

        self.assertEqual(actual_calls[:2], [("app", "20260227"), ("app", "20260226")])
        self.assertEqual([args[1] for args in actual_calls[2:]], expected_trend_dates)
        self.assertEqual(len(actual_calls), 12)
        self.assertEqual([row["ftime"] for row in captured["trend_rows"]], expected_trend_dates)
        self.assertEqual(captured["date_display"], "2026-02-27")


if __name__ == "__main__":
    unittest.main()
