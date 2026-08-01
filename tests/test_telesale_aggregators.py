"""Regression coverage for telesale report aggregation boundaries.

Covers:
- agg_telesale zero-denominator rate safety, AI>0 averaging, numeric string parsing
- dept_rows multi-row merge, manager attribution, revenue sort, call/link fallbacks
- color_kpi threshold banding for higher/lower-is-better metrics
- prev_date month/year calendar rollbacks

Deterministic stdlib unittest; no network or live database required.
"""

from __future__ import annotations

import unittest

from generate_telesale_full_report import (
    DEPT_MANAGERS,
    agg_telesale,
    color_kpi,
    dept_rows,
    prev_date,
)


def _row(**overrides):
    base = {
        "dept_name": "电销一部",
        "worker_nums": "10",
        "pay_1d_amt": "10000",
        "callout_1d_num": "100",
        "link_1d_num": "40",
        "linkmems_deeptalk_10_1d_num": "12",
        "pay_1d_num": "2",
        "pay_1m_amt": "50000",
        "new_worker_num": "1",
        "ai_score": "80",
    }
    base.update(overrides)
    return base


class AggTelesaleTests(unittest.TestCase):
    def test_agg_telesale_computes_funnel_rates_and_filters_zero_ai(self):
        rows = [
            _row(pay_1d_amt="10000", callout_1d_num="100", link_1d_num="40",
                 linkmems_deeptalk_10_1d_num="10", pay_1d_num="2",
                 worker_nums="5", ai_score="80"),
            _row(pay_1d_amt="5,000.5", callout_1d_num="100", link_1d_num="60",
                 linkmems_deeptalk_10_1d_num="20", pay_1d_num="3",
                 worker_nums="5", ai_score="0"),  # ignored in AI average
            _row(pay_1d_amt="0", callout_1d_num="0", link_1d_num="0",
                 linkmems_deeptalk_10_1d_num="0", pay_1d_num="0",
                 worker_nums="0", ai_score="90"),
        ]

        result = agg_telesale(rows)

        self.assertAlmostEqual(result["total_rev"], 15000.5)
        self.assertEqual(result["workers"], 10)
        self.assertEqual(result["calls"], 200)
        self.assertEqual(result["links"], 100)
        self.assertEqual(result["deep"], 30)
        self.assertEqual(result["signed"], 5)
        self.assertAlmostEqual(result["connect_rate"], 50.0)
        self.assertAlmostEqual(result["deep_rate"], 30.0)
        self.assertAlmostEqual(result["conv_rate"], 5 / 30 * 100)
        self.assertAlmostEqual(result["per_capita"], 1500.05)
        # Only ai_score 80 and 90 count; zero is excluded
        self.assertAlmostEqual(result["avg_ai"], 85.0)

    def test_agg_telesale_empty_and_zero_activity_stay_finite(self):
        empty = agg_telesale([])
        self.assertEqual(empty["total_rev"], 0)
        self.assertEqual(empty["connect_rate"], 0)
        self.assertEqual(empty["deep_rate"], 0)
        self.assertEqual(empty["conv_rate"], 0)
        self.assertEqual(empty["per_capita"], 0)
        self.assertEqual(empty["avg_ai"], 0)

        zero_calls = agg_telesale([
            _row(callout_1d_num="0", link_1d_num="0",
                 linkmems_deeptalk_10_1d_num="0", pay_1d_num="0",
                 worker_nums="0", ai_score="0"),
        ])
        self.assertEqual(zero_calls["connect_rate"], 0)
        self.assertEqual(zero_calls["deep_rate"], 0)
        self.assertEqual(zero_calls["conv_rate"], 0)
        self.assertEqual(zero_calls["per_capita"], 0)


