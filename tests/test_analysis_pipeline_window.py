import os
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock

from agent_system.engines.analysis_pipeline import AnalysisPipeline


class AnalysisPipelineDateWindowTest(unittest.TestCase):
    def test_default_window_contains_ten_dates_across_month_boundary(self):
        dates = AnalysisPipeline._build_dates_range("2026-03-05")

        self.assertEqual(10, len(dates))
        self.assertEqual("2026-02-24", dates[0])
        self.assertEqual("2026-03-05", dates[-1])
        self.assertEqual(10, len(set(dates)))

    def test_pull_data_limits_trends_to_explicit_dates(self):
        pipeline, trend_aggregator = self._pipeline_with_test_database()

        pipeline._pull_data(
            "2026-03-02",
            ["2026-02-20", "2026-03-02"],
        )

        selected_rows = trend_aggregator.call_args.args[0]
        self.assertEqual(
            ["2026-02-20", "2026-03-02"],
            [row["report_date"] for row in selected_rows],
        )

    def test_empty_window_does_not_load_unbounded_history(self):
        pipeline, trend_aggregator = self._pipeline_with_test_database()

        pipeline._pull_data("2026-03-02", [])

        trend_aggregator.assert_called_once_with([])

    def _pipeline_with_test_database(self):
        database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database.close()
        self.addCleanup(lambda: os.path.exists(database.name) and os.unlink(database.name))

        with sqlite3.connect(database.name) as conn:
            conn.execute(
                """
                CREATE TABLE ts_daily (
                    report_date TEXT,
                    dept_name TEXT,
                    total_revenue REAL,
                    new_hire INTEGER,
                    new_hire_month_avg REAL,
                    per_capita_revenue REAL
                )
                """
            )
            conn.execute(
                "CREATE TABLE ts_person (report_date TEXT, revenue REAL)"
            )
            conn.executemany(
                "INSERT INTO ts_daily VALUES (?, ?, ?, ?, ?, ?)",
                [
                    ("2026-02-20", "电销一部", 100.0, 1, 80.0, 100.0),
                    ("2026-03-01", "电销一部", 200.0, 1, 80.0, 200.0),
                    ("2026-03-02", "电销一部", 300.0, 1, 80.0, 300.0),
                ],
            )

        pipeline = AnalysisPipeline(database.name)
        pipeline._aggregate_summary = Mock(return_value={})
        trend_aggregator = Mock(return_value=[])
        pipeline._aggregate_trends = trend_aggregator
        return pipeline, trend_aggregator


if __name__ == "__main__":
    unittest.main()
