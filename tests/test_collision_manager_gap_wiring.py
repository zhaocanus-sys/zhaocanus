# -*- coding: utf-8 -*-
"""Regression coverage for CollisionFinding manager/gap wiring.

Open PR #78 locks to_dict() on a hand-built finding. This file goes
through DataCollisionEngine._add_finding so a later change cannot attach
management_gap without a mapped manager, or leak those fields on the
serialized global/unknown-dept path that reports actually consume.
"""
import unittest

from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    MANAGEMENT_GAP_RULES,
)


def _add(engine, *, dept_name="", gap_key="", scope="dept"):
    engine._add_finding(
        "metric_x_metric",
        "高接通·短通话",
        "fixture",
        1000,
        "P1",
        scope=scope,
        dept_name=dept_name,
        gap_key=gap_key,
    )
    return engine.findings[-1]


class CollisionManagerGapWiringTests(unittest.TestCase):
    def test_mapped_manager_attaches_named_gap(self):
        eng = DataCollisionEngine()
        eng.dept_managers = {"电销六部": "吴胜悍"}
        finding = _add(
            eng, dept_name="电销六部", gap_key="high_connect_low_dur"
        )
        payload = finding.to_dict()
        self.assertEqual(finding.manager_name, "吴胜悍")
        self.assertEqual(
            finding.management_gap,
            MANAGEMENT_GAP_RULES["high_connect_low_dur"],
        )
        self.assertEqual(payload["manager_name"], "吴胜悍")
        self.assertEqual(
            payload["management_gap"],
            MANAGEMENT_GAP_RULES["high_connect_low_dur"],
        )
        self.assertIn("开场白", payload["management_gap"])

    def test_unknown_dept_suppresses_manager_and_gap_in_to_dict(self):
        eng = DataCollisionEngine()
        eng.dept_managers = {"电销一部": "罗阳"}
        finding = _add(
            eng, dept_name="电销六部", gap_key="high_connect_low_dur"
        )
        self.assertEqual(finding.manager_name, "")
        self.assertEqual(finding.management_gap, "")
        payload = finding.to_dict()
        self.assertNotIn("manager_name", payload)
        self.assertNotIn("management_gap", payload)

    def test_empty_managers_map_never_leaks_gap(self):
        eng = DataCollisionEngine()
        eng.dept_managers = {}
        finding = _add(
            eng, dept_name="电销六部", gap_key="low_connect"
        )
        self.assertEqual(finding.management_gap, "")
        self.assertNotIn("management_gap", finding.to_dict())
        self.assertNotIn("manager_name", finding.to_dict())

    def test_global_scope_ignores_gap_key_even_when_managers_exist(self):
        eng = DataCollisionEngine()
        eng.dept_managers = {"电销六部": "吴胜悍"}
        finding = _add(
            eng, dept_name="", gap_key="high_top20", scope="global"
        )
        self.assertEqual(finding.scope, "global")
        self.assertEqual(finding.manager_name, "")
        self.assertEqual(finding.management_gap, "")
        payload = finding.to_dict()
        self.assertNotIn("manager_name", payload)
        self.assertNotIn("management_gap", payload)

    def test_blank_gap_key_keeps_manager_but_no_inference(self):
        eng = DataCollisionEngine()
        eng.dept_managers = {"电销六部": "吴胜悍"}
        finding = _add(eng, dept_name="电销六部", gap_key="")
        payload = finding.to_dict()
        self.assertEqual(payload["manager_name"], "吴胜悍")
        self.assertEqual(payload["management_gap"], "")
        self.assertNotIn("开场白", payload["management_gap"])
        self.assertNotIn("号码健康度", payload["management_gap"])


if __name__ == "__main__":
    unittest.main()
