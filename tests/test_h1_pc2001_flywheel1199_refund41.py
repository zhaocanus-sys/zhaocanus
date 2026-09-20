"""Regression coverage for leftover H1 |Δpc|==200.1 and CrossDomain 1199/4.1.

PR #109/#125 locked |Δpc|==200 as *unnamed* in the H1 alternative.
PR #97 locked a far pc-only composition, not the first `> 200` tick.

PR #115 locked CrossDomain exact silence at 飞轮 pc==1200 and
品牌修复 ref_rate==4. PR #81 locked far fire on both tags.

The leftover first ticks were never the primary lock:

- |Δpc|==200.1 is the first named 人均产值变化 (`> 200`)
- |Δpc|==200 stays unnamed
- pc==1199 is the first 飞轮效应×困境六悖论 (`< 1200`)
- ref_rate==4.1 is the first 客户成功×品牌修复信任链 (`> 4`)

Does not retest PR #115 ==1200 / ==4 silence as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    CrossDomainCollisionEngine,
    LogicCollisionEngine,
)


def _full_summary(**overrides):
    """Complete format keys so leftover gated rules do not KeyError."""
    summary = {
        "dr": 10.0,
        "conv": 2.0,
        "avg_deal": 6000,
        "t20": 40,
        "fc_rate": 5.0,
        "ai": 80,
        "ref_rate": 2.0,
    }
    summary.update(overrides)
    return summary


def _depts(*pcs):
    return [
        {"dept_name": f"电销{i}部", "per_capita_revenue": pc}
        for i, pc in enumerate(pcs, 1)
    ]


def _tags(engine):
    return {f.tag for f in engine.findings}


class H1Pc2001FirstNamedTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, pc_prev, pc_last):
        self.engine.hypotheses = []
        self.engine.findings = []
        self.engine._build_and_test_hypotheses(
            {"t20": 40, "pc": 3000},
            [{"dept_name": "电销六部", "refund_rate": 5, "signed_deals": 10, "avg_ai_score": 70}],
            [
                {
                    "total_revenue": 100000,
                    "cr": 45.0,
                    "conv": 1.0,
                    "pc": pc_prev,
                    "allocated": 1000,
                },
                {
                    "total_revenue": 110000,
                    "cr": 45.4,
                    "conv": 1.03,
                    "pc": pc_last,
                    "allocated": 1040,
                },
            ],
            [],
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H1"]

    def test_pc_plus_200_1_is_first_named_driver(self):
        # 4200.1 - 4000 == 200.1 > 200. |Δcr|=0.4 / |Δalloc|=40 /
        # |Δconv|=0.03 stay unnamed. Distinct from PR #97's far pc-only.
        h1s = self._h1(4000, 4200.1)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("人均产值变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertTrue(any("幅度不大" in e for e in h1["reject_evidence"]))
        self.assertIn("增长", h1["hypothesis"])

    def test_pc_plus_exactly_200_stays_unnamed(self):
        # 4200 - 4000 == 200 is not `> 200`. Flipping to `>=` would
        # keep PR #97 far-pc green while naming a 贴线 200 人效日.
        h1s = self._h1(4000, 4200)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("营收变动主因可能是:", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])


class Flywheel1199AndRefund41FirstFireTests(unittest.TestCase):
    def test_pc_1199_is_first_flywheel_tick(self):
        # 1199 < 1200. Distinct from PR #81 far-below-1200 fire.
        # 2 depts keep 辛普森 / 271 off; pcs stay inside 1.5× mean.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(1199, 1300), [], [])
        cards = [f for f in engine.findings if f.tag == "飞轮效应×困境六悖论"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("人均产值<1200", cards[0].description)
        self.assertIn("飞轮", cards[0].description)
        self.assertIn("R01:从优秀到卓越-飞轮效应", cards[0].knowledge_refs)
        self.assertTrue(any("卡点" in r for r in cards[0].recommendations))

    def test_pc_exactly_1200_stays_silent_for_flywheel(self):
        # Contrast: leftover 4.1 品牌修复 must not drag 飞轮 in when
        # every department sits on the 1200 redline.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(ref_rate=4.1), _depts(1200, 1300), [], [])
        self.assertNotIn("飞轮效应×困境六悖论", _tags(engine))

    def test_ref_rate_4_1_is_first_brand_repair_tick(self):
        # 4.1 > 4. Distinct from PR #111 interpolation at 4.5.
        # pcs stay >=1200 so 飞轮 stays off.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(ref_rate=4.1), _depts(1200, 1300), [], [])
        cards = [f for f in engine.findings if f.tag == "客户成功×品牌修复信任链"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("退费率4.1%偏高", cards[0].description)
        self.assertIn("二次伤害", cards[0].description)
        self.assertIn("R34:品牌洗脑-信任重建", cards[0].knowledge_refs)

    def test_ref_rate_exactly_4_stays_silent_for_brand_repair(self):
        # Contrast: leftover 1199 飞轮 must not drag 品牌修复 in when
        # ref_rate sits on the 4.0 redline.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(ref_rate=4), _depts(1199, 1300), [], [])
        self.assertNotIn("客户成功×品牌修复信任链", _tags(engine))


if __name__ == "__main__":
    unittest.main()
