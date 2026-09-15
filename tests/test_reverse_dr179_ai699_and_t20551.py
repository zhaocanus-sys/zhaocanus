"""Regression coverage for leftover reverse-trace 深沟 / AI / t20 first fire.

PR #108 locked far reverse-trace fire for 深沟 / AI-only / t20-only
and the pc>=4000 skip.
PR #122 locked exact silence: cr==43 / dr==18 / ai==70 / t20==55
with pc=3999 emit no 因果链追溯.
PR #129 locked leftover cr==42.9 as the first 接通率 cause.

The remaining just-over ticks were never the primary lock:

- dr==17.9 is the first reverse-trace 深沟率 cause (`< 18`)
- because 会话深度 is also warning on the forward chain, consistency
  stays 正反向因果链一致
- ai==69.9 is the first reverse-trace AI cause (`< 70`); AI is not a
  forward-node status, so consistency is 偏差
- t20==55.1 is the first reverse-trace 集中度 cause (`> 55`); t20 is
  also not a forward-node status, so consistency is 偏差

Does not retest PR #122 all-four-on-redline silence or PR #129
cr==42.9 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def _forward_summary(**overrides):
    # allocated > on_duty*12 so 资源输入 is normal. Other forward
    # nodes sit on-or-above their redlines unless overridden.
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


class ReverseTraceDrAiT20FirstCauseTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _reverse_cards(self):
        return [f for f in self.engine.findings if f.tag == "因果链追溯"]

    def test_dr_17_9_is_first_reverse_deep_cause_and_consistent(self):
        # 17.9 < 18 is the first 深沟率 reverse cause after PR #122
        # exact silence. Forward 会话深度 is also warning → 一致.
        self.engine._build_causal_chains(
            _forward_summary(dr=17.9),
            [],
            [],
        )
        cards = self._reverse_cards()
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("1个可能原因", cards[0].description)
        self.assertIn("深沟率", cards[0].description)
        self.assertIn("正反向因果链一致", cards[0].description)
        self.assertNotIn("存在偏差", cards[0].description)

        reverse = [c for c in self.engine.causal_chains if c["direction"] == "反向"]
        self.assertEqual(1, len(reverse))
        self.assertEqual(1, len(reverse[0]["possible_causes"]))
        self.assertIn("深沟率17.9%<18%", reverse[0]["possible_causes"][0])
        self.assertEqual("正反向因果链一致", reverse[0]["consistency_check"])

        forward = self.engine.causal_chains[0]
        by_name = {n["name"]: n["status"] for n in forward["nodes"]}
        self.assertEqual("warning", by_name["会话深度"])
        self.assertEqual("normal", by_name["触达效率"])
        self.assertEqual("会话深度", forward["bottleneck"])

    def test_ai_69_9_is_first_reverse_ai_cause_and_divergent(self):
        # 69.9 < 70 is the first AI reverse cause. Forward 会话深度
        # only watches dr (still 18), so no forward warning → 偏差.
        # Distinct from PR #108's far-AI 偏差 payload.
        self.engine._build_causal_chains(
            _forward_summary(ai=69.9),
            [],
            [],
        )
        cards = self._reverse_cards()
        self.assertEqual(1, len(cards))
        self.assertIn("1个可能原因", cards[0].description)
        self.assertIn("AI均分", cards[0].description)
        self.assertIn("存在偏差", cards[0].description)
        self.assertNotIn("正反向因果链一致", cards[0].description)

        reverse = [c for c in self.engine.causal_chains if c["direction"] == "反向"]
        self.assertEqual(1, len(reverse))
        self.assertEqual(1, len(reverse[0]["possible_causes"]))
        self.assertIn("AI均分69.9<70", reverse[0]["possible_causes"][0])
        self.assertEqual("正反向因果链存在偏差，需进一步分析", reverse[0]["consistency_check"])

        forward = self.engine.causal_chains[0]
        self.assertNotIn("bottleneck", forward)
        by_name = {n["name"]: n["status"] for n in forward["nodes"]}
        self.assertEqual("normal", by_name["会话深度"])

    def test_t20_55_1_is_first_reverse_concentration_cause_and_divergent(self):
        # 55.1 > 55 is the first t20 reverse cause after PR #122's
        # ==55 silence. t20 is not a forward-node status → 偏差.
        self.engine._build_causal_chains(
            _forward_summary(t20=55.1),
            [],
            [],
        )
        cards = self._reverse_cards()
        self.assertEqual(1, len(cards))
        self.assertIn("1个可能原因", cards[0].description)
        self.assertIn("TOP20%", cards[0].description)
        self.assertIn("存在偏差", cards[0].description)

        reverse = [c for c in self.engine.causal_chains if c["direction"] == "反向"]
        self.assertEqual(1, len(reverse))
        self.assertEqual(1, len(reverse[0]["possible_causes"]))
        self.assertIn("TOP20%占比55.1%>55%", reverse[0]["possible_causes"][0])
        self.assertEqual("正反向因果链存在偏差，需进一步分析", reverse[0]["consistency_check"])
        self.assertNotIn("bottleneck", self.engine.causal_chains[0])

    def test_dr_17_9_plus_ai_69_9_keeps_deep_as_primary_cause(self):
        # Two leftover ticks together: 深沟 is appended first, so the
        # card's 主因 stays 深沟率 even though AI also just-fires.
        # Forward 会话深度 warning keeps 一致. Flipping append order
        # would keep the single-cause suites green while mis-ranking.
        self.engine._build_causal_chains(
            _forward_summary(dr=17.9, ai=69.9),
            [],
            [],
        )
        cards = self._reverse_cards()
        self.assertEqual(1, len(cards))
        self.assertIn("2个可能原因", cards[0].description)
        self.assertIn("深沟率", cards[0].description)
        self.assertIn("正反向因果链一致", cards[0].description)

        reverse = [c for c in self.engine.causal_chains if c["direction"] == "反向"]
        self.assertEqual(2, len(reverse[0]["possible_causes"]))
        self.assertIn("深沟率17.9%<18%", reverse[0]["possible_causes"][0])
        self.assertIn("AI均分69.9<70", reverse[0]["possible_causes"][1])
        self.assertEqual("会话深度", self.engine.causal_chains[0]["bottleneck"])


if __name__ == "__main__":
    unittest.main()
