import tempfile
import time
import unittest
from pathlib import Path

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.memory_manager import ReportMemory
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class ReportSparklineTests(unittest.TestCase):
    def test_sparkline_handles_missing_points_and_marks_decline(self):
        svg = sparkline_svg([10, None, 20, 15], width=40, height=20, color="#123456")

        self.assertTrue(svg.startswith('<svg width="40" height="20"'))
        self.assertIn('<polyline points="', svg)
        self.assertIn('stroke="#123456"', svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertNotIn("None", svg)

    def test_sparkline_flat_values_do_not_divide_by_zero(self):
        svg = sparkline_svg([5, 5, 5], fill=False)

        self.assertIn("<svg", svg)
        self.assertIn('fill="#16a34a"', svg)
        self.assertNotIn("<polygon", svg)

    def test_sparkline_requires_at_least_two_numeric_points(self):
        self.assertEqual("", sparkline_svg([None, 7]))
        self.assertEqual("", sparkline_svg([7]))

    def test_extract_trend_values_returns_chronological_history_then_today(self):
        history_desc = [
            {"date": "20260226", "metrics": {"revenue": "30"}},
            {"date": "20260225", "metrics": {"revenue": None}},
            {"date": "20260224", "metrics": {}},
        ]

        values = extract_trend_values(history_desc, "revenue", today_val="40")

        self.assertEqual([0.0, 0.0, 30.0, 40.0], values)

    def test_extract_trend_values_uses_previous_value_when_history_is_empty(self):
        values = extract_trend_values([], "revenue", today_val=120, prev_val=100)

        self.assertEqual([100.0, 120.0], values)


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_returns_empty_list_for_no_calls(self):
        self.assertEqual([], parallel_fetch([]))

    def test_parallel_fetch_preserves_call_order_despite_completion_order(self):
        def slow_first():
            time.sleep(0.03)
            return {"name": "first"}

        def fast_second():
            return {"name": "second"}

        results = parallel_fetch([slow_first, fast_second])

        self.assertEqual([{"name": "first"}, {"name": "second"}], results)

    def test_parallel_fetch_converts_worker_exceptions_to_error_payload(self):
        def ok():
            return {"rows": [1]}

        def boom():
            raise RuntimeError("api unavailable")

        results = parallel_fetch([ok, boom])

        self.assertEqual({"rows": [1]}, results[0])
        self.assertIn("api unavailable", results[1]["error"])
        self.assertEqual([], results[1]["rows"])
        self.assertEqual(0, results[1]["row_count"])
        self.assertEqual([], results[1]["columns"])


class ReportMemoryTests(unittest.TestCase):
    def test_recall_filters_before_date_orders_descending_and_upserts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            memory = ReportMemory(db_path=db_path)
            memory.save("app", "20260224", {"total_rev": 10})
            memory.save("app", "20260225", {"total_rev": 20})
            memory.save("app", "20260226", {"total_rev": 30})
            memory.save("app", "20260227", {"total_rev": 40})
            memory.save("app", "20260226", {"total_rev": 300})

            rows = memory.recall("app", days=2, before_date="20260227")

        self.assertEqual(["20260226", "20260225"], [row["date"] for row in rows])
        self.assertEqual(300, rows[0]["metrics"]["total_rev"])

    def test_trend_comparison_html_marks_lower_refund_rate_as_good(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "memory.db"
            memory = ReportMemory(db_path=db_path)
            memory.save("app", "20260224", {"total_rev": 50.0, "refund_rate": 4.0})
            memory.save("app", "20260225", {"total_rev": 100.0, "refund_rate": 3.0})
            memory.save("app", "20260226", {"total_rev": 100.0, "refund_rate": 2.0})

            html = memory.trend_comparison_html(
                "app",
                "20260227",
                {"total_rev": 150.0, "refund_rate": 1.0},
                {"total_rev": "营收", "refund_rate": "退款率"},
                days=3,
            )

        self.assertIn("历史趋势对比", html)
        self.assertIn("昨日(2026-02-26)", html)
        self.assertIn("↑50.0%", html)
        self.assertIn("退款率", html)
        self.assertIn("↓50.0%", html)
        self.assertIn("color:#16a34a", html)


if __name__ == "__main__":
    unittest.main()
