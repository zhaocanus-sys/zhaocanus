"""Regression coverage for AnalysisPipeline.run funnel/pc_cv and finding order.

Covers:
- AnalysisReport.get_all_findings_sorted priority then revenue_impact ordering
- Funnel stage rates stay finite when denominators are zero
- pc_cv is 0 with fewer than 2 departments; correct CV with 2+ departments

Deterministic stdlib unittest only — engines and I/O are mocked; no network.
"""

from __future__ import annotations

import statistics
import unittest
from unittest.mock import patch

from agent_system.engines.analysis_pipeline import AnalysisPipeline, AnalysisReport
from agent_system.engines.collision_engine import CollisionFinding


def make_finding(priority: str, revenue_impact: float, tag: str = "tag") -> CollisionFinding:
    return CollisionFinding(
        collision_type="test",
        tag=tag,
        description=f"{tag}:{priority}",
        revenue_impact=revenue_impact,
        priority=priority,
    )


def make_summary(**overrides):
    summary = {
        "date": "2026-02-27",
        "head_count": 0,
        "on_duty": 0,
        "new_hire": 0,
        "allocated": 0,
        "dial_count": 0,
        "link_1d_num": 0,
        "deep_talk": 0,
        "first_call_conv": 0,
        "signed_deals": 0,
        "total_revenue": 0,
        "refund_count": 0,
        "refund_amount": 0,
        "complaint_count": 0,
        "jx_transfer_in": 0,
        "jx_signed": 0,
        "pool_in": 0,
        "pool_retrieval": 0,
        "pool_signed": 0,
        "peak_hour_revenue": 0,
        "offpeak_hour_revenue": 0,
        "cr": 50.0,
        "dr": 25.0,
        "conv": 2.0,
        "pc": 1000,
        "avg_deal": 2500,
        "ref_rate": 1.0,
        "fc_rate": 5.0,
        "jx_cr": 20.0,
        "p_cr": 15.0,
        "ai": 80.0,
        "dur": 120,
        "conn_dur": 80,
        "deep_dur": 300,
        "t20": 40.0,
        "roi": 30.0,
        "peak_pct": 50.0,
        "alloc_rate": 0.9,
        "rev_dod": 0,
        "cr_dod": 0,
        "pc_dod": 0,
        "week_avg_rev": 0,
    }
    summary.update(overrides)
    return summary


def make_dept(name: str, per_capita_revenue: float, **overrides):
    dept = {
        "dept_name": name,
        "per_capita_revenue": per_capita_revenue,
        "deep_talk_rate": 20.0,
        "on_duty": 5,
        "total_revenue": per_capita_revenue * 5,
        "top20_pct": 40.0,
    }
    dept.update(overrides)
    return dept


class FindingsSortedTests(unittest.TestCase):
    def test_priority_then_revenue_impact_across_engines(self):
        report = AnalysisReport(
            date="2026-02-27",
            summary={},
            departments=[],
            trends=[],
            persons=[],
            top_performers=[],
            bottom_performers=[],
            new_hire_stats=[],
            tenure_analysis={},
            data_collision_findings=[
                make_finding("P1", 100, "data-p1-low"),
                make_finding("P0", 50, "data-p0"),
            ],
            data_collision_summary={},
            logic_collision_findings=[
                make_finding("P2", 999, "logic-p2"),
                make_finding("P1", 500, "logic-p1-high"),
            ],
            logic_collision_summary={},
            cross_domain_findings=[
                make_finding("UNKNOWN", 10_000, "xd-unknown"),
                make_finding("P0", 200, "xd-p0-high"),
            ],
        )

        sorted_findings = report.get_all_findings_sorted()
        tags = [f.tag for f in sorted_findings]

        # P0 before P1 before P2; unknown priority last (order key 9).
        self.assertEqual(
            ["xd-p0-high", "data-p0", "logic-p1-high", "data-p1-low", "logic-p2", "xd-unknown"],
            tags,
        )
        # Same priority: higher revenue_impact first.
        self.assertGreater(
            sorted_findings[0].revenue_impact,
            sorted_findings[1].revenue_impact,
        )
        self.assertGreater(
            sorted_findings[2].revenue_impact,
            sorted_findings[3].revenue_impact,
        )

    def test_empty_engines_return_empty_list(self):
        report = AnalysisReport(
            date="2026-02-27",
            summary={},
            departments=[],
            trends=[],
            persons=[],
            top_performers=[],
            bottom_performers=[],
            new_hire_stats=[],
            tenure_analysis={},
            data_collision_findings=[],
            data_collision_summary={},
            logic_collision_findings=[],
            logic_collision_summary={},
        )
        self.assertEqual([], report.get_all_findings_sorted())


class PipelineRunFunnelAndCvTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def _run_isolated(self, summary, depts):
        """Run pipeline with I/O and engines mocked so only run() math is exercised."""
        pull = (summary, depts, [], [], [], [], [])
        with patch.object(self.pipeline, "_pull_data", return_value=pull), \
             patch.object(self.pipeline, "_compute_tenure_analysis", return_value={}), \
             patch.object(self.pipeline, "_calc_improvements", return_value=([], 0)), \
             patch.object(self.pipeline.data_engine, "execute", return_value=[]), \
             patch.object(self.pipeline.data_engine, "get_summary", return_value={}), \
             patch.object(
                 self.pipeline.logic_engine, "execute", return_value=([], [], [])
             ), \
             patch.object(self.pipeline.logic_engine, "get_summary", return_value={}), \
             patch.object(self.pipeline.cross_domain_engine, "execute", return_value=[]), \
             patch.object(
                 self.pipeline.cross_domain_engine, "get_summary", return_value={}
             ):
            return self.pipeline.run("2026-02-27", dates_range=["2026-02-27"])

    def test_funnel_zero_denominators_stay_finite(self):
        summary = make_summary(
            allocated=0,
            dial_count=0,
            link_1d_num=0,
            deep_talk=0,
            signed_deals=0,
        )
        report = self._run_isolated(summary, [])

        self.assertEqual(4, len(report.funnel))
        stage_names = [stage[0] for stage in report.funnel]
        self.assertEqual(
            ["分配→拨打", "拨打→接通", "接通→深沟", "深沟→签单"],
            stage_names,
        )

        for name, value, benchmark, unit in report.funnel:
            with self.subTest(stage=name):
                self.assertIsInstance(value, (int, float))
                self.assertFalse(value != value, f"{name} became NaN")
                self.assertTrue(abs(value) != float("inf"), f"{name} became Inf")
                self.assertIsInstance(benchmark, (int, float))
                self.assertIsInstance(unit, str)

        # Documented `or 1` denominator fallbacks with zero numerators → 0 rates.
        by_name = {name: value for name, value, _, _ in report.funnel}
        self.assertEqual(0.0, by_name["分配→拨打"])
        self.assertEqual(0.0, by_name["拨打→接通"])
        self.assertEqual(0.0, by_name["接通→深沟"])
        self.assertEqual(0.0, by_name["深沟→签单"])

    def test_funnel_rates_use_summary_counts(self):
        summary = make_summary(
            allocated=100,
            dial_count=300,
            link_1d_num=45,
            deep_talk=9,
            signed_deals=3,
        )
        report = self._run_isolated(summary, [make_dept("电销一部", 1000)])

        by_name = {name: value for name, value, _, _ in report.funnel}
        self.assertEqual(3.0, by_name["分配→拨打"])  # 300 / 100
        self.assertEqual(15.0, by_name["拨打→接通"])  # 45 / 300 * 100
        self.assertEqual(20.0, by_name["接通→深沟"])  # 9 / 45 * 100
        self.assertEqual(100 / 3, by_name["深沟→签单"])  # 3 / 9 * 100

    def test_pc_cv_zero_with_fewer_than_two_departments(self):
        summary = make_summary()
        empty = self._run_isolated(summary, [])
        single = self._run_isolated(summary, [make_dept("电销一部", 1200)])

        self.assertEqual(0, empty.pc_cv)
        self.assertEqual(0, single.pc_cv)

    def test_pc_cv_computed_for_two_or_more_departments(self):
        summary = make_summary()
        depts = [
            make_dept("电销一部", 1000),
            make_dept("电销二部", 3000),
        ]
        report = self._run_isolated(summary, depts)

        pcs = [1000, 3000]
        expected = round(statistics.stdev(pcs) / statistics.mean(pcs), 2)
        self.assertEqual(expected, report.pc_cv)
        self.assertGreater(report.pc_cv, 0)


if __name__ == "__main__":
    unittest.main()
