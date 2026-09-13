"""Regression coverage for leftover summary on_duty==0 with live revenue.

PR #82 locked *empty* depts: `or 1` keeps pc/avg_deal finite (1).
A day that still has revenue but summed on_duty==0 was never the
primary lock. `pc = round(rv / (on_duty or 1))` then equals
total_revenue, and AI/duration weights collapse to 0 because they
multiply by raw on_duty before dividing by the sentinel.

Flipping `or 1` to a skip, or using raw 0 in the pc divisor, would
either ZeroDivisionError or report pc=0 on a 有营收零在岗 day —
wrong input for H2 impact and exec-facing 人均产值.

Does not retest PR #82 empty-dept ratios as primary.
Does not lock `_collide_dept_variance` pc==0 ZeroDivisionError.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline


def make_row(**overrides):
    row = {
        "head_count": 10,
        "on_duty": 0,
        "new_hire": 0,
        "allocated": 100,
        "dial_count": 200,
        "link_1d_num": 20,
        "deep_talk": 4,
        "first_call_conv": 1,
        "signed_deals": 2,
        "total_revenue": 5000,
        "refund_count": 0,
        "refund_amount": 0,
        "complaint_count": 0,
        "jx_transfer_in": 0,
        "jx_signed": 0,
        "pool_in": 0,
        "pool_retrieval": 0,
        "pool_signed": 0,
        "peak_hour_revenue": 3000,
        "offpeak_hour_revenue": 2000,
        "avg_ai_score": 80.0,
        "avg_call_dur": 120,
        "avg_connect_dur": 90,
        "avg_deep_dur": 180,
        "top20_pct": 40,
        "alloc_rate": 0.8,
    }
    row.update(overrides)
    return row


class SummaryOnDutyZeroPcTests(unittest.TestCase):
    def setUp(self):
        self.pipe = AnalysisPipeline(db_path=":memory:")

    def test_on_duty_zero_with_revenue_sets_pc_to_total_revenue(self):
        # 5000 / (0 or 1) == 5000. on_duty itself stays 0.
        summary = self.pipe._aggregate_summary([make_row()], "2026-09-13")
        self.assertEqual(0, summary["on_duty"])
        self.assertEqual(5000, summary["total_revenue"])
        self.assertEqual(5000, summary["pc"])

    def test_on_duty_zero_roi_uses_sentinel_headcount(self):
        # roi = round(5000 / (1 * 280) * 100, 1) == 1785.7
        summary = self.pipe._aggregate_summary([make_row()], "2026-09-13")
        self.assertEqual(1785.7, summary["roi"])

    def test_all_zero_duty_collapses_weighted_ai_and_duration(self):
        # Weights multiply raw on_duty (0) then divide by sentinel 1.
        # Live scores 90/60 must not leak into ai/dur.
        summary = self.pipe._aggregate_summary(
            [
                make_row(total_revenue=3000, avg_ai_score=90.0, avg_call_dur=200),
                make_row(total_revenue=2000, avg_ai_score=60.0, avg_call_dur=40),
            ],
            "2026-09-13",
        )
        self.assertEqual(0, summary["on_duty"])
        self.assertEqual(5000, summary["pc"])
        self.assertEqual(0.0, summary["ai"])
        self.assertEqual(0, summary["dur"])
        self.assertEqual(0, summary["conn_dur"])
        self.assertEqual(0, summary["deep_dur"])

    def test_t20_and_deal_still_use_live_revenue_when_duty_is_zero(self):
        # t20_rev = 3000*50/100 + 2000*25/100 = 1500+500=2000 → 40.0%
        # avg_deal = round(5000 / 4) = 1250
        summary = self.pipe._aggregate_summary(
            [
                make_row(
                    total_revenue=3000,
                    signed_deals=1,
                    top20_pct=50,
                ),
                make_row(
                    total_revenue=2000,
                    signed_deals=3,
                    top20_pct=25,
                ),
            ],
            "2026-09-13",
        )
        self.assertEqual(40.0, summary["t20"])
        self.assertEqual(1250, summary["avg_deal"])


if __name__ == "__main__":
    unittest.main()
