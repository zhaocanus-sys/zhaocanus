"""Regression coverage for AnalysisPipeline aggregation math.

Covers daily summary rates, multi-day trend grouping, tenure bucket
boundaries, and day-over-day deltas in `_pull_data`.

Deterministic stdlib unittest only — no network; DoD uses a temp SQLite DB.
"""

import os
import sqlite3
import tempfile
import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline


def make_dept(**overrides):
    dept = {
        "report_date": "2026-02-27",
        "dept_name": "电销一部",
        "head_count": 10,
        "on_duty": 10,
        "new_hire": 1,
        "allocated": 100,
        "dial_count": 300,
        "link_1d_num": 40,
        "deep_talk": 8,
        "first_call_conv": 2,
        "signed_deals": 2,
        "total_revenue": 10_000,
        "refund_count": 0,
        "refund_amount": 0,
        "complaint_count": 0,
        "jx_transfer_in": 10,
        "jx_signed": 2,
        "pool_in": 5,
        "pool_retrieval": 10,
        "pool_signed": 1,
        "peak_hour_revenue": 6_000,
        "offpeak_hour_revenue": 4_000,
        "avg_ai_score": 70.0,
        "avg_call_dur": 120.0,
        "avg_connect_dur": 80.0,
        "avg_deep_dur": 300.0,
        "top20_pct": 50.0,
        "alloc_rate": 0.9,
    }
    dept.update(overrides)
    return dept


def make_person(tenure_months, revenue=1000, ai_score=70, dial_count=100):
    return {
        "tenure_months": tenure_months,
        "revenue": revenue,
        "ai_score": ai_score,
        "dial_count": dial_count,
    }


class AggregateSummaryTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_weighted_rates_and_concentration(self):
        depts = [
            make_dept(
                dept_name="电销一部",
                on_duty=2,
                allocated=100,
                link_1d_num=50,
                deep_talk=10,
                signed_deals=2,
                total_revenue=4_000,
                refund_amount=200,
                first_call_conv=1,
                jx_transfer_in=10,
                jx_signed=1,
                pool_retrieval=10,
                pool_signed=1,
                peak_hour_revenue=3_000,
                avg_ai_score=80.0,
                avg_call_dur=100.0,
                avg_connect_dur=50.0,
                avg_deep_dur=200.0,
                top20_pct=60.0,
                alloc_rate=0.8,
            ),
            make_dept(
                dept_name="电销二部",
                on_duty=8,
                allocated=100,
                link_1d_num=30,
                deep_talk=6,
                signed_deals=2,
                total_revenue=6_000,
                refund_amount=300,
                first_call_conv=3,
                jx_transfer_in=10,
                jx_signed=3,
                pool_retrieval=10,
                pool_signed=2,
                peak_hour_revenue=2_000,
                avg_ai_score=60.0,
                avg_call_dur=200.0,
                avg_connect_dur=100.0,
                avg_deep_dur=400.0,
                top20_pct=40.0,
                alloc_rate=1.0,
            ),
        ]

        summary = self.pipeline._aggregate_summary(depts, "2026-02-27")

        self.assertEqual("2026-02-27", summary["date"])
        self.assertEqual(10, summary["on_duty"])
        self.assertEqual(200, summary["allocated"])
        self.assertEqual(80, summary["link_1d_num"])
        self.assertEqual(10_000, summary["total_revenue"])

        # Rates use aggregate denominators, not department averages.
        self.assertEqual(40.0, summary["cr"])  # 80 / 200 * 100
        self.assertEqual(20.0, summary["dr"])  # 16 / 80 * 100
        self.assertEqual(2.0, summary["conv"])  # 4 / 200 * 100
        self.assertEqual(1_000, summary["pc"])  # 10000 / 10
        self.assertEqual(2_500, summary["avg_deal"])  # 10000 / 4
        self.assertEqual(5.0, summary["ref_rate"])  # 500 / 10000 * 100
        self.assertEqual(5.0, summary["fc_rate"])  # 4 / 80 * 100
        self.assertEqual(20.0, summary["jx_cr"])  # 4 / 20 * 100
        self.assertEqual(15.0, summary["p_cr"])  # 3 / 20 * 100
        self.assertEqual(50.0, summary["peak_pct"])  # 5000 / 10000 * 100

        # Weighted by on_duty: (80*2 + 60*8) / 10 = 64
        self.assertEqual(64.0, summary["ai"])
        self.assertEqual(180, summary["dur"])  # (100*2 + 200*8) / 10
        self.assertEqual(90, summary["conn_dur"])
        self.assertEqual(360, summary["deep_dur"])

        # TOP20 revenue share: (4000*0.6 + 6000*0.4) / 10000 * 100 = 48
        self.assertEqual(48.0, summary["t20"])
        self.assertEqual(round(10000 / (10 * 280) * 100, 1), summary["roi"])
        self.assertEqual(0.9, summary["alloc_rate"])  # (0.8 + 1.0) / 2

    def test_zero_denominators_stay_finite(self):
        summary = self.pipeline._aggregate_summary([], "2026-02-27")

        self.assertEqual("2026-02-27", summary["date"])
        for key in (
            "cr",
            "dr",
            "conv",
            "pc",
            "avg_deal",
            "ref_rate",
            "fc_rate",
            "jx_cr",
            "p_cr",
            "ai",
            "dur",
            "conn_dur",
            "deep_dur",
            "t20",
            "roi",
            "peak_pct",
            "alloc_rate",
        ):
            with self.subTest(key=key):
                self.assertIsInstance(summary[key], (int, float))
                self.assertFalse(
                    summary[key] != summary[key],  # NaN check
                    f"{key} became NaN",
                )

        # Empty input uses `or 1` denominator fallbacks — no ZeroDivisionError.
        # Numerators stay 0, so rate metrics are 0; absolute ratios that divide
        # the fallback revenue/on_duty sentinels become 1 (documented behavior).
        self.assertEqual(0.0, summary["cr"])
        self.assertEqual(0.0, summary["dr"])
        self.assertEqual(0.0, summary["conv"])
        self.assertEqual(1, summary["pc"])
        self.assertEqual(1, summary["avg_deal"])
        self.assertEqual(0.0, summary["t20"])
        self.assertEqual(0.0, summary["alloc_rate"])
        self.assertEqual(round(1 / 280 * 100, 1), summary["roi"])


class AggregateTrendsTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_groups_by_date_sorts_and_computes_rates(self):
        rows = [
            {
                "report_date": "2026-02-28",
                "allocated": 50,
                "link_1d_num": 10,
                "deep_talk": 2,
                "signed_deals": 1,
                "total_revenue": 3_000,
                "on_duty": 5,
                "refund_amount": 150,
                "dial_count": 100,
            },
            {
                "report_date": "2026-02-27",
                "allocated": 40,
                "link_1d_num": 8,
                "deep_talk": 4,
                "signed_deals": 0,
                "total_revenue": 1_000,
                "on_duty": 4,
                "refund_amount": 0,
                "dial_count": 80,
            },
            {
                "report_date": "2026-02-28",
                "allocated": 50,
                "link_1d_num": 10,
                "deep_talk": 2,
                "signed_deals": 1,
                "total_revenue": 2_000,
                "on_duty": 5,
                "refund_amount": 50,
                "dial_count": 100,
            },
        ]

        trends = self.pipeline._aggregate_trends(rows)

        self.assertEqual(["2026-02-27", "2026-02-28"], [t["dt"] for t in trends])

        day1, day2 = trends
        self.assertEqual(40, day1["allocated"])
        self.assertEqual(20.0, day1["cr"])  # 8 / 40 * 100
        self.assertEqual(250, day1["pc"])  # 1000 / 4
        self.assertEqual(0.0, day1["conv"])
        self.assertEqual(50.0, day1["dr"])  # 4 / 8 * 100
        self.assertEqual(0.0, day1["rr"])
        self.assertEqual(20.0, day1["dials_pp"])  # 80 / 4

        # Same-date rows are summed before rates are computed.
        self.assertEqual(100, day2["allocated"])
        self.assertEqual(20, day2["link_1d_num"])
        self.assertEqual(5_000, day2["total_revenue"])
        self.assertEqual(10, day2["on_duty"])
        self.assertEqual(20.0, day2["cr"])  # 20 / 100 * 100
        self.assertEqual(500, day2["pc"])  # 5000 / 10
        self.assertEqual(2.0, day2["conv"])  # 2 / 100 * 100
        self.assertEqual(20.0, day2["dr"])  # 4 / 20 * 100
        self.assertEqual(4.0, day2["rr"])  # 200 / 5000 * 100
        self.assertEqual(20.0, day2["dials_pp"])  # 200 / 10

    def test_zero_activity_day_stays_finite(self):
        trends = self.pipeline._aggregate_trends(
            [
                {
                    "report_date": "2026-02-27",
                    "allocated": 0,
                    "link_1d_num": 0,
                    "deep_talk": 0,
                    "signed_deals": 0,
                    "total_revenue": 0,
                    "on_duty": 0,
                    "refund_amount": 0,
                    "dial_count": 0,
                }
            ]
        )

        self.assertEqual(1, len(trends))
        for key in ("cr", "pc", "conv", "dr", "rr", "dials_pp"):
            with self.subTest(key=key):
                self.assertEqual(0.0 if key != "pc" else 0, trends[0][key])


class TenureAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_bucket_boundaries_and_averages(self):
        persons = [
            make_person(0, revenue=500, ai_score=60, dial_count=50),
            make_person(3, revenue=1_500, ai_score=70, dial_count=150),  # still newbie
            make_person(4, revenue=2_000, ai_score=80, dial_count=200),  # growth
            make_person(12, revenue=4_000, ai_score=90, dial_count=300),  # growth
            make_person(13, revenue=3_000, ai_score=85, dial_count=250),  # mature
            make_person(24, revenue=5_000, ai_score=95, dial_count=350),  # mature
            make_person(25, revenue=6_000, ai_score=88, dial_count=400),  # senior
        ]

        result = self.pipeline._compute_tenure_analysis(persons)

        self.assertEqual(
            {"新人(≤3月)", "成长期(4-12月)", "成熟期(1-2年)", "老员工(>2年)"},
            set(result),
        )
        self.assertEqual(2, result["新人(≤3月)"]["count"])
        self.assertEqual(1_000, result["新人(≤3月)"]["avg_rev"])  # (500+1500)/2
        self.assertEqual(65.0, result["新人(≤3月)"]["avg_ai"])
        self.assertEqual(100, result["新人(≤3月)"]["avg_dials"])

        self.assertEqual(2, result["成长期(4-12月)"]["count"])
        self.assertEqual(3_000, result["成长期(4-12月)"]["avg_rev"])
        self.assertEqual(2, result["成熟期(1-2年)"]["count"])
        self.assertEqual(4_000, result["成熟期(1-2年)"]["avg_rev"])
        self.assertEqual(1, result["老员工(>2年)"]["count"])
        self.assertEqual(6_000, result["老员工(>2年)"]["avg_rev"])

    def test_empty_persons_returns_empty_dict(self):
        self.assertEqual({}, self.pipeline._compute_tenure_analysis([]))


