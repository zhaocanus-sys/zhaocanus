"""Regression coverage for leftover multi-perspective 5.1 / 55.1.

PR #80/#121 locked roi==200 as the 健康 else-branch that *does*
arm 健康×退费 when refund is already far (>5).
PR #108 locked far t20=56 中腰部 evidence and exact ==55 silence,
behind a far ref_rate=7 vehicle.
PR #126 locked roi==199.9 as 偏低 (does not arm 健康×退费).
PR #130 locked ref_rate==5.1 as forward 质量保障 and t20==55.1 as
reverse 集中度 — not as multi-perspective evidence.

The leftover ticks:

- ref_rate==5.1 + roi==200 is the first 客户退费 evidence and the
  first 健康×退费 conflict at the leftover refund gate
- ref_rate==5 + roi==200 stays silent (no 客户 evidence, no card)
- t20==55.1 is the first 中腰部 evidence on an already-armed
  健康×退费 card (`> 55`)
- t20==55 does not attach 中腰部 / TOP20%

Does not retest PR #108 t20=56 / PR #121 far refund=7 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_summary(**overrides):
    summary = {
        "allocated": 1300,
        "on_duty": 100,
        "dial_count": 10000,
        "roi": 200,
        "ref_rate": 5,
        "t20": 40,
        "complaint_count": 1,
    }
    summary.update(overrides)
    return summary


def _equal_pc_depts():
    # Equal per-capita keeps CV off so 数据 evidence cannot mask
    # the leftover 客户 / 一线 ticks.
    return [
        {"dept_name": "电销一部", "per_capita_revenue": 3000},
        {"dept_name": "电销六部", "per_capita_revenue": 3000},
    ]


def _evidence_blob(finding):
    return " | ".join(finding.evidence)


class PerspectiveRef51AndT20551FirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_ref_rate_5_1_plus_roi_200_is_first_healthy_refund_conflict(self):
        # 5.1 > 5 is the first 客户退费 tick after PR #121's far
        # refund=7 behind roi==200. 10000/100 dials stay off 负荷.
        self.engine._multi_perspective_collision(
            make_summary(roi=200, ref_rate=5.1),
            _equal_pc_depts(),
        )
        cards = [f for f in self.engine.findings if f.tag == "多视角矛盾"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P1", cards[0].priority)
        self.assertIn("ROI健康", cards[0].description)
        self.assertIn("退费率偏高", cards[0].description)
        blob = _evidence_blob(cards[0])
        self.assertIn("团队ROI 200%健康", blob)
        self.assertIn("退费率5.1%偏高", blob)
        self.assertNotIn("工作负荷较重", blob)
        self.assertNotIn("中腰部", blob)

    def test_ref_rate_exactly_5_plus_roi_200_stays_silent(self):
        # ==5 is not `> 5`. Healthy ROI alone does not emit a card.
        # Flipping to `>=` would keep PR #121's far-refund 健康×退费
        # suite green while accusing a 贴线 5% day.
        self.engine._multi_perspective_collision(
            make_summary(roi=200, ref_rate=5),
            _equal_pc_depts(),
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "多视角矛盾"],
        )

    def test_t20_55_1_is_first_mid_tier_evidence_on_healthy_refund_conflict(self):
        # 55.1 > 55 is the first 中腰部 evidence after PR #108's far
        # t20=56. Vehicle stays the already-locked far refund=7 +
        # roi==200 so this test does not re-lock the 5.1 gate.
        self.engine._multi_perspective_collision(
            make_summary(roi=200, ref_rate=7, t20=55.1),
            _equal_pc_depts(),
        )
        cards = [f for f in self.engine.findings if f.tag == "多视角矛盾"]
        self.assertEqual(1, len(cards))
        blob = _evidence_blob(cards[0])
        self.assertIn("TOP20%占55.1%", blob)
        self.assertIn("中腰部", blob)
        self.assertIn("退费率7%偏高", blob)

    def test_t20_exactly_55_does_not_attach_mid_tier_on_healthy_refund_conflict(self):
        # ==55 is not `> 55`. The 健康×退费 card still fires from
        # far refund=7, but 一线 must not grow a 中腰部 sentence.
        self.engine._multi_perspective_collision(
            make_summary(roi=200, ref_rate=7, t20=55),
            _equal_pc_depts(),
        )
        cards = [f for f in self.engine.findings if f.tag == "多视角矛盾"]
        self.assertEqual(1, len(cards))
        blob = _evidence_blob(cards[0])
        self.assertNotIn("中腰部", blob)
        self.assertNotIn("TOP20%", blob)
        self.assertIn("退费率7%偏高", blob)


if __name__ == "__main__":
    unittest.main()
