import unittest

from agent_system.engines.collision_engine import (
    MANAGEMENT_GAP_RULES,
    CollisionFinding,
    CrossDomainCollisionEngine,
    DataCollisionEngine,
)


def make_dept(**overrides):
    dept = {
        "dept_name": "电销四部",
        "deep_talk_rate": 18,
        "avg_ai_score": 70,
        "deep_talk": 40,
        "link_1d_num": 200,
        "avg_deal_amount": 5000,
        "signed_deals": 10,
        "refund_rate": 3,
        "refund_amount": 1000,
    }
    dept.update(overrides)
    return dept


class DeepTalkAiCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销四部": "宋晓鹏"}

    def test_high_deep_low_ai_attaches_manager_and_structured_gap(self):
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=22, avg_ai_score=65, deep_talk=50)]
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        payload = finding.to_dict()

        self.assertEqual("高深沟·低AI", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销四部", finding.dept_name)
        self.assertEqual("宋晓鹏", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["high_deep_low_ai"],
            finding.management_gap,
        )
        self.assertIn("话术结构化", finding.management_gap)
        self.assertEqual(round(50 * 0.05 * 5000), finding.revenue_impact)
        self.assertEqual("宋晓鹏", payload["manager_name"])
        self.assertEqual(finding.management_gap, payload["management_gap"])

    def test_low_deep_high_ai_emits_p2_pickiness_finding(self):
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=12, avg_ai_score=80, link_1d_num=100)]
        )

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]

        self.assertEqual("低深沟·高AI", finding.tag)
        self.assertEqual("P2", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("宋晓鹏", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["low_deep_high_ai"],
            finding.management_gap,
        )
        self.assertIn("挑客", finding.management_gap)
        self.assertEqual(round(100 * 0.05 * 0.08 * 5000), finding.revenue_impact)

    def test_balanced_deep_talk_and_ai_produces_no_finding(self):
        self.engine._collide_deep_talk_x_ai_score(
            [make_dept(deep_talk_rate=18, avg_ai_score=72)]
        )

        self.assertEqual([], self.engine.findings)


class SignedRefundCollisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {
            "电销四部": "宋晓鹏",
            "电销五部": "吴胜悍",
        }

    def test_high_signed_high_refund_attaches_compliance_gap(self):
        depts = [
            make_dept(
                dept_name="电销四部",
                signed_deals=20,
                refund_rate=7.5,
                refund_amount=8000,
            ),
            make_dept(
                dept_name="电销五部",
                signed_deals=8,
                refund_rate=2,
                refund_amount=500,
            ),
        ]

        self.engine._collide_signed_x_refund(depts)

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        payload = finding.to_dict()

        self.assertEqual("高签单·高退费", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销四部", finding.dept_name)
        self.assertEqual("宋晓鹏", finding.manager_name)
        self.assertEqual(
            MANAGEMENT_GAP_RULES["high_refund"],
            finding.management_gap,
        )
        self.assertIn("签单话术合规", finding.management_gap)
        self.assertEqual(4000, finding.revenue_impact)
        self.assertIn("过度承诺", finding.description)
        self.assertTrue(any("退费率" in item for item in finding.evidence))
        self.assertEqual("宋晓鹏", payload["manager_name"])

    def test_high_refund_below_average_signed_is_ignored(self):
        depts = [
            make_dept(
                dept_name="电销四部",
                signed_deals=6,
                refund_rate=9,
                refund_amount=3000,
            ),
            make_dept(
                dept_name="电销五部",
                signed_deals=12,
                refund_rate=2,
                refund_amount=400,
            ),
        ]

        self.engine._collide_signed_x_refund(depts)

        self.assertEqual([], self.engine.findings)

    def test_missing_manager_suppresses_management_gap_text(self):
        self.engine.dept_managers = {}
        depts = [
            make_dept(signed_deals=18, refund_rate=8, refund_amount=5000),
            make_dept(
                dept_name="电销五部",
                signed_deals=8,
                refund_rate=2,
                refund_amount=400,
            ),
        ]

        self.engine._collide_signed_x_refund(depts)

        finding = self.engine.findings[0]
        payload = finding.to_dict()
        self.assertEqual("电销四部", finding.dept_name)
        self.assertEqual("", finding.manager_name)
        self.assertEqual("", finding.management_gap)
        self.assertNotIn("manager_name", payload)
        self.assertNotIn("management_gap", payload)


class CrossDomainRefundEnrichmentTests(unittest.TestCase):
    def test_refund_data_finding_triggers_psychology_super_collision(self):
        engine = CrossDomainCollisionEngine()
        engine.findings = []
        data_findings = [
            CollisionFinding(
                collision_type="metric_x_metric",
                tag="高签单·高退费",
                description="电销四部高签单伴随高退费",
                revenue_impact=4000,
                priority="P1",
            )
        ]

        engine._enrich_from_data_findings(data_findings, {})

        self.assertEqual(1, len(engine.findings))
        finding = engine.findings[0]
        self.assertEqual("cross_domain:super_collision", finding.collision_type)
        self.assertIn("退费风险", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertTrue(any("48h" in rec for rec in finding.recommendations))
        self.assertIn("超级对撞", engine.domains_used)


if __name__ == "__main__":
    unittest.main()
