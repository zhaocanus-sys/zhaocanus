"""Regression coverage for leftover H3 6.1 × 11.1 × equal-AI 待定.

PR #127 locked signed 11.1 + equal AI as 待定 — but on already-qualifying
refund rates that had already passed `> 6`.
PR #130 locked refund==6.1 as first 高退费 inclusion with equal signed /
equal AI (verdicts were not the lock).
PR #131 locked 6.1 + 11.1 + *higher* AI as first 支持.

The combined leftover was never the primary lock:

- refund==6.1 + signed 11.1 vs 10 + *equal* AI is 待定
  (signed support is cancelled by the equal-AI reject)
- refund==6.1 + signed 11.1 + AI 70.1 is the first 支持 at the
  leftover AI tick on the leftover inclusion gate
- refund==6.0 + signed 11.1 + equal AI still skips H3 (`> 6`)

Does not retest PR #131 higher-AI 71 支持 or PR #127 far-refund
equal-AI as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


class H3Refund61Signed111EqualAiPendingTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h3(self, high_refund, high_signed, high_ai=70):
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            {"t20": 40, "pc": 3000},
            [
                {
                    "dept_name": "电销六部",
                    "refund_rate": high_refund,
                    "signed_deals": high_signed,
                    "avg_ai_score": high_ai,
                },
                {
                    "dept_name": "电销一部",
                    "refund_rate": 4.0,
                    "signed_deals": 10,
                    "avg_ai_score": 70,
                },
            ],
            [],
            [],
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H3"]

    def test_refund_6_1_plus_signed_11_1_equal_ai_is_pending(self):
        # 6.1 > 6 includes the department. 11.1 > 10*1.1 is support,
        # but AI 70 == 70 is not `>` so the equal-AI reject + 客服跟进
        # alternative keep the verdict at 待定. Distinct from PR #131's
        # higher-AI 支持 and PR #127's far-refund equal-AI 待定.
        h3s = self._h3(6.1, 11.1, high_ai=70)
        self.assertEqual(1, len(h3s))
        h3 = h3s[0]
        self.assertEqual("待定", h3["verdict"])
        self.assertEqual(1, len(h3["support_evidence"]))
        self.assertEqual(1, len(h3["reject_evidence"]))
        self.assertTrue(any("冲签单" in e for e in h3["support_evidence"]))
        self.assertTrue(any("整体能力问题" in e for e in h3["reject_evidence"]))
        self.assertIn("客服跟进", h3["alternative"])

    def test_refund_6_1_plus_signed_11_1_ai_70_1_is_first_support(self):
        # 70.1 > 70 is the first AI support tick on the leftover
        # 6.1×11.1 inclusion. Two supports / zero rejects → 支持.
        # Distinct from PR #131's far-higher 71.
        h3s = self._h3(6.1, 11.1, high_ai=70.1)
        self.assertEqual(1, len(h3s))
        h3 = h3s[0]
        self.assertEqual("支持", h3["verdict"])
        self.assertEqual(2, len(h3["support_evidence"]))
        self.assertEqual(0, len(h3["reject_evidence"]))
        self.assertTrue(any("冲签单" in e for e in h3["support_evidence"]))
        self.assertTrue(any("话术激进" in e for e in h3["support_evidence"]))
        self.assertEqual("", h3["alternative"])

    def test_refund_exactly_6_plus_signed_11_1_equal_ai_skips_h3(self):
        # ==6 is not `> 6`. A 贴线 6.0% department must not enter the
        # 高退费 bucket even when signed would support and AI is equal.
        # Distinct from PR #131's skip which used higher AI.
        self.assertEqual([], self._h3(6.0, 11.1, high_ai=70))


if __name__ == "__main__":
    unittest.main()
