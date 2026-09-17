"""Regression coverage for leftover live-headcount complaint first fire.

`_multi_perspective_collision` compares complaint_count against
raw `on_duty * 0.1` (no `or 1` sentinel).

PR #108 locked on_duty=100 (10 vs 11).
PR #128 locked on_duty==0 (complaint 1 > 0).

A non-100 live headcount was never the primary lock:

- on_duty=10, complaint=2 is the first 投诉 tick (`2 > 1.0`)
- on_duty=10, complaint=1 stays silent (`1 > 1.0` is false)
- on_duty=15, complaint=2 is the first non-integer threshold
  (`2 > 1.5`); complaint=1 stays silent

ROI stays 健康 and ref_rate stays just over 5 so 健康×退费 is
the vehicle — the leftover is whether 投诉 appears in evidence.

Does not retest PR #108 headcount=100 or PR #128 zero-duty.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def _perspective_summary(**overrides):
    summary = {
        "roi": 200,
        "dial_count": 800,
        "on_duty": 10,
        "t20": 40,
        "ref_rate": 5.1,
        "complaint_count": 2,
    }
    summary.update(overrides)
    return summary


class ComplaintLiveHeadcountFirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _run(self, summary):
        self.engine.findings = []
        self.engine._multi_perspective_collision(summary, [])
        return [f for f in self.engine.findings if f.tag == "多视角矛盾"]

    def test_onduty_10_complaint_2_is_first_customer_complaint(self):
        # 2 > 10 * 0.1. ROI 200 is 健康; ref_rate 5.1 > 5 arms
        # 健康×退费 so the 客户 perspective is visible.
        cards = self._run(_perspective_summary())
        self.assertEqual(1, len(cards))
        blob = " ".join(cards[0].evidence)
        self.assertIn("投诉2件", blob)
        self.assertIn("退费率", blob)
        self.assertIn("健康", blob)
        self.assertIn("短期利润", cards[0].description)

    def test_onduty_10_complaint_1_stays_off_customer_perspective(self):
        # 1 > 1.0 is false. Same conflict still fires from 退费, but
        # complaints must not appear. Flipping `>` to `>=` would keep
        # the on_duty=100 / on_duty=0 suites green while tagging a
        # 贴线 10% day as 过度承诺.
        cards = self._run(_perspective_summary(complaint_count=1))
        self.assertEqual(1, len(cards))
        blob = " ".join(cards[0].evidence)
        self.assertNotIn("投诉", blob)
        self.assertIn("退费率", blob)

    def test_onduty_15_complaint_2_is_first_non_integer_threshold(self):
        # 2 > 15 * 0.1 = 1.5. Distinct from the round 10-person /
        # 100-person locks — this is the first leftover at a
        # non-integer 0.1× headcount line.
        cards = self._run(_perspective_summary(on_duty=15, complaint_count=2))
        self.assertEqual(1, len(cards))
        blob = " ".join(cards[0].evidence)
        self.assertIn("投诉2件", blob)
        self.assertIn("退费率", blob)

    def test_onduty_15_complaint_1_stays_silent(self):
        # 1 > 1.5 is false. 退费 conflict remains; 投诉 must not attach.
        cards = self._run(_perspective_summary(on_duty=15, complaint_count=1))
        self.assertEqual(1, len(cards))
        blob = " ".join(cards[0].evidence)
        self.assertNotIn("投诉", blob)
        self.assertIn("退费率", blob)


if __name__ == "__main__":
    unittest.main()
