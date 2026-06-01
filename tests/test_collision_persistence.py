import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


def _dept(name, connect_rate):
    return {
        "dept_name": name,
        "connect_rate": connect_rate,
        "allocated": 1000,
        "avg_deal_amount": 5000,
    }


class CollisionPersistenceTests(unittest.TestCase):
    def test_dept_specific_seven_day_low_connect_escalates_with_manager_gap(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        trends = [
            {
                "dt": f"2026-02-{day:02d}",
                "dept_trends": [
                    {"dept_name": "电销六部", "connect_rate": 39},
                    {"dept_name": "电销四部", "connect_rate": 48},
                ],
            }
            for day in range(20, 30)
        ]

        engine._collide_persistence_detection(
            [_dept("电销六部", 39), _dept("电销四部", 39)],
            trends,
        )

        findings = [f for f in engine.findings if f.tag == "持续不达标预警"]
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.priority, "P0")
        self.assertEqual(finding.scope, "dept")
        self.assertEqual(finding.dept_name, "电销六部")
        self.assertEqual(finding.manager_name, "游云清")
        self.assertIn("执行力", finding.management_gap)

    def test_six_days_below_redline_does_not_escalate_to_penalty(self):
        engine = DataCollisionEngine()
        trends = [
            {
                "dt": f"2026-02-{day:02d}",
                "dept_trends": [{"dept_name": "电销六部", "cr": 39 if idx < 6 else 45}],
            }
            for idx, day in enumerate(range(20, 30))
        ]

        engine._collide_persistence_detection([_dept("电销六部", 39)], trends)

        self.assertEqual(
            [f for f in engine.findings if f.tag == "持续不达标预警"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
