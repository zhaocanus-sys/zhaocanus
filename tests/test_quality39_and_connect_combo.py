"""Regression coverage for leftover quality 3.8 and 39.9×150.1 combo.

PR #120 locked dials_pp==45 / quality_ratio==4 silence.
PR #126 locked leftover dials 45.1 behind a *far* quality 1.1.

The leftover quality operand was never the primary lock:

- dials 45.1 + quality_ratio==3.8 is the first 高拨打·低质量
  quality tick (`< 4`)
- dials 45.1 + quality_ratio==4.0 stays silent

PR #126 locked cr==39.9 + far dur=180.
PR #131 locked dur==150.1 + far cr=30.

The combined leftover:

- cr==39.9 + dur==150.1 is the first 低接通·长通话 at *both*
  leftover ticks
- cr==40 + dur==150.1 stays silent; cr==39.9 + dur==150 stays silent

Does not retest PR #126 far-quality 1.1 or PR #131 far-cr 30 as primary.
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
        "dial_count": 451,
        "deep_talk": 17,
        "per_capita_revenue": 2500,
        "allocated": 500,
        "link_1d_num": 180,
    }
    dept.update(overrides)
    return dept


class Quality38FirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_dials_45_1_plus_quality_3_8_is_first_quality_tick(self):
        # 451/10 == 45.1 > 45. deep_talk=17 → quality_conv=1.7,
        # ratio = 1.7/45.1*100 ≈ 3.769 → 3.8 < 4.
        # Distinct from PR #126's far 0.5/45.1 ≈ 1.1.
        # Impact = 10 * 1.5 * 5000 * 0.1 = 7500.
        self.engine._collide_activity_x_quality([make_dept()])
        cards = [f for f in self.engine.findings if f.tag == "高拨打·低质量"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertEqual("游云清", cards[0].manager_name)
        self.assertEqual(7500, cards[0].revenue_impact)
        self.assertIn("人均拨打45通", cards[0].description)
        self.assertTrue(any("质量会话占比3.8%<4%" in e for e in cards[0].evidence))
        self.assertIn("刷量", cards[0].description)
        self.assertIn("只追拨打量", cards[0].management_gap)

    def test_dials_45_1_plus_quality_4_0_stays_silent(self):
        # deep_talk=18 → 1.8/45.1*100 ≈ 3.991 → 4.0, not `< 4`.
        # Flipping to `<=` would keep PR #126's 1.1 fire green while
        # tagging a 贴线 4% quality day as 刷量.
        self.engine._collide_activity_x_quality(
            [make_dept(deep_talk=18)]
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "高拨打·低质量"],
        )


class Connect399TimesDur1501ComboTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_cr_39_9_plus_dur_150_1_is_first_combined_low_connect(self):
        # Both leftover operands together. Impact =
        # 500 * (43-39.9)/100 * 2/100 * 5000 = 1550.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=39.9, avg_connect_dur=150.1)]
        )
        cards = [f for f in self.engine.findings if f.tag == "低接通·长通话"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P0", cards[0].priority)
        self.assertEqual(1550, cards[0].revenue_impact)
        self.assertEqual("游云清", cards[0].manager_name)
        self.assertIn("号码健康度", cards[0].management_gap)
        self.assertTrue(any("接通率39.9%<40%" in e for e in cards[0].evidence))
        self.assertTrue(any("均接通时长150s>150s" in e for e in cards[0].evidence))
        self.assertIn("话术能力强但号码/时段有瓶颈", cards[0].description)

    def test_either_operand_on_redline_stays_silent(self):
        # cr==40 is not `< 40`; dur==150 is not `> 150`.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=40, avg_connect_dur=150.1)]
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "低接通·长通话"],
        )

        self.engine.findings = []
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=39.9, avg_connect_dur=150)]
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "低接通·长通话"],
        )


if __name__ == "__main__":
    unittest.main()
