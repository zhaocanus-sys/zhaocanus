import unittest
from unittest.mock import patch

from agent_system.actions.api_client import parallel_fetch
from agent_system.engines.collision_engine import DataCollisionEngine, validate_feasibility
from app_report_data import build_trend_data
from app_report_html import kpi_cards_html


def _base_app_metrics():
    return {
        "active": 1000,
        "retain_rate_1d": 20.0,
        "retain_rate_7d": 12.0,
        "pay_rate": 5.0,
        "pay_num": 50,
        "arpu": 100.0,
        "total_rev": 5000.0,
        "fugou_amt": 1000.0,
        "fugou_pct": 20.0,
        "refund_rate": 2.0,
        "order_conv": 60.0,
        "order_fail": 4,
        "zhenxin_pct": 50.0,
        "amt_m": 50000.0,
        "pay_m": 500,
    }


def _base_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "connect_rate": 38,
        "avg_connect_dur": 180,
        "allocated": 1000,
        "avg_deal_amount": 5000,
    }
    dept.update(overrides)
    return dept


class ParallelFetchRegressionTest(unittest.TestCase):
    def test_parallel_fetch_handles_empty_call_list(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_captures_errors(self):
        def boom():
            raise RuntimeError("network unavailable")

        results = parallel_fetch([lambda: "first", boom, lambda: "third"])

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("network unavailable", results[1]["error"])


class AppTrendRegressionTest(unittest.TestCase):
    def test_build_trend_data_derives_refund_and_retention_rates(self):
        trends = build_trend_data([
            {
                "ftime": "20260226",
                "amt": "10000",
                "refund_money": "100",
                "retain_1d": "20",
                "mems": "100",
                "pay_num": "10",
                "active_members": "1000",
                "order_cnt": "10",
                "order_pay": "5",
            },
            {
                "ftime": "20260227",
                "amt": "500",
                "refund_money": "20",
                "retain_1d": "40",
                "mems": "100",
                "pay_num": "5",
                "active_members": "1000",
                "order_cnt": "8",
                "order_pay": "4",
            },
        ])

        self.assertEqual([t["dt"] for t in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual([t["refund_rate"] for t in trends], [1.0, 4.0])
        self.assertEqual([t["retain_rate_1d"] for t in trends], [20.0, 40.0])

    def test_kpi_cards_use_rate_trends_not_raw_refund_or_retention_counts(self):
        trends = build_trend_data([
            {
                "ftime": "20260226",
                "amt": "10000",
                "refund_money": "100",
                "retain_1d": "20",
                "mems": "100",
                "pay_num": "10",
                "active_members": "1000",
                "fugou_amt": "1000",
                "order_cnt": "10",
                "order_pay": "5",
            },
            {
                "ftime": "20260227",
                "amt": "500",
                "refund_money": "20",
                "retain_1d": "40",
                "mems": "100",
                "pay_num": "5",
                "active_members": "1000",
                "fugou_amt": "500",
                "order_cnt": "8",
                "order_pay": "4",
            },
        ])
        captured_values = []

        def fake_sparkline(values, **_kwargs):
            captured_values.append(list(values))
            return "<sparkline/>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            html = kpi_cards_html(_base_app_metrics(), {}, trends)

        self.assertIn("退款率", html)
        self.assertIn([1.0, 4.0], captured_values)
        self.assertIn([20.0, 40.0], captured_values)
        self.assertNotIn([100.0, 20.0], captured_values)


class CollisionEngineRegressionTest(unittest.TestCase):
    def test_dept_finding_includes_scope_manager_and_management_gap(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}

        engine._collide_connect_rate_x_duration([_base_dept()])

        finding = engine.findings[0].to_dict()
        self.assertEqual(finding["priority"], "P0")
        self.assertEqual(finding["scope"], "dept")
        self.assertEqual(finding["dept_name"], "电销六部")
        self.assertEqual(finding["manager_name"], "游云清")
        self.assertIn("号码健康度", finding["management_gap"])

    def test_persistent_low_connect_rate_escalates_to_p0_with_penalty_action(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        trends = [{"cr": value} for value in [40, 41, 39, 42, 38]]

        engine._collide_persistence_detection([_base_dept(connect_rate=38)], trends)

        finding = engine.findings[0]
        self.assertEqual(finding.priority, "P0")
        self.assertEqual(finding.scope, "dept")
        self.assertEqual(finding.manager_name, "游云清")
        self.assertIn("连续约5天低于43%红线", finding.description)
        self.assertTrue(any("绩效分数扣减5分/日" in rec for rec in finding.recommendations))

    def test_validate_feasibility_flags_cross_dept_overload_and_compliance_risks(self):
        result = validate_feasibility({
            "title": "APP端系统升级后提高拨打量",
            "daily_action": "要求一线加量并推动高客单价快速转化",
        })

        self.assertEqual(result["feasibility"], "low")
        self.assertEqual(result["dependency"], "cross_dept")
        self.assertIn("跨部门协调成本较高", result["risk_notes"])
        self.assertIn("鞭打快牛预警", result["risk_notes"])
        self.assertIn("风险回流总部预警", result["risk_notes"])


if __name__ == "__main__":
    unittest.main()
