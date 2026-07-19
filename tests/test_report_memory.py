import tempfile
import unittest
from pathlib import Path

from agent_system.actions.memory_manager import ReportMemory


class ReportMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "report-memory.sqlite3"
        self.memory = ReportMemory(self.db_path)

    def test_save_upserts_and_recall_isolates_team_orders_and_limits(self):
        self.memory.save("app", "20260301", {"revenue": 100, "note": "首日"})
        self.memory.save("app", "20260302", {"revenue": 200})
        self.memory.save("app", "20260302", {"revenue": 220, "note": "已修正"})
        self.memory.save("shop", "20260302", {"revenue": 999})

        reloaded = ReportMemory(self.db_path)
        latest = reloaded.recall("app", days=1, before_date="20260303")
        older = reloaded.recall("app", days=10, before_date="20260302")

        self.assertEqual(
            latest,
            [{"date": "20260302", "metrics": {"revenue": 220, "note": "已修正"}}],
        )
        self.assertEqual(
            older,
            [{"date": "20260301", "metrics": {"revenue": 100, "note": "首日"}}],
        )

    def test_trend_html_handles_zero_baseline_and_metric_direction(self):
        history = [
            ("20260301", {"revenue": 60, "refund_rate": 14}),
            ("20260302", {"revenue": 80, "refund_rate": 12}),
            ("20260303", {"revenue": 100, "refund_rate": 10}),
        ]
        for date, metrics in history:
            self.memory.save("app", date, metrics)

        html = self.memory.trend_comparison_html(
            "app",
            "20260304",
            {"revenue": 120, "refund_rate": 8, "new_metric": 5},
            {
                "revenue": "营收",
                "refund_rate": "退款率",
                "new_metric": "新增指标",
            },
        )

        self.assertIn("基于最近 3 天", html)
        self.assertIn("↑20.0%", html)
        self.assertIn("↓20.0%", html)
        self.assertIn("新增指标", html)
        self.assertIn("↑100.0%", html)
        self.assertGreaterEqual(html.count("#16a34a"), 2)
        self.assertNotIn("nan", html.lower())
        self.assertNotIn("inf", html.lower())

    def test_trend_html_is_empty_without_prior_episodes(self):
        html = self.memory.trend_comparison_html(
            "jianxin",
            "20260304",
            {"revenue": 100},
            {"revenue": "营收"},
        )

        self.assertEqual(html, "")


if __name__ == "__main__":
    unittest.main()
