"""Regression coverage for leftover causal just-over + funnel tie-break.

PR #79 locked 漏斗瓶颈 as a global P0 (including zero-denom) and
causal 触达效率 fire.
PR #108 locked allocated == on_duty*12 → 资源输入 warning, plus
other single-node bottlenecks and the all-healthy skip.
PR #122 locked reverse-trace equality silence (used allocated=1300
only as a fixture).

Remaining operators were never the primary lock:

- allocated == on_duty*12 + 1 is already 资源输入 normal
  (`>` not `>=`)
- when two funnel stages share the same rate/benchmark ratio,
  min() keeps the earlier stage in list order

A flipped `>` to `>=` would keep marking a fully staffed day as
资源不足 the moment allocated ticks one lead past 12×值班.
A flipped tie-break (or a later-stage-wins rewrite) would move the
P0 漏斗瓶颈 off the true first constraint and send the daily
repair order to the wrong step.

Does not retest PR #79 zero-denom / PR #108 ==12 warning as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    LogicCollisionEngine,
)


def _forward_summary(**overrides):
    summary = {
        "allocated": 1201,
        "on_duty": 100,
        "alloc_rate": 0.9,
        "cr": 43,
        "dial_count": 8000,
        "dr": 18,
        "ai": 70,
        "conv": 1.0,
        "signed_deals": 20,
        "total_revenue": 400000,
        "pc": 4000,
        "ref_rate": 5,
        "complaint_count": 1,
        "t20": 40,
    }
    summary.update(overrides)
    return summary


class CausalAllocatedJustOverTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_allocated_just_over_12x_is_normal_resource_node(self):
        # 100*12+1 = 1201. Need `>` so this is healthy; cr=42 makes
        # 触达效率 the bottleneck instead.
        self.engine._build_causal_chains(
            _forward_summary(allocated=1201, on_duty=100, cr=42),
            [],
            [],
        )
        chain = self.engine.causal_chains[0]
        by_name = {n["name"]: n["status"] for n in chain["nodes"]}
        self.assertEqual("normal", by_name["资源输入"])
        self.assertEqual("warning", by_name["触达效率"])
        self.assertEqual("触达效率", chain["bottleneck"])

    def test_allocated_just_over_12x_with_healthy_kpis_has_no_bottleneck(self):
        self.engine._build_causal_chains(_forward_summary(), [], [])
        chain = self.engine.causal_chains[0]
        self.assertTrue(all(n["status"] == "normal" for n in chain["nodes"]))
        self.assertNotIn("bottleneck", chain)


class FunnelTieBreakTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def _bottleneck(self, summary):
        self.engine.findings = []
        self.engine._collide_funnel_x_benchmark(summary)
        cards = [f for f in self.engine.findings if f.tag == "漏斗瓶颈"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P0", cards[0].priority)
        self.assertEqual("global", cards[0].scope)
        return cards[0]

    def test_tied_first_two_stages_keep_allocate_to_dial(self):
        # Both 分配→拨打 and 拨打→接通 sit at ratio 0.5;
        # 接通→深沟 / 深沟→签单 are healthier (ratio 5 / 10).
        card = self._bottleneck({
            "allocated": 200,
            "dial_count": 300,       # 1.5 / 3.0 = 0.5
            "link_1d_num": 22.5,     # 7.5 / 15 = 0.5
            "deep_talk": 22.5,       # 100 / 20 = 5
            "signed_deals": 22.5,    # 100 / 10 = 10
        })
        self.assertIn("分配→拨打", card.description)
        self.assertNotIn("拨打→接通(当前", card.description)

    def test_tied_last_two_stages_keep_connect_to_deep(self):
        # First two stages at ratio 1.0; last two tied at 0.5.
        # min() must keep 接通→深沟 (earlier of the tied pair).
        card = self._bottleneck({
            "allocated": 100,
            "dial_count": 300,       # 3.0 / 3.0 = 1.0
            "link_1d_num": 45,       # 15 / 15 = 1.0
            "deep_talk": 4.5,        # 10 / 20 = 0.5
            "signed_deals": 0.225,   # 5 / 10 = 0.5
        })
        self.assertIn("接通→深沟", card.description)
        self.assertNotIn("深沟→签单(当前", card.description)


if __name__ == "__main__":
    unittest.main()
