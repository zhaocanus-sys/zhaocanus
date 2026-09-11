"""Regression coverage for leftover DataCollision just-over first fire.

PR #78/#79/#80 locked far-from-threshold fire.
PR #121 locked exact-threshold silence:

- dials_pp == 50 / cr == 42 / pc == mean*0.75 (need all three strict)
- deep_talk_rate == 20 / avg_ai_score == 68
- deep_talk_rate == 15 / avg_ai_score == 75
- dept CV == 0.35 / trend CV == 0.15
- senior avg_rev == mature * 0.85

The first tick *over* those operators was never the primary lock.
Flipping any `>`/`<` would keep the exact-silence suite green while
hiding the first 高活动低转化 / 闲聊 / 部门CV / 老员工倦怠 card.

Does not retest PR #121 equalities or PR #120 peak/refund/jx/connect
equalities as primary.
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


class DialsConnectsRevenueJustOverTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_three_gates_just_over_is_first_low_rev_fire(self):
        # 510/10 == 51 > 50; cr 42.1 > 42; 1000 < mean*0.75 (4125).
        self.engine._collide_dials_x_connects_x_revenue(
            [
                make_dept(
                    dept_name="电销六部",
                    on_duty=10,
                    dial_count=510,
                    connect_rate=42.1,
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
        cards = [f for f in self.engine.findings if f.tag == "高活动·高接通·低营收"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P0", cards[0].priority)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertIn("转化环节", cards[0].description)
        self.assertIn("接通率42.1%>42%", cards[0].evidence[1])


class DeepTalkJustOverTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_high_deep_20_1_and_ai_67_9_is_first_idle_chat_fire(self):
        # PR #121 locked dr==20 / ai==68 as silent even when the other
        # leg would fire. Both just-over is the first 高深沟·低AI card.
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=20.1, avg_ai_score=67.9, deep_talk=40)]
        )
        cards = [f for f in self.engine.findings if f.tag == "高深沟·低AI"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("深沟率20.1%", cards[0].description)
        self.assertIn("AI均分仅67.9", cards[0].description)
        self.assertIn("闲聊", cards[0].description)

    def test_low_deep_14_9_and_ai_75_1_is_first_cherry_pick_fire(self):
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=14.9, avg_ai_score=75.1, link_1d_num=200)]
        )
        cards = [f for f in self.engine.findings if f.tag == "低深沟·高AI"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertIn("AI均分75.1", cards[0].description)
        self.assertIn("深沟率仅14.9%", cards[0].description)
        self.assertIn("挑客", cards[0].description)


class VarianceTrendTenureJustOverTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_dept_cv_036_is_first_variance_fire(self):
        # 125.2 / 74.8 → sample CV rounds to 0.36. PR #121 locked 125/75 == 0.35.
        # Keep both pcs > 0 so we do not lock the pc==0 ZeroDivisionError.
        self.engine._collide_dept_variance(
            {},
            [
                make_dept(dept_name="电销一部", per_capita_revenue=125.2, on_duty=10),
                make_dept(dept_name="电销六部", per_capita_revenue=74.8, on_duty=10),
            ],
        )
        cards = [f for f in self.engine.findings if f.tag == "部门间差距悬殊"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertIn("CV=0.36", cards[0].description)
        self.assertIn("CV变异系数=0.36>0.35", cards[0].evidence[0])

    def test_trend_cv_016_is_first_volatility_fire(self):
        # 840/1000/1160 → CV=0.16. PR #121 locked 850/1000/1150 == 0.15.
        self.engine._collide_trend_x_volatility(
            [
                {"dt": "20260901", "total_revenue": 840},
                {"dt": "20260902", "total_revenue": 1000},
                {"dt": "20260903", "total_revenue": 1160},
            ]
        )
        cards = [f for f in self.engine.findings if f.tag == "营收波动过大"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertEqual("global", cards[0].scope)
        self.assertIn("7日营收CV=0.16", cards[0].description)

    def test_senior_rev_just_under_85pct_is_first_burnout_fire(self):
        # 849 < 1000 * 0.85. PR #121 locked 850 == 85%.
        self.engine._collide_tenure_x_productivity(
            {"pc": 2000},
            [
                make_person(name="成熟", tenure_months=18, revenue=1000),
                make_person(name="老人", tenure_months=30, revenue=849),
            ],
        )
        cards = [f for f in self.engine.findings if f.tag == "老员工倦怠"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertIn("效能衰减曲线", cards[0].description)
        self.assertIn("老员工均产¥849", cards[0].evidence[0])


if __name__ == "__main__":
    unittest.main()
