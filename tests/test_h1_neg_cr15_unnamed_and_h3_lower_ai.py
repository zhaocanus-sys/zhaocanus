"""Regression coverage for leftover H1 falling-CR silence and H3 lower-AI.

PR #127 locked |Δcr|==+1.5 (43→44.5) + conv=1.049 unnamed / 1.051 named.
The falling-CR leg was never the primary lock: 44.5→43 is still
abs==1.5, so it must reject as 幅度不大. Flipping `abs(cr)>1.5` to
`>=` would keep the +1.5 suite green while naming a 0.049pp wobble
as 转化率变化 on a 营收下降 day.

PR #127 locked H3 signed 11.1 vs 10 + higher/equal AI. The third
production leg — high-refund AI *lower* than low-refund — still
rejects and stays 待定 with 客服跟进. Flipping `hr_avg_ai > lr`
to `>=` (or dropping the else) would hide 能力/服务 as the
alternative on a 贴线冲签单 day.

Does not retest PR #127 +1.5 / equal-AI as primary.
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


class H1NegativeCrJustUnderUnnamedTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, trends):
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses({}, [], trends, [])
        h1 = [h for h in self.engine.hypotheses if h["id"] == "H1"]
        self.assertEqual(1, len(h1))
        return h1[0]

    def test_cr_minus_1_5_plus_conv_1_049_unnamed_on_decline(self):
        # 43.0 - 44.5 == -1.5, abs is not > 1.5. 1.049 - 1.0 == 0.049
        # is not > 0.05. Mirror of PR #127's +1.5 + 1.049 on a 下降 day.
        h1 = self._h1(_trend_pair(44.5, 43.0, conv=1.049, total_revenue=90000))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("下降", h1["hypothesis"])
        self.assertTrue(any("幅度不大" in e for e in h1["reject_evidence"]))
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])

    def test_cr_minus_1_5_plus_conv_1_051_names_only_conversion(self):
        # Same reject-CR line; 1.051 - 1.0 == 0.051 > 0.05 names only
        # 转化率变化. First named-conversion tick on the falling-CR
        # leftover after PR #127's rising-CR 1.051.
        h1 = self._h1(_trend_pair(44.5, 43.0, conv=1.051, total_revenue=90000))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("下降", h1["hypothesis"])
        self.assertIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_cr_minus_1_6_is_first_falling_support(self):
        # 43.4 - 45.0 == -1.6, abs > 1.5. No alloc/pc reject → 支持.
        # Distinct from PR #127's +1.5 reject and this file's -1.5 reject.
        h1 = self._h1(_trend_pair(45.0, 43.4, total_revenue=90000))
        self.assertEqual("支持", h1["verdict"])
        self.assertIn("下降", h1["hypothesis"])
        self.assertTrue(any("幅度显著" in e for e in h1["support_evidence"]))
        self.assertEqual(1, len(h1["support_evidence"]))
        self.assertEqual(0, len(h1["reject_evidence"]))
        self.assertEqual("", h1["alternative"])

    def test_flat_revenue_uses_decline_wording(self):
        # rev_change == 0 is not > 0, so the hypothesis says 下降.
        # Flipping `>` to `>=` would label a 持平日 as 增长.
        h1 = self._h1(_trend_pair(43.0, 44.5, total_revenue=100000))
        self.assertIn("下降", h1["hypothesis"])
        self.assertNotIn("增长", h1["hypothesis"])
        self.assertEqual("推翻", h1["verdict"])


class H3SignedJustOverLowerAiTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _run(self, depts):
        # Empty trends skip H1; t20<=50 skips H2. Only H3 can appear.
        self.engine._build_and_test_hypotheses(
            {"t20": 40}, depts, [], []
        )

    def test_signed_11_1_vs_10_plus_lower_ai_stays_pending(self):
        # 11.1 > 10 * 1.1 == 11.0 is support; 65 < 70 is reject.
        # 1==1 → 待定 + 客服跟进. PR #127 locked higher/equal AI only.
        self._run([
            make_dept("电销六部", 8.0, signed_deals=11.1, avg_ai_score=65.0),
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
        self.assertTrue(any("更低" in e for e in h3["reject_evidence"]))
        self.assertTrue(any("整体能力问题" in e for e in h3["reject_evidence"]))
        self.assertIn("客服跟进", h3["alternative"])


if __name__ == "__main__":
    unittest.main()
