"""Regression coverage for leftover healthy-funnel always-on + H1 exact drivers.

PR #79 locked 漏斗瓶颈 as a global P0 (including zero-denom).
PR #123 / #124 locked below-benchmark ties and |Δcr|==1.5 *named*
secondary drivers.
PR #109 locked equal-gate silence with a *small* |Δcr|=0.4 reject.
PR #81 / #111 locked 接通/漏斗/高营收 / 低营收 alternatives.

Remaining operators were never the primary lock:

- all four funnel stages *above* benchmark still emit P0 漏斗瓶颈
  and still pick the relatively weakest stage (TOC always-on)
- |Δcr|==1.5 + |Δalloc|==50 / |Δpc|==200 stay unnamed
- |Δcr|==1.5 + alloc==50 + conv just-over names only 转化率变化
- production tag 高活动·高接通·低营收 prefers 接通 (not 大单)
- 营收波动过大 has 营收 but not 高 → None

Dropping the always-on funnel card on a "全绿"日 would hide the
TOC 修复顺序. Flipping a driver `>` to `>=` would put 分配量变化
on a 50-条抖动. Reordering 营收+高 ahead of 接通 would blame
大单效应 on the P0 高活动·高接通·低营收 card.

Does not retest PR #123/#124 below-benchmark ties or named 1.5
drivers as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    CollisionFinding,
    DataCollisionEngine,
    LogicCollisionEngine,
)


def _trend_pair(cr_prev, cr_last, **last_overrides):
    prev = {
        "total_revenue": 100000,
        "cr": cr_prev,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last = {
        "total_revenue": 110000,
        "cr": cr_last,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last.update(last_overrides)
    return [prev, last]


def _finding(tag):
    return CollisionFinding(
        collision_type="metric_x_metric",
        tag=tag,
        description="fixture",
        revenue_impact=1000,
        priority="P0",
    )


class HealthyFunnelAlwaysOnTests(unittest.TestCase):
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

    def test_all_stages_above_benchmark_still_picks_first_weakest(self):
        # All ratios > 1.0; 分配→拨打 is closest to its benchmark.
        card = self._bottleneck({
            "allocated": 100,
            "dial_count": 310,      # 3.1 / 3.0 ≈ 1.033
            "link_1d_num": 62,      # 20 / 15 ≈ 1.333
            "deep_talk": 18.6,      # 30 / 20 = 1.5
            "signed_deals": 2.8,    # 15.05 / 10 = 1.505
        })
        self.assertIn("分配→拨打", card.description)
        self.assertNotIn("拨打→接通(当前", card.description)
        self.assertNotIn("深沟→签单(当前", card.description)
        self.assertEqual(4, len(card.evidence))

    def test_all_stages_above_benchmark_can_still_name_last_stage(self):
        # All ratios > 1.0; 深沟→签单 is the relative bottleneck.
        card = self._bottleneck({
            "allocated": 100,
            "dial_count": 400,      # 4.0 / 3.0 ≈ 1.333
            "link_1d_num": 80,      # 20 / 15 ≈ 1.333
            "deep_talk": 20,        # 25 / 20 = 1.25
            "signed_deals": 2.1,    # 10.5 / 10 = 1.05
        })
        self.assertIn("深沟→签单", card.description)
        self.assertNotIn("分配→拨打(当前", card.description)
        self.assertNotIn("接通→深沟(当前", card.description)


class H1ExactDriverSilenceAndAltTagTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, trends):
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses({}, [], trends, [])
        h1 = [h for h in self.engine.hypotheses if h["id"] == "H1"]
        self.assertEqual(1, len(h1))
        return h1[0]

    def test_cr_1_5_plus_alloc_exactly_50_does_not_name_allocation(self):
        h1 = self._h1(_trend_pair(43, 44.5, allocated=1050))
        self.assertEqual("推翻", h1["verdict"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])

    def test_cr_1_5_plus_pc_exactly_200_does_not_name_per_capita(self):
        h1 = self._h1(_trend_pair(43, 44.5, pc=3200))
        self.assertEqual("推翻", h1["verdict"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])

    def test_cr_1_5_plus_alloc_50_and_conv_over_names_only_conversion(self):
        h1 = self._h1(_trend_pair(43, 44.5, allocated=1050, conv=1.06))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_high_activity_low_rev_prefers_connect_over_big_deal(self):
        alt = self.engine._generate_alternative(
            _finding("高活动·高接通·低营收"), {}, []
        )
        self.assertIsNotNone(alt)
        self.assertIn("运营商", alt)
        self.assertNotIn("大单", alt)

    def test_revenue_volatility_tag_without_high_has_no_alternative(self):
        self.assertIsNone(
            self.engine._generate_alternative(_finding("营收波动过大"), {}, [])
        )


if __name__ == "__main__":
    unittest.main()
