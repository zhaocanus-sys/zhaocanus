"""Regression coverage for leftover two-P0 漏斗 TOC enrichment.

PR #81 locked a *single* P0 漏斗 → one TOC card.
PR #111 locked two 退费 / 过度承诺 findings → *one* 认知失调
card because that branch `break`s.

The leftover contract was never the primary lock:

- two P0 tags that both contain 漏斗 emit TWO TOC cards
  (the 漏斗 branch has no `break`)
- two P0 漏斗 + one 退费 → two TOC + one 退费
- one P0 漏斗 + two 退费 → one TOC + one 退费 (break still holds)
- P1 漏斗 and P0 without 漏斗 do not emit TOC

Does not retest PR #111 first-match 退费 break as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import (
    CollisionFinding,
    CrossDomainCollisionEngine,
)


def _finding(**overrides):
    payload = {
        "collision_type": "funnel_x_benchmark",
        "tag": "漏斗瓶颈",
        "description": "漏斗最薄弱环节: 分配→拨打",
        "revenue_impact": 0,
        "priority": "P0",
    }
    payload.update(overrides)
    return CollisionFinding(**payload)


class TwoP0FunnelTocNoBreakTests(unittest.TestCase):
    def setUp(self):
        self.engine = CrossDomainCollisionEngine()

    def _enrich(self, findings):
        self.engine.findings = []
        self.engine.collision_count = 0
        self.engine.domains_used = set()
        self.engine._enrich_from_data_findings(findings, {})
        return self.engine.findings

    def test_two_p0_funnel_findings_emit_two_toc_cards(self):
        # No `break` on the 漏斗 branch. Two P0 漏斗 tags are two
        # independent TOC enrichments — flipping in a `break` would
        # keep PR #81's single-card suite green while dropping the
        # second bottleneck's 贝叶斯迭代 recs.
        cards = self._enrich([
            _finding(tag="漏斗瓶颈"),
            _finding(tag="漏斗×标杆"),
        ])
        toc = [f for f in cards if f.tag == "漏斗瓶颈×TOC约束×贝叶斯迭代"]
        self.assertEqual(2, len(toc))
        self.assertTrue(all(f.priority == "P1" for f in toc))
        self.assertTrue(all("ICE评分>20" in f.description for f in toc))
        self.assertTrue(all("O04:TOC约束理论" in f.knowledge_refs for f in toc))
        self.assertEqual(0, len([
            f for f in cards if "认知失调" in f.tag or "退费风险" in f.tag
        ]))

    def test_two_p0_funnel_plus_refund_keeps_two_toc_and_one_refund(self):
        cards = self._enrich([
            _finding(tag="漏斗瓶颈"),
            _finding(tag="漏斗×标杆"),
            _finding(tag="高签单·高退费", priority="P1"),
        ])
        toc = [f for f in cards if f.tag == "漏斗瓶颈×TOC约束×贝叶斯迭代"]
        refund = [f for f in cards if f.tag == "退费风险×认知失调×沉没成本设计"]
        self.assertEqual(2, len(toc))
        self.assertEqual(1, len(refund))
        self.assertIn("购后认知失调", refund[0].description)
        self.assertIn("48h内回访", " ".join(refund[0].recommendations))

    def test_one_p0_funnel_plus_two_refund_still_breaks_after_first_refund(self):
        # 退费 branch still `break`s. Two 退费/过度承诺 tags must not
        # stack a second 认知失调 card on top of the single TOC.
        cards = self._enrich([
            _finding(tag="漏斗瓶颈"),
            _finding(tag="高签单·高退费", priority="P1"),
            _finding(tag="过度承诺检测", priority="P2"),
        ])
        toc = [f for f in cards if f.tag == "漏斗瓶颈×TOC约束×贝叶斯迭代"]
        refund = [f for f in cards if f.tag == "退费风险×认知失调×沉没成本设计"]
        self.assertEqual(1, len(toc))
        self.assertEqual(1, len(refund))

    def test_p1_funnel_and_p0_without_funnel_skip_toc(self):
        # Priority gate is `P0 and "漏斗"`. A P1 漏斗 or a P0 高活动
        # card must not mint a TOC enrichment.
        cards = self._enrich([
            _finding(tag="漏斗瓶颈", priority="P1"),
            _finding(tag="高活动·高接通·低营收", priority="P0"),
        ])
        self.assertEqual(
            [],
            [f for f in cards if f.tag == "漏斗瓶颈×TOC约束×贝叶斯迭代"],
        )
        self.assertEqual(
            [],
            [f for f in cards if "退费风险" in f.tag],
        )


if __name__ == "__main__":
    unittest.main()
