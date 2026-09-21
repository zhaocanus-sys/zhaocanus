"""Regression coverage for leftover H1 falling |Δcr|==1.51 first 支持.

PR #123–#127 locked |Δcr|==1.5 as reject (幅度不大).
PR #128 locked the first *falling* support at -1.6 (45.0→43.4).
PR #133 locked the first *rising* support at +1.51 (43.0→44.51).

The leftover falling counterpart of +1.51 was never the primary lock:

- 44.51→43.0 == -1.51 is the first falling 支持 (`abs > 1.5`)
- 44.5→43.0 == -1.5 stays 推翻 + 幅度不大
- leftover -1.51 + alloc==51 is a 1-1 tie → still 支持
  (`reject > support` is false)
- leftover -1.51 + alloc==50 stays 支持 (alloc not a reject)

Does not retest PR #128 falling -1.6 or PR #133 rising +1.51 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


class H1Falling151FirstSupportTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, cr_prev, cr_last, alloc_prev=1000, alloc_last=1000):
        self.engine.hypotheses = []
        self.engine.findings = []
        self.engine._build_and_test_hypotheses(
            {"t20": 40, "pc": 3000},
            [{"dept_name": "电销六部", "refund_rate": 5, "signed_deals": 10, "avg_ai_score": 70}],
            [
                {
                    "total_revenue": 101000,
                    "cr": cr_prev,
                    "conv": 2.0,
                    "pc": 3000,
                    "allocated": alloc_prev,
                },
                {
                    "total_revenue": 100000,
                    "cr": cr_last,
                    "conv": 2.0,
                    "pc": 3000,
                    "allocated": alloc_last,
                },
            ],
            [],
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H1"]

    def test_cr_minus_1_51_is_first_falling_support(self):
        # Mirror of PR #133's 43.0→44.51. Distinct from PR #128's -1.6.
        h1s = self._h1(44.51, 43.0)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("支持", h1["verdict"])
        self.assertEqual(1, len(h1["support_evidence"]))
        self.assertEqual(0, len(h1["reject_evidence"]))
        self.assertTrue(any("接通率变动" in e and "幅度显著" in e
                            for e in h1["support_evidence"]))
        self.assertIn("下降", h1["hypothesis"])
        self.assertEqual("", h1["alternative"])

    def test_cr_minus_exactly_1_5_stays_rejected(self):
        # 43.0 - 44.5 == -1.5 is not `abs > 1.5`. Flipping to `>=`
        # would keep PR #128's -1.6 suite green while promoting a
        # 贴线下跌日 to 接通率主因.
        h1s = self._h1(44.5, 43.0)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("推翻", h1["verdict"])
        self.assertEqual(0, len(h1["support_evidence"]))
        self.assertEqual(1, len(h1["reject_evidence"]))
        self.assertTrue(any("幅度不大" in e for e in h1["reject_evidence"]))
        self.assertIn("营收变动主因可能是:", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_leftover_falling_151_plus_alloc_51_is_still_support(self):
        # 1 support (幅度显著) + 1 reject (分配量变动51) → reject is
        # not strictly greater → 支持, empty alternative.
        # Distinct from PR #124's |Δcr|==1.5 + alloc==51 推翻.
        h1s = self._h1(44.51, 43.0, alloc_prev=1000, alloc_last=1051)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("支持", h1["verdict"])
        self.assertEqual(1, len(h1["support_evidence"]))
        self.assertEqual(1, len(h1["reject_evidence"]))
        self.assertTrue(any("分配量变动+51条" in e for e in h1["reject_evidence"]))
        self.assertEqual("", h1["alternative"])

    def test_leftover_falling_151_plus_alloc_50_stays_support(self):
        # ==50 is not `> 50`. Leftover falling 1.51 still needs no
        # extra reject to stay 支持.
        h1s = self._h1(44.51, 43.0, alloc_prev=1000, alloc_last=1050)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("支持", h1["verdict"])
        self.assertEqual(0, len(h1["reject_evidence"]))
        self.assertNotIn("分配量变化", h1["alternative"])


if __name__ == "__main__":
    unittest.main()
