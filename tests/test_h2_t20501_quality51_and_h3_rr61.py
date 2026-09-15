"""Regression coverage for leftover H2 t20==50.1, 质量保障 5.1, H3 6.1.

PR #108 locked H2 skip at t20<=50 and far 质量保障 when ref_rate>5.
PR #122 locked H2 ==15 / ==1.3x reject plus mixed 部分推翻.
PR #129 locked leftover AI gap 15.1 first support — but still behind
the t20>50 gate, which was never locked at the first tick.

PR #127/#128 locked H3 signed 11.1 / AI 比较 verdicts using refund
rates that already passed `> 6`. The inclusion gate itself was never
the primary lock.

The leftover ticks:

- t20==50.1 is the first H2 emission (`> 50`); small AI/dials gaps
  stay 部分推翻 + 挖需求
- t20==50 stays silent (one-liner guard vs `<` → `<=` flip)
- ref_rate==5.1 is the first forward 质量保障 bottleneck (`> 5`);
  reverse gates stay on-redline so no 因果链追溯 card
- refund_rate==6.1 is the first H3 高退费 inclusion (`> 6`);
  ==6.0 is excluded even when a <=4 counterpart exists

Does not retest PR #108 far 退费 / t20<=50 skip payload as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


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
    """10 people → TOP20%=2, BOTTOM30%=3. Default gaps stay reject."""
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


def _forward_summary(**overrides):
    summary = {
        "allocated": 1300,
        "on_duty": 100,
        "alloc_rate": 0.9,
        "cr": 43,
        "dial_count": 8000,
        "dr": 18,
        "ai": 70,
        "conv": 1.0,
        "signed_deals": 20,
        "total_revenue": 399900,
        "pc": 3999,
        "ref_rate": 5,
        "complaint_count": 1,
        "t20": 55,
    }
    summary.update(overrides)
    return summary


class H2T20JustOverFirstEmissionTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h2(self, t20):
        self.engine.findings = []
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            {"t20": t20, "pc": 3000},
            [{"dept_name": "电销六部", "refund_rate": 5,
              "signed_deals": 10, "avg_ai_score": 70}],
            [],
            _ten_persons(),
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H2"]

    def test_t20_50_1_is_first_h2_emission_as_partial_reject(self):
        # 50.1 > 50 is the first H2 build after PR #108's <=50 skip.
        # Default roster keeps both gaps in reject → 部分推翻 / 挖需求.
        # Distinct from PR #129's 15.1 AI first-support behind a far t20.
        h2s = self._h2(50.1)
        self.assertEqual(1, len(h2s))
        h2 = h2s[0]
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertEqual(0, len(h2["support_evidence"]))
        self.assertEqual(2, len(h2["reject_evidence"]))
        self.assertIn("挖需求", h2["alternative"])
        self.assertNotIn("勤奋度", h2["alternative"])
        cards = [f for f in self.engine.findings if f.tag.startswith("假设验证")]
        self.assertEqual(1, len(cards))
        self.assertEqual("假设验证: 部分推翻", cards[0].tag)

    def test_t20_exactly_50_skips_h2(self):
        # One-liner guard so flipping `>` to `>=` cannot hide behind
        # the 50.1 fire case. Not a retest of PR #108's far-below skip.
        self.assertEqual([], self._h2(50))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag.startswith("假设验证")],
        )


class QualityNode51FirstBottleneckTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_ref_rate_5_1_is_first_quality_bottleneck_without_reverse_card(self):
        # 5.1 > 5 is the first 质量保障 warning after PR #108's far
        # 退费>5. Reverse gates stay on-redline (cr/dr/ai/t20), so the
        # leftover is a forward-only bottleneck — no 因果链追溯 card.
        self.engine._build_causal_chains(
            _forward_summary(ref_rate=5.1),
            [],
            [],
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "因果链追溯"],
        )
        self.assertEqual(1, len(self.engine.causal_chains))
        forward = self.engine.causal_chains[0]
        by_name = {n["name"]: n["status"] for n in forward["nodes"]}
        self.assertEqual("warning", by_name["质量保障"])
        self.assertEqual("normal", by_name["触达效率"])
        self.assertEqual("normal", by_name["会话深度"])
        self.assertEqual("normal", by_name["转化产出"])
        self.assertEqual("质量保障", forward["bottleneck"])
        self.assertIn("质量保障", forward["diagnosis"])

    def test_ref_rate_exactly_5_stays_off_quality_bottleneck(self):
        # ==5 is not `> 5`. Flipping to `>=` would mark a 贴线退费
        # day as the chain bottleneck while PR #108's far fire stays green.
        self.engine._build_causal_chains(_forward_summary(ref_rate=5), [], [])
        self.assertEqual(1, len(self.engine.causal_chains))
        self.assertNotIn("bottleneck", self.engine.causal_chains[0])
        by_name = {n["name"]: n["status"] for n in self.engine.causal_chains[0]["nodes"]}
        self.assertEqual("normal", by_name["质量保障"])


class H3Refund61FirstInclusionTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h3(self, high_refund):
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            {"t20": 40, "pc": 3000},
            [
                {"dept_name": "电销六部", "refund_rate": high_refund,
                 "signed_deals": 10, "avg_ai_score": 70},
                {"dept_name": "电销一部", "refund_rate": 4.0,
                 "signed_deals": 10, "avg_ai_score": 70},
            ],
            [],
            [],
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H3"]

    def test_refund_6_1_is_first_h3_high_refund_inclusion(self):
        # 6.1 > 6 is the first 高退费 bucket after PR #127/#128 used
        # already-qualifying rates. Equal signed / equal AI is enough
        # to build H3; verdicts themselves are not the lock here.
        h3s = self._h3(6.1)
        self.assertEqual(1, len(h3s))
        self.assertEqual("H3", h3s[0]["id"])
        self.assertTrue(h3s[0]["verdict"])

    def test_refund_exactly_6_is_excluded_from_h3(self):
        # ==6 is not `> 6`. A 贴线 6.0% department must not be labeled
        # 高退费 just because a <=4 counterpart exists.
        self.assertEqual([], self._h3(6.0))


if __name__ == "__main__":
    unittest.main()
