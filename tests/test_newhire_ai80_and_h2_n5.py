"""Regression coverage for leftover new-hire AI 0.8 tick and H2 n=5.

PR #80 locked far 新人AI评分断层 fire.
PR #126 locked leftover first fire at 63 vs 96 (all=79.5, 80%=63.6).

The leftover 0.8 operand was never the primary lock:

- new=79.9 vs veteran=120.1 (all=100, 80%=80) is the first
  `new_avg < all*0.8` tick
- new==80 vs veteran=120 stays silent

PR #122 locked n=3 (int slices 0/0) + t20>50 still 部分推翻.
The leftover smallest roster that can actually score TOP20%:

- n=5 → TOP20%=1, BOTTOM30%=1; leftover 15.1 + 130.1 is first 支持
- n=4 → TOP20%=0 still 部分推翻 (empty top slice)

Does not retest PR #126 far 63/96 or PR #122 n=3 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    LogicCollisionEngine,
)


def _person(**overrides):
    person = {
        "name": "员工",
        "tenure_months": 12,
        "ai_score": 80,
        "revenue": 3000,
        "dial_count": 100,
    }
    person.update(overrides)
    return person


class NewHireAi80FirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_new_79_9_vs_all_100_is_first_08_tick(self):
        # 79.9 < 100*0.8. Distinct from PR #126's 63 vs 96.
        # gap=20.1, impact=round(1*20.1*50)=1005.
        self.engine._collide_new_hire_x_overall(
            {},
            [
                _person(name="新人", tenure_months=2, ai_score=79.9, revenue=800),
                _person(name="老人", tenure_months=18, ai_score=120.1, revenue=4000),
            ],
        )
        cards = [f for f in self.engine.findings if f.tag == "新人AI评分断层"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual(1005, cards[0].revenue_impact)
        self.assertIn("新人(≤3月)AI均分79.9", cards[0].description)
        self.assertIn("比全员100.0低20.1分", cards[0].description)
        self.assertTrue(any("新人AI均分79.9" in e for e in cards[0].evidence))
        self.assertIn("S06:销售加速公式", cards[0].knowledge_refs)

    def test_new_exactly_80_vs_all_100_stays_silent(self):
        # 80 < 100*0.8 is false. Flipping to `<=` would keep
        # PR #126's 63/96 suite green while tagging a 贴线 80%
        # 新人日 as 话术技能传承不足.
        self.engine._collide_new_hire_x_overall(
            {},
            [
                _person(name="新人", tenure_months=2, ai_score=80, revenue=800),
                _person(name="老人", tenure_months=18, ai_score=120, revenue=4000),
            ],
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "新人AI评分断层"],
        )

    def test_leftover_079_cannot_fire_without_a_new_hire(self):
        # 79.9 is not enough when nobody is tenure<=3.
        self.engine._collide_new_hire_x_overall(
            {},
            [
                _person(name="成长期", tenure_months=4, ai_score=79.9, revenue=800),
                _person(name="老人", tenure_months=18, ai_score=120.1, revenue=4000),
            ],
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "新人AI评分断层"],
        )


class H2FivePersonFirstSupportTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h2(self, n, top_ai=85.1, bot_ai=70, top_dials=130.1, bot_dials=100):
        persons = [_person(name="TOP", revenue=9000, ai_score=top_ai, dial_count=top_dials)]
        for i in range(max(0, n - 2)):
            persons.append(_person(name=f"MID{i}", revenue=4000 - i, ai_score=72, dial_count=110))
        if n >= 2:
            persons.append(_person(name="BOT", revenue=500, ai_score=bot_ai, dial_count=bot_dials))
        self.engine.findings = []
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            {"t20": 50.1, "pc": 3000},
            [{"dept_name": "电销六部", "refund_rate": 5, "signed_deals": 10, "avg_ai_score": 70}],
            [],
            persons[:n],
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H2"]

    def test_n5_plus_leftover_15_1_and_130_1_is_first_real_support(self):
        # n=5 → int(1.0)=1 TOP, int(1.5)=1 BOT. First roster that
        # can actually score both slices. Distinct from PR #122 n=3
        # (empty slices) and PR #133 n=10 leftover 130.1.
        h2s = self._h2(5)
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
        self.assertEqual("P1", cards[0].priority)

    def test_n4_empty_top_slice_stays_partial(self):
        # n=4 → TOP20%=0, BOTTOM30%=1. Empty top → AI/dials both
        # reject (0 vs live bottom). Stays 部分推翻 + 挖需求 even
        # with leftover 15.1 / 130.1 sitting on the unused top row.
        h2s = self._h2(4)
        self.assertEqual(1, len(h2s))
        h2 = h2s[0]
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertEqual(0, len(h2["support_evidence"]))
        self.assertEqual(2, len(h2["reject_evidence"]))
        self.assertIn("挖需求", h2["alternative"])
        self.assertNotIn("勤奋度", h2["alternative"])


if __name__ == "__main__":
    unittest.main()
