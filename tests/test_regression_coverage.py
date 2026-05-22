import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ApiClientRegressionTests(unittest.TestCase):
    def test_parallel_fetch_empty_call_list_returns_empty_result(self):
        from agent_system.actions.api_client import parallel_fetch

        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_wraps_exceptions(self):
        from agent_system.actions.api_client import parallel_fetch

        def boom():
            raise RuntimeError("network timeout")

        results = parallel_fetch([
            lambda: {"rows": [{"idx": 0}]},
            boom,
            lambda: {"rows": [{"idx": 2}]},
        ])

        self.assertEqual(results[0], {"rows": [{"idx": 0}]})
        self.assertEqual(results[2], {"rows": [{"idx": 2}]})
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("network timeout", results[1]["error"])


class AppTrendRegressionTests(unittest.TestCase):
    def test_build_trend_data_groups_by_day_and_derives_rates(self):
        from generate_app_full_report import build_trend_data

        trends = build_trend_data([
            {
                "ftime": "20260228",
                "amt": "300",
                "pay_num": "3",
                "active_members": "30",
                "refund_money": "9",
                "retain_1d": "6",
            },
            {
                "ftime": "20260227",
                "amt": "100",
                "pay_num": "2",
                "active_members": "50",
                "refund_money": "0",
                "retain_1d": "5",
            },
            {
                "ftime": "20260227",
                "amt": "50",
                "pay_num": "1",
                "active_members": "25",
                "refund_money": "1",
                "retain_1d": "0",
            },
            {
                "ftime": "20260301",
                "amt": "10",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "0",
                "retain_1d": "0",
            },
        ])

        self.assertEqual([row["dt"] for row in trends], ["2026-02-27", "2026-02-28", "2026-03-01"])
        self.assertEqual(trends[0]["amt"], 150)
        self.assertEqual(trends[0]["pay_num"], 3)
        self.assertEqual(trends[0]["active_members"], 75)
        self.assertEqual(trends[0]["refund_money"], 1)
        self.assertEqual(trends[0]["retain_1d"], 5)
        self.assertEqual(trends[0]["arpu"], 50)
        self.assertEqual(trends[0]["pay_rate"], 4)
        self.assertEqual(trends[2]["arpu"], 0)
        self.assertEqual(trends[2]["pay_rate"], 0)

    def test_app_main_fetches_today_previous_and_exact_ten_day_trend(self):
        import generate_app_full_report as app_report

        calls = []

        def fake_daily(team, date):
            calls.append((team, date))
            return {
                "rows": [{
                    "amt": "100",
                    "pay_num": "10",
                    "active_members": "100",
                    "refund_money": "0",
                    "retain_1d": "20",
                    "retain_7d": "10",
                    "order_cnt": "10",
                    "order_pay": "8",
                    "reg_num_m": "50",
                    "pay_num_m": "20",
                    "pay_amt_m": "1000",
                    "mems": "40",
                    "zhenxin_member": "50",
                    "pay_amt": "100",
                }]
            }

        with patch.object(app_report.sys, "argv", ["generate_app_full_report.py", "--date", "2026-03-02", "--no-email"]), \
             patch.object(app_report, "daily", side_effect=fake_daily), \
             patch.object(app_report, "generate_html", return_value="<html>ok</html>") as generate_html, \
             patch.object(app_report, "export_html", return_value="/tmp/app.html"), \
             patch.object(app_report, "send_report_email", return_value=True):
            app_report.main()

        expected_dates = ["20260302", "20260301"] + [
            "20260221", "20260222", "20260223", "20260224", "20260225",
            "20260226", "20260227", "20260228", "20260301", "20260302",
        ]
        self.assertEqual(calls, [("app", date) for date in expected_dates])

        trend_rows = generate_html.call_args.args[2]
        self.assertEqual(len(trend_rows), 10)
        self.assertEqual([row["ftime"] for row in trend_rows], expected_dates[2:])


class SparklineRegressionTests(unittest.TestCase):
    def test_sparkline_handles_sparse_constant_and_directional_values(self):
        from agent_system.actions.report_sparkline import sparkline_svg

        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 5]), "")

        flat = sparkline_svg([7, 7, 7], width=30, height=10, fill=False)
        self.assertIn('<svg width="30" height="10"', flat)
        self.assertNotIn("<polygon", flat)
        self.assertIn('points="1.0,9.0 15.0,9.0 29.0,9.0"', flat)
        self.assertIn('fill="#16a34a"', flat)

        down = sparkline_svg([3, 1], fill=False)
        self.assertIn('fill="#dc2626"', down)

    def test_extract_trend_values_reverses_recall_order_and_fills_fallbacks(self):
        from agent_system.actions.report_sparkline import extract_trend_values

        history = [
            {"date": "2026-03-02", "metrics": {"revenue": 300}},
            {"date": "2026-03-01", "metrics": {"revenue": None}},
            {"date": "2026-02-28", "metrics": {}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=400),
            [0.0, 0.0, 300.0, 400.0],
        )
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=400, prev_val=250),
            [250.0, 400.0],
        )


if __name__ == "__main__":
    unittest.main()
