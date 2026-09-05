"""Regression coverage for leftover collision exact-threshold silence.

PR #78/#79/#80 locked fire paths and far-from-threshold silence
(均衡高峰、转入量过低、退费高但签单低于均值、质量会话 6%、接通 45/80s).
Exact equality on the comparison operators was never the primary lock:

- peak_ratio == 0.72  (need > 0.72)
- refund_rate == 6    (need > 6) even when signed > mean
- jx_transfer_in == 30 (need > 30)
- jx_conv == own * 0.6 (need <)
- new_avg_ai == all * 0.8 (need <)
- avg_connect_dur == 100 (need < 100) even when cr >= 43
- connect_rate == 40 (need < 40) even when dur > 150
- dials_pp == 45 / quality_ratio == 4 (need > 45 and < 4)

A flipped `>`/`>=` would emit a false P0/P1 部门诊断 the day a KPI
sits exactly on the redline, or hide a real 建信信任折损 / 时段失衡.

Does not retest fire formulas or manager-gap wiring as primary.
Does not lock persistence global cr_below_count (PR #48).
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
        "on_duty": 20,
        "dial_count": 800,
        "deep_talk": 40,
        "per_capita_revenue": 2500,
        "allocated": 500,
    }
    dept.update(overrides)
    return dept


def make_person(**overrides):
    person = {
        "name": "员工A",
        "tenure_months": 12,
        "ai_score": 75,
        "revenue": 3000,
        "dial_count": 80,
    }
    person.update(overrides)
    return person


class CollisionExactSilenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_peak_ratio_exactly_72_is_silent(self):
        # 7200 / (7200+2800) == 0.72; trigger is >
        self.engine._collide_peak_x_offpeak(
            [make_dept(peak_hour_revenue=7200, offpeak_hour_revenue=2800)]
        )
        self.assertEqual([], self.engine.findings)

    def test_refund_rate_exactly_6_is_silent_even_when_signed_above_mean(self):
        self.engine._collide_signed_x_refund(
            [
                make_dept(dept_name="电销四部", signed_deals=20, refund_rate=6),
                make_dept(dept_name="电销五部", signed_deals=10, refund_rate=2),
            ]
        )
        self.assertEqual([], self.engine.findings)

    def test_jx_transfer_exactly_30_is_silent_even_with_rate_gap(self):
        # 1.0 < 2.0 * 0.6, but transfer == 30 is not > 30
        self.engine._collide_jx_x_own_conversion(
            [
                make_dept(
                    conversion_rate=2.0,
                    jx_conv_rate=1.0,
                    jx_transfer_in=30,
                )
            ]
        )
        self.assertEqual([], self.engine.findings)

    def test_jx_conv_exactly_60pct_of_own_is_silent(self):
        # 1.2 == 2.0 * 0.6; trigger is <
        self.engine._collide_jx_x_own_conversion(
            [
                make_dept(
                    conversion_rate=2.0,
                    jx_conv_rate=1.2,
                    jx_transfer_in=40,
                )
            ]
        )
        self.assertEqual([], self.engine.findings)

    def test_new_hire_ai_exactly_80pct_of_all_is_silent(self):
        # new=64, veteran=96 → all_avg=80, 80*0.8=64; trigger is <
        self.engine._collide_new_hire_x_overall(
            {},
            [
                make_person(name="新人", tenure_months=2, ai_score=64),
                make_person(name="老人", tenure_months=12, ai_score=96),
            ],
        )
        self.assertEqual([], self.engine.findings)

    def test_connect_duration_exactly_100s_is_silent_when_cr_meets_43(self):
        # high-connect branch needs dur < 100; low-connect needs cr < 40
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=45, avg_connect_dur=100)]
        )
        self.assertEqual([], self.engine.findings)

    def test_connect_rate_exactly_40_is_silent_even_when_duration_is_long(self):
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=40, avg_connect_dur=180)]
        )
        self.assertEqual([], self.engine.findings)

    def test_activity_exact_dials_or_quality_ratio_is_silent(self):
        # dials_pp == 45 (need > 45) even with quality_ratio ~1.1%
        self.engine._collide_activity_x_quality(
            [make_dept(on_duty=10, dial_count=450, deep_talk=5)]
        )
        self.assertEqual([], self.engine.findings)

        # quality_ratio == 4 (need < 4) even with dials_pp=50
        self.engine._collide_activity_x_quality(
            [make_dept(on_duty=10, dial_count=500, deep_talk=20)]
        )
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
