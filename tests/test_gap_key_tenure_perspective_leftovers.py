"""Regression coverage for leftover gap_key / 新人司龄 / 多视角贴线.

PR #107 locked blank gap_key (keeps manager, no inference) and
unknown-dept suppression. An *unknown* gap_key with a mapped
manager was never the primary lock — to_dict still emits the
manager, but must not invent a MANAGEMENT_GAP_RULES sentence.

PR #123 locked tenure==3 vs ==4 only for productivity buckets.
`_collide_new_hire_x_overall` uses the same `<= 3` cut and was
never the primary lock: a 4th-month employee must not create a
新人AI评分断层 card.

PR #121 locked roi==200 (健康 else-branch) and dials_pp==180
silence. The first tick *off* those lines was never the primary
lock: 199.9 must not arm 健康×退费, and 180.1 + 偏低 is the
first 负荷×低ROI card.

Does not retest PR #107 blank-key / unknown-dept, PR #123
productivity buckets, or PR #80 far 多视角 fire as primary.
Does not lock persistence global cr_below_count (PR #48).
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    MANAGEMENT_GAP_RULES,
    DataCollisionEngine,
    LogicCollisionEngine,
)


def make_person(**overrides):
    person = {
        "name": "员工A",
        "tenure_months": 12,
        "ai_score": 75,
        "revenue": 3000,
        "dial_count": 80,
    }
    person.update(overrides)
    return person


class UnknownGapKeyWiringTests(unittest.TestCase):
    def test_unknown_gap_key_keeps_manager_and_empty_gap(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        engine._add_finding(
            "metric_x_metric",
            "高接通·短通话",
            "fixture",
            1000,
            "P1",
            scope="dept",
            dept_name="电销六部",
            gap_key="not_a_real_gap",
        )
        finding = engine.findings[-1]
        payload = finding.to_dict()
        self.assertEqual("游云清", payload["manager_name"])
        self.assertEqual("", payload["management_gap"])
        self.assertEqual("", finding.management_gap)
        for text in MANAGEMENT_GAP_RULES.values():
            self.assertNotEqual(text, payload["management_gap"])
            self.assertNotIn(text, payload["management_gap"])


class NewHireTenureBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_tenure_exactly_3_still_counts_as_new_hire_ai_gap(self):
        # tenure==3 is still 新人; 50 < ((50+90)/2)*0.8 = 56.
        self.engine._collide_new_hire_x_overall(
            {},
            [
                make_person(name="新人", tenure_months=3, ai_score=50),
                make_person(name="老人", tenure_months=12, ai_score=90),
            ],
        )
        cards = [f for f in self.engine.findings if f.tag == "新人AI评分断层"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("新人(≤3月)AI均分50.0", cards[0].description)

    def test_tenure_exactly_4_is_excluded_from_new_hire_ai_gap(self):
        # A 4th-month low-AI employee is not 新人; no new_hires → early return.
        self.engine._collide_new_hire_x_overall(
            {},
            [
                make_person(name="准新人", tenure_months=4, ai_score=50),
                make_person(name="老人", tenure_months=12, ai_score=90),
            ],
        )
        self.assertEqual([], self.engine.findings)


class MultiPerspectiveJustOffThresholdTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _summary(self, **overrides):
        summary = {
            "roi": 199.9,
            "dial_count": 1800,
            "on_duty": 10,
            "t20": 40,
            "ref_rate": 6,
            "complaint_count": 0,
        }
        summary.update(overrides)
        return summary

    def _balanced_depts(self):
        return [
            {"per_capita_revenue": 2500},
            {"per_capita_revenue": 2600},
        ]

    def test_roi_199_9_plus_high_refund_does_not_arm_healthy_conflict(self):
        # roi==199.9 is 偏低, not 健康. dials_pp==180 stays silent.
        # PR #121 locked roi==200 as the 健康 else-branch that *does*
        # arm 健康×退费.
        self.engine._multi_perspective_collision(
            self._summary(), self._balanced_depts()
        )
        self.assertEqual([], self.engine.findings)

    def test_dials_180_1_plus_low_roi_is_first_load_conflict(self):
        # 1801/10 == 180.1 > 180 and roi 199.9 < 200.
        # Keep ref_rate low so the only conflict is 负荷×低ROI.
        self.engine._multi_perspective_collision(
            self._summary(dial_count=1801, ref_rate=3),
            self._balanced_depts(),
        )
        cards = [f for f in self.engine.findings if f.tag == "多视角矛盾"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("工作量大但ROI偏低", cards[0].description)
        self.assertIn("不是不够努力而是效率有问题", cards[0].description)
        self.assertNotIn("短期利润", cards[0].description)


if __name__ == "__main__":
    unittest.main()
