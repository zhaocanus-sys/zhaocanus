"""Regression coverage for leftover H3 refund 6.1 × signed 11.1 支持.

PR #125 locked signed==1.1x as reject (11.0 vs 10).
PR #127 locked 11.1 vs 10 + higher AI as first 支持 — but on
already-qualifying refund rates that had already passed `> 6`.
PR #128 locked 11.1 vs 10 + lower AI as 待定.
PR #130 locked refund==6.1 as first 高退费 inclusion with equal
signed / equal AI (H3 builds, verdicts were not the lock).

The combined leftover was never the primary lock:

- refund==6.1 + signed 11.1 vs 10 + higher AI is the first 支持
  at both leftover ticks together
- refund==6.1 + signed 11.0 + higher AI stays 待定 (signed == 1.1x
  reject offsets the AI support)
- refund==6.0 + signed 11.1 + higher AI still skips H3 (`> 6`)

Does not retest PR #130 inclusion-only or PR #127 far-refund 11.1
as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


class H3Refund61PlusSigned111FirstSupportTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h3(self, high_refund, high_signed, high_ai=71):
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

    def test_refund_6_1_plus_signed_11_1_higher_ai_is_first_support(self):
        # 6.1 > 6 includes the department; 11.1 > 10*1.1 and AI 71>70
        # are both support ticks. Together they are the first 支持 at
        # the leftover inclusion gate. Distinct from PR #127's far
        # refund + 11.1 and PR #130's equal-signed inclusion.
        h3s = self._h3(6.1, 11.1, high_ai=71)
        self.assertEqual(1, len(h3s))
        h3 = h3s[0]
        self.assertEqual("支持", h3["verdict"])
        self.assertEqual(2, len(h3["support_evidence"]))
        self.assertEqual(0, len(h3["reject_evidence"]))
        self.assertTrue(any("冲签单" in e for e in h3["support_evidence"]))
        self.assertTrue(any("话术激进" in e for e in h3["support_evidence"]))
        self.assertEqual("", h3["alternative"])

    def test_refund_6_1_plus_signed_11_0_higher_ai_stays_pending(self):
        # 11.0 == 10*1.1 is still reject (need `>`). AI support cannot
        # outvote it, so 待定. Flipping signed `>` to `>=` would keep
        # the far-refund 11.1 支持 suite green while promoting a 贴线
        # 1.1x day to 冲签单.
        h3s = self._h3(6.1, 11.0, high_ai=71)
        self.assertEqual(1, len(h3s))
        h3 = h3s[0]
        self.assertEqual("待定", h3["verdict"])
        self.assertEqual(1, len(h3["support_evidence"]))
        self.assertEqual(1, len(h3["reject_evidence"]))
        self.assertTrue(any("并不高于" in e for e in h3["reject_evidence"]))
        self.assertTrue(any("话术激进" in e for e in h3["support_evidence"]))

    def test_refund_exactly_6_plus_signed_11_1_skips_h3(self):
        # ==6 is not `> 6`. A 贴线 6.0% department must not enter the
        # 高退费 bucket even when signed/AI would otherwise 支持.
        self.assertEqual([], self._h3(6.0, 11.1, high_ai=71))


if __name__ == "__main__":
    unittest.main()
