"""Regression coverage for leftover multi-warning first-wins + H-count.

PR #108 locked *single-node* causal bottlenecks (资源输入 ==12×,
会话深度, 转化产出, 质量保障) and the all-healthy skip.
PR #122 locked reverse-trace exact redline silence.
PR #79 locked 触达效率 fire as a single warning.

Remaining operators were never the primary lock:

- when several forward nodes are warning, bottleneck is the
  first in chain order (资源输入 → 触达 → 会话 → 转化 → 质量)
- reverse-trace 主因 is the first matching cause (接通 before
  深沟 / AI) when several redlines fire together
- `_validate_rules` emits 假设数量不足 when fewer than 3
  hypotheses were built (0 or H1-only)

A "pick the worst KPI" rewrite would move the daily TOC repair
order off the true first constraint. Dropping the <3-hypothesis
card would let a thin-data day ship as a complete 逻辑对撞.

Does not retest PR #108 single-node / all-healthy skip or
PR #122 exact-redline silence as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def _forward_summary(**overrides):
    summary = {
        "allocated": 1300,
        "on_duty": 100,
        "alloc_rate": 0.9,
        "cr": 43,
        "dial_count": 8000,
        "dr": 18,
        "ai": 70,
        "conv": 1.0,
        "signed_deals": 20,
        "total_revenue": 400000,
        "pc": 4000,
        "ref_rate": 5,
        "complaint_count": 1,
        "t20": 40,
    }
    summary.update(overrides)
    return summary


class CausalMultiWarningFirstWinsTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _chain(self, summary):
        self.engine._build_causal_chains(summary, [], [])
        return self.engine.causal_chains[0]

    def test_all_five_warnings_keep_resource_as_first_bottleneck(self):
        chain = self._chain(_forward_summary(
            allocated=1000,  # <= 100*12 → 资源输入 warning
            cr=42,
            dr=17,
            conv=0.8,
            ref_rate=6,
        ))
        warnings = [n["name"] for n in chain["nodes"] if n["status"] == "warning"]
        self.assertEqual(
            ["资源输入", "触达效率", "会话深度", "转化产出", "质量保障"],
            warnings,
        )
        self.assertEqual("资源输入", chain["bottleneck"])

    def test_reach_plus_depth_plus_convert_keeps_reach_first(self):
        chain = self._chain(_forward_summary(cr=42, dr=17, conv=0.8))
        warnings = [n["name"] for n in chain["nodes"] if n["status"] == "warning"]
        self.assertEqual(["触达效率", "会话深度", "转化产出"], warnings)
        self.assertEqual("触达效率", chain["bottleneck"])

    def test_depth_plus_convert_plus_quality_keeps_depth_first(self):
        chain = self._chain(_forward_summary(dr=17, conv=0.8, ref_rate=6))
        warnings = [n["name"] for n in chain["nodes"] if n["status"] == "warning"]
        self.assertEqual(["会话深度", "转化产出", "质量保障"], warnings)
        self.assertEqual("会话深度", chain["bottleneck"])

    def test_convert_plus_quality_keeps_convert_first(self):
        chain = self._chain(_forward_summary(conv=0.8, ref_rate=6))
        warnings = [n["name"] for n in chain["nodes"] if n["status"] == "warning"]
        self.assertEqual(["转化产出", "质量保障"], warnings)
        self.assertEqual("转化产出", chain["bottleneck"])


class ReverseTraceFirstCauseTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_cr_and_dr_and_ai_below_keep_connect_as_primary_cause(self):
        # pc<4000 arms reverse-trace; cr/dr/ai all red.
        # 主因 must stay the first matching cause (接通), not 深沟.
        self.engine._build_causal_chains(
            _forward_summary(pc=3000, cr=42, dr=17, ai=60, t20=40),
            [],
            [],
        )
        cards = [f for f in self.engine.findings if f.tag == "因果链追溯"]
        self.assertEqual(1, len(cards))
        self.assertIn("主因: 接通率", cards[0].description)
        self.assertEqual(3, len(cards[0].evidence))
        self.assertIn("接通率42%", cards[0].evidence[0])
        self.assertTrue(any("深沟率" in e for e in cards[0].evidence))
        self.assertTrue(any("AI均分" in e for e in cards[0].evidence))
        self.assertIn("正反向因果链一致", cards[0].description)


class HypothesisCountValidationTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_zero_hypotheses_emits_假设数量不足(self):
        # No trends → no H1; t20 missing → no H2; empty depts → no H3.
        self.engine._build_and_test_hypotheses({}, [], [], [])
        self.assertEqual([], self.engine.hypotheses)
        self.engine._validate_rules()
        cards = [f for f in self.engine.findings if f.tag == "假设数量不足"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertIn("当前仅建立0个假设", cards[0].description)

    def test_h1_only_still_emits_假设数量不足(self):
        trends = [
            {"total_revenue": 100000, "cr": 43, "conv": 1.0, "pc": 3000, "allocated": 1000},
            {"total_revenue": 110000, "cr": 43.2, "conv": 1.0, "pc": 3000, "allocated": 1000},
        ]
        self.engine._build_and_test_hypotheses({"t20": 40}, [], trends, [])
        self.assertEqual(["H1"], [h["id"] for h in self.engine.hypotheses])
        self.engine._validate_rules()
        cards = [f for f in self.engine.findings if f.tag == "假设数量不足"]
        self.assertEqual(1, len(cards))
        self.assertIn("当前仅建立1个假设", cards[0].description)


if __name__ == "__main__":
    unittest.main()