class PullDataDodTests(unittest.TestCase):
    """Day-over-day deltas computed after trend aggregation."""

    COLUMNS = (
        "report_date",
        "dept_name",
        "head_count",
        "on_duty",
        "new_hire",
        "new_hire_month_avg",
        "allocated",
        "alloc_rate",
        "dial_count",
        "link_1d_num",
        "deep_talk",
        "first_call_conv",
        "signed_deals",
        "total_revenue",
        "refund_count",
        "refund_amount",
        "complaint_count",
        "jx_transfer_in",
        "jx_signed",
        "pool_in",
        "pool_retrieval",
        "pool_signed",
        "peak_hour_revenue",
        "offpeak_hour_revenue",
        "avg_ai_score",
        "avg_call_dur",
        "avg_connect_dur",
        "avg_deep_dur",
        "top20_pct",
        "per_capita_revenue",
    )

    def _write_db(self, rows):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.addCleanup(
            lambda: os.path.exists(handle.name) and os.unlink(handle.name)
        )

        placeholders = ", ".join("?" for _ in self.COLUMNS)
        col_defs = ", ".join(f"{c} REAL" if c not in ("report_date", "dept_name") else f"{c} TEXT"
                             for c in self.COLUMNS)
        with sqlite3.connect(handle.name) as conn:
            conn.execute(f"CREATE TABLE ts_daily ({col_defs})")
            conn.execute(
                "CREATE TABLE ts_person ("
                "report_date TEXT, dept_name TEXT, revenue REAL, "
                "tenure_months REAL, ai_score REAL, dial_count REAL)"
            )
            conn.executemany(
                f"INSERT INTO ts_daily ({', '.join(self.COLUMNS)}) "
                f"VALUES ({placeholders})",
                rows,
            )
        return handle.name

    def _row(self, date, dept, revenue, allocated, links, on_duty):
        values = {
            "report_date": date,
            "dept_name": dept,
            "head_count": on_duty,
            "on_duty": on_duty,
            "new_hire": 0,
            "new_hire_month_avg": 0,
            "allocated": allocated,
            "alloc_rate": 1.0,
            "dial_count": allocated * 3,
            "link_1d_num": links,
            "deep_talk": 1,
            "first_call_conv": 0,
            "signed_deals": 1,
            "total_revenue": revenue,
            "refund_count": 0,
            "refund_amount": 0,
            "complaint_count": 0,
            "jx_transfer_in": 0,
            "jx_signed": 0,
            "pool_in": 0,
            "pool_retrieval": 0,
            "pool_signed": 0,
            "peak_hour_revenue": revenue // 2,
            "offpeak_hour_revenue": revenue - revenue // 2,
            "avg_ai_score": 70.0,
            "avg_call_dur": 100.0,
            "avg_connect_dur": 80.0,
            "avg_deep_dur": 200.0,
            "top20_pct": 40.0,
            "per_capita_revenue": revenue / on_duty,
        }
        return tuple(values[c] for c in self.COLUMNS)

    def test_day_over_day_and_week_average(self):
        db_path = self._write_db(
            [
                self._row("2026-02-26", "电销一部", 4_000, 100, 20, 4),
                self._row("2026-02-27", "电销一部", 6_000, 100, 40, 4),
                self._row("2026-02-27", "电销二部", 4_000, 100, 40, 6),
            ]
        )
        pipeline = AnalysisPipeline(db_path)

        summary, depts, trends, *_ = pipeline._pull_data(
            "2026-02-27", ["2026-02-26", "2026-02-27"]
        )

        self.assertEqual(2, len(depts))
        self.assertEqual(["2026-02-26", "2026-02-27"], [t["dt"] for t in trends])

        # Prior day revenue 4000 → today 10000 ⇒ +150%
        self.assertEqual(150.0, summary["rev_dod"])
        # Prior CR 20.0 → today 40.0 ⇒ +20.0 pp
        self.assertEqual(20.0, summary["cr_dod"])
        # Prior PC 1000 → today 1000 ⇒ 0%
        self.assertEqual(0.0, summary["pc_dod"])
        # Average of both trend days: (4000 + 10000) / 2
        self.assertEqual(7_000, summary["week_avg_rev"])

    def test_single_trend_day_zeros_dod(self):
        db_path = self._write_db(
            [self._row("2026-02-27", "电销一部", 5_000, 100, 30, 5)]
        )
        pipeline = AnalysisPipeline(db_path)

        summary, _, trends, *_ = pipeline._pull_data("2026-02-27", ["2026-02-27"])

        self.assertEqual(1, len(trends))
        self.assertEqual(0, summary["rev_dod"])
        self.assertEqual(0, summary["cr_dod"])
        self.assertEqual(0, summary["pc_dod"])
        self.assertEqual(5_000, summary["week_avg_rev"])


if __name__ == "__main__":
    unittest.main()
