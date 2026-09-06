"""Regression coverage for leftover DataCollision exact-threshold silence.

PR #78/#79/#80 locked fire paths and far-from-threshold silence.
PR #120 locked peak==0.72 / refund==6 / jx / new-AI / connect / activity
exact equality. These remaining operators were never the primary lock:

- dials_pp == 50 / connect_rate == 42 / pc == mean*0.75
  (_collide_dials_x_connects_x_revenue needs all three strict)
- deep_talk_rate == 20 / avg_ai_score == 68 (高深沟·低AI)
- deep_talk_rate == 15 / avg_ai_score == 75 (低深沟·高AI)
- dept per-capita CV == 0.35 (need > 0.35)
- 7-day revenue CV == 0.15 (need > 0.15)
- senior avg_rev == mature * 0.85; newbie ratio == 50
- refund > 6 but signed_deals == mean (need signed > mean)

A flipped `>`/`>=` would emit a false P0/P1 部门诊断 the day a KPI
sits exactly on the redline, or hide a real 高活动低转化 / 话术闲聊.

Does not retest fire formulas, manager-gap wiring, or PR #120
peak/refund/jx/new-AI/connect/activity equalities as primary.
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
        "deep_talk_rate": 18,
        "link_1d_num": 200,
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


class DialsConnectsRevenueExactSilenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_dials_pp_exactly_50_is_silent(self):
        # 500/10 == 50; trigger is > 50. Other two legs would fire.
        self.engine._collide_dials_x_connects_x_revenue(
            [
                make_dept(
                    dept_name="电销六部",
                    on_duty=10,
                    dial_count=500,
                    connect_rate=50,
                    per_capita_revenue=1000,
                ),
                make_dept(
                    dept_name="电销一部",
                    on_duty=10,
                    dial_count=400,
                    connect_rate=40,
                    per_capita_revenue=10000,
                ),
            ]
        )
        self.assertEqual([], self.engine.findings)

    def test_connect_rate_exactly_42_is_silent(self):
        # dials_pp=60>50 and pc < mean*0.75, but cr == 42 is not > 42
        self.engine._collide_dials_x_connects_x_revenue(
            [
                make_dept(
                    dept_name="电销六部",
                    on_duty=10,
                    dial_count=600,
                    connect_rate=42,
                    per_capita_revenue=1000,
                ),
                make_dept(
                    dept_name="电销一部",
                    on_duty=10,
                    dial_count=400,
                    connect_rate=40,
                    per_capita_revenue=10000,
                ),
            ]
        )
        self.assertEqual([], self.engine.findings)

    def test_per_capita_exactly_75pct_of_mean_is_silent(self):
        # 3000 == ((3000+5000)/2)*0.75; trigger is <
        self.engine._collide_dials_x_connects_x_revenue(
            [
                make_dept(
                    dept_name="电销六部",
                    on_duty=10,
                    dial_count=600,
                    connect_rate=50,
                    per_capita_revenue=3000,
                ),
                make_dept(
                    dept_name="电销一部",
                    on_duty=10,
                    dial_count=400,
                    connect_rate=40,
                    per_capita_revenue=5000,
                ),
            ]
        )
        self.assertEqual([], self.engine.findings)


class DeepTalkExactSilenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_high_deep_exact_rate_or_ai_is_silent(self):
        # dr == 20 (need > 20) even with ai=67 < 68
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=20, avg_ai_score=67)]
        )
        self.assertEqual([], self.engine.findings)

        # ai == 68 (need < 68) even with dr=21 > 20
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=21, avg_ai_score=68)]
        )
        self.assertEqual([], self.engine.findings)

    def test_low_deep_exact_rate_or_ai_is_silent(self):
        # dr == 15 (need < 15) even with ai=76 > 75
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=15, avg_ai_score=76)]
        )
        self.assertEqual([], self.engine.findings)

        # ai == 75 (need > 75) even with dr=14 < 15
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=14, avg_ai_score=75)]
        )
        self.assertEqual([], self.engine.findings)


class VarianceTrendTenureRefundExactSilenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_dept_cv_exactly_035_is_silent(self):
        # n=2, pcs=125/75 → sample CV rounds to 0.35; trigger is >
        self.engine._collide_dept_variance(
            {},
            [
                make_dept(dept_name="电销一部", per_capita_revenue=125, on_duty=10),
                make_dept(dept_name="电销六部", per_capita_revenue=75, on_duty=10),
            ],
        )
        self.assertEqual([], self.engine.findings)

    def test_trend_cv_exactly_015_is_silent(self):
        # 850/1000/1150 → stdev/mean == 0.15; trigger is >
        self.engine._collide_trend_x_volatility(
            [
                {"dt": "20260901", "total_revenue": 850},
                {"dt": "20260902", "total_revenue": 1000},
                {"dt": "20260903", "total_revenue": 1150},
            ]
        )
        self.assertEqual([], self.engine.findings)

    def test_senior_rev_exactly_85pct_of_mature_is_silent(self):
        # 850 == 1000 * 0.85; trigger is <
        self.engine._collide_tenure_x_productivity(
            {"pc": 2000},
            [
                make_person(name="成熟", tenure_months=18, revenue=1000),
                make_person(name="老人", tenure_months=30, revenue=850),
            ],
        )
        self.assertEqual([], self.engine.findings)

    def test_newbie_ratio_exactly_50_is_silent(self):
        # 500 / 1000 * 100 == 50; trigger is < 50
        self.engine._collide_tenure_x_productivity(
            {"pc": 1000},
            [make_person(name="新人", tenure_months=2, revenue=500)],
        )
        self.assertEqual([], self.engine.findings)

    def test_high_refund_but_signed_equals_mean_is_silent(self):
        # refund 8 > 6, but both signed=10 so signed is not > mean
        self.engine._collide_signed_x_refund(
            [
                make_dept(dept_name="电销四部", signed_deals=10, refund_rate=8),
                make_dept(dept_name="电销五部", signed_deals=10, refund_rate=2),
            ]
        )
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
