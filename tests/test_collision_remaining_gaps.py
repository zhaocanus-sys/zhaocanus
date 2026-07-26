"""Regression coverage for remaining high-risk collision engine paths.

Covers tenure×productivity, activity×quality, department variance,
trend volatility, dials×connects×revenue, LogicCollisionEngine H2/H3,
rule×exception, and multi-perspective conflicts.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.collision_engine import (
    MANAGEMENT_GAP_RULES,
    DataCollisionEngine,
    LogicCollisionEngine,
)


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "connect_rate": 45,
        "avg_connect_dur": 120,
        "deep_talk_rate": 18,
        "avg_ai_score": 72,
        "deep_talk": 40,
        "link_1d_num": 200,
        "allocated": 500,
        "avg_deal_amount": 5000,
        "conversion_rate": 2.0,
        "jx_conv_rate": 1.8,
        "jx_transfer_in": 10,
        "signed_deals": 10,
        "refund_rate": 3,
        "refund_amount": 5000,
        "total_revenue": 50000,
        "on_duty": 20,
        "dial_count": 800,
        "per_capita_revenue": 2500,
        "peak_hour_revenue": 7000,
        "offpeak_hour_revenue": 3000,
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


def make_summary(**overrides):
    summary = {
        "allocated": 8000,
        "dial_count": 20000,
        "link_1d_num": 3000,
        "deep_talk": 600,
        "signed_deals": 40,
        "on_duty": 200,
        "cr": 40,
        "dr": 16,
        "ai": 68,
        "conv": 0.8,
        "pc": 3200,
        "total_revenue": 640000,
        "ref_rate": 6,
        "complaint_count": 2,
        "alloc_rate": 0.9,
        "t20": 58,
        "roi": 180,
    }
    summary.update(overrides)
    return summary


class TenureProductivityCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_senior_burnout_when_revenue_drops_below_mature_threshold(self):
        persons = [
            # 成熟期(1-2年): avg_rev = 10000
            make_person(name="成熟甲", tenure_months=18, revenue=10000),
            make_person(name="成熟乙", tenure_months=20, revenue=10000),
            # 老员工(>2年): avg_rev = 8000 < 10000*0.85
            make_person(name="老甲", tenure_months=30, revenue=8000),
            make_person(name="老乙", tenure_months=36, revenue=8000),
        ]

        tenure_avg = self.engine._collide_tenure_x_productivity(
            make_summary(pc=9000), persons
        )

        burnout = [f for f in self.engine.findings if f.tag == "老员工倦怠"]
        self.assertEqual(1, len(burnout))
        finding = burnout[0]
        self.assertEqual("P2", finding.priority)
        self.assertEqual("global", finding.scope)
        self.assertIn("效能衰减", finding.description)
        expected_loss = round(2 * (10000 - 8000) * 0.3)
        self.assertEqual(expected_loss, finding.revenue_impact)
        self.assertIn("成熟期(1-2年)", tenure_avg)
        self.assertIn("老员工(>2年)", tenure_avg)

    def test_newbie_cliff_when_per_capita_below_half_of_overall(self):
        persons = [
            make_person(name="新人甲", tenure_months=2, revenue=1000),
            make_person(name="新人乙", tenure_months=1, revenue=1000),
            make_person(name="老人丙", tenure_months=18, revenue=5000),
        ]
        # newbie avg=1000, overall pc=4000 → ratio=25% < 50%
        summary = make_summary(pc=4000)

        self.engine._collide_tenure_x_productivity(summary, persons)

        cliffs = [f for f in self.engine.findings if f.tag == "新人断崖"]
        self.assertEqual(1, len(cliffs))
        finding = cliffs[0]
        self.assertEqual("P1", finding.priority)
        self.assertEqual("global", finding.scope)
        self.assertIn("爬坡期过长", finding.description)
        expected_loss = round(2 * (4000 * 0.7 - 1000) * 0.5)
        self.assertEqual(expected_loss, finding.revenue_impact)

    def test_healthy_tenure_curve_produces_no_finding(self):
        persons = [
            make_person(tenure_months=2, revenue=3500),
            make_person(tenure_months=8, revenue=4000),
            make_person(tenure_months=18, revenue=5000),
            make_person(tenure_months=30, revenue=4800),  # >= mature*0.85
        ]
        # newbie ratio = 3500/4000 = 87.5% >= 50%
        self.engine._collide_tenure_x_productivity(make_summary(pc=4000), persons)
        self.assertEqual([], self.engine.findings)


class ActivityQualityCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_high_dials_low_quality_attaches_quality_gap(self):
        # dials_pp=50>45; quality_conv=1; quality_ratio=2%<4
        self.engine._collide_activity_x_quality(
            [
                make_dept(
                    on_duty=10,
                    dial_count=500,
                    deep_talk=10,
                    avg_deal_amount=5000,
                )
            ]
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        payload = finding.to_dict()

        self.assertEqual("高拨打·低质量", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销六部", finding.dept_name)
        self.assertEqual("游云清", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["low_quality_ratio"],
            finding.management_gap,
        )
        self.assertEqual(round(10 * 1.5 * 5000 * 0.1), finding.revenue_impact)
        self.assertTrue(any("4%" in item for item in finding.evidence))
        self.assertEqual("游云清", payload["manager_name"])

    def test_healthy_quality_ratio_is_ignored(self):
        # dials_pp=40 <=45 → no trigger even if quality low
        # dials_pp=50 but quality_ratio=6% >=4 → no trigger
        self.engine._collide_activity_x_quality(
            [
                make_dept(on_duty=10, dial_count=400, deep_talk=5),
                make_dept(
                    dept_name="电销一部",
                    on_duty=10,
                    dial_count=500,
                    deep_talk=30,
                ),
            ]
        )
        self.assertEqual([], self.engine.findings)


class DeptVarianceCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {
            "电销一部": "何丹丹",
            "电销六部": "游云清",
        }

    def test_high_cv_emits_finding_on_worst_dept_with_manager_gap(self):
        depts = [
            make_dept(
                dept_name="电销一部",
                per_capita_revenue=10000,
                on_duty=20,
            ),
            make_dept(
                dept_name="电销六部",
                per_capita_revenue=2000,
                on_duty=20,
            ),
        ]

        pc_cv = self.engine._collide_dept_variance({}, depts)

        self.assertGreater(pc_cv, 0.35)
        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("部门间差距悬殊", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销六部", finding.dept_name)
        self.assertEqual("游云清", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["high_top20"],
            finding.management_gap,
        )
        self.assertIn("游云清", finding.description)
        mean_pc = (10000 + 2000) / 2
        expected_rev = round((mean_pc - 2000) * 20 * 0.3)
        self.assertEqual(expected_rev, finding.revenue_impact)

    def test_single_department_or_low_cv_is_silent(self):
        self.engine._collide_dept_variance(
            {},
            [make_dept(per_capita_revenue=3000)],
        )
        self.assertEqual([], self.engine.findings)

        self.engine.findings = []
        self.engine._collide_dept_variance(
            {},
            [
                make_dept(dept_name="电销一部", per_capita_revenue=3000),
                make_dept(dept_name="电销六部", per_capita_revenue=3100),
            ],
        )
        self.assertEqual([], self.engine.findings)


class TrendVolatilityCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_high_revenue_cv_emits_volatility_finding(self):
        trends = [
            {"dt": "2026-07-20", "total_revenue": 100000},
            {"dt": "2026-07-21", "total_revenue": 200000},
            {"dt": "2026-07-22", "total_revenue": 100000},
        ]

        self.engine._collide_trend_x_volatility(trends)

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("营收波动过大", finding.tag)
        self.assertEqual("P2", finding.priority)
        self.assertEqual("global", finding.scope)
        self.assertIn("系统脆弱性", finding.description)
        self.assertGreater(finding.revenue_impact, 0)
        self.assertTrue(any("CV=" in item for item in finding.evidence))

    def test_short_or_stable_trends_produce_no_finding(self):
        self.engine._collide_trend_x_volatility(
            [
                {"dt": "2026-07-20", "total_revenue": 100000},
                {"dt": "2026-07-21", "total_revenue": 101000},
            ]
        )
        self.assertEqual([], self.engine.findings)

        self.engine.findings = []
        self.engine._collide_trend_x_volatility(
            [
                {"dt": "2026-07-20", "total_revenue": 100000},
                {"dt": "2026-07-21", "total_revenue": 101000},
                {"dt": "2026-07-22", "total_revenue": 100500},
            ]
        )
        self.assertEqual([], self.engine.findings)


class DialsConnectsRevenueCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_high_activity_high_connect_low_revenue_is_p0(self):
        depts = [
            make_dept(
                dept_name="电销六部",
                on_duty=10,
                dial_count=600,  # dials_pp=60 > 50
                connect_rate=45,  # > 42
                per_capita_revenue=1500,
            ),
            make_dept(
                dept_name="电销一部",
                on_duty=10,
                dial_count=400,
                connect_rate=44,
                per_capita_revenue=4000,
            ),
        ]
        # avg_pc = 2750; 1500 < 2750*0.75=2062.5 → trigger

        self.engine._collide_dials_x_connects_x_revenue(depts)

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("高活动·高接通·低营收", finding.tag)
        self.assertEqual("P0", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销六部", finding.dept_name)
        self.assertEqual("游云清", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["high_activity_low_rev"],
            finding.management_gap,
        )
        self.assertIn("转化环节", finding.description)
        expected_rev = round((2750 - 1500) * 10 * 0.2)
        self.assertEqual(expected_rev, finding.revenue_impact)

    def test_missing_any_dimension_gate_is_ignored(self):
        depts = [
            # dials too low
            make_dept(
                on_duty=10,
                dial_count=400,
                connect_rate=45,
                per_capita_revenue=1000,
            ),
            make_dept(
                dept_name="电销一部",
                per_capita_revenue=4000,
            ),
        ]
        self.engine._collide_dials_x_connects_x_revenue(depts)
        self.assertEqual([], self.engine.findings)


class ConnectDurationCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_high_connect_short_duration_attaches_open_gap(self):
        self.engine._collide_connect_rate_x_duration(
            [
                make_dept(
                    connect_rate=45,
                    avg_connect_dur=80,
                    allocated=1000,
                    avg_deal_amount=5000,
                )
            ]
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("高接通·短通话", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("游云清", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["high_connect_low_dur"],
            finding.management_gap,
        )
        self.assertEqual(round(1000 * 0.02 * 5000), finding.revenue_impact)

    def test_low_connect_long_duration_is_p0_with_low_connect_gap(self):
        self.engine._collide_connect_rate_x_duration(
            [
                make_dept(
                    connect_rate=35,
                    avg_connect_dur=180,
                    allocated=1000,
                    conversion_rate=2.0,
                    avg_deal_amount=5000,
                )
            ]
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("低接通·长通话", finding.tag)
        self.assertEqual("P0", finding.priority)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["low_connect"],
            finding.management_gap,
        )
        expected = round(1000 * (43 - 35) / 100 * 2.0 / 100 * 5000)
        self.assertEqual(expected, finding.revenue_impact)


class LogicH2H3AndPerspectiveTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_h2_supports_when_ai_and_activity_gaps_are_large(self):
        # 10 persons → top20%=2, bottom30%=3
        persons = [
            make_person(name="T1", revenue=10000, ai_score=90, dial_count=120),
            make_person(name="T2", revenue=9000, ai_score=88, dial_count=110),
            make_person(name="M1", revenue=5000, ai_score=75, dial_count=80),
            make_person(name="M2", revenue=4500, ai_score=74, dial_count=75),
            make_person(name="M3", revenue=4000, ai_score=72, dial_count=70),
            make_person(name="M4", revenue=3500, ai_score=70, dial_count=65),
            make_person(name="M5", revenue=3000, ai_score=68, dial_count=60),
            make_person(name="B1", revenue=1000, ai_score=55, dial_count=40),
            make_person(name="B2", revenue=900, ai_score=54, dial_count=38),
            make_person(name="B3", revenue=800, ai_score=50, dial_count=35),
        ]
        # top_ai≈89, bot_ai≈53 → gap>15; top_dials≈115 > bot*1.3≈49

        self.engine._build_and_test_hypotheses(
            make_summary(t20=60, pc=4000), [], [], persons
        )

        h2 = next(h for h in self.engine.hypotheses if h["id"] == "H2")
        self.assertEqual("支持", h2["verdict"])
        self.assertTrue(h2["support_evidence"])
        self.assertIn("勤奋度", h2["alternative"])

        finding = next(f for f in self.engine.findings if "假设验证" in f.tag)
        self.assertEqual("P1", finding.priority)
        self.assertIn("支持", finding.description)

    def test_h3_supports_overpromise_when_high_refund_depts_sign_more(self):
        depts = [
            make_dept(
                dept_name="电销六部",
                refund_rate=8,
                signed_deals=20,
                avg_ai_score=78,
            ),
            make_dept(
                dept_name="电销一部",
                refund_rate=3,
                signed_deals=10,
                avg_ai_score=70,
            ),
        ]

        self.engine._build_and_test_hypotheses(
            make_summary(t20=40), depts, [], []
        )

        h3 = next(h for h in self.engine.hypotheses if h["id"] == "H3")
        self.assertEqual("支持", h3["verdict"])
        self.assertTrue(
            any("过度承诺" in e or "冲签单" in e for e in h3["support_evidence"])
        )

    def test_h3_pending_when_high_refund_does_not_outsign_or_outscore(self):
        depts = [
            make_dept(
                dept_name="电销六部",
                refund_rate=8,
                signed_deals=8,
                avg_ai_score=60,
            ),
            make_dept(
                dept_name="电销一部",
                refund_rate=3,
                signed_deals=12,
                avg_ai_score=75,
            ),
        ]

        self.engine._build_and_test_hypotheses(
            make_summary(t20=40), depts, [], []
        )

        h3 = next(h for h in self.engine.hypotheses if h["id"] == "H3")
        self.assertEqual("待定", h3["verdict"])
        self.assertTrue(h3["reject_evidence"])
        self.assertIn("客服跟进", h3["alternative"])

    def test_rule_exception_finds_high_connect_low_revenue_dept(self):
        depts = [
            make_dept(
                dept_name="电销六部",
                connect_rate=50,
                total_revenue=20000,
            ),
            make_dept(
                dept_name="电销一部",
                connect_rate=40,
                total_revenue=80000,
            ),
        ]
        # avg_cr=45, avg_rev=50000; 六部 cr>45 and rev < 50000*0.85

        self.engine._rule_exception_analysis(make_summary(), depts, [])

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("规律例外发现", finding.tag)
        self.assertEqual("P2", finding.priority)
        self.assertIn("接通率高→营收高", finding.description)
        self.assertTrue(any("电销六部" in e for e in finding.evidence))

    def test_multi_perspective_flags_roi_vs_refund_conflict(self):
        # ROI healthy + high refund → conflict
        summary = make_summary(
            roi=250,
            ref_rate=7,
            dial_count=10000,
            on_duty=100,  # dials_pp=100, not overload
            t20=40,
            complaint_count=1,
        )
        depts = [
            make_dept(dept_name="电销一部", per_capita_revenue=3000),
            make_dept(dept_name="电销六部", per_capita_revenue=3100),
        ]

        self.engine._multi_perspective_collision(summary, depts)

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("多视角矛盾", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertIn("退费率", finding.description)
        self.assertIn("ROI健康", finding.description)

    def test_multi_perspective_flags_overload_with_low_roi(self):
        summary = make_summary(
            roi=150,  # low
            dial_count=20000,
            on_duty=100,  # dials_pp=200 > 180
            ref_rate=3,
            t20=40,
            complaint_count=1,
        )
        depts = [
            make_dept(per_capita_revenue=3000),
            make_dept(dept_name="电销一部", per_capita_revenue=3000),
        ]

        self.engine._multi_perspective_collision(summary, depts)

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("多视角矛盾", finding.tag)
        self.assertIn("效率有问题", finding.description)


if __name__ == "__main__":
    unittest.main()
