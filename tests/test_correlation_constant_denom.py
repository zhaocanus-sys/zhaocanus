"""Regression coverage for leftover constant-series correlation guard.

`_check_correlation` is called on every logic-collision run from
`_rule_exception_analysis`. When every department shares the same
connect_rate (common on a 贴线 45% day) x_var==0, denom==0.

The leftover guard was never the primary lock:

- constant X or constant Y returns 0 (no ZeroDivisionError)
- n<3 returns 0 without touching denom
- `_rule_exception_analysis` with 3 equal-CR depts completes
  and stays silent (no CR > mean)
- non-constant perfect positive still returns 1.0

Does not retest PR #80/#112 规律例外 fire / 0.85 silence as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_dept(**overrides):
    dept = {
        "dept_name": "电销一部",
        "connect_rate": 45,
        "total_revenue": 50000,
    }
    dept.update(overrides)
    return dept


class CheckCorrelationConstantDenomTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_constant_x_returns_zero_not_crash(self):
        self.assertEqual(0, self.engine._check_correlation([45, 45, 45], [10, 20, 30]))

    def test_constant_y_returns_zero_not_crash(self):
        self.assertEqual(0, self.engine._check_correlation([40, 45, 50], [100, 100, 100]))

    def test_n_less_than_3_returns_zero(self):
        self.assertEqual(0, self.engine._check_correlation([1, 2], [3, 4]))
        self.assertEqual(0, self.engine._check_correlation([], []))

    def test_perfect_positive_returns_one(self):
        self.assertEqual(1.0, self.engine._check_correlation([1, 2, 3], [2, 4, 6]))


class RuleExceptionConstantCrNoCrashTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_three_equal_cr_depts_do_not_crash_or_emit(self):
        # All CR==45 → x_var==0 hits the denom guard. No department
        # is above mean CR, so 规律例外 stays silent. Without
        # `if denom else 0` this path raises ZeroDivisionError on
        # every healthy same-connect-rate day.
        self.engine._rule_exception_analysis(
            {},
            [
                make_dept(dept_name="电销一部", connect_rate=45, total_revenue=80000),
                make_dept(dept_name="电销四部", connect_rate=45, total_revenue=50000),
                make_dept(dept_name="电销六部", connect_rate=45, total_revenue=20000),
            ],
            [],
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "规律例外发现"],
        )


if __name__ == "__main__":
    unittest.main()
