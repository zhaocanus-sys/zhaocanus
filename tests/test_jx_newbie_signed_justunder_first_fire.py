"""Regression coverage for leftover DataCollision just-under / just-over fire.

PR #120 locked exact silence:

- jx_conv == own * 0.6 (with transfer already > 30)
- refund_rate == 6 even when signed is far above mean

PR #121 locked exact silence:

- newbie ratio == 50
- signed_deals == mean even when refund > 6

PR #126 locked first fire on the *other* leg of those ANDs:

- transfer == 31 with jx_conv far under 0.6 (1.0 vs 2.0)
- refund == 6.1 with signed far above mean (20 vs 10)

The first tick *over/under the remaining operand* was never the
primary lock. Flipping `jx_conv < own*0.6` to `<=`, `ratio < 50`
to `<=`, or `signed > mean` to `>=` would keep those exact-silence
suites green while swallowing the first real 建信折损 / 新人断崖 /
过度承诺 card — or, for refund==6 + signed just-over, emit a
false P1 on a 贴线退费日.

Does not retest PR #120/#121 equalities or PR #126 far-leg first
fire as primary.
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


class JxConvJustUnderFirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_jx_conv_1_19_with_transfer_31_is_first_ratio_fire(self):
        # 1.19 < 2.0 * 0.6 == 1.2, and 31 > 30.
        # PR #120 locked 1.2 as silent; PR #126 locked transfer==31
        # with jx_conv far under (1.0).
        self.engine._collide_jx_x_own_conversion(
            [
                make_dept(
                    conversion_rate=2.0,
                    jx_conv_rate=1.19,
                    jx_transfer_in=31,
                )
            ]
        )
        cards = [f for f in self.engine.findings if f.tag == "建信→电销信任折损"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertIn("建信资源转化仅1.19%", cards[0].description)
        self.assertIn("不足自有的60%", cards[0].description)
        self.assertIn("日转入31条", cards[0].evidence[-1])

    def test_jx_conv_exactly_60pct_stays_silent_when_transfer_just_over(self):
        # Transfer is already on the first-fire side (31), but ratio
        # sits exactly on own*0.6. Flipping `<` to `<=` would fire here.
        self.engine._collide_jx_x_own_conversion(
            [
                make_dept(
                    conversion_rate=2.0,
                    jx_conv_rate=1.2,
                    jx_transfer_in=31,
                )
            ]
        )
        self.assertEqual([], self.engine.findings)


class NewbieRatioJustUnderFirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_newbie_ratio_49_9_is_first_cliff_fire(self):
        # 499 / 1000 * 100 == 49.9; PR #121 locked == 50 as silent.
        self.engine._collide_tenure_x_productivity(
            {"pc": 1000},
            [make_person(name="新人", tenure_months=2, revenue=499)],
        )
        cards = [f for f in self.engine.findings if f.tag == "新人断崖"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual("global", cards[0].scope)
        self.assertIn("人均产值仅¥499", cards[0].description)
        self.assertIn("为全员均值的49.9%", cards[0].description)
        self.assertIn("达标率49.9%<50%", cards[0].evidence[-1])


class SignedJustOverMeanFirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_signed_11_vs_10_with_refund_6_1_is_first_mean_fire(self):
        # mean = 10.5; 11 > 10.5 and 6.1 > 6.
        # PR #121 locked signed==mean; PR #126 locked refund 6.1
        # with signed far above mean (20 vs 10).
        self.engine._collide_signed_x_refund(
            [
                make_dept(
                    dept_name="电销四部",
                    signed_deals=11,
                    refund_rate=6.1,
                    refund_amount=8000,
                ),
                make_dept(dept_name="电销五部", signed_deals=10, refund_rate=2),
            ]
        )
        cards = [f for f in self.engine.findings if f.tag == "高签单·高退费"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual("电销四部", cards[0].dept_name)
        self.assertIn("签单11笔", cards[0].description)
        self.assertIn("退费率6.1%", cards[0].description)
        self.assertIn("过度承诺", cards[0].description)

    def test_refund_exactly_6_stays_silent_even_when_signed_just_over_mean(self):
        # Signed is already on the first-fire side (11 vs 10), but
        # refund == 6 is not > 6. PR #120 locked refund==6 with
        # signed far above mean (20 vs 10).
        self.engine._collide_signed_x_refund(
            [
                make_dept(
                    dept_name="电销四部",
                    signed_deals=11,
                    refund_rate=6,
                    refund_amount=8000,
                ),
                make_dept(dept_name="电销五部", signed_deals=10, refund_rate=2),
            ]
        )
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
