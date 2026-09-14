"""Regression coverage for leftover reverse-trace 接通率 first fire.

PR #108 locked reverse-trace fire for 深沟 / AI-only / t20-only and
the pc>=4000 skip.
PR #122 locked exact silence: cr==43 / dr==18 / ai==70 / t20==55
with pc=3999 emit no 因果链追溯.

The leftover 接通率 tick was never the primary lock:

- cr==42.9 is the first reverse-trace 接通率 cause (`< 43`)
- because 触达效率 is also warning on the forward chain, consistency
  stays 正反向因果链一致 (not the 偏差 branch PR #108 locked for
  AI-only / t20-only)

Does not retest PR #122 all-four-on-redline silence as primary.
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


class ReverseTraceCr429FirstCauseTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_cr_42_9_is_first_reverse_connect_cause_and_consistent(self):
        # 42.9 < 43 is the first 接通率 reverse cause after PR #122
        # exact silence. Forward 触达效率 is also warning → 一致.
        self.engine._build_causal_chains(
            _forward_summary(cr=42.9),
            [],
            [],
        )
        cards = [f for f in self.engine.findings if f.tag == "因果链追溯"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("1个可能原因", cards[0].description)
        self.assertIn("接通率", cards[0].description)
        self.assertIn("正反向因果链一致", cards[0].description)
        self.assertNotIn("存在偏差", cards[0].description)

        reverse = [c for c in self.engine.causal_chains if c["direction"] == "反向"]
        self.assertEqual(1, len(reverse))
        self.assertEqual(1, len(reverse[0]["possible_causes"]))
        self.assertIn("接通率42.9%<43%", reverse[0]["possible_causes"][0])
        self.assertEqual("正反向因果链一致", reverse[0]["consistency_check"])

        forward = self.engine.causal_chains[0]
        by_name = {n["name"]: n["status"] for n in forward["nodes"]}
        self.assertEqual("warning", by_name["触达效率"])
        self.assertEqual("normal", by_name["资源输入"])
        self.assertEqual("触达效率", forward["bottleneck"])

    def test_cr_exactly_43_stays_silent_when_other_reverse_gates_hold(self):
        # Sanity leftover vs PR #122: cr==43 with pc=3999 and the
        # other three reverse gates on-redline still emit nothing.
        # Kept as a one-liner guard so a future `<` → `<=` on cr
        # cannot hide behind the 42.9 fire case.
        self.engine._build_causal_chains(_forward_summary(cr=43), [], [])
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "因果链追溯"],
        )
        self.assertEqual(1, len(self.engine.causal_chains))
        self.assertNotIn("bottleneck", self.engine.causal_chains[0])


if __name__ == "__main__":
    unittest.main()
