# -*- coding: utf-8 -*-
import re
import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from agent_system.engines.collision_engine import validate_feasibility
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html
from quality_supervision.verification_engine import verify_transcript


class AppTrendRegressionTests(unittest.TestCase):
    def test_build_trend_data_groups_sorts_and_derives_rates(self):
        rows = [
            {
                "ftime": "202602270900",
                "amt": "300",
                "pay_num": "3",
                "active_members": "30",
                "refund_money": "9",
                "retain_1d": "6",
                "order_cnt": "10",
                "order_pay": "5",
                "anchmems": "2",
                "giftmems": "4",
                "fugou_amt": "30",
            },
            {
                "ftime": "202602260900",
                "amt": "100",
                "pay_num": "2",
                "active_members": "20",
                "refund_money": "1",
                "retain_1d": "4",
                "order_cnt": "4",
                "order_pay": "2",
                "anchmems": "1",
                "giftmems": "2",
                "fugou_amt": "10",
            },
            {
                "ftime": "202602271200",
                "amt": "200",
                "pay_num": "2",
                "active_members": "20",
                "refund_money": "2",
                "retain_1d": "4",
                "order_cnt": "5",
                "order_pay": "5",
                "anchmems": "3",
                "giftmems": "6",
                "fugou_amt": "20",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([d["dt"] for d in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[1]["amt"], 500)
        self.assertEqual(trends[1]["pay_num"], 5)
        self.assertEqual(trends[1]["active_members"], 50)
        self.assertEqual(trends[1]["arpu"], 100)
        self.assertEqual(trends[1]["pay_rate"], 10)
        self.assertAlmostEqual(trends[1]["order_conv"], 10 / 15 * 100)

    def test_build_trend_data_handles_zero_denominators(self):
        trends = build_trend_data([
            {
                "ftime": "20260227",
                "amt": "100",
                "pay_num": "0",
                "active_members": "0",
                "order_cnt": "0",
                "order_pay": "0",
            }
        ])

        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)

    def test_kpi_cards_render_sparklines_from_last_ten_positive_trends(self):
        today = {
            "active": 200000,
            "retain_rate_1d": 45.0,
            "retain_rate_7d": 35.0,
            "pay_rate": 5.0,
            "pay_num": 10000,
            "arpu": 30.0,
            "total_rev": 300000,
            "fugou_amt": 50000,
            "fugou_pct": 16.7,
            "refund_rate": 1.0,
            "order_conv": 80.0,
            "order_fail": 20,
            "zhenxin_pct": 60.0,
            "amt_m": 9000000,
            "pay_m": 200000,
        }
        prev = {**today, "active": 190000, "total_rev": 280000}
        trends = [
            {
                "active_members": 100000 + i,
                "pay_rate": 3 + i / 10,
                "arpu": 20 + i,
                "amt": 200000 + i,
                "fugou_amt": 10000 + i,
                "refund_money": 100 + i,
                "order_conv": 60 + i,
                "retain_1d": 30 + i,
            }
            for i in range(12)
        ]

        html = kpi_cards_html(today, prev, trends)

        self.assertEqual(html.count("<svg"), 8)
        first_points = re.search(r'<polyline points="([^"]+)"', html).group(1)
        self.assertEqual(len(first_points.split()), 10)


class SparklineRegressionTests(unittest.TestCase):
    def test_sparkline_handles_edge_cases_and_downward_dot(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([7]), "")

        svg = sparkline_svg([5, 5, 3], width=10, height=8, fill=False)

        self.assertIn('<svg width="10" height="8"', svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertNotIn("<polygon", svg)

    def test_extract_trend_values_uses_history_in_time_order_and_fallbacks(self):
        history = [
            {"date": "2026-02-27", "metrics": {"revenue": 300}},
            {"date": "2026-02-26", "metrics": {"revenue": None}},
            {"date": "2026-02-25", "metrics": {"revenue": 100}},
        ]

        values = extract_trend_values(history, "revenue", today_val=400)

        self.assertEqual(values, [100.0, 0.0, 300.0, 400.0])
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=400, prev_val=200),
            [200.0, 400.0],
        )


class ParallelFetchRegressionTests(unittest.TestCase):
    def test_parallel_fetch_preserves_order_and_wraps_errors(self):
        def fail():
            raise RuntimeError("boom")

        results = parallel_fetch([
            lambda: {"rows": [1]},
            fail,
            lambda: {"rows": [3]},
        ])

        self.assertEqual(results[0], {"rows": [1]})
        self.assertEqual(results[2], {"rows": [3]})
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])

    def test_parallel_fetch_empty_calls_returns_empty_list(self):
        self.assertEqual(parallel_fetch([]), [])


class FeasibilityRegressionTests(unittest.TestCase):
    def test_validate_feasibility_classifies_default_cross_dept_and_budget(self):
        self.assertEqual(
            validate_feasibility({"title": "优化晨会话术"})["dependency"],
            "self_contained",
        )

        cross = validate_feasibility({"detail": "需要技术部配合系统升级"})
        self.assertEqual(cross["dependency"], "cross_dept")
        self.assertEqual(cross["feasibility"], "medium")
        self.assertIn("跨部门协调成本较高", cross["risk_notes"])

        budget = validate_feasibility({"act": "采购外部顾问工具"})
        self.assertEqual(budget["dependency"], "budget_required")
        self.assertEqual(budget["feasibility"], "medium")
        self.assertIn("边际ROI", budget["risk_notes"])

    def test_validate_feasibility_low_priority_for_overload_and_compliance(self):
        overload = validate_feasibility({"daily_action": "全员加量提高拨打量"})
        self.assertEqual(overload["feasibility"], "low")
        self.assertIn("鞭打快牛预警", overload["risk_notes"])

        compliance = validate_feasibility({"title": "门店扩张并快速转化"})
        self.assertEqual(compliance["feasibility"], "low")
        self.assertIn("风险回流总部预警", compliance["risk_notes"])


class VerificationEngineRegressionTests(unittest.TestCase):
    def test_hongniang_transcript_passes_when_required_terms_present(self):
        text = "本次服务会说明价格、收费、退费、合同、服务期和冷静期。"

        result = verify_transcript(text, "hongniang")

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_transcript_reports_missing_required_and_forbidden_terms(self):
        result = verify_transcript("价格和退费已说明，但一定能成功。", "hongniang")

        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：收费", result["issues"])
        self.assertIn("必说缺失：合同", result["issues"])
        self.assertIn("禁止用语：一定能", result["issues"])

    def test_unknown_line_still_blocks_forbidden_terms(self):
        result = verify_transcript("未知业务线也不能保证找到", "unknown")

        self.assertFalse(result["pass"])
        self.assertEqual(result["issues"], ["禁止用语：保证找到"])


if __name__ == "__main__":
    unittest.main()
