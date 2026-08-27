"""Regression coverage for leftover CrossDomain interpolation and refund enrich.

PR #81 locked CrossDomain trigger on/off (including 退费品牌) and P0
漏斗 → TOC enrichment. PR #110 locked `{avg_deal:,}` on the 锚定 card.
Neither locked the remaining `{dr}` / `{conv}` / `{t20}` / `{fc_rate}` /
`{ai}` / `{ref_rate}` interpolations, nor the 退费/过度承诺 enrichment
that fires on any priority and stops after the first match.

Does not retest PR #81 trigger silence, PR #110 锚定 thousands
separator, or P0 漏斗 TOC as the primary assertion.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.collision_engine import (
    CollisionFinding,
    CrossDomainCollisionEngine,
)


def _complete_summary(**overrides):
    # Every interpolating rule that can fire needs its keys present,
    # otherwise desc.format(**summary) raises KeyError mid-execute.
    summary = {
        "dr": 10,
        "conv": 2.0,
        "avg_deal": 6_000,
        "t20": 40,
        "fc_rate": 5,
        "ai": 80,
        "ref_rate": 3,
    }
    summary.update(overrides)
    return summary


def _depts(n=2, per_capita=3_000):
    return [
        {"dept_name": f"电销{i}部", "per_capita_revenue": per_capita}
        for i in range(1, n + 1)
    ]


def _finding(tag, priority="P1"):
    return CollisionFinding(
        collision_type="metric_x_metric",
        tag=tag,
        description="fixture finding",
        revenue_impact=1_000,
        priority=priority,
    )


def _by_tag(findings):
    return {f.tag: f for f in findings}


class CrossDomainInterpolationTests(unittest.TestCase):
    def setUp(self):
        self.engine = CrossDomainCollisionEngine()

    def test_spin_rule_interpolates_deep_talk_and_conversion(self):
        findings = self.engine.execute(
            _complete_summary(dr=18, conv=1.0),
            _depts(),
            [],
            [],
        )
        card = _by_tag(findings)["SPIN暗示问题×损失厌恶"]
        self.assertIn("深沟率18%尚可但转化率仅1.0%", card.description)
        self.assertNotIn("{dr}", card.description)
        self.assertNotIn("{conv}", card.description)

    def test_social_proof_rule_interpolates_top20_share(self):
        # 2 depts so 271 (needs len>3) stays off; only 社会认同 uses {t20}.
        findings = self.engine.execute(
            _complete_summary(t20=60),
            _depts(2),
            [],
            [],
        )
        card = _by_tag(findings)["影响力社会认同×从众效应"]
        self.assertIn("TOP20%占60%业绩", card.description)
        self.assertNotIn("{t20}", card.description)

    def test_trust_rule_interpolates_first_call_rate(self):
        findings = self.engine.execute(
            _complete_summary(fc_rate=2.5),
            _depts(),
            [],
            [],
        )
        card = _by_tag(findings)["信任构建×非暴力沟通共情"]
        self.assertIn("首通转化率仅2.5%", card.description)
        self.assertNotIn("{fc_rate}", card.description)

    def test_ai_qc_rule_interpolates_score(self):
        findings = self.engine.execute(
            _complete_summary(ai=70),
            _depts(),
            [],
            [],
        )
        card = _by_tag(findings)["质检AI化×复盘四步法"]
        self.assertIn("AI均分70未达标", card.description)
        self.assertNotIn("{ai}", card.description)

    def test_refund_brand_rule_interpolates_refund_rate(self):
        findings = self.engine.execute(
            _complete_summary(ref_rate=4.5),
            _depts(),
            [],
            [],
        )
        card = _by_tag(findings)["客户成功×品牌修复信任链"]
        self.assertIn("退费率4.5%偏高", card.description)
        self.assertNotIn("{ref_rate}", card.description)


class RefundEnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = CrossDomainCollisionEngine()
        self.engine.findings = []
        self.engine.collision_count = 0
        self.engine.domains_used = set()

    def _tags(self):
        return [f.tag for f in self.engine.findings]

    def test_p1_refund_finding_enriches_cognitive_dissonance(self):
        self.engine._enrich_from_data_findings(
            [_finding("高签单·高退费", "P1")], {}
        )
        self.assertIn("退费风险×认知失调×沉没成本设计", self._tags())
        self.assertEqual(1, self.engine.collision_count)

    def test_overpromise_tag_without_refund_word_also_enriches(self):
        self.engine._enrich_from_data_findings(
            [_finding("话术过度承诺", "P2")], {}
        )
        self.assertIn("退费风险×认知失调×沉没成本设计", self._tags())

    def test_only_first_refund_finding_enriches_then_stops(self):
        self.engine._enrich_from_data_findings(
            [
                _finding("高签单·高退费", "P1"),
                _finding("退费品牌风险", "P0"),
            ],
            {},
        )
        enrich = [
            f for f in self.engine.findings
            if f.tag == "退费风险×认知失调×沉没成本设计"
        ]
        self.assertEqual(1, len(enrich))

    def test_unrelated_finding_does_not_enrich_refund_psychology(self):
        self.engine._enrich_from_data_findings(
            [_finding("漏斗瓶颈", "P1")], {}
        )
        self.assertNotIn("退费风险×认知失调×沉没成本设计", self._tags())


if __name__ == "__main__":
    unittest.main()
