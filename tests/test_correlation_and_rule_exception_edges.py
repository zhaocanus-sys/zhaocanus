"""Regression coverage for leftover correlation + 规律例外 edges.

PR #80 locked 规律例外 fire (high connect + revenue < mean*0.85).
The correlation helper itself and the remaining equality / truncation
operators were never the primary lock:

- _check_correlation n<3 → 0 (even if the two points are collinear)
- constant series denom==0 → 0
- perfect +1.0 / -1.0 on n>=3
- connect_rate == mean is not an exception (need >)
- total_revenue == mean*0.85 is not an exception (need <)
- 3+ exceptions: description keeps only the first two, evidence keeps all

A flipped n<3 guard would treat a 2-day pair as a real 规律.
A flipped `>`/`<` would emit a false P2 规律例外 the day a department
sits exactly on mean connect or 85% of mean revenue. Truncating the
description to [:2] without a lock would let a later edit hide the
third exception department from managers.

Does not retest PR #80 fire wording as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "connect_rate": 45,
        "total_revenue": 100,
    }
    dept.update(overrides)
    return dept


class CheckCorrelationEdgesTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_n_less_than_3_returns_zero_even_when_collinear(self):
        self.assertEqual(0, self.engine._check_correlation([], []))
        self.assertEqual(0, self.engine._check_correlation([1], [2]))
        self.assertEqual(0, self.engine._check_correlation([1, 2], [2, 4]))

    def test_zero_variance_returns_zero(self):
        self.assertEqual(0, self.engine._check_correlation([3, 3, 3], [1, 2, 9]))
        self.assertEqual(0, self.engine._check_correlation([1, 2, 9], [4, 4, 4]))

    def test_perfect_positive_and_negative_correlation(self):
        self.assertEqual(1.0, self.engine._check_correlation([1, 2, 3], [2, 4, 6]))
        self.assertEqual(-1.0, self.engine._check_correlation([1, 2, 3], [6, 4, 2]))


class RuleExceptionEqualityAndTruncationTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_connect_exactly_mean_is_not_an_exception(self):
        # mean cr=50. D1 sits on the mean with rev well below 85% of
        # mean (50 < 85). Need connect_rate > mean.
        self.engine._rule_exception_analysis(
            {},
            [
                make_dept(dept_name="电销一部", connect_rate=50, total_revenue=50),
                make_dept(dept_name="电销二部", connect_rate=40, total_revenue=100),
                make_dept(dept_name="电销三部", connect_rate=60, total_revenue=150),
            ],
            [],
        )
        self.assertEqual([], self.engine.findings)

    def test_revenue_exactly_85_percent_of_mean_is_silent(self):
        # mean cr=50, mean rev=100, 0.85*100=85. D1 has cr>mean but
        # rev sits exactly on the 85% line (need <).
        self.engine._rule_exception_analysis(
            {},
            [
                make_dept(dept_name="电销一部", connect_rate=60, total_revenue=85),
                make_dept(dept_name="电销二部", connect_rate=40, total_revenue=100),
                make_dept(dept_name="电销三部", connect_rate=50, total_revenue=115),
            ],
            [],
        )
        self.assertEqual([], self.engine.findings)

    def test_three_exceptions_description_keeps_only_first_two(self):
        # mean cr=55, mean rev=287.5, 0.85*mean=244.375. First three
        # depts are exceptions; description uses exceptions[:2].
        self.engine._rule_exception_analysis(
            {},
            [
                make_dept(dept_name="电销一部", connect_rate=70, total_revenue=50),
                make_dept(dept_name="电销二部", connect_rate=70, total_revenue=50),
                make_dept(dept_name="电销三部", connect_rate=70, total_revenue=50),
                make_dept(dept_name="电销四部", connect_rate=10, total_revenue=1000),
            ],
            [],
        )
        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("规律例外发现", finding.tag)
        self.assertEqual("P2", finding.priority)
        self.assertIn("电销一部", finding.description)
        self.assertIn("电销二部", finding.description)
        self.assertNotIn("电销三部", finding.description)
        self.assertEqual(3, len(finding.evidence))
        self.assertTrue(any("电销三部" in e for e in finding.evidence))

    def test_empty_depts_stay_silent(self):
        self.engine._rule_exception_analysis({}, [], [])
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
