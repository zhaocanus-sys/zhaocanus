"""Regression coverage for LogicCollision H3 refund-band skip.

PR #80 locked H3 支持 / 待定 when both a high-refund department
(refund_rate > 6) and a low-refund department (refund_rate <= 4)
are present. It did not lock the skip when that pair is missing.

Does not retest PR #80 H3 支持/待定 verdicts, or PR #79/#109 H1 /
PR #80/#108 H2, as the primary assertion.

Deterministic stdlib unittest only — no network/DB.
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


def _h3_ids(engine):
    return [h["id"] for h in engine.hypotheses if h["id"] == "H3"]


class H3RefundBandSkipTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _run(self, depts):
        # Empty trends skip H1; t20=40 skips H2. Only H3 can appear.
        self.engine._build_and_test_hypotheses(make_summary(), depts, [], [])

    def test_only_high_refund_depts_skip_h3(self):
        self._run([
            make_dept("电销一部", 7.0),
            make_dept("电销二部", 8.5),
        ])
        self.assertEqual([], _h3_ids(self.engine))

    def test_only_low_refund_depts_skip_h3(self):
        self._run([
            make_dept("电销一部", 3.0),
            make_dept("电销二部", 4.0),
        ])
        self.assertEqual([], _h3_ids(self.engine))

    def test_only_mid_band_refund_depts_skip_h3(self):
        # 4 < rate <= 6 is neither high nor low
        self._run([
            make_dept("电销一部", 5.0),
            make_dept("电销二部", 6.0),
        ])
        self.assertEqual([], _h3_ids(self.engine))

    def test_empty_depts_skip_h3(self):
        self._run([])
        self.assertEqual([], _h3_ids(self.engine))

    def test_high_plus_mid_without_low_skips_h3(self):
        self._run([
            make_dept("电销一部", 7.2),
            make_dept("电销二部", 5.5),
        ])
        self.assertEqual([], _h3_ids(self.engine))

    def test_low_plus_mid_without_high_skips_h3(self):
        self._run([
            make_dept("电销一部", 3.5),
            make_dept("电销二部", 5.5),
        ])
        self.assertEqual([], _h3_ids(self.engine))

    def test_refund_rate_exactly_6_is_not_high(self):
        # 6.0 is mid; paired with a true low still has no high bucket
        self._run([
            make_dept("电销一部", 6.0),
            make_dept("电销二部", 4.0),
        ])
        self.assertEqual([], _h3_ids(self.engine))

    def test_just_over_6_plus_low_emits_h3(self):
        self._run([
            make_dept("电销一部", 6.01, signed_deals=12, avg_ai_score=72.0),
            make_dept("电销二部", 4.0, signed_deals=10, avg_ai_score=70.0),
        ])
        self.assertEqual(["H3"], _h3_ids(self.engine))

    def test_just_over_4_is_not_low(self):
        self._run([
            make_dept("电销一部", 6.01),
            make_dept("电销二部", 4.01),
        ])
        self.assertEqual([], _h3_ids(self.engine))


if __name__ == "__main__":
    unittest.main()
