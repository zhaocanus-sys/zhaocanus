"""Regression coverage for leftover H1 |Δcr|==1.5 + unknown-line QA.

PR #79 locked H1 支持 on a large connect swing and 推翻 on a large
allocation swing.
PR #109 locked the other equal gates (|Δalloc|==50, |Δpc|==200,
|Δconv| just under 0.05) and the empty-alternative 推翻 wording.

Remaining operators were never the primary lock:

- abs(cr_change) == 1.5 is reject evidence (need > 1.5)
- abs(cr_change) == 1.51 is the first support tick
- verify_transcript on an unknown line skips MUST_SAY but still
  flags FORBIDDEN tokens

A flipped `>` to `>=` on the H1 connect gate would treat a 1.5pp
wiggle as the 营收主因 and suppress the empty-driver 推翻 path.
Dropping the unknown-line MUST_SAY miss would be correct, but
dropping FORBIDDEN with it would let 保证找到 / 一定能 leak on
any line that is not hongniang/kefu.

Does not retest PR #79 large-cr 支持 wording or PR #109 alloc/pc
equal-gate silence as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine
from quality_supervision.verification_engine import verify_transcript


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


class H1ConnectChangeExact15Tests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, trends):
        self.engine._build_and_test_hypotheses({}, [], trends, [])
        h1 = [h for h in self.engine.hypotheses if h["id"] == "H1"]
        self.assertEqual(1, len(h1))
        return h1[0]

    def test_cr_change_exactly_1_5_is_reject_and_overturns(self):
        h1 = self._h1(_trend_pair(43, 44.5))
        self.assertEqual(0, len(h1["support_evidence"]))
        self.assertEqual(1, len(h1["reject_evidence"]))
        self.assertIn("幅度不大", h1["reject_evidence"][0])
        self.assertEqual("推翻", h1["verdict"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])

    def test_cr_change_exactly_minus_1_5_is_also_reject(self):
        h1 = self._h1(_trend_pair(44.5, 43))
        self.assertEqual(0, len(h1["support_evidence"]))
        self.assertIn("幅度不大", h1["reject_evidence"][0])
        self.assertEqual("推翻", h1["verdict"])

    def test_cr_change_1_51_is_first_support_tick(self):
        h1 = self._h1(_trend_pair(43, 44.51))
        self.assertEqual(1, len(h1["support_evidence"]))
        self.assertIn("幅度显著", h1["support_evidence"][0])
        self.assertEqual(0, len(h1["reject_evidence"]))
        self.assertEqual("支持", h1["verdict"])
        self.assertEqual("", h1["alternative"])


class QualityUnknownLineTests(unittest.TestCase):
    def test_unknown_line_skips_must_say_and_passes_clean_text(self):
        result = verify_transcript("正常沟通服务安排", line="telesale")
        self.assertTrue(result["pass"])
        self.assertEqual([], result["issues"])

    def test_unknown_line_still_flags_forbidden_tokens(self):
        result = verify_transcript("保证找到合适的人，一定能成功", line="unknown")
        self.assertFalse(result["pass"])
        self.assertIn("禁止用语：保证找到", result["issues"])
        self.assertIn("禁止用语：一定能", result["issues"])
        self.assertFalse(any(i.startswith("必说缺失") for i in result["issues"]))


if __name__ == "__main__":
    unittest.main()
