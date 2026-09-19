"""Regression coverage for leftover P0 revenue_impact==1 改善卡.

PR #111 locked `_calc_improvements` findings-loop skip at
P0 `revenue_impact==0` and P2 with a positive impact.
PR #132 locked the first positive tick on a *P1* finding (`==1`).

The leftover P0 operand was never the primary lock:

- P0 `revenue_impact==1` is the first `[对撞]` card (`> 0`)
- P0 `revenue_impact==0` still skips
- P2 `==1` still skips (priority gate independent of P0==1)

Does not retest PR #132's P1==1 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline
from agent_system.engines.collision_engine import CollisionFinding


def make_summary(**overrides):
    summary = {
        "date": "2026-09-19",
        "cr": 45,
        "t20": 40,
        "dr": 20,
        "ai": 80,
        "ref_rate": 4,
        "jx_cr": 20,
        "p_cr": 15,
        "allocated": 1000,
        "conv": 2.0,
        "avg_deal": 5000,
        "on_duty": 20,
        "link_1d_num": 400,
        "jx_transfer_in": 50,
        "pool_retrieval": 40,
        "total_revenue": 100000,
    }
    summary.update(overrides)
    return summary


def make_depts():
    return [
        {
            "dept_name": "电销四部",
            "deep_talk_rate": 20,
            "per_capita_revenue": 2500,
        }
    ]


def _finding(**overrides):
    payload = {
        "collision_type": "metric_x_metric",
        "tag": "低接通·长通话",
        "description": "电销四部接通率偏低但一旦接通时长达标",
        "revenue_impact": 1,
        "priority": "P0",
        "recommendations": ["排查号码标记比例，轮换外呼线路"],
        "knowledge_refs": ["T18:外呼营销实战-接通率提升"],
        "scope": "dept",
        "dept_name": "电销四部",
        "manager_name": "宋晓鹏",
        "management_gap": "该管理者可能缺乏对号码健康度和外呼时段的精细化管理意识，未及时排查号码标记和线路轮换",
    }
    payload.update(overrides)
    return CollisionFinding(**payload)


def _titles(items):
    return [item["title"] for item in items]


class P0Impact1FirstCardTests(unittest.TestCase):
    def setUp(self):
        self.pipe = AnalysisPipeline("/tmp/unused-coverage.db")

    def test_p0_revenue_impact_1_is_first_collision_card(self):
        # `priority in (P0, P1) and revenue_impact > 0` first fires
        # a P0 card at 1. Distinct from PR #132's P1==1 vehicle.
        items, total = self.pipe._calc_improvements(
            make_summary(), make_depts(), [_finding()]
        )
        self.assertIn("[对撞] 低接通·长通话", _titles(items))
        card = next(i for i in items if i["title"] == "[对撞] 低接通·长通话")
        self.assertEqual("P0", card["p"])
        self.assertEqual(1, card["rev"])
        self.assertEqual(1, total)
        self.assertEqual("电销四部(管理者:宋晓鹏)", card["target_entity"])
        self.assertEqual("排查号码标记比例，轮换外呼线路", card["daily_action"])
        self.assertEqual("2026-09-20", card["deploy_date"])
        self.assertEqual(7, card["duration_days"])
        self.assertEqual("第3天检查数据变化，第7天验收", card["milestone"])
        self.assertIn("feasibility", card)
        self.assertEqual("high", card["feasibility"])

    def test_p0_revenue_impact_0_still_skips(self):
        # Contrast: flipping `> 0` to `>= 0` would emit a ¥0 P0 card
        # while keeping PR #132's P1==1 suite green.
        items, total = self.pipe._calc_improvements(
            make_summary(), make_depts(), [_finding(revenue_impact=0)]
        )
        self.assertNotIn("[对撞] 低接通·长通话", _titles(items))
        self.assertEqual(0, total)

    def test_p2_revenue_impact_1_still_skips(self):
        items, total = self.pipe._calc_improvements(
            make_summary(), make_depts(), [_finding(priority="P2")]
        )
        self.assertNotIn("[对撞] 低接通·长通话", _titles(items))
        self.assertEqual(0, total)


if __name__ == "__main__":
    unittest.main()
