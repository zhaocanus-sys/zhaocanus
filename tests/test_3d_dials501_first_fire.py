"""Regression coverage for leftover 3D dials_pp==50.1 first fire.

PR #121 locked the three-gate silence at
dials_pp==50 / cr==42 / pc==mean*0.75.
PR #126 locked leftover first fire at dials_pp==51 (510/10)
behind cr==42.1 and a far pc=1000 vs 10000.

The leftover DIALS operand was never the primary lock:

- 501/10 == 50.1 is the first `> 50` tick
- cr==42.1 stays the leftover connect tick
- ==50 + leftover cr/pc stays silent
- leftover 50.1 + cr==42 stays silent

Does not retest PR #126's far 51 as primary.
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


def _pair(low_dials, low_cr, low_pc=1000):
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


class Dials501ThreeDFirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_dials_50_1_plus_cr_42_1_is_first_dials_tick(self):
        # 501/10 == 50.1 > 50. Distinct from PR #126's 510/10 == 51.
        # avg_pc = (1000+10000)/2 = 5500; 1000 < 5500*0.75.
        # Impact = (5500-1000)*10*0.2 = 9000.
        self.engine._collide_dials_x_connects_x_revenue(_pair(501, 42.1))
        cards = [f for f in self.engine.findings if f.tag == "高活动·高接通·低营收"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P0", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertEqual("游云清", cards[0].manager_name)
        self.assertEqual(9000, cards[0].revenue_impact)
        self.assertIn("转化环节", cards[0].description)
        self.assertTrue(any("接通率42.1%>42%" in e for e in cards[0].evidence))
        self.assertTrue(any("拨打50通>50" in e for e in cards[0].evidence))
        self.assertIn("只关注活动量", cards[0].management_gap)

    def test_dials_exactly_50_plus_leftover_cr_stays_silent(self):
        # 500/10 == 50 is not `> 50`. Flipping to `>=` would keep
        # PR #126's 51 fire green while tagging a 贴线 50-dial day.
        self.engine._collide_dials_x_connects_x_revenue(_pair(500, 42.1))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "高活动·高接通·低营收"],
        )

    def test_dials_50_1_plus_cr_exactly_42_stays_silent(self):
        # Leftover dials tick cannot fire when cr is on the redline.
        self.engine._collide_dials_x_connects_x_revenue(_pair(501, 42))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "高活动·高接通·低营收"],
        )


if __name__ == "__main__":
    unittest.main()
