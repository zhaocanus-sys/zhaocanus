"""Regression coverage for ReportMemory 2-day history mean-column gate.

PR #113 locked 1 prior day → 昨日/环比 and no 日均值, and 3 prior days
→ `{n}日均值` / vs均值. The `len(week_data) >= 3` threshold itself
was not locked: two prior days must still omit the mean columns.

If that gate slips to `>= 2`, a two-day window would present
yesterday+day-before as a 「日均值」, which operators read as a
stable baseline.

Does not retest _fmt 万/小数位, inverted _tc, or empty-history "".

Deterministic stdlib unittest only — tempfile SQLite, no network.
"""

import os
import tempfile
import unittest

from agent_system.actions.memory_manager import ReportMemory


class TwoDayMeanGateTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.mem = ReportMemory(os.path.join(self._tmpdir.name, "memory.db"))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_two_prior_days_have_dod_but_no_mean_columns(self):
        self.mem.save("telesale", "2026-08-30", {"revenue": 100})
        self.mem.save("telesale", "2026-08-31", {"revenue": 110})

        html = self.mem.trend_comparison_html(
            "telesale",
            "2026-09-01",
            {"revenue": 121},
            metric_labels={"revenue": "营收"},
        )

        self.assertIn("昨日(2026-08-31)", html)
        self.assertIn("环比", html)
        self.assertIn("↑10.0%", html)
        self.assertIn("营收", html)
        self.assertNotIn("日均值", html)
        self.assertNotIn("vs均值", html)


if __name__ == "__main__":
    unittest.main()
