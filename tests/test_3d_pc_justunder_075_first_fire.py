"""Regression coverage for leftover 3D pc < mean*0.75 first fire.

PR #121 locked the three-gate silence at
dials_pp==50 / cr==42 / pc==mean*0.75.
PR #126 locked leftover first fire at dials 51 + cr 42.1 behind a
far pc=1000 vs 10000.
PR #134 locked leftover dials 50.1 + cr 42.1 behind the same far pc.

The leftover PC operand was never the primary lock:

- 5999 vs 10000 (avg=7999.5, 0.75×=5999.625) is the first
  `pc < avg*0.75` tick
- 6000 vs 10000 is exact `== mean*0.75` and stays silent
- leftover 50.1 + 42.1 still cannot fire when pc is on the redline

Does not retest PR #126/#134 far pc=1000 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


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
        "on_duty": 10,
        "dial_count": 400,
        "deep_talk": 17,
        "deep_talk_rate": 18,
        "link_1d_num": 180,
        "per_capita_revenue": 2500,
        "allocated": 500,
    }
    dept.update(overrides)
    return dept


def _pair(low_pc, low_dials=501, low_cr=42.1):
    return [
        make_dept(
            dept_name="电销六部",
            on_duty=10,
            dial_count=low_dials,
            connect_rate=low_cr,
            per_capita_revenue=low_pc,
        ),
        make_dept(
            dept_name="电销一部",
            on_duty=10,
            dial_count=400,
            connect_rate=40,
            per_capita_revenue=10000,
        ),
    ]


class PcJustUnder075ThreeDFirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_pc_5999_vs_10000_is_first_075_tick(self):
        # leftover 50.1 / 42.1 + 5999 vs 10000:
        # avg_pc = 7999.5; 5999 < 7999.5*0.75 == 5999.625.
        # Distinct from PR #126/#134 far pc=1000.
        # Impact = (7999.5-5999)*10*0.2 = 4001.
        self.engine._collide_dials_x_connects_x_revenue(_pair(5999))
        cards = [f for f in self.engine.findings if f.tag == "高活动·高接通·低营收"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P0", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertEqual("游云清", cards[0].manager_name)
        self.assertEqual(4001, cards[0].revenue_impact)
        self.assertIn("转化环节", cards[0].description)
        self.assertTrue(any("人均产值¥5,999<均值75%" in e for e in cards[0].evidence))
        self.assertIn("只关注活动量", cards[0].management_gap)

    def test_pc_exactly_6000_vs_10000_stays_silent(self):
        # 6000 == 8000*0.75. Flipping `<` to `<=` would keep
        # PR #126/#134 far-1000 suites green while tagging a
        # 贴线 75% 人效 day as 转化话术 P0.
        self.engine._collide_dials_x_connects_x_revenue(_pair(6000))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "高活动·高接通·低营收"],
        )

    def test_leftover_pc_cannot_fire_when_dials_on_redline(self):
        # 5999 is not enough when dials_pp==50. The leftover pc tick
        # still needs all three strict gates.
        self.engine._collide_dials_x_connects_x_revenue(_pair(5999, 500, 42.1))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "高活动·高接通·低营收"],
        )


if __name__ == "__main__":
    unittest.main()
