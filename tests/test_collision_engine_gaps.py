"""Regression coverage for previously untested collision engine paths.

Covers peak/off-peak imbalance, Jianxin trust transfer, funnel bottleneck
selection, new-hire AI cliff, and LogicCollisionEngine hypothesis/causal
chain verdicts. Deterministic stdlib unittest only — no network/DB.
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
        "peak_hour_revenue": 7000,
        "offpeak_hour_revenue": 3000,
        "conversion_rate": 2.0,
        "jx_conv_rate": 1.8,
        "jx_transfer_in": 10,
        "avg_deal_amount": 5000,
        "connect_rate": 45,
        "signed_deals": 10,
        "refund_rate": 3,
        "avg_ai_score": 72,
        "total_revenue": 50000,
        "on_duty": 20,
        "dial_count": 1000,
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
    }
    summary.update(overrides)
    return summary


class PeakOffpeakCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "罗阳"}

    def test_peak_heavy_revenue_attaches_imbalance_gap(self):
        # 8000/(8000+2000)=0.8 > 0.72
        self.engine._collide_peak_x_offpeak(
            [
                make_dept(
                    peak_hour_revenue=8000,
                    offpeak_hour_revenue=2000,
                )
            ]
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        payload = finding.to_dict()

        self.assertEqual("时段失衡", finding.tag)
        self.assertEqual("P2", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销六部", finding.dept_name)
        self.assertEqual("罗阳", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["peak_imbalance"],
            finding.management_gap,
        )
        self.assertEqual(round(2000 * 0.3), finding.revenue_impact)
        self.assertTrue(any("72%" in item for item in finding.evidence))
        self.assertEqual("罗阳", payload["manager_name"])
        self.assertEqual(finding.management_gap, payload["management_gap"])

    def test_balanced_or_zero_revenue_produces_no_finding(self):
        self.engine._collide_peak_x_offpeak(
            [
                make_dept(peak_hour_revenue=6000, offpeak_hour_revenue=4000),
                make_dept(
                    dept_name="电销七部",
                    peak_hour_revenue=0,
                    offpeak_hour_revenue=0,
                ),
            ]
        )

        self.assertEqual([], self.engine.findings)


class JianxinConversionCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "罗阳"}

    def test_low_jx_conversion_with_volume_emits_trust_loss_finding(self):
        # jx 1.0 < own 2.0 * 0.6, transfer 40 > 30
        self.engine._collide_jx_x_own_conversion(
            [
                make_dept(
                    conversion_rate=2.0,
                    jx_conv_rate=1.0,
                    jx_transfer_in=40,
                    avg_deal_amount=5000,
                )
            ]
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]

        self.assertEqual("建信→电销信任折损", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("罗阳", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["jx_low_conv"],
            finding.management_gap,
        )
        expected_rev = round(40 * (2.0 - 1.0) / 100 * 5000)
        self.assertEqual(expected_rev, finding.revenue_impact)
        self.assertIn("信任传递", finding.description)

    def test_low_transfer_volume_or_healthy_jx_rate_is_ignored(self):
        self.engine._collide_jx_x_own_conversion(
            [
                # rate gap exists but volume too small
                make_dept(
                    conversion_rate=2.0,
                    jx_conv_rate=1.0,
                    jx_transfer_in=20,
                ),
                # volume enough but jx rate healthy (>= 60% of own)
                make_dept(
                    dept_name="电销七部",
                    conversion_rate=2.0,
                    jx_conv_rate=1.3,
                    jx_transfer_in=50,
                ),
            ]
        )

        self.assertEqual([], self.engine.findings)


class FunnelBenchmarkCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_selects_weakest_stage_by_rate_over_threshold(self):
        # dial/alloc=3.0/3.0=1.0; connect=15/15=1.0;
        # deep=10/20=0.5 (weakest); signed≈44.4/10=4.44
        summary = {
            "allocated": 1000,
            "dial_count": 3000,
            "link_1d_num": 450,
            "deep_talk": 45,
            "signed_deals": 20,
        }

        funnel = self.engine._collide_funnel_x_benchmark(summary)

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("漏斗瓶颈", finding.tag)
        self.assertEqual("P0", finding.priority)
        self.assertEqual("global", finding.scope)
        self.assertIn("接通→深沟", finding.description)
        self.assertEqual(0, finding.revenue_impact)
        self.assertEqual(4, len(funnel))
        worst = min(funnel, key=lambda x: x[1] / (x[2] or 1))
        self.assertEqual("接通→深沟", worst[0])

    def test_zero_denominators_still_emit_global_bottleneck(self):
        # All zeros → each stage uses `or 1` safe divisor; still emits one P0.
        self.engine._collide_funnel_x_benchmark(
            {
                "allocated": 0,
                "dial_count": 0,
                "link_1d_num": 0,
                "deep_talk": 0,
                "signed_deals": 0,
            }
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("漏斗瓶颈", finding.tag)
        self.assertEqual("P0", finding.priority)
        self.assertEqual("global", finding.scope)


class NewHireCliffCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_new_hire_ai_cliff_emits_p1_with_revenue_impact(self):
        persons = [
            make_person(name="新人甲", tenure_months=2, ai_score=50),
            make_person(name="新人乙", tenure_months=1, ai_score=54),
            make_person(name="老人丙", tenure_months=18, ai_score=80),
            make_person(name="老人丁", tenure_months=24, ai_score=84),
        ]
        # new avg = 52, all avg = 67, 52 < 67*0.8=53.6 → cliff

        self.engine._collide_new_hire_x_overall({}, persons)

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("新人AI评分断层", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("global", finding.scope)
        self.assertIn("新人", finding.description)
        expected_gap = round(67.0 - 52.0, 1)
        self.assertEqual(round(2 * expected_gap * 50), finding.revenue_impact)

    def test_no_new_hires_or_healthy_scores_produce_no_finding(self):
        veterans_only = [
            make_person(tenure_months=10, ai_score=70),
            make_person(tenure_months=14, ai_score=72),
        ]
        self.engine._collide_new_hire_x_overall({}, veterans_only)
        self.assertEqual([], self.engine.findings)

        healthy = [
            make_person(tenure_months=2, ai_score=70),
            make_person(tenure_months=12, ai_score=75),
        ]
        self.engine._collide_new_hire_x_overall({}, healthy)
        self.assertEqual([], self.engine.findings)


class LogicHypothesisAndCausalTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_h1_rejects_connect_rate_driver_when_allocation_moves(self):
        trends = [
            {
                "total_revenue": 100000,
                "cr": 45.0,
                "conv": 1.0,
                "pc": 3000,
                "allocated": 1000,
            },
            {
                "total_revenue": 120000,
                "cr": 45.5,  # |Δcr|=0.5 <= 1.5 → reject evidence
                "conv": 1.1,
                "pc": 3200,
                "allocated": 1200,  # |Δalloc|=200 > 50 → reject evidence
            },
        ]

        self.engine._build_and_test_hypotheses(
            make_summary(t20=40), [], trends, []
        )

        h1 = next(h for h in self.engine.hypotheses if h["id"] == "H1")
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("分配量变化", h1["alternative"])
        self.assertGreater(len(h1["reject_evidence"]), len(h1["support_evidence"]))

    def test_h1_supports_connect_rate_driver_on_large_cr_swing(self):
        trends = [
            {
                "total_revenue": 100000,
                "cr": 40.0,
                "conv": 1.0,
                "pc": 3000,
                "allocated": 1000,
            },
            {
                "total_revenue": 80000,
                "cr": 36.0,  # |Δcr|=4 > 1.5 → support
                "conv": 0.95,
                "pc": 2800,
                "allocated": 1010,  # small alloc change
            },
        ]

        self.engine._build_and_test_hypotheses(
            make_summary(t20=40), [], trends, []
        )

        h1 = next(h for h in self.engine.hypotheses if h["id"] == "H1")
        self.assertEqual("支持", h1["verdict"])
        self.assertTrue(any("接通率变动" in e for e in h1["support_evidence"]))

    def test_causal_chain_marks_upstream_bottleneck_and_reverse_trace(self):
        summary = make_summary(
            cr=40,  # warning
            dr=16,  # warning
            ai=68,  # warning
            conv=0.8,  # warning
            pc=3200,  # < 4000 → reverse chain
            ref_rate=6,  # warning
            t20=58,
        )

        self.engine._build_causal_chains(summary, [], [])

        self.assertGreaterEqual(len(self.engine.causal_chains), 2)
        forward = self.engine.causal_chains[0]
        self.assertEqual("营收因果链", forward["name"])
        self.assertEqual("触达效率", forward["bottleneck"])
        self.assertIn("触达效率", forward["diagnosis"])

        reverse = next(
            c for c in self.engine.causal_chains if c["direction"] == "反向"
        )
        self.assertTrue(reverse["possible_causes"])
        self.assertEqual("正反向因果链一致", reverse["consistency_check"])

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("因果链追溯", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertIn("人均产值", finding.description)
        self.assertTrue(any("接通率" in e for e in finding.evidence))


if __name__ == "__main__":
    unittest.main()
