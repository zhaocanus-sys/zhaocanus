"""Regression coverage for leftover persistence AND-gate first fire.

PR #110 locked early exits: trends < 5 stay silent; current
connect_rate == 43 stays silent even when every trend day is red.

PR #114 locked the far fire path: 7 aligned days at cr=30 + current
30 emit P0 持续不达标预警 with the salary-linked contract.

The leftover ticks were never the primary lock:

- cr_below_count == 5 is the first fire (`>= 5`, not 7)
- current connect_rate == 42.9 is the first current-CR fire after
  PR #110's ==43 silence
- a trend day sitting at cr==43 does *not* increment the streak
  (`< 43`, not `<=`)
- four just-below days among five trend rows stay silent

Fixtures keep global `cr` and matching `dept_trends` in agreement so
this does **not** lock the buggy global `cr_below_count` (open PR #48).

Does not retest PR #114's 7-day / 部门负责人 payload as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


def _low_cr_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "connect_rate": 42.9,
        "allocated": 200,
        "avg_deal_amount": 4_000,
    }
    dept.update(overrides)
    return dept


def _aligned_day(cr, dept="电销六部"):
    """Global cr *and* dept_trends agree, so PR #48 would still fire."""
    return {"cr": cr, "dept_trends": [{"dept_name": dept, "cr": cr}]}


def _aligned_red_trends(n=5, cr=42.9, dept="电销六部"):
    return [_aligned_day(cr, dept) for _ in range(n)]


class PersistenceCountFiveAndCr429FirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def _persist(self):
        return [f for f in self.engine.findings if f.tag == "持续不达标预警"]

    def test_five_just_below_days_plus_current_42_9_is_first_fire(self):
        # 5 days at 42.9: count >= 5. Current 42.9 is < 43.
        # Distinct from PR #114's 7×30 far fire and PR #110's ==43 silence.
        self.engine._collide_persistence_detection(
            [_low_cr_dept()],
            _aligned_red_trends(n=5, cr=42.9),
        )
        persist = self._persist()
        self.assertEqual(1, len(persist))
        finding = persist[0]
        self.assertEqual("P0", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销六部", finding.dept_name)
        self.assertEqual("metric_x_time", finding.collision_type)
        self.assertIn("游云清", finding.description)
        self.assertIn("连续约5天", finding.description)
        self.assertIn("当前42.9%", finding.description)
        recs = " ".join(finding.recommendations)
        self.assertIn("绩效分数扣减5分/日", recs)
        self.assertIn("书面改善计划", recs)
        # 200 * 0.03 * 4000 = 24000 — leftover formula tick on the
        # just-over path, not PR #114's 500*0.03*5000=75000.
        self.assertEqual(24_000, finding.revenue_impact)
        payload = finding.to_dict()
        self.assertEqual("游云清", payload["manager_name"])
        self.assertIn("连续多日", payload["management_gap"])

    def test_four_just_below_days_among_five_trends_is_silent(self):
        # 5 trend rows pass the early-exit; only 4 sit < 43 so
        # cr_below_count == 4 is not >= 5. Flipping `>=` to `>` would
        # keep PR #114's 7-day fire green while swallowing the first
        # real 5-day card; flipping `>=` to `==7` is already guarded
        # by the first-fire case. This locks the silent side of 4.
        trends = _aligned_red_trends(n=4, cr=42.9) + [_aligned_day(50)]
        self.engine._collide_persistence_detection(
            [_low_cr_dept()],
            trends,
        )
        self.assertEqual([], self._persist())

    def test_trend_day_cr_exactly_43_does_not_count_as_below(self):
        # Five days sitting *on* the 43 redline are not `< 43`.
        # Current 42.9 would fire if those days counted. Flipping
        # trend `<` to `<=` would P0 a 贴线 week.
        self.engine._collide_persistence_detection(
            [_low_cr_dept()],
            _aligned_red_trends(n=5, cr=43),
        )
        self.assertEqual([], self._persist())

    def test_missing_cr_key_defaults_healthy_and_stays_silent(self):
        # t.get("cr", 50) treats a missing key as healthy 50.
        # Five empty trend dicts + current 42.9 must not P0.
        # No dept_trends key either, so this does not compare
        # global vs department counts (PR #48).
        self.engine._collide_persistence_detection(
            [_low_cr_dept()],
            [{}, {}, {}, {}, {}],
        )
        self.assertEqual([], self._persist())


if __name__ == "__main__":
    unittest.main()
