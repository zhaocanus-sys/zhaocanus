"""Regression coverage for leftover on_duty==0 sentinels.

`_collide_activity_x_quality` uses `on_duty or 1` before dials_pp
and quality_ratio. PR #126 locked first fire at dials_pp==45.1 with
on_duty=10. Zero-headcount days were never the primary lock —
removing `or 1` would ZeroDivisionError, and skipping the row
would hide a 刷量 card when HR 在岗 is missing.

`_multi_perspective_collision` is asymmetric: dials_pp uses
`on_duty or 1`, but complaints compare against raw `on_duty * 0.1`.
With on_duty==0, complaint_count==1 is already > 0. PR #108 locked
on_duty=100 (10 vs 11). The zero-duty complaint / 负荷 path was
never the primary lock.

Does not retest PR #126 dials_pp==45.1 / 180.1 with live headcount.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    LogicCollisionEngine,
)


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "peak_hour_revenue": 7000,
        "offpeak_hour_revenue": 3000,
        "conversion_rate": 2.0,
        "jx_conv_rate": 1.8,
        "jx_transfer_in": 10,
        "avg_deal_amount": 5000,
        "connect_rate": 45,
        "avg_connect_dur": 120,
        "signed_deals": 10,
        "refund_rate": 3,
        "refund_amount": 1000,
        "avg_ai_score": 72,
        "total_revenue": 50000,
        "on_duty": 20,
        "dial_count": 800,
        "deep_talk": 40,
        "per_capita_revenue": 2500,
        "allocated": 500,
    }
    dept.update(overrides)
    return dept


def _perspective_summary(**overrides):
    summary = {
        "roi": 201,
        "dial_count": 0,
        "on_duty": 0,
        "t20": 40,
        "ref_rate": 5.1,
        "complaint_count": 1,
    }
    summary.update(overrides)
    return summary


class ActivityOnDutyZeroTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()
        self.engine.dept_managers = {"电销六部": "游云清"}

    def test_on_duty_zero_dials_46_is_first_quality_fire(self):
        # od becomes 1: dials_pp=46 > 45, quality_ratio=1/46*100=2.2 < 4.
        # Impact uses the sentinel od=1, not the raw 0.
        self.engine._collide_activity_x_quality(
            [make_dept(on_duty=0, dial_count=46, deep_talk=1, avg_deal_amount=5000)]
        )
        cards = [f for f in self.engine.findings if f.tag == "高拨打·低质量"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertEqual("dept", cards[0].scope)
        self.assertEqual("电销六部", cards[0].dept_name)
        self.assertEqual("游云清", cards[0].manager_name)
        self.assertIn("刷量", cards[0].description)
        self.assertIn("只追拨打量", cards[0].management_gap)
        self.assertEqual(750, cards[0].revenue_impact)
        self.assertIn("人均拨打46通", cards[0].description)
        self.assertIn("2.2%", cards[0].description)

    def test_on_duty_zero_dials_45_stays_silent(self):
        # 45 / 1 == 45 is not > 45. Exact silence on the leftover
        # or-1 path; PR #126 fired 45.1 with on_duty=10.
        self.engine._collide_activity_x_quality(
            [make_dept(on_duty=0, dial_count=45, deep_talk=0)]
        )
        self.assertEqual([], self.engine.findings)


class PerspectiveOnDutyZeroTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _run(self, summary):
        self.engine.findings = []
        self.engine._multi_perspective_collision(summary, [])
        return [f for f in self.engine.findings if f.tag == "多视角矛盾"]

    def test_on_duty_zero_complaint_1_appears_in_health_x_refund(self):
        # complaint 1 > 0 * 0.1. ROI 201 is 健康; ref_rate 5.1 > 5
        # arms 健康×退费 so the 客户 perspective is visible.
        cards = self._run(_perspective_summary())
        self.assertEqual(1, len(cards))
        blob = " ".join(cards[0].evidence)
        self.assertIn("投诉1件", blob)
        self.assertIn("退费率", blob)
        self.assertIn("健康", blob)

    def test_on_duty_zero_complaint_0_stays_off_customer_perspective(self):
        # 0 > 0 is false. Same conflict still fires from 退费, but
        # complaints must not appear.
        cards = self._run(_perspective_summary(complaint_count=0))
        self.assertEqual(1, len(cards))
        blob = " ".join(cards[0].evidence)
        self.assertNotIn("投诉", blob)
        self.assertIn("退费率", blob)

    def test_on_duty_zero_dials_181_is_first_load_x_low_roi(self):
        # 181 / 1 > 180 and roi 199 < 200. Distinct from PR #126's
        # 180.1 with live headcount — this is the or-1 sentinel.
        cards = self._run(_perspective_summary(
            roi=199,
            dial_count=181,
            ref_rate=3,
            complaint_count=0,
        ))
        self.assertEqual(1, len(cards))
        self.assertIn("效率有问题", cards[0].description)
        blob = " ".join(cards[0].evidence)
        self.assertIn("工作负荷较重", blob)
        self.assertIn("偏低", blob)

    def test_on_duty_zero_dials_180_stays_silent_on_load(self):
        # 180 / 1 is not > 180. No 工作负荷, roi 偏低, low refund
        # → no conflict finding.
        cards = self._run(_perspective_summary(
            roi=199,
            dial_count=180,
            ref_rate=3,
            complaint_count=0,
        ))
        self.assertEqual([], cards)


if __name__ == "__main__":
    unittest.main()
