"""Regression coverage for leftover 转化产出 0.99 and 接通时长 150.1.

PR #108 locked far conv=0.9 as 转化产出 bottleneck and far 质量保障.
PR #123 locked allocated == on_duty*12+1 as 资源输入 normal.
PR #129 locked cr==42.9 as reverse 接通率.
PR #130 locked dr==17.9 / ref_rate==5.1 as first 会话深度 / 质量保障.

PR #120 locked 低接通 silence at cr==40 even when dur is long.
PR #126 locked leftover cr==39.9 + far dur=180, and dur==99 + far cr=45.

The remaining first ticks were never the primary lock:

- conv==0.99 is the first forward 转化产出 warning (`< 1.0`); reverse
  gates stay on-redline so no 因果链追溯 card
- conv==1.0 stays off the bottleneck
- dur==150.1 is the first 低接通·长通话 duration tick (`> 150`)
  after PR #126 locked the CR operand; dur==150 stays silent
- cr==43 is the first 高接通·短通话 connect tick (`>= 43`) after
  PR #126 locked the duration operand; cr==42.9 stays silent

Does not retest PR #108 far conv=0.9 / PR #126 cr==39.9+180 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    LogicCollisionEngine,
)


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


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "peak_hour_revenue": 7000,
        "offpeak_hour_revenue": 3000,
        "conversion_rate": 2.0,
        "jx_conv_rate": 1.8,
        "jx_transfer_in": 10,
        "avg_deal_amount": 5000,
        "connect_rate": 45,
        "avg_connect_dur": 120,
        "signed_deals": 10,
        "refund_rate": 3,
        "refund_amount": 1000,
        "avg_ai_score": 72,
        "total_revenue": 50000,
        "on_duty": 20,
        "dial_count": 800,
        "deep_talk": 40,
        "per_capita_revenue": 2500,
        "allocated": 500,
    }
    dept.update(overrides)
    return dept


class Conversion099FirstBottleneckTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_conv_0_99_is_first_conversion_bottleneck_without_reverse_card(self):
        # 0.99 < 1.0 is the first 转化产出 warning after PR #108's
        # far conv=0.9. Reverse gates stay on-redline (cr/dr/ai/t20),
        # so the leftover is a forward-only bottleneck — no 因果链追溯.
        self.engine._build_causal_chains(
            _forward_summary(conv=0.99),
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
        self.assertEqual("warning", by_name["转化产出"])
        self.assertEqual("normal", by_name["触达效率"])
        self.assertEqual("normal", by_name["会话深度"])
        self.assertEqual("normal", by_name["质量保障"])
        self.assertEqual("转化产出", forward["bottleneck"])
        self.assertIn("转化产出", forward["diagnosis"])

    def test_conv_exactly_1_0_stays_off_conversion_bottleneck(self):
        # ==1.0 is not `< 1.0`. Flipping to `<=` would mark a 贴线
        # 转化 day as the chain bottleneck while PR #108's far fire
        # stays green.
        self.engine._build_causal_chains(_forward_summary(conv=1.0), [], [])
        self.assertEqual(1, len(self.engine.causal_chains))
        self.assertNotIn("bottleneck", self.engine.causal_chains[0])
        by_name = {
            n["name"]: n["status"] for n in self.engine.causal_chains[0]["nodes"]
        }
        self.assertEqual("normal", by_name["转化产出"])


class LowConnectDur1501AndHighConnectCr43Tests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_dur_150_1_is_first_low_connect_long_talk_duration_tick(self):
        # 150.1 > 150 is the first duration operand after PR #126
        # locked cr==39.9 behind a far 180s. Far cr=30 already
        # qualifies `< 40`. Impact = 500*(43-30)/100*2/100*5000 = 6500.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=30, avg_connect_dur=150.1)]
        )
        cards = [f for f in self.engine.findings if f.tag == "低接通·长通话"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P0", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertEqual("游云清", cards[0].manager_name)
        self.assertIn("号码健康度", cards[0].management_gap)
        self.assertEqual(6500, cards[0].revenue_impact)
        self.assertIn("接通率仅30%", cards[0].description)
        self.assertIn("均时长150s", cards[0].description)
        self.assertNotIn("高接通·短通话", {f.tag for f in self.engine.findings})

    def test_dur_exactly_150_stays_off_low_connect_long_talk(self):
        # ==150 is not `> 150`. Flipping to `>=` would P0 a 贴线
        # 150s day while PR #126's far-180 suite stays green.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=30, avg_connect_dur=150)]
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "低接通·长通话"],
        )

    def test_cr_43_is_first_high_connect_short_talk_connect_tick(self):
        # 43 >= 43 is the first connect operand after PR #126 locked
        # dur==99 behind a far cr=45. Impact = 500*0.02*5000 = 50000.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=43, avg_connect_dur=99)]
        )
        cards = [f for f in self.engine.findings if f.tag == "高接通·短通话"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertEqual("游云清", cards[0].manager_name)
        self.assertIn("开场白", cards[0].management_gap)
        self.assertEqual(50000, cards[0].revenue_impact)
        self.assertIn("接通率43%达标", cards[0].description)
        self.assertIn("均接通时长仅99s", cards[0].description)
        self.assertNotIn("低接通·长通话", {f.tag for f in self.engine.findings})

    def test_cr_42_9_stays_off_high_connect_short_talk(self):
        # 42.9 >= 43 is False. Flipping to `>` would keep PR #126's
        # dur==99 fire green while swallowing the first 43% 开场白 card.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=42.9, avg_connect_dur=99)]
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "高接通·短通话"],
        )


if __name__ == "__main__":
    unittest.main()
