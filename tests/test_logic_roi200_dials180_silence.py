"""Regression coverage for leftover Logic multi-perspective exact gates.

PR #80 locked ROI×退费 fire (healthy ROI + high refund) and 负荷×低ROI
fire (dials_pp>180 + ROI偏低). PR #108 locked t20==55 / complaint
threshold / CV evidence edges. Exact equality on the remaining two
operators was never the primary lock:

- roi == 200 is the healthy else-branch (need < 200 for 偏低)
- dials_pp == 180 is not 工作负荷较重 (need > 180)

Flipping `< 200` to `<=` would relabel a 200% ROI team as 偏低 and
drop the 健康×退费 contradiction. Flipping `> 180` to `>=` would
attach a false 鞭打快牛 / 倦怠 card the day load sits on 180.

Does not retest t20/complaint/CV evidence or PR #80 conflict
verdicts as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "per_capita_revenue": 3000,
        "connect_rate": 45,
        "total_revenue": 50000,
        "on_duty": 20,
    }
    dept.update(overrides)
    return dept


def make_summary(**overrides):
    summary = {
        "roi": 180,
        "dial_count": 10000,
        "on_duty": 100,
        "t20": 40,
        "ref_rate": 3,
        "complaint_count": 1,
    }
    summary.update(overrides)
    return summary


def _balanced_depts():
    return [
        make_dept(dept_name="电销一部", per_capita_revenue=3000),
        make_dept(dept_name="电销六部", per_capita_revenue=3000),
    ]


class LogicRoi200Dials180Tests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_roi_exactly_200_is_healthy_and_enables_refund_conflict(self):
        # ==200 takes the else branch ("健康"), which is what arms
        # the already-known ROI×退费 contradiction when ref_rate>5.
        self.engine._multi_perspective_collision(
            make_summary(roi=200, ref_rate=7, dial_count=10000, on_duty=100),
            _balanced_depts(),
        )
        self.assertEqual(1, len(self.engine.findings))
        desc = self.engine.findings[0].description
        blob = " | ".join(self.engine.findings[0].evidence)
        self.assertEqual("多视角矛盾", self.engine.findings[0].tag)
        self.assertIn("ROI健康", desc)
        self.assertIn("退费率", desc)
        self.assertNotIn("偏低", desc)
        self.assertIn("健康", blob)
        self.assertNotIn("工作负荷较重", blob)

    def test_dials_pp_exactly_180_with_low_roi_is_silent(self):
        # 1800/10 == 180; 负荷 needs > 180. ROI 150 is 偏低, so a
        # flipped >= would emit 负荷×低ROI.
        self.engine._multi_perspective_collision(
            make_summary(
                roi=150,
                ref_rate=3,
                dial_count=1800,
                on_duty=10,
                t20=40,
                complaint_count=1,
            ),
            _balanced_depts(),
        )
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
