"""Regression coverage for leftover DataCollision just-over first fire.

PR #78/#79/#80 locked far-from-threshold fire and healthy silence.
PR #120 locked exact-threshold silence:

- peak_ratio == 0.72
- refund_rate == 6 even when signed > mean
- jx_transfer_in == 30
- new_avg_ai == all * 0.8
- avg_connect_dur == 100 / connect_rate == 40
- dials_pp == 45 / quality_ratio == 4

The first tick *over* those operators was never the primary lock.
A flipped `>` to `>=` (or `<` to `<=`) would keep those exact-silence
tests green while swallowing the first real 时段失衡 / 建信折损 /
开场白 / 刷量 card.

Does not retest PR #120 equalities or PR #78/#79/#80 far fire as primary.
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


def _tags(engine):
    return {f.tag for f in engine.findings}


class CollisionJustOverFirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_peak_ratio_just_over_072_is_first_imbalance_fire(self):
        # 7210 / 10000 == 0.721; PR #120 locked == 0.72 as silent.
        self.engine._collide_peak_x_offpeak(
            [make_dept(peak_hour_revenue=7210, offpeak_hour_revenue=2790)]
        )
        cards = [f for f in self.engine.findings if f.tag == "时段失衡"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertIn("高峰时段", cards[0].description)

    def test_refund_just_over_6_with_above_mean_signed_is_first_fire(self):
        self.engine._collide_signed_x_refund(
            [
                make_dept(
                    dept_name="电销四部",
                    signed_deals=20,
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
        self.assertIn("退费率6.1%", cards[0].description)
        self.assertIn("过度承诺", cards[0].description)

    def test_jx_transfer_31_is_first_trust_loss_fire(self):
        # 1.0 < 2.0 * 0.6 and 31 > 30. PR #120 locked transfer == 30.
        self.engine._collide_jx_x_own_conversion(
            [
                make_dept(
                    conversion_rate=2.0,
                    jx_conv_rate=1.0,
                    jx_transfer_in=31,
                )
            ]
        )
        cards = [f for f in self.engine.findings if f.tag == "建信→电销信任折损"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("建信资源转化仅1.0%", cards[0].description)
        self.assertIn("日转入31条", cards[0].evidence[-1])

    def test_new_hire_ai_just_under_80pct_is_first_gap_fire(self):
        # new=63, veteran=96 → all=79.5, 79.5*0.8=63.6; 63 < 63.6.
        # PR #120 locked 64 vs 96 (exactly 80%).
        self.engine._collide_new_hire_x_overall(
            {},
            [
                make_person(name="新人", tenure_months=2, ai_score=63),
                make_person(name="老人", tenure_months=12, ai_score=96),
            ],
        )
        cards = [f for f in self.engine.findings if f.tag == "新人AI评分断层"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("新人(≤3月)AI均分63.0", cards[0].description)
        self.assertIn("话术技能传承不足", cards[0].description)

    def test_connect_duration_99s_is_first_short_talk_fire(self):
        # cr >= 43 and dur < 100. PR #120 locked dur == 100.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=45, avg_connect_dur=99)]
        )
        cards = [f for f in self.engine.findings if f.tag == "高接通·短通话"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("均接通时长仅99s", cards[0].description)
        self.assertNotIn("低接通·长通话", _tags(self.engine))

    def test_connect_rate_39_9_is_first_low_connect_fire(self):
        # cr < 40 and dur > 150. PR #120 locked cr == 40.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=39.9, avg_connect_dur=180)]
        )
        cards = [f for f in self.engine.findings if f.tag == "低接通·长通话"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P0", cards[0].priority)
        self.assertIn("接通率仅39.9%", cards[0].description)
        self.assertIn("均时长180s", cards[0].description)
        self.assertNotIn("高接通·短通话", _tags(self.engine))

    def test_activity_just_over_45_dials_and_under_4_quality_is_first_fire(self):
        # 451/10 == 45.1 > 45; quality_ratio = 0.5/45.1*100 ≈ 1.1 < 4.
        self.engine._collide_activity_x_quality(
            [make_dept(on_duty=10, dial_count=451, deep_talk=5)]
        )
        cards = [f for f in self.engine.findings if f.tag == "高拨打·低质量"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("刷量", cards[0].description)
        self.assertIn("质量会话占比1.1%<4%", cards[0].evidence[-1])


if __name__ == "__main__":
    unittest.main()
