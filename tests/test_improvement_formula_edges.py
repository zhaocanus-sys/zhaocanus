"""Regression coverage for AnalysisPipeline improvement numeric formulas.

PR #72 locked the execution-contract fields and threshold silence
(all gates at/above the line + P2 / zero-impact findings excluded).
It did not lock the uplift math, the 公海 max(1, …) floor, unnamed
manager act text, or collision target_entity fallbacks.

Does not retest PR #72 title-set / deploy_date / feasibility contract
as primary assertions.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline
from agent_system.engines.collision_engine import CollisionFinding


def healthy_summary(**overrides):
    values = {
        "date": "2026-08-24",
        "avg_deal": 5_000,
        "cr": 43,
        "allocated": 1_000,
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


class ImprovementFormulaTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_connect_rate_uplift_uses_gap_times_conversion(self):
        # gap=3pp, extra=int(1000*3/100)=30, rev=round(30*2/100*5000)=3000
        items, total = self.pipeline._calc_improvements(
            healthy_summary(cr=40), two_depts(), []
        )
        card = _by_title(items)["接通率修复至43%"]
        self.assertEqual("P0", card["p"])
        self.assertEqual("40%", card["cur"])
        self.assertEqual(3_000, card["rev"])
        self.assertIn("增加有效接通30通→多签1单", card["detail"])
        self.assertEqual(3_000, total)

    def test_mid_tier_copy_uses_half_headcount_and_20pct_gap(self):
        # bot_n=int(20*0.5)=10, gap_pc=4000, rev=round(10*4000*0.2)=8000
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(t20=60), two_depts(), []
        )
        card = _by_title(items)["中腰部标杆复制"]
        self.assertEqual(8_000, card["rev"])
        self.assertEqual("TOP20%占60%", card["cur"])
        self.assertIn("后50%(10人)人均提升¥800", card["detail"])
        self.assertEqual(
            "中腰部员工(后50%约10人)，重点电销二部",
            card["target_entity"],
        )
        self.assertEqual(
            "提取电销一部标杆录音→电销二部话术通关",
            card["act"],
        )

    def test_named_worst_manager_is_parenthesized_in_act(self):
        self.pipeline.dept_managers = {"电销二部": "赵梅"}
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(t20=60), two_depts(), []
        )
        self.assertEqual(
            "提取电销一部标杆录音→电销二部(赵梅)话术通关",
            _by_title(items)["中腰部标杆复制"]["act"],
        )

    def test_deep_talk_uplift_uses_12pct_close_rate(self):
        # gap=10pp, extra_d=int(400*10/100)=40, rev=round(40*0.12*5000)=24000
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(dr=15), two_depts(), []
        )
        card = _by_title(items)["深沟率向标杆看齐"]
        self.assertEqual(24_000, card["rev"])
        self.assertEqual("15%", card["cur"])
        self.assertEqual("25%", card["tgt"])
        self.assertIn("深沟率+10.0pp→多深沟40通→按12%签单率", card["detail"])

    def test_refund_save_is_rate_gap_times_revenue(self):
        # save=round(100000*(8-4.5)/100)=3500
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(ref_rate=8), two_depts(), []
        )
        card = _by_title(items)["退费率管控至4.5%"]
        self.assertEqual(3_500, card["rev"])
        self.assertEqual("8%", card["cur"])
        self.assertEqual("P1", card["p"])

    def test_jianxin_transfer_uplift_is_extra_deals_times_avg(self):
        # extra=int(200*(18-10)/100)=16, rev=16*5000=80000
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(jx_cr=10), two_depts(), []
        )
        card = _by_title(items)["建信调配转化率→18%"]
        self.assertEqual(80_000, card["rev"])
        self.assertIn("日转入200条→多签16单", card["detail"])

    def test_pool_retrieval_floors_extra_deals_at_one(self):
        # int(10*(12-11)/100)=0 → max(1,0)=1 → rev=5000
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(p_cr=11, pool_retrieval=10), two_depts(), []
        )
        card = _by_title(items)["公海捞取转化→12%"]
        self.assertEqual(5_000, card["rev"])
        self.assertIn("日捞取10条→多签1单", card["detail"])


class CollisionImprovementFallbackTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_global_finding_targets_相关部门_and_default_action(self):
        finding = CollisionFinding(
            collision_type="metric_x_metric",
            tag="全局漏斗",
            description="X" * 180,
            revenue_impact=1_200,
            priority="P1",
            recommendations=[],
            knowledge_refs=["O04:TOC"],
        )
        items, total = self.pipeline._calc_improvements(
            healthy_summary(), two_depts(), [finding]
        )
        card = _by_title(items)["[对撞] 全局漏斗"]
        self.assertEqual("相关部门", card["target_entity"])
        self.assertEqual("按对撞建议执行", card["daily_action"])
        self.assertEqual("X" * 150, card["act"])
        self.assertEqual(["O04:TOC"], card["refs"])
        self.assertEqual(1_200, card["rev"])
        self.assertEqual(1_200, total)

    def test_dept_finding_without_manager_keeps_empty_parens(self):
        finding = CollisionFinding(
            collision_type="metric_x_entity",
            tag="部门转化异常",
            description="电销二部转化率显著低于基准",
            revenue_impact=2_500,
            priority="P0",
            recommendations=["每日复盘三通未成交录音"],
            scope="dept",
            dept_name="电销二部",
            manager_name="",
        )
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(), two_depts(), [finding]
        )
        card = _by_title(items)["[对撞] 部门转化异常"]
        self.assertEqual("电销二部()", card["target_entity"])
        self.assertEqual("每日复盘三通未成交录音", card["daily_action"])
        self.assertEqual("P0", card["p"])


if __name__ == "__main__":
    unittest.main()