class DeptRowsTests(unittest.TestCase):
    def test_dept_rows_merges_sorts_and_attaches_managers(self):
        rows = [
            _row(dept_name="电销六部", pay_1d_amt="30000", worker_nums="10",
                 callout_1d_num="200", link_1d_num="80",
                 linkmems_deeptalk_10_1d_num="20", ai_score="70"),
            _row(dept_name="电销六部", pay_1d_amt="20000", worker_nums="5",
                 callout_1d_num="100", link_1d_num="40",
                 linkmems_deeptalk_10_1d_num="10", ai_score="90"),
            _row(dept_name="电销一部", pay_1d_amt="10000", worker_nums="8",
                 callout_1d_num="80", link_1d_num="20",
                 linkmems_deeptalk_10_1d_num="4", ai_score="0"),
            _row(dept_name="未知临时组", pay_1d_amt="5000", worker_nums="2",
                 callout_1d_num="0", link_1d_num="0",
                 linkmems_deeptalk_10_1d_num="0", ai_score="60"),
        ]

        result = dept_rows(rows)
        names = [d["dept_name"] for d in result]
        self.assertEqual(names, ["电销六部", "电销一部", "未知临时组"])

        d6 = result[0]
        self.assertEqual(d6["worker_nums"], 15)
        self.assertEqual(d6["pay_1d_amt"], 50000)
        self.assertEqual(d6["callout_1d_num"], 300)
        self.assertEqual(d6["link_1d_num"], 120)
        self.assertAlmostEqual(d6["per_capita"], 50000 / 15)
        self.assertAlmostEqual(d6["connect_rate"], 120 / 300 * 100)
        self.assertAlmostEqual(d6["deep_rate"], 30 / 120 * 100)
        self.assertAlmostEqual(d6["avg_ai"], 80.0)
        self.assertEqual(d6["manager"], DEPT_MANAGERS["电销六部"])

        d1 = result[1]
        self.assertEqual(d1["manager"], DEPT_MANAGERS["电销一部"])
        self.assertEqual(d1["avg_ai"], 0)  # only zero AI scores → no average

        unknown = result[2]
        self.assertEqual(unknown["manager"], "（待确认）")
        # zero calls uses `or 1` denominator → finite 0% connect rate
        self.assertEqual(unknown["connect_rate"], 0.0)
        self.assertEqual(unknown["deep_rate"], 0)
        self.assertAlmostEqual(unknown["per_capita"], 2500.0)
        self.assertAlmostEqual(unknown["avg_ai"], 60.0)


class ColorKpiAndPrevDateTests(unittest.TestCase):
    def test_color_kpi_bands_for_higher_and_lower_is_better(self):
        # higher_is_better: green >= green_thresh, orange >= red_thresh, else red
        self.assertEqual(color_kpi(50, 45, 35, higher_is_better=True), "#27ae60")
        self.assertEqual(color_kpi(40, 45, 35, higher_is_better=True), "#e67e22")
        self.assertEqual(color_kpi(30, 45, 35, higher_is_better=True), "#e74c3c")
        self.assertEqual(color_kpi(45, 45, 35, higher_is_better=True), "#27ae60")
        self.assertEqual(color_kpi(35, 45, 35, higher_is_better=True), "#e67e22")

        # lower_is_better (e.g. refund rate): green <= green_thresh
        self.assertEqual(color_kpi(3, 4.5, 6, higher_is_better=False), "#27ae60")
        self.assertEqual(color_kpi(5, 4.5, 6, higher_is_better=False), "#e67e22")
        self.assertEqual(color_kpi(7, 4.5, 6, higher_is_better=False), "#e74c3c")
        self.assertEqual(color_kpi(4.5, 4.5, 6, higher_is_better=False), "#27ae60")
        self.assertEqual(color_kpi(6, 4.5, 6, higher_is_better=False), "#e67e22")

    def test_prev_date_rolls_across_month_and_year(self):
        self.assertEqual(prev_date("20260301"), "20260228")
        self.assertEqual(prev_date("20260101"), "20251231")
        self.assertEqual(prev_date("20260227"), "20260226")


if __name__ == "__main__":
    unittest.main()
