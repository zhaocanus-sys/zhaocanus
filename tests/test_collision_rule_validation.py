"""Regression coverage for collision rule gates and correlation edges.

Covers:
- DataCollisionEngine._validate_rules emits count/type coverage findings
- LogicCollisionEngine._validate_rules emits hypothesis-count findings
- LogicCollisionEngine._check_correlation short / zero-variance / signed cases

Deterministic stdlib unittest; no network required.
"""

from __future__ import annotations

import unittest

from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    LogicCollisionEngine,
)


class CollisionRuleValidationTests(unittest.TestCase):
    def test_data_engine_validate_rules_flags_insufficient_count_and_types(self):
        engine = DataCollisionEngine()
        engine.findings = []
        engine.collision_count = 2
        engine.collision_types_used = {"metric_x_metric"}

        engine._validate_rules()

        tags = {f.tag for f in engine.findings}
        self.assertIn("对撞数量不足", tags)
        self.assertIn("对撞类型覆盖不足", tags)
        for finding in engine.findings:
            self.assertEqual(finding.priority, "P2")
            self.assertEqual(finding.collision_type, "rule_validation")
            self.assertEqual(finding.revenue_impact, 0)

    def test_data_engine_validate_rules_silent_when_minimums_met(self):
        engine = DataCollisionEngine()
        engine.findings = []
        engine.collision_count = 5
        engine.collision_types_used = {
            "metric_x_metric",
            "metric_x_time",
            "funnel_x_benchmark",
        }

        engine._validate_rules()
        self.assertEqual(engine.findings, [])

    def test_logic_engine_validate_rules_flags_insufficient_hypotheses(self):
        engine = LogicCollisionEngine()
        engine.findings = []
        engine.hypotheses = [{"id": "H1"}, {"id": "H2"}]

        engine._validate_rules()

        self.assertEqual(len(engine.findings), 1)
        finding = engine.findings[0]
        self.assertEqual(finding.tag, "假设数量不足")
        self.assertEqual(finding.priority, "P2")
        self.assertIn("2个假设", finding.description)

    def test_logic_engine_validate_rules_silent_with_three_hypotheses(self):
        engine = LogicCollisionEngine()
        engine.findings = []
        engine.hypotheses = [{"id": "H1"}, {"id": "H2"}, {"id": "H3"}]

        engine._validate_rules()
        self.assertEqual(engine.findings, [])

    def test_check_correlation_edges(self):
        engine = LogicCollisionEngine()

        self.assertEqual(engine._check_correlation([1, 2], [3, 4]), 0)
        self.assertEqual(engine._check_correlation([5, 5, 5], [1, 2, 3]), 0)
        self.assertEqual(engine._check_correlation([1, 2, 3], [10, 10, 10]), 0)
        self.assertEqual(engine._check_correlation([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertEqual(engine._check_correlation([1, 2, 3], [6, 4, 2]), -1.0)


if __name__ == "__main__":
    unittest.main()
