"""Regression coverage for leftover funnel three-way / non-adjacent ties.

PR #79 locked 漏斗瓶颈 as a global P0 (including zero-denom).
PR #123 locked *adjacent* pair ties at ratio 0.5
(分配→拨打 vs 拨打→接通, and 接通→深沟 vs 深沟→签单).

Remaining operators were never the primary lock:

- three-way tie across stages 1+3+4 (skipping a healthier mid stage)
  still keeps the earliest stage 分配→拨打
- non-adjacent two-way tie (分配→拨打 vs 深沟→签单) also keeps
  the earlier stage
- three-way tie on the last three stages keeps 拨打→接通

A later-stage-wins rewrite, or a "skip healthy mid-stage then
pick the last red cell" heuristic, would move the P0 漏斗瓶颈
off the true first constraint and send the daily repair order
to 深沟→签单 while 分配→拨打 is equally weak.

Does not retest PR #79 zero-denom / PR #123 adjacent-pair ties
as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


class FunnelThreeWayAndNonAdjacentTieTests(unittest.TestCase):
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

    def test_three_way_tie_skipping_mid_stage_keeps_allocate_to_dial(self):
        # 分配→拨打 / 接通→深沟 / 深沟→签单 at ratio 0.5;
        # 拨打→接通 is healthier (ratio 1.0).
        card = self._bottleneck({
            "allocated": 200,
            "dial_count": 300,       # 1.5 / 3.0 = 0.5
            "link_1d_num": 45,       # 15 / 15 = 1.0
            "deep_talk": 4.5,        # 10 / 20 = 0.5
            "signed_deals": 0.225,   # 5 / 10 = 0.5
        })
        self.assertIn("分配→拨打", card.description)
        self.assertNotIn("接通→深沟(当前", card.description)
        self.assertNotIn("深沟→签单(当前", card.description)

    def test_nonadjacent_first_and_last_keep_allocate_to_dial(self):
        # Only the first and last stages sit at 0.5; the two
        # middle stages are on-benchmark (ratio 1.0).
        card = self._bottleneck({
            "allocated": 200,
            "dial_count": 300,       # 1.5 / 3.0 = 0.5
            "link_1d_num": 45,       # 15 / 15 = 1.0
            "deep_talk": 9,          # 20 / 20 = 1.0
            "signed_deals": 0.45,    # 5 / 10 = 0.5
        })
        self.assertIn("分配→拨打", card.description)
        self.assertNotIn("深沟→签单(当前", card.description)

    def test_three_way_tie_on_last_three_keeps_dial_to_connect(self):
        # First stage on-benchmark; last three tied at 0.5.
        # min() must keep 拨打→接通 (earliest of the tied trio).
        card = self._bottleneck({
            "allocated": 100,
            "dial_count": 300,       # 3.0 / 3.0 = 1.0
            "link_1d_num": 22.5,     # 7.5 / 15 = 0.5
            "deep_talk": 2.25,       # 10 / 20 = 0.5
            "signed_deals": 0.1125,  # 5 / 10 = 0.5
        })
        self.assertIn("拨打→接通", card.description)
        self.assertNotIn("接通→深沟(当前", card.description)
        self.assertNotIn("深沟→签单(当前", card.description)


if __name__ == "__main__":
    unittest.main()
