import datetime
import sys
import unittest
from unittest.mock import patch

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class ParallelFetchRegressionTests(unittest.TestCase):
    def test_empty_call_list_returns_empty_result(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_preserves_order_and_converts_worker_exceptions_to_error_payload(self):
        def fail():
            raise RuntimeError("boom")

        results = parallel_fetch([
            lambda: {"rows": [1]},
            fail,
            lambda: {"rows": [3]},
        ])

        self.assertEqual(results[0], {"rows": [1]})
        self.assertEqual(results[2], {"rows": [3]})
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("boom", results[1]["error"])


class SparklineRegressionTests(unittest.TestCase):
    def test_sparkline_handles_none_values_and_constant_series(self):
        increasing = sparkline_svg([None, 10, 20], width=10, height=6, color="#111111", fill=False)
        self.assertIn('<svg width="10" height="6"', increasing)
        self.assertIn('<polyline points="1.0,5.0 9.0,1.0"', increasing)
        self.assertNotIn("<polygon", increasing)
        self.assertIn('fill="#16a34a"', increasing)

        constant = sparkline_svg([7, 7, 7])
        self.assertIn("<svg", constant)
        self.assertIn("<polyline", constant)

    def test_extract_trend_values_returns_chronological_series_with_fallbacks(self):
        history_from_recall = [
            {"date": "20260303", "metrics": {"revenue": 300, "refund_rate": None}},
            {"date": "20260302", "metrics": {"revenue": "200"}},
            {"date": "20260301", "metrics": {"revenue": 100}},
        ]

        self.assertEqual(
            extract_trend_values(history_from_recall, "revenue", today_val=400),
            [100.0, 200.0, 300.0, 400.0],
        )
        self.assertEqual(
            extract_trend_values(history_from_recall, "refund_rate", today_val=1.5),
            [0.0, 0.0, 0.0, 1.5],
        )
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=120, prev_val=100),
            [100.0, 120.0],
        )


class AppReportTrendFetchRegressionTests(unittest.TestCase):
    def test_main_fetches_exact_ten_day_trend_window_and_stamps_dates(self):
        import generate_app_full_report as report

        target_date = "20260305"
        base_dt = datetime.datetime.strptime(target_date, "%Y%m%d")
        expected_trend_dates = [
            (base_dt - datetime.timedelta(days=delta)).strftime("%Y%m%d")
            for delta in range(9, -1, -1)
        ]
        daily_calls = []
        captured = {}

        def fake_daily(team, date):
            daily_calls.append((team, date))
            return {"rows": [{"amt": "100", "pay_num": "1", "active_members": "10"}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html>ok</html>"

        old_argv = sys.argv[:]
        try:
            sys.argv = ["generate_app_full_report.py", "--date", target_date]
            with patch.object(report, "daily", side_effect=fake_daily), \
                 patch.object(report, "generate_html", side_effect=fake_generate_html), \
                 patch.object(report, "export_html", return_value="/tmp/app.html"), \
                 patch.object(report, "send_report_email", return_value=True):
                report.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(
            daily_calls,
            [("app", target_date), ("app", "20260304")] +
            [("app", d) for d in expected_trend_dates],
        )
        self.assertEqual(captured["date_display"], "2026-03-05")
        self.assertEqual(len(captured["trend_rows"]), 10)
        self.assertEqual([row["ftime"] for row in captured["trend_rows"]], expected_trend_dates)


if __name__ == "__main__":
    unittest.main()
