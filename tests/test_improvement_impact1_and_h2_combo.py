"""Regression coverage for leftover impact==1 改善卡 and H2 50.1×15.1×1.3x.

PR #111 locked `_calc_improvements` findings-loop skip at
P0 `revenue_impact==0` and P2 with a positive impact. The first
positive tick (`==1`) on a P0/P1 finding was never the primary lock.

PR #130 locked t20==50.1 as first H2 emission — but with small
AI/dials gaps that stay 部分推翻.
PR #129 locked AI gap 15.1 first support behind a far t20.
PR #122 locked exact ==15 / ==1.3x reject.

The combined leftover:

- P1 `revenue_impact==1` is the first `[对撞]` card (`> 0`)
- P1 `revenue_impact==0` and P2 `==1` still skip
- t20==50.1 + AI 15.1 + dials 131 vs 100 is the first 支持
  at the leftover inclusion gate
- t20==50.1 + AI 15.1 + equal dials stays 部分推翻
- t20==50 + both leftover ticks still skips H2

Does not retest PR #111 skip-at-zero / P2-skip or PR #130
small-gap 部分推翻 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline
from agent_system.engines.collision_engine import (
    CollisionFinding,
    LogicCollisionEngine,
)


def make_summary(**overrides):
    summary = {
        "date": "2026-09-17",
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
        "tag": "高签单·高退费",
        "description": "电销四部签单高于均值但退费率偏高",
        "revenue_impact": 1,
        "priority": "P1",
        "recommendations": ["签单后48h回访确认制度"],
        "knowledge_refs": ["S15:客户成功-LTV管理"],
        "scope": "dept",
        "dept_name": "电销四部",
        "manager_name": "宋晓鹏",
        "management_gap": "该管理者可能对签单话术合规性监管不足，团队存在过度承诺倾向",
    }
    payload.update(overrides)
    return CollisionFinding(**payload)


def _titles(items):
    return [item["title"] for item in items]


def make_person(**overrides):
    person = {
        "name": "员工A",
        "revenue": 3000,
        "ai_score": 70,
        "dial_count": 100,
    }
    person.update(overrides)
    return person


def _ten_persons(top_ai=72, bot_ai=70, top_dials=100, bot_dials=100):
    """10 people → TOP20%=2, BOTTOM30%=3."""
    persons = []
    for i in range(2):
        persons.append(make_person(
            name=f"TOP{i}", revenue=9000 - i, ai_score=top_ai, dial_count=top_dials,
        ))
    for i in range(5):
        persons.append(make_person(
            name=f"MID{i}", revenue=4000 - i, ai_score=70, dial_count=100,
        ))
    for i in range(3):
        persons.append(make_person(
            name=f"BOT{i}", revenue=1000 - i, ai_score=bot_ai, dial_count=bot_dials,
        ))
    return persons


class ImprovementImpact1FirstCardTests(unittest.TestCase):
    def setUp(self):
        self.pipe = AnalysisPipeline("/tmp/unused-coverage.db")

    def test_p1_revenue_impact_1_is_first_collision_card(self):
        # `> 0` first fires at 1. PR #111 locked ==0 skip and a far
        # 2000 emit; the leftover tick is the first yuan.
        items, total = self.pipe._calc_improvements(
            make_summary(), make_depts(), [_finding()]
        )
        self.assertIn("[对撞] 高签单·高退费", _titles(items))
        card = next(i for i in items if i["title"] == "[对撞] 高签单·高退费")
        self.assertEqual("P1", card["p"])
        self.assertEqual(1, card["rev"])
        self.assertEqual(1, total)
        self.assertEqual("电销四部(管理者:宋晓鹏)", card["target_entity"])
        self.assertEqual("签单后48h回访确认制度", card["daily_action"])
        self.assertEqual("2026-09-18", card["deploy_date"])
        self.assertEqual(7, card["duration_days"])
        self.assertIn("feasibility", card)

    def test_p1_revenue_impact_0_still_skips(self):
        items, total = self.pipe._calc_improvements(
            make_summary(), make_depts(), [_finding(revenue_impact=0)]
        )
        self.assertNotIn("[对撞] 高签单·高退费", _titles(items))
        self.assertEqual(0, total)

    def test_p2_revenue_impact_1_still_skips(self):
        # Priority gate is independent of the leftover ==1 tick.
        items, total = self.pipe._calc_improvements(
            make_summary(), make_depts(), [_finding(priority="P2")]
        )
        self.assertNotIn("[对撞] 高签单·高退费", _titles(items))
        self.assertEqual(0, total)


class H2T501PlusAi151PlusDials131Tests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h2(self, t20, top_ai=85.1, bot_ai=70, top_dials=131, bot_dials=100):
        self.engine.findings = []
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            {"t20": t20, "pc": 3000},
            [{"dept_name": "电销六部", "refund_rate": 5,
              "signed_deals": 10, "avg_ai_score": 70}],
            [],
            _ten_persons(
                top_ai=top_ai, bot_ai=bot_ai,
                top_dials=top_dials, bot_dials=bot_dials,
            ),
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H2"]

    def test_t20_50_1_plus_ai_15_1_plus_dials_131_is_first_support(self):
        # 50.1 > 50 includes H2. 85.1-70 == 15.1 > 15 and
        # 131 > 100*1.3 are both leftover support ticks.
        # Together they are the first 支持 at the inclusion gate.
        # Distinct from PR #130's small-gap 部分推翻 and PR #129's
        # 15.1 behind a far t20.
        h2s = self._h2(50.1)
        self.assertEqual(1, len(h2s))
        h2 = h2s[0]
        self.assertEqual("支持", h2["verdict"])
        self.assertEqual(2, len(h2["support_evidence"]))
        self.assertEqual(0, len(h2["reject_evidence"]))
        self.assertIn("勤奋度", h2["alternative"])
        self.assertNotIn("挖需求", h2["alternative"])
        cards = [f for f in self.engine.findings if f.tag.startswith("假设验证")]
        self.assertEqual(1, len(cards))
        self.assertEqual("假设验证: 支持", cards[0].tag)

    def test_t20_50_1_plus_ai_15_1_equal_dials_stays_partial(self):
        # AI support cannot outvote the equal-dials reject
        # (`>=` on reject). Stays 部分推翻 + 挖需求.
        h2s = self._h2(50.1, top_dials=100, bot_dials=100)
        self.assertEqual(1, len(h2s))
        h2 = h2s[0]
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertEqual(1, len(h2["support_evidence"]))
        self.assertEqual(1, len(h2["reject_evidence"]))
        self.assertIn("挖需求", h2["alternative"])
        self.assertNotIn("勤奋度", h2["alternative"])

    def test_t20_exactly_50_plus_both_leftover_ticks_skips_h2(self):
        # ==50 is not `> 50`. Both leftover support ticks must not
        # emit H2 (or a 假设验证 card) on a 贴线集中度 day.
        self.assertEqual([], self._h2(50))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag.startswith("假设验证")],
        )


if __name__ == "__main__":
    unittest.main()
