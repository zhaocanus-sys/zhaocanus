"""Regression coverage for leftover H3 exact ties and 2-hypothesis validation.

PR #80 locked H3 支持 when high-refund depts clearly out-sign and
out-score, and 待定 when they do neither.
PR #110 locked the skip when a high+low refund pair is missing.
PR #124 locked 假设数量不足 on 0 / H1-only payloads.

Remaining operators were never the primary lock:

- signed == low * 1.1 is reject (need >), so a just-on-threshold
  high-refund dept plus higher AI is 1-1 → 待定
- equal AI is reject and still names 客服跟进, even when signed
  is well over 1.1×
- signed == 1.1× AND equal AI → two rejects, still 待定
- H1+H2 (exactly 2) still emits 假设数量不足
- get_summary counts 部分推翻 / 待定 as neither 支持 nor 推翻

Flipping `>` to `>=` on the signed 1.1× gate would turn a 贴线
签单日 into 支持 and hide the 客服跟进 alternative. Counting
部分推翻 as 推翻 would inflate the executive-summary 推翻 tally
on every TOP20% 集中日.

Does not retest PR #80 far 支持/待定 wording or PR #124 0/H1-only
as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_summary(**overrides):
    summary = {
        "allocated": 2000,
        "dial_count": 10000,
        "link_1d_num": 3000,
        "deep_talk": 600,
        "signed_deals": 40,
        "on_duty": 100,
        "cr": 45,
        "dr": 20,
        "ai": 75,
        "conv": 1.2,
        "pc": 5000,
        "total_revenue": 500000,
        "ref_rate": 3,
        "complaint_count": 2,
        "alloc_rate": 0.9,
        "t20": 40,
        "roi": 180,
    }
    summary.update(overrides)
    return summary


def make_dept(name, refund_rate, signed_deals=10, avg_ai_score=70.0):
    return {
        "dept_name": name,
        "refund_rate": refund_rate,
        "signed_deals": signed_deals,
        "avg_ai_score": avg_ai_score,
    }


def _trend_pair():
    # |Δcr|=0.4 → H1 reject / 推翻 (PR #109 composition path).
    return [
        {
            "total_revenue": 100000,
            "cr": 43.0,
            "conv": 1.0,
            "pc": 3000,
            "allocated": 1000,
        },
        {
            "total_revenue": 110000,
            "cr": 43.4,
            "conv": 1.0,
            "pc": 3000,
            "allocated": 1000,
        },
    ]


def _small_gap_persons():
    """10-person roster: H2 AI/dials gaps stay in the reject band → 部分推翻."""
    return [
        {"name": "T1", "revenue": 10000, "ai_score": 70, "dial_count": 50},
        {"name": "T2", "revenue": 9000, "ai_score": 70, "dial_count": 50},
        {"name": "M1", "revenue": 5000, "ai_score": 69, "dial_count": 49},
        {"name": "M2", "revenue": 4500, "ai_score": 69, "dial_count": 49},
        {"name": "M3", "revenue": 4000, "ai_score": 69, "dial_count": 49},
        {"name": "M4", "revenue": 3500, "ai_score": 68, "dial_count": 48},
        {"name": "M5", "revenue": 3000, "ai_score": 68, "dial_count": 48},
        {"name": "B1", "revenue": 1000, "ai_score": 68, "dial_count": 48},
        {"name": "B2", "revenue": 900, "ai_score": 68, "dial_count": 48},
        {"name": "B3", "revenue": 800, "ai_score": 68, "dial_count": 48},
    ]


def _h3(engine):
    found = [h for h in engine.hypotheses if h["id"] == "H3"]
    return found[0] if found else None


class H3ExactGateTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _run(self, depts):
        # Empty trends skip H1; t20=40 skips H2. Only H3 can appear.
        self.engine._build_and_test_hypotheses(make_summary(), depts, [], [])

    def test_signed_exactly_1_1x_is_reject_so_ai_lead_stays_pending(self):
        # 11 == 10 * 1.1 → signed reject; AI 80>70 → support. 1-1 → 待定.
        self._run([
            make_dept("电销六部", 8.0, signed_deals=11, avg_ai_score=80.0),
            make_dept("电销一部", 3.0, signed_deals=10, avg_ai_score=70.0),
        ])
        h3 = _h3(self.engine)
        self.assertIsNotNone(h3)
        self.assertEqual("待定", h3["verdict"])
        self.assertTrue(
            any("签单量并不高于" in e for e in h3["reject_evidence"])
        )
        self.assertTrue(any("AI均分" in e for e in h3["support_evidence"]))
        self.assertEqual(1, len(h3["support_evidence"]))
        self.assertEqual(1, len(h3["reject_evidence"]))

    def test_equal_ai_is_reject_and_names_service_followup(self):
        # signed 20 vs 10 is well over 1.1× → support; AI 70==70 → reject.
        self._run([
            make_dept("电销六部", 8.0, signed_deals=20, avg_ai_score=70.0),
            make_dept("电销一部", 3.0, signed_deals=10, avg_ai_score=70.0),
        ])
        h3 = _h3(self.engine)
        self.assertIsNotNone(h3)
        self.assertEqual("待定", h3["verdict"])
        self.assertIn("客服跟进", h3["alternative"])
        self.assertTrue(
            any("整体能力问题" in e for e in h3["reject_evidence"])
        )
        self.assertTrue(
            any("冲签单" in e or "过度承诺" in e for e in h3["support_evidence"])
        )

    def test_signed_1_1x_and_equal_ai_are_two_rejects(self):
        self._run([
            make_dept("电销六部", 8.0, signed_deals=11, avg_ai_score=70.0),
            make_dept("电销一部", 3.0, signed_deals=10, avg_ai_score=70.0),
        ])
        h3 = _h3(self.engine)
        self.assertIsNotNone(h3)
        self.assertEqual("待定", h3["verdict"])
        self.assertEqual(0, len(h3["support_evidence"]))
        self.assertEqual(2, len(h3["reject_evidence"]))
        self.assertIn("客服跟进", h3["alternative"])


class TwoHypothesisValidationAndSummaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_h1_plus_h2_still_flags_insufficient_hypotheses(self):
        # Mid-band refunds skip H3 → exactly 2 hypotheses.
        depts = [
            make_dept("电销一部", 5.0),
            make_dept("电销二部", 5.5),
        ]
        self.engine._build_and_test_hypotheses(
            make_summary(t20=60), depts, _trend_pair(), _small_gap_persons()
        )
        self.engine._validate_rules()
        ids = [h["id"] for h in self.engine.hypotheses]
        self.assertEqual(["H1", "H2"], ids)
        flags = [f for f in self.engine.findings if f.tag == "假设数量不足"]
        self.assertEqual(1, len(flags))
        self.assertEqual("P2", flags[0].priority)
        self.assertIn("仅建立2个假设", flags[0].description)

    def test_summary_excludes_partial_and_pending_from_support_reject(self):
        depts = [
            make_dept("电销六部", 8.0, signed_deals=11, avg_ai_score=70.0),
            make_dept("电销一部", 3.0, signed_deals=10, avg_ai_score=70.0),
        ]
        self.engine._build_and_test_hypotheses(
            make_summary(t20=60), depts, _trend_pair(), _small_gap_persons()
        )
        self.engine._validate_rules()
        summary = self.engine.get_summary()
        self.assertEqual(3, summary["total_hypotheses"])
        # H1 推翻, H2 部分推翻, H3 待定 — only 推翻 counts as rejected.
        self.assertEqual(0, summary["hypotheses_supported"])
        self.assertEqual(1, summary["hypotheses_rejected"])
        self.assertTrue(summary["rules_satisfied"])
        self.assertFalse(
            any(f.tag == "假设数量不足" for f in self.engine.findings)
        )
        h2 = next(h for h in self.engine.hypotheses if h["id"] == "H2")
        h3 = next(h for h in self.engine.hypotheses if h["id"] == "H3")
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertEqual("待定", h3["verdict"])


if __name__ == "__main__":
    unittest.main()
