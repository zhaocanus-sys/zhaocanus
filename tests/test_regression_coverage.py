import sys
import unittest
from unittest.mock import patch

import generate_app_full_report as app_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class ReportSparklineRegressionTest(unittest.TestCase):
    def test_sparkline_handles_sparse_constant_and_directional_values(self):
        self.assertEqual(sparkline_svg([None, 7]), "")

        constant = sparkline_svg([5, 5, 5], width=30, height=10, color="#abc", fill=False)
        self.assertIn('<svg width="30" height="10"', constant)
        self.assertNotIn("<polygon", constant)
        self.assertIn('stroke="#abc"', constant)
        self.assertIn('fill="#16a34a"', constant)

        falling = sparkline_svg([3, None, 1], fill=True)
        self.assertIn("<polygon", falling)
        self.assertIn('fill="#dc2626"', falling)

    def test_extract_trend_values_preserves_chronology_and_fallback(self):
        history = [
            {"date": "2026-02-27", "metrics": {"revenue": 300}},
            {"date": "2026-02-26", "metrics": {"revenue": 200}},
            {"date": "2026-02-25", "metrics": {"revenue": None}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=400),
            [0.0, 200.0, 300.0, 400.0],
        )
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=9, prev_val=8),
            [8.0, 9.0],
        )


class ApiClientRegressionTest(unittest.TestCase):
    def test_parallel_fetch_empty_order_and_exception_paths(self):
        self.assertEqual(parallel_fetch([]), [])

        calls = [
            lambda: "first",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            lambda: "third",
        ]
        results = parallel_fetch(calls)

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])


class AppReportRegressionTest(unittest.TestCase):
    @staticmethod
    def _app_row(**overrides):
        row = {
            "amt": 100000,
            "pay_num": 10,
            "active_members": 100,
            "refund_money": 0,
            "pay_num_new": 3,
            "retain_1d": 40,
            "retain_7d": 25,
            "order_cnt": 20,
            "order_pay": 10,
            "reg_num_m": 1000,
            "pay_num_m": 200,
            "pay_amt_m": 300000,
            "mems": 100,
            "pay_amt": 100000,
            "zhenxin_member": 50000,
            "super_member_full": 20000,
            "live_guard": 10000,
            "super_member_plus": 5000,
            "zhenai_coin": 4000,
            "super_remind": 3000,
            "star_privilege": 2000,
            "super_recommend": 1000,
            "other": 0,
        }
        row.update(overrides)
        return row

    def test_app_main_fetches_exact_10_day_trend_and_stamps_ftime(self):
        calls = []

        def fake_daily(team, date=None, page=1, size=500):
            calls.append((team, date))
            return {"rows": [self._app_row(amt=1000, marker=date)]}

        expected_trend_dates = [
            "20260218", "20260219", "20260220", "20260221", "20260222",
            "20260223", "20260224", "20260225", "20260226", "20260227",
        ]

        with patch.object(app_report, "daily", side_effect=fake_daily), \
             patch.object(app_report, "generate_html", return_value="<html></html>") as generate_html, \
             patch.object(app_report, "export_html", return_value="/tmp/app.html"), \
             patch.object(app_report, "send_report_email", return_value=True), \
             patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-02-27"]):
            app_report.main()

        self.assertEqual(
            [date for _, date in calls],
            ["20260227", "20260226"] + expected_trend_dates,
        )
        trend_rows = generate_html.call_args.args[2]
        self.assertEqual([row["ftime"] for row in trend_rows], expected_trend_dates)

    def test_product_comparison_renders_real_product_names(self):
        html = app_report.generate_html(
            [self._app_row()],
            [],
            [],
            "2026-02-27",
        )

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("珍心会员设计值得珍爱币借鉴", html)


if __name__ == "__main__":
    unittest.main()
