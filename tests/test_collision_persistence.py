import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


def make_dept(name, connect_rate):
    return {
        "dept_name": name,
        "connect_rate": connect_rate,
        "allocated": 1000,
        "avg_deal_amount": 2000,
    }


def make_trend(day_rates_by_dept, global_cr=60):
    return {
        "cr": global_cr,
        "dept_trends": [
            {"dept_name": dept_name, "connect_rate": rate}
            for dept_name, rate in day_rates_by_dept.items()
        ],
    }


class PersistenceDetectionTest(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {
            "电销一部": "何丹丹",
            "电销二部": "赵梅",
        }

    def test_requires_seven_days_before_p0_escalation(self):
        trends = [{"cr": 38} for _ in range(6)]

        self.engine._collide_persistence_detection(
            [make_dept("电销一部", 38)],
            trends,
        )

        self.assertEqual([], self.engine.findings)

    def test_uses_department_trends_instead_of_global_rate(self):
        trends = [
            make_trend({"电销一部": 39, "电销二部": 48}, global_cr=60)
            for _ in range(7)
        ]
        depts = [
            make_dept("电销一部", 39),
            make_dept("电销二部", 39),
        ]

        self.engine._collide_persistence_detection(depts, trends)

        self.assertEqual(1, len(self.engine.findings))
        self.assertEqual("电销一部", self.engine.findings[0].dept_name)

    def test_finding_includes_manager_gap_and_escalation_actions(self):
        trends = [
            make_trend({"电销一部": 38}, global_cr=62)
            for _ in range(7)
        ]

        self.engine._collide_persistence_detection(
            [make_dept("电销一部", 38)],
            trends,
        )

        finding = self.engine.findings[0]
        finding_dict = finding.to_dict()
        self.assertEqual("P0", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("何丹丹", finding.manager_name)
        self.assertIn("执行力", finding.management_gap)
        self.assertEqual("何丹丹", finding_dict["manager_name"])
        self.assertIn("绩效分数扣减5分/日", "\n".join(finding.recommendations))
        self.assertIn("书面改善计划", "\n".join(finding.recommendations))


if __name__ == "__main__":
    unittest.main()
