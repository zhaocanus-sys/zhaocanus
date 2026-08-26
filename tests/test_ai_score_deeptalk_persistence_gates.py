"""Regression coverage for leftover improvement gates and persistence early-exit.

PR #109 locked 接通 / 中腰部 / 深沟公式 / 退费 / 建信 / 公海 arithmetic
and collision target fallbacks. It did not lock the AI Score +0.03pp
formula or the deep-talk `best_dr - 2` silence line.

PR #48 has an unmerged persistence production fix. These cases only
lock the already-correct early exits (short trend window; current
connect_rate already at/above 43) and do not lock the buggy global
`cr_below_count`.

CrossDomain interpolation of `{avg_deal:,}` is also locked here so a
missing-key KeyError cannot silently drop the 锚定 card when the
summary is complete. PR #81 locked trigger on/off, not the formatted
amount text.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline
from agent_system.engines.collision_engine import (
    CrossDomainCollisionEngine,
    DataCollisionEngine,
)


def healthy_summary(**overrides):
    values = {
        "date": "2026-08-26",
        "avg_deal": 5_000,
        "cr": 43,
        "allocated": 10_000,
        "conv": 2,
        "t20": 50,
        "on_duty": 20,
        "dr": 25,
        "link_1d_num": 400,
        "ai": 75,
        "ref_rate": 5,
        "total_revenue": 100_000,
        "jx_cr": 18,
        "jx_transfer_in": 200,
        "p_cr": 12,
        "pool_retrieval": 100,
    }
    values.update(overrides)
    return values


def two_depts():
    return [
        {
            "dept_name": "电销一部",
            "per_capita_revenue": 8_000,
            "deep_talk_rate": 25,
        },
        {
            "dept_name": "电销二部",
            "per_capita_revenue": 4_000,
            "deep_talk_rate": 20,
        },
    ]


def _by_title(items):
    return {item["title"]: item for item in items}


def _low_cr_dept():
    return {
        "dept_name": "电销六部",
        "connect_rate": 30,
        "allocated": 500,
        "avg_deal_amount": 5_000,
    }


def _cross_summary(**overrides):
    # Keys used by any rule that can trigger via .get() defaults.
    summary = {
        "dr": 10,
        "conv": 2.0,
        "avg_deal": 4_800,
        "t20": 40,
        "fc_rate": 5,
        "ai": 80,
        "ref_rate": 3,
    }
    summary.update(overrides)
    return summary


def _healthy_cross_depts(n=2):
    return [
        {"dept_name": f"电销{i}部", "per_capita_revenue": 3_000}
        for i in range(1, n + 1)
    ]


class AIScoreImprovementTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_ai_score_uplift_is_allocated_gap_times_03bp(self):
        # gap=5, extra_s=round(10000*5*0.0003, 1)=15.0, rev=round(15*5000)=75000
        items, total = self.pipeline._calc_improvements(
            healthy_summary(ai=70), two_depts(), []
        )
        card = _by_title(items)["AI Score提升至75"]
        self.assertEqual("P2", card["p"])
        self.assertEqual("70", card["cur"])
        self.assertEqual("75", card["tgt"])
        self.assertEqual(75_000, card["rev"])
        self.assertIn("每+1分约转化率+0.03pp，+5.0分→多签15单", card["detail"])
        self.assertEqual(75_000, total)

    def test_ai_score_at_75_is_silent(self):
        items, total = self.pipeline._calc_improvements(
            healthy_summary(ai=75), two_depts(), []
        )
        self.assertNotIn("AI Score提升至75", _by_title(items))
        self.assertEqual(0, total)

    def test_ai_score_just_below_75_fires(self):
        # gap=0.1, extra_s=round(10000*0.1*0.0003, 1)=0.3, rev=round(0.3*5000)=1500
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(ai=74.9), two_depts(), []
        )
        card = _by_title(items)["AI Score提升至75"]
        self.assertEqual(1_500, card["rev"])
        self.assertEqual("74.9", card["cur"])


class DeepTalkGapGateTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_deep_talk_exactly_two_points_below_benchmark_is_silent(self):
        # best_dr=25, dr=23 → 23 < 25-2 is False
        items, total = self.pipeline._calc_improvements(
            healthy_summary(dr=23), two_depts(), []
        )
        self.assertNotIn("深沟率向标杆看齐", _by_title(items))
        self.assertEqual(0, total)

    def test_deep_talk_just_under_two_point_gap_emits_card(self):
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(dr=22.9), two_depts(), []
        )
        card = _by_title(items)["深沟率向标杆看齐"]
        self.assertEqual("22.9%", card["cur"])
        self.assertEqual("25%", card["tgt"])


class PersistenceEarlyExitTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_fewer_than_five_trends_is_silent_even_with_low_connect(self):
        trends = [{"cr": 30} for _ in range(4)]
        self.engine._collide_persistence_detection([_low_cr_dept()], trends)
        self.assertEqual([], self.engine.findings)

        self.engine.findings = []
        self.engine._collide_persistence_detection([_low_cr_dept()], [])
        self.assertEqual([], self.engine.findings)

    def test_five_trends_but_current_connect_at_redline_is_silent(self):
        trends = [{"cr": 30} for _ in range(5)]
        healthy = dict(_low_cr_dept(), connect_rate=43)
        self.engine._collide_persistence_detection([healthy], trends)
        self.assertEqual([], self.engine.findings)


class CrossDomainFormatInterpolationTests(unittest.TestCase):
    def test_anchor_rule_interpolates_thousands_separator(self):
        engine = CrossDomainCollisionEngine()
        findings = engine.execute(
            _cross_summary(avg_deal=4_800),
            _healthy_cross_depts(),
            [],
            [],
        )
        tags = [f.tag for f in findings]
        self.assertIn("挑战式销售×锚定效应", tags)
        anchor = next(f for f in findings if f.tag == "挑战式销售×锚定效应")
        self.assertIn("客单价¥4,800偏低", anchor.description)
        self.assertNotIn("{avg_deal", anchor.description)


if __name__ == "__main__":
    unittest.main()
