"""Regression coverage for leftover tenure skip + new-hire month boundary.

PR #80 locked 老员工倦怠 fire (senior < mature*0.85) and 新人断崖
fire (newbie < 50% of pc).
PR #112 locked bucket edges 0/3/4/12/13/24/25 on a healthy roster.
PR #121 locked senior == mature*0.85 and newbie ratio == 50 silence.

Remaining operators were never the primary lock:

- senior-only roster (no 成熟期 bucket) skips 老员工倦怠 even when
  senior revenue is far below company pc
- mature-only / growth-only rosters also cannot emit 倦怠
- senior + newbie without mature still allows 新人断崖
- _collide_new_hire_x_overall treats tenure==3 as 新人 and tenure==4
  as 成长期 (not in the AI-gap set)

A later edit that ORs "has seniors" without requiring a mature
baseline would fire a false 老员工倦怠 the month a team has no
1-2 year cohort. Sliding `<= 3` to `< 3` would drop month-3 hires
from the AI断层 card; sliding to `<= 4` would diagnose 成长期 staff
as 新人.

Does not retest PR #80 fire wording or PR #112 healthy bucket
labels as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


def make_person(**overrides):
    person = {
        "name": "员工A",
        "tenure_months": 12,
        "revenue": 3000,
        "ai_score": 70,
        "dial_count": 100,
    }
    person.update(overrides)
    return person


class TenureSeniorOnlySkipTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def _tags(self):
        return [f.tag for f in self.engine.findings]

    def test_senior_only_roster_skips_burnout_even_when_revenue_is_low(self):
        self.engine._collide_tenure_x_productivity(
            {"pc": 8000},
            [
                make_person(name="老A", tenure_months=25, revenue=800),
                make_person(name="老B", tenure_months=36, revenue=900),
            ],
        )
        self.assertNotIn("老员工倦怠", self._tags())
        self.assertNotIn("新人断崖", self._tags())

    def test_mature_only_roster_cannot_emit_burnout(self):
        self.engine._collide_tenure_x_productivity(
            {"pc": 8000},
            [
                make_person(name="熟A", tenure_months=13, revenue=800),
                make_person(name="熟B", tenure_months=24, revenue=900),
            ],
        )
        self.assertNotIn("老员工倦怠", self._tags())

    def test_growth_only_low_revenue_skips_burnout_and_cliff(self):
        # 4-12月 is neither 新人 nor 老员工; low rev vs pc must not
        # be diagnosed as 断崖 or 倦怠.
        self.engine._collide_tenure_x_productivity(
            {"pc": 8000},
            [
                make_person(name="长A", tenure_months=4, revenue=400),
                make_person(name="长B", tenure_months=12, revenue=500),
            ],
        )
        self.assertEqual([], self.engine.findings)

    def test_senior_plus_newbie_without_mature_still_allows_cliff(self):
        self.engine._collide_tenure_x_productivity(
            {"pc": 5000},
            [
                make_person(name="老A", tenure_months=25, revenue=4000),
                make_person(name="老B", tenure_months=30, revenue=4000),
                make_person(name="新A", tenure_months=1, revenue=200),
                make_person(name="新B", tenure_months=2, revenue=200),
            ],
        )
        tags = self._tags()
        self.assertNotIn("老员工倦怠", tags)
        self.assertIn("新人断崖", tags)

    def test_empty_persons_skips_tenure_and_new_hire_cards(self):
        self.engine._collide_tenure_x_productivity({"pc": 5000}, [])
        self.engine._collide_new_hire_x_overall({"pc": 5000}, [])
        self.assertEqual([], self.engine.findings)


class NewHireTenureMonthBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_tenure_exactly_3_months_is_included_in_new_hire_ai_gap(self):
        # new=40, all=65, 40 < 65*0.8=52 → 新人AI评分断层.
        self.engine._collide_new_hire_x_overall(
            {},
            [
                make_person(name="月3", tenure_months=3, ai_score=40),
                make_person(name="熟手", tenure_months=20, ai_score=90),
            ],
        )
        tags = [f.tag for f in self.engine.findings]
        self.assertEqual(["新人AI评分断层"], tags)

    def test_tenure_exactly_4_months_is_excluded_from_new_hire_set(self):
        # Same AI gap, but month-4 is 成长期 — no new_hires → silent.
        self.engine._collide_new_hire_x_overall(
            {},
            [
                make_person(name="月4", tenure_months=4, ai_score=40),
                make_person(name="熟手", tenure_months=20, ai_score=90),
            ],
        )
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
