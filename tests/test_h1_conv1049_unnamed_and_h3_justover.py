"""Regression coverage for leftover H1 conv just-under and H3 1.1× just-over.

PR #109 locked equal-gate silence with a *small* |Δcr|=0.4 reject
and warned that 1.00→1.05 is IEEE 0.050000000000000044 (would name
转化率变化). PR #124/#125 locked |Δcr|==1.5 *named* drivers at
conv==1.06 (far over 0.05) and exact alloc==50 / pc==200 unnamed.

The first tick *under* 0.05 at the |Δcr|==1.5 reject line was never
the primary lock: conv=1.049 must stay unnamed. The first tick *over*
0.05 (1.051) must name only 转化率变化.

PR #125 locked signed == low * 1.1 as reject (11 vs 10). The first
tick *over* 1.1× (11.1 vs 10) was never the primary lock — flipping
`>` to `>=` would keep that exact-reject suite green while hiding
the first real 冲签单 支持.

Does not retest PR #124/#125 named 1.06 / exact 1.1× as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def _trend_pair(cr_prev, cr_last, **last_overrides):
    prev = {
        "total_revenue": 100000,
        "cr": cr_prev,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last = {
        "total_revenue": 110000,
        "cr": cr_last,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last.update(last_overrides)
    return [prev, last]


def make_dept(name, refund_rate, signed_deals=10, avg_ai_score=70.0):
    return {
        "dept_name": name,
        "refund_rate": refund_rate,
        "signed_deals": signed_deals,
        "avg_ai_score": avg_ai_score,
    }


def _h3(engine):
    found = [h for h in engine.hypotheses if h["id"] == "H3"]
    return found[0] if found else None


class H1ConvJustUnderUnnamedTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, trends):
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses({}, [], trends, [])
        h1 = [h for h in self.engine.hypotheses if h["id"] == "H1"]
        self.assertEqual(1, len(h1))
        return h1[0]

    def test_cr_1_5_plus_conv_1_049_does_not_name_conversion(self):
        # 1.049 - 1.0 == 0.049 which is not > 0.05 (IEEE-safe).
        # PR #125 locked conv==1.06 as the named just-over.
        h1 = self._h1(_trend_pair(43, 44.5, conv=1.049))
        self.assertEqual("推翻", h1["verdict"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])

    def test_cr_1_5_plus_conv_1_051_names_only_conversion(self):
        # 1.051 - 1.0 == 0.051 > 0.05. First named-conversion tick
        # after the 1.049 silence; still below PR #125's 1.06.
        h1 = self._h1(_trend_pair(43, 44.5, conv=1.051))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_cr_1_5_plus_alloc_50_and_conv_1_049_stay_unnamed(self):
        # Both leftover exact-silence legs together: alloc==50
        # (PR #125) and conv just-under 0.05 (this run).
        h1 = self._h1(_trend_pair(43, 44.5, allocated=1050, conv=1.049))
        self.assertEqual("推翻", h1["verdict"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])


class H3SignedJustOver11xTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _run(self, depts):
        # Empty trends skip H1; no t20 skip H2. Only H3 can appear.
        self.engine._build_and_test_hypotheses(
            {"t20": 40}, depts, [], []
        )

    def test_signed_11_1_vs_10_plus_higher_ai_is_first_support(self):
        # 11.1 > 10 * 1.1 == 11.0; AI 80>70. Two supports → 支持.
        # PR #125 locked 11 == 11.0 as reject so the same AI lead
        # stayed 待定.
        self._run([
            make_dept("电销六部", 8.0, signed_deals=11.1, avg_ai_score=80.0),
            make_dept("电销一部", 3.0, signed_deals=10, avg_ai_score=70.0),
        ])
        h3 = _h3(self.engine)
        self.assertIsNotNone(h3)
        self.assertEqual("支持", h3["verdict"])
        self.assertTrue(
            any("冲签单" in e or "过度承诺" in e for e in h3["support_evidence"])
        )
        self.assertTrue(any("AI均分" in e for e in h3["support_evidence"]))
        self.assertEqual(2, len(h3["support_evidence"]))
        self.assertEqual(0, len(h3["reject_evidence"]))

    def test_signed_11_1_vs_10_plus_equal_ai_stays_pending(self):
        # Signed just-over is support; equal AI is still reject → 待定.
        self._run([
            make_dept("电销六部", 8.0, signed_deals=11.1, avg_ai_score=70.0),
            make_dept("电销一部", 3.0, signed_deals=10, avg_ai_score=70.0),
        ])
        h3 = _h3(self.engine)
        self.assertIsNotNone(h3)
        self.assertEqual("待定", h3["verdict"])
        self.assertEqual(1, len(h3["support_evidence"]))
        self.assertEqual(1, len(h3["reject_evidence"]))
        self.assertTrue(
            any("冲签单" in e or "过度承诺" in e for e in h3["support_evidence"])
        )
        self.assertIn("客服跟进", h3["alternative"])


if __name__ == "__main__":
    unittest.main()
