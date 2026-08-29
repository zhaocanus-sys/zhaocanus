"""Regression coverage for ReportMemory persistence and trend HTML.

No prior coverage PR locked save/upsert isolation, recall(before_date)
windows, zero-denominator _chg, inverted _tc bands for refund/fail-rate
keys, _fmt 万/小数位, or trend_comparison_html empty / 昨日 / 均值 columns.

These paths sit under every report's 情景记忆 contract: a wrong team
leak, including today in history, or inverted refund colors would
silently mislead DoD and 10-day trend reads.

Does not retest PR #112 extract_trend_values missing-key / history
ignores prev_val, or sparkline downtrend red / fill polygon.

Deterministic stdlib unittest only — tempfile SQLite, no network.
"""

import os
import tempfile
import unittest

from agent_system.actions.memory_manager import ReportMemory


class ReportMemoryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.mem = ReportMemory(os.path.join(self._tmpdir.name, "memory.db"))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_upsert_same_team_date_overwrites_metrics(self):
        self.mem.save("telesale", "2026-08-27", {"revenue": 100})
        self.mem.save("telesale", "2026-08-27", {"revenue": 250})

        rows = self.mem.recall("telesale", days=10)
        self.assertEqual(1, len(rows))
        self.assertEqual("2026-08-27", rows[0]["date"])
        self.assertEqual(250, rows[0]["metrics"]["revenue"])

    def test_recall_is_isolated_by_team(self):
        self.mem.save("telesale", "2026-08-27", {"revenue": 100})
        self.mem.save("jianxin", "2026-08-27", {"pay_amt": 80})

        self.assertEqual([], self.mem.recall("hongniang", days=10))
        ts = self.mem.recall("telesale", days=10)
        self.assertEqual(1, len(ts))
        self.assertEqual(100, ts[0]["metrics"]["revenue"])
        self.assertNotIn("pay_amt", ts[0]["metrics"])

    def test_recall_before_date_excludes_today_and_honors_limit(self):
        for day, rev in (
            ("2026-08-24", 10),
            ("2026-08-25", 20),
            ("2026-08-26", 30),
            ("2026-08-27", 40),
            ("2026-08-28", 50),
        ):
            self.mem.save("telesale", day, {"revenue": rev})

        rows = self.mem.recall("telesale", days=2, before_date="2026-08-28")
        self.assertEqual(["2026-08-27", "2026-08-26"], [r["date"] for r in rows])
        self.assertEqual([40, 30], [r["metrics"]["revenue"] for r in rows])


class ReportMemoryMathTests(unittest.TestCase):
    def test_chg_zero_old_is_zero_or_one_hundred(self):
        self.assertEqual(0, ReportMemory._chg(0, 0))
        self.assertEqual(100, ReportMemory._chg(80, 0))
        self.assertEqual(10.0, ReportMemory._chg(110, 100))
        self.assertEqual(-10.0, ReportMemory._chg(90, 100))
        self.assertEqual(100.0, ReportMemory._chg(0, -10))

    def test_tc_inverts_refund_and_fail_rate_and_uses_5pt_band(self):
        self.assertEqual("#16a34a", ReportMemory._tc(-6, "refund_rate"))
        self.assertEqual("#dc2626", ReportMemory._tc(6, "refund_rate"))
        self.assertEqual("#64748b", ReportMemory._tc(-5, "refund_rate"))
        self.assertEqual("#64748b", ReportMemory._tc(5, "refund"))
        self.assertEqual("#dc2626", ReportMemory._tc(6, "order_fail_rate"))
        self.assertEqual("#16a34a", ReportMemory._tc(6, "revenue"))
        self.assertEqual("#dc2626", ReportMemory._tc(-6, "revenue"))
        self.assertEqual("#64748b", ReportMemory._tc(5, "revenue"))
        self.assertEqual("#64748b", ReportMemory._tc(-5, "connect_rate"))

    def test_fmt_uses_wan_above_10000_and_two_decimals_below_one(self):
        self.assertEqual("1.0万", ReportMemory._fmt(10000.0))
        self.assertEqual("2.5万", ReportMemory._fmt(25000.0))
        self.assertEqual("-1.0万", ReportMemory._fmt(-10000.0))
        self.assertEqual("9999.9", ReportMemory._fmt(9999.9))
        self.assertEqual("0.00", ReportMemory._fmt(0.0))
        self.assertEqual("0.50", ReportMemory._fmt(0.5))
        self.assertEqual("1.0", ReportMemory._fmt(1.0))
        self.assertEqual("42", ReportMemory._fmt(42))


class ReportMemoryTrendHtmlTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.mem = ReportMemory(os.path.join(self._tmpdir.name, "memory.db"))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_empty_history_returns_empty_string(self):
        html = self.mem.trend_comparison_html(
            "telesale", "2026-08-28", {"revenue": 100}
        )
        self.assertEqual("", html)

    def test_single_prior_day_has_dod_but_no_week_mean(self):
        self.mem.save("telesale", "2026-08-27", {"revenue": 100})
        html = self.mem.trend_comparison_html(
            "telesale",
            "2026-08-28",
            {"revenue": 110},
            metric_labels={"revenue": "营收"},
        )

        self.assertIn("营收", html)
        self.assertIn("昨日(2026-08-27)", html)
        self.assertIn("环比", html)
        self.assertIn("#16a34a", html)
        self.assertIn("↑10.0%", html)
        self.assertNotIn("日均值", html)
        self.assertNotIn("vs均值", html)

    def test_compact_date_formats_yesterday_header(self):
        self.mem.save("telesale", "20260827", {"revenue": 100})
        html = self.mem.trend_comparison_html(
            "telesale", "20260828", {"revenue": 100}
        )
        self.assertIn("昨日(2026-08-27)", html)

    def test_three_day_window_emits_mean_and_inverts_refund_color(self):
        self.mem.save("app", "2026-08-25", {"refund_rate": 2.0, "revenue": 100})
        self.mem.save("app", "2026-08-26", {"refund_rate": 2.0, "revenue": 100})
        self.mem.save("app", "2026-08-27", {"refund_rate": 2.0, "revenue": 100})

        html = self.mem.trend_comparison_html(
            "app",
            "2026-08-28",
            {"refund_rate": 3.0, "revenue": None},
            metric_labels={"refund_rate": "退费率", "revenue": "营收"},
        )

        self.assertIn("3日均值", html)
        self.assertIn("vs均值", html)
        self.assertIn("退费率", html)
        # refund_rate +50% vs yesterday → inverted red
        self.assertIn("#dc2626", html)
        self.assertIn("↑50.0%", html)
        # None today treated as 0 vs yesterday 100 → ↓100%
        self.assertIn("↓100.0%", html)


if __name__ == "__main__":
    unittest.main()
