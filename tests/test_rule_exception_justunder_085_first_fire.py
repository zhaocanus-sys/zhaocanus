"""Regression coverage for leftover 规律例外 rev < mean*0.85 first fire.

PR #80 locked far 规律例外 fire (high CR + far-below-mean revenue).
PR #122 locked exact silence at connect_rate==mean and
total_revenue==mean*0.85.
PR #134 locked three equal-CR departments (denom==0) with no card.

The leftover just-under 0.85 tick was never the primary lock:

- cr 40.1 vs 40.0 (just above mean) + rev 8499 vs 11500
  (8499 < 9999.5*0.85 == 8499.575) is the first fire
- same leftover CR + rev==8500 stays silent
- leftover rev 8499 + equal CR stays silent (need CR > mean)

Does not retest PR #80 far fire or PR #122/#134 exact silence as primary.
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


class RuleExceptionJustUnder085FirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _run(self, low_cr, low_rev, peer_cr=40.0, peer_rev=11500):
        self.engine.findings = []
        self.engine._rule_exception_analysis(
            {},
            [
                make_dept(
                    dept_name="电销六部",
                    connect_rate=low_cr,
                    total_revenue=low_rev,
                ),
                make_dept(
                    dept_name="电销一部",
                    connect_rate=peer_cr,
                    total_revenue=peer_rev,
                ),
            ],
            [],
        )
        return [f for f in self.engine.findings if f.tag == "规律例外发现"]

    def test_cr_just_over_mean_plus_rev_8499_is_first_085_tick(self):
        # avg_cr=40.05 → 40.1 is the leftover `>` tick.
        # avg_rev=9999.5 → 0.85×=8499.575; 8499 is the leftover `<`.
        # Distinct from PR #80's far-below-mean vehicle.
        cards = self._run(40.1, 8499)
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertIn("电销六部", cards[0].description)
        self.assertIn("接通率40.1%高于均值", cards[0].description)
        self.assertTrue(any("电销六部" in e and "40.1%" in e for e in cards[0].evidence))
        self.assertIn("转化效率同等重要", cards[0].description)

    def test_leftover_cr_plus_rev_exactly_8500_stays_silent(self):
        # 8500 == 10000*0.85. Flipping `<` to `<=` would keep
        # PR #80 far-fire green while tagging a 贴线 85% 营收 day.
        self.assertEqual([], self._run(40.1, 8500))

    def test_leftover_rev_plus_equal_cr_stays_silent(self):
        # 8499 is not enough when CR cannot beat the mean.
        # Equal CR was locked as a denom-guard vehicle in PR #134;
        # here it is the contrast that the leftover 0.85 tick
        # still needs CR > mean.
        self.assertEqual([], self._run(40.0, 8499, peer_cr=40.0))

    def test_leftover_rev_plus_cr_exactly_on_mean_stays_silent(self):
        # Two-dept mean with 40.0 / 40.0: 40.0 > 40.0 is false.
        self.assertEqual([], self._run(40.0, 8499, peer_cr=40.0, peer_rev=11500))


if __name__ == "__main__":
    unittest.main()
