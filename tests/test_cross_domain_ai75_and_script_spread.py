"""Regression coverage for leftover CrossDomain AI / 话术标准化 exact gates.

PR #81 locked 质检AI化 fire at ai=70 and silence at 80, and 话术标准化
fire on a far spread (8000 vs 2000) with balanced depts silent.
PR #115 locked 飞轮 ==1200 / 品牌修复 ==4 / 271 t20==50 / 辛普森 3-dept
exact silences.

Remaining operators were never the primary lock:

- ai == 75 is silent for 质检AI化×复盘四步法 (need < 75)
- ai == 74.9 is the first fire and still interpolates {ai}
- 话术标准化 is silent when max(pc) == 1.5 × mean (need >)
- just-over 1.5 × mean is the first fire

A flipped `<` to `<=` on the AI gate would turn a 75.0 达标日 into a
质检复盘卡；a flipped `>` to `>=` on the 1.5× spread would flag a
department that is exactly at the 标准化门槛 and push a false SOP 通关.

Does not retest PR #81 far-from-threshold fire/silence as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import CrossDomainCollisionEngine


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


class CrossDomainAi75AndScriptSpreadTests(unittest.TestCase):
    def test_ai_exactly_75_is_silent_for_quality_review(self):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(ai=75), _depts(2500, 2600), [], [])
        self.assertNotIn("质检AI化×复盘四步法", _tags(engine))

    def test_ai_74_9_is_first_quality_review_fire(self):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(ai=74.9), _depts(2500, 2600), [], [])
        cards = [f for f in engine.findings if f.tag == "质检AI化×复盘四步法"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("74.9", cards[0].description)
        self.assertIn("未达标(标杆75)", cards[0].description)
        self.assertIn("T22:电销新思维-AI质检", cards[0].knowledge_refs)

    def test_script_spread_silent_when_max_pc_equals_1_5x_mean(self):
        # 3750 & 1250 → mean=2500, 1.5×=3750; 3750 > 3750 is False.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(3750, 1250), [], [])
        self.assertNotIn("话术标准化×优势管理", _tags(engine))

    def test_script_spread_fires_just_over_1_5x_mean(self):
        # 3751 & 1249 → mean=2500, 1.5×=3750; 3751 > 3750.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(3751, 1249), [], [])
        cards = [f for f in engine.findings if f.tag == "话术标准化×优势管理"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("可复制", cards[0].description)
        self.assertIn("T06:可复制的销售力-SOP", cards[0].knowledge_refs)


if __name__ == "__main__":
    unittest.main()
