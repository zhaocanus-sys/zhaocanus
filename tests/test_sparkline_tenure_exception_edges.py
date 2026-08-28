"""Regression coverage for leftover sparkline, tenure-bucket, and exception edges.

PR #64 locked sparkline empty/all-None → "", flat series green + no
div-by-zero, extract chronological+today, and empty-history prev_val
baseline. PR #80 locked 规律例外 fire and tenure burnout/cliff fire.

Neither locked: downtrend red dot, fill polygon, extract missing-key /
prev_val-ignored-when-history-exists, tenure month bucket boundaries,
or 规律例外 exact 0.85 silence and first-2 description truncation.

Does not retest PR #64 empty/flat/prev_val-baseline or PR #80
burnout/cliff/规律例外 fire as the primary assertion.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from agent_system.engines.collision_engine import DataCollisionEngine, LogicCollisionEngine


def _person(name="甲", tenure_months=6, revenue=8000, ai_score=72, dial_count=100):
    return {
        "name": name,
        "tenure_months": tenure_months,
        "revenue": revenue,
        "ai_score": ai_score,
        "dial_count": dial_count,
    }


def _dept(dept_name="电销一部", **overrides):
    dept = {
        "dept_name": dept_name,
        "connect_rate": 45,
        "total_revenue": 50_000,
    }
    dept.update(overrides)
    return dept


class SparklineRemainingEdgeTests(unittest.TestCase):
    def test_downtrend_dot_is_red(self):
        svg = sparkline_svg([12, 9], fill=False)

        self.assertIn("<svg", svg)
        self.assertIn("<polyline", svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertNotIn('fill="#16a34a"', svg)

    def test_fill_true_emits_polygon_under_polyline(self):
        svg = sparkline_svg([1, 3, 2], color="#2563eb", fill=True)

        self.assertIn("<polygon", svg)
        self.assertIn('fill="#2563eb"', svg)
        self.assertIn("<polyline", svg)

    def test_mixed_none_with_two_valid_points_still_renders(self):
        svg = sparkline_svg([None, 4, None, 7])

        self.assertIn("<polyline", svg)
        self.assertIn("<circle", svg)
        # last valid 7 > 4 → green
        self.assertIn('fill="#16a34a"', svg)

    def test_extract_missing_key_becomes_zero(self):
        history = [
            {"date": "2026-03-03", "metrics": {}},
            {"date": "2026-03-02", "metrics": {"revenue": 50}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue"),
            [50.0, 0.0],
        )

    def test_extract_ignores_prev_val_when_history_exists(self):
        history = [{"date": "2026-03-02", "metrics": {"revenue": 10}}]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=20, prev_val=999),
            [10.0, 20.0],
        )

    def test_extract_omits_today_when_today_val_is_none(self):
        history = [{"date": "2026-03-02", "metrics": {"revenue": 10}}]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=None),
            [10.0],
        )


class TenureBucketBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_month_boundaries_land_in_documented_buckets(self):
        # Healthy revenues so burnout/cliff stay silent — buckets only.
        persons = [
            _person(name="m0", tenure_months=0, revenue=8000),
            _person(name="m3", tenure_months=3, revenue=8000),
            _person(name="m4", tenure_months=4, revenue=8000),
            _person(name="m12", tenure_months=12, revenue=8000),
            _person(name="m13", tenure_months=13, revenue=8000),
            _person(name="m24", tenure_months=24, revenue=8000),
            _person(name="m25", tenure_months=25, revenue=8000),
        ]

        tenure_avg = self.engine._collide_tenure_x_productivity(
            {"pc": 8000}, persons
        )

        self.assertEqual(2, tenure_avg["新人(≤3月)"]["count"])
        self.assertEqual(2, tenure_avg["成长期(4-12月)"]["count"])
        self.assertEqual(2, tenure_avg["成熟期(1-2年)"]["count"])
        self.assertEqual(1, tenure_avg["老员工(>2年)"]["count"])
        self.assertEqual([], self.engine.findings)


class RuleExceptionRemainingEdgeTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_revenue_exactly_at_85_percent_of_mean_is_silent(self):
        # avg_cr=45, avg_rev=10000; 一部 cr>45 but rev == 8500 == 0.85*mean
        depts = [
            _dept(dept_name="电销一部", connect_rate=50, total_revenue=8_500),
            _dept(dept_name="电销二部", connect_rate=40, total_revenue=11_500),
        ]

        self.engine._rule_exception_analysis({}, depts, [])

        self.assertEqual([], self.engine.findings)

    def test_description_keeps_first_two_exceptions_evidence_keeps_all(self):
        depts = [
            _dept(dept_name="电销一部", connect_rate=60, total_revenue=10_000),
            _dept(dept_name="电销二部", connect_rate=61, total_revenue=10_000),
            _dept(dept_name="电销三部", connect_rate=62, total_revenue=10_000),
            _dept(dept_name="电销四部", connect_rate=20, total_revenue=100_000),
        ]
        # avg_cr=50.75, avg_rev=32500; first three all cr>avg and rev<0.85*avg

        self.engine._rule_exception_analysis({}, depts, [])

        self.assertEqual(1, len(self.engine.findings))
        finding = self.engine.findings[0]
        self.assertEqual("规律例外发现", finding.tag)
        self.assertEqual(3, len(finding.evidence))
        self.assertTrue(any("电销一部" in e for e in finding.evidence))
        self.assertTrue(any("电销三部" in e for e in finding.evidence))
        self.assertIn("电销一部", finding.description)
        self.assertIn("电销二部", finding.description)
        self.assertNotIn("电销三部", finding.description)


if __name__ == "__main__":
    unittest.main()
