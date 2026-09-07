"""Regression coverage for leftover 接通×时长 boundary operators.

PR #78 locked fire formulas. PR #120 locked dur==100 silence
(高接通·短通话 needs <100) and cr==40 silence (低接通·长通话
needs <40). The remaining operators were never the primary lock:

- cr == 43 with dur<100 FIRES 高接通·短通话 (operator is >= 43)
- cr == 42.9 with dur<100 stays silent
- dur == 150 with cr<40 stays silent (低接通 needs > 150)

Flipping `>= 43` to `>` would hide a department sitting on the
接通红线 with a short open. Flipping `> 150` to `>=` would emit a
false P0 低接通·长通话 the day duration sits on 150s.

Does not retest PR #78 impact formulas or PR #120 dur==100 / cr==40
as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "connect_rate": 45,
        "avg_connect_dur": 120,
        "allocated": 500,
        "avg_deal_amount": 5000,
        "conversion_rate": 2.0,
    }
    dept.update(overrides)
    return dept


class ConnectDurationLeftoverBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_connect_exactly_43_with_short_talk_fires(self):
        # >= 43 is the leftover fire edge. dur=99 is already <100.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=43, avg_connect_dur=99)]
        )
        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("高接通·短通话", finding.tag)
        self.assertEqual("P1", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销六部", finding.dept_name)
        self.assertTrue(any("接通率43%≥43%" in e for e in finding.evidence))

    def test_connect_just_under_43_with_short_talk_is_silent(self):
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=42.9, avg_connect_dur=99)]
        )
        self.assertEqual([], self.engine.findings)

    def test_duration_exactly_150_with_low_connect_is_silent(self):
        # cr=39 is already <40 (the other leftover fire). dur==150
        # must stay silent; trigger is > 150.
        self.engine._collide_connect_rate_x_duration(
            [make_dept(connect_rate=39, avg_connect_dur=150)]
        )
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
