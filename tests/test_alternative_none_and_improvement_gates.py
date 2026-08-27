"""Regression coverage for unused-tag alternatives and improvement gates.

PR #81 locked `_generate_alternative` text for 接通 / 漏斗 / 高营收
and P0+alternative → P2 cross-validation. It did not lock the None
path for unmatched tags (including 低营收, which has 营收 but not 高)
or that unmatched P0 findings stay undowngraded.

PR #109 locked collision target fallbacks and improvement arithmetic.
It did not lock year-end `deploy_date`, P0/P2 skip gates, or that
`validate_feasibility` is actually applied to generated cards.

Does not retest PR #81 alternative wording, PR #109 formulas, or
PR #103 keyword tables as the primary assertion.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline
from agent_system.engines.collision_engine import (
    CollisionFinding,
    LogicCollisionEngine,
)


def healthy_summary(**overrides):
    values = {
        "date": "2026-08-27",
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
        {"dept_name": "电销一部", "per_capita_revenue": 8_000, "deep_talk_rate": 25},
        {"dept_name": "电销二部", "per_capita_revenue": 4_000, "deep_talk_rate": 20},
    ]


def _finding(tag, priority="P0", revenue_impact=1_000, description="fixture"):
    return CollisionFinding(
        collision_type="metric_x_metric",
        tag=tag,
        description=description,
        revenue_impact=revenue_impact,
        priority=priority,
    )


def _by_title(items):
    return {item["title"]: item for item in items}


class UnusedAlternativeTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_unmatched_and_low_revenue_tags_return_none(self):
        unused = _finding("持续不达标预警")
        low_rev = _finding("低营收部门")
        self.assertIsNone(self.engine._generate_alternative(unused, {}, []))
        self.assertIsNone(self.engine._generate_alternative(low_rev, {}, []))

    def test_unmatched_p0_findings_do_not_emit_cross_validation(self):
        self.engine._cross_validate_with_data_findings(
            [
                _finding("持续不达标预警", "P0"),
                _finding("低营收部门", "P0"),
            ],
            {},
            [],
        )
        self.assertEqual([], self.engine.findings)

    def test_mixed_p0_only_validates_the_matching_tag(self):
        self.engine._cross_validate_with_data_findings(
            [
                _finding("接通率异常", "P0", description="接通偏低"),
                _finding("持续不达标预警", "P0"),
            ],
            {},
            [],
        )
        tags = [f.tag for f in self.engine.findings]
        self.assertEqual(["验证: 接通率异常"], tags)
        self.assertEqual("P2", self.engine.findings[0].priority)


class ImprovementGateTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_deploy_date_rolls_year_and_month_boundaries(self):
        year_items, _ = self.pipeline._calc_improvements(
            healthy_summary(date="2026-12-31", cr=40), two_depts(), []
        )
        month_items, _ = self.pipeline._calc_improvements(
            healthy_summary(date="2026-08-31", cr=40), two_depts(), []
        )
        self.assertEqual(
            "2027-01-01",
            _by_title(year_items)["接通率修复至43%"]["deploy_date"],
        )
        self.assertEqual(
            "2026-09-01",
            _by_title(month_items)["接通率修复至43%"]["deploy_date"],
        )

    def test_zero_impact_p0_and_positive_p2_do_not_create_collision_cards(self):
        items, total = self.pipeline._calc_improvements(
            healthy_summary(),
            two_depts(),
            [
                _finding("漏斗瓶颈", "P0", revenue_impact=0),
                _finding("时段失衡", "P2", revenue_impact=9_000),
            ],
        )
        titles = [item["title"] for item in items]
        self.assertNotIn("[对撞] 漏斗瓶颈", titles)
        self.assertNotIn("[对撞] 时段失衡", titles)
        self.assertEqual(0, total)

    def test_generated_connect_card_is_self_contained_high_feasibility(self):
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(cr=40), two_depts(), []
        )
        card = _by_title(items)["接通率修复至43%"]
        self.assertEqual("high", card["feasibility"])
        self.assertEqual("self_contained", card["dependency"])
        self.assertIn("弱依赖", card["risk_notes"])

    def test_collision_card_inherits_overload_feasibility_from_finding_text(self):
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(),
            two_depts(),
            [
                _finding(
                    "活动量不足",
                    "P1",
                    revenue_impact=2_000,
                    description="建议增加拨打量以提升触达覆盖",
                )
            ],
        )
        card = _by_title(items)["[对撞] 活动量不足"]
        self.assertEqual("low", card["feasibility"])
        self.assertIn("一线大幅加量", card["risk_notes"])


if __name__ == "__main__":
    unittest.main()
