"""Regression coverage for leftover peak-hour skip / all-peak fire
and `_generate_alternative` tags that are not 接通/漏斗/高营收.

PR #120 locked peak_ratio == 0.72 silence.
PR #126 locked 0.721 as the first 时段失衡 fire.
Neither locked the total<=0 early-return (0/0 would otherwise
divide) or the all-peak day (offpeak==0 → ratio 1.0).

PR #81 / #111 / #125 locked alternatives for 接通 / 漏斗 / 高营收
and None for 低营收 / 营收波动过大. Tags that contain 高 but not
营收 (高签单·高退费) or contain 接通 (低接通·长通话) were never
the primary lock — reordering `营收+高` ahead of `接通` would
blame 大单效应 on a 号码/时段 P0.

Does not retest PR #120/#126 peak 0.72/0.721 or PR #125 接通-first
as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    CollisionFinding,
    DataCollisionEngine,
    LogicCollisionEngine,
)


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


def _finding(tag):
    return CollisionFinding(
        collision_type="metric_x_metric",
        tag=tag,
        description="fixture",
        revenue_impact=1000,
        priority="P0",
    )


class PeakZeroAndAllPeakTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_zero_peak_and_offpeak_skips_without_dividing(self):
        # total <= 0 must continue before peak/total. Removing the
        # guard would raise ZeroDivisionError on a 零营收日.
        self.engine._collide_peak_x_offpeak(
            [make_dept(peak_hour_revenue=0, offpeak_hour_revenue=0)]
        )
        self.assertEqual([], self.engine.findings)

    def test_all_peak_offpeak_zero_is_first_100pct_imbalance_fire(self):
        # 1000 / 1000 == 1.0 > 0.72. Distinct from PR #126's 0.721.
        self.engine._collide_peak_x_offpeak(
            [make_dept(peak_hour_revenue=1000, offpeak_hour_revenue=0)]
        )
        cards = [f for f in self.engine.findings if f.tag == "时段失衡"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertIn("高峰时段贡献100%营收", cards[0].description)
        self.assertIn("高峰占比100%>72%", cards[0].evidence[0])

    def test_zero_peak_with_positive_offpeak_is_silent(self):
        # ratio == 0.0 is not > 0.72. A 非高峰-only day must not
        # emit 时段失衡.
        self.engine._collide_peak_x_offpeak(
            [make_dept(peak_hour_revenue=0, offpeak_hour_revenue=1000)]
        )
        self.assertEqual([], self.engine.findings)


class GenerateAlternativeLeftoverTagTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_low_connect_long_talk_prefers_connect_over_big_deal(self):
        alt = self.engine._generate_alternative(
            _finding("低接通·长通话"), {}, []
        )
        self.assertIsNotNone(alt)
        self.assertIn("运营商", alt)
        self.assertNotIn("大单", alt)

    def test_high_signed_high_refund_has_no_alternative(self):
        # Tag has 高 but not 营收, so the 高营收 / 大单 branch
        # must not fire.
        self.assertIsNone(
            self.engine._generate_alternative(_finding("高签单·高退费"), {}, [])
        )

    def test_high_deep_low_ai_has_no_alternative(self):
        self.assertIsNone(
            self.engine._generate_alternative(_finding("高深沟·低AI"), {}, [])
        )


if __name__ == "__main__":
    unittest.main()
