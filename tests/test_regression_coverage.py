import sys
import unittest
from unittest.mock import patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.engines.collision_engine import DataCollisionEngine


class ParallelFetchTests(unittest.TestCase):
    def test_empty_call_list_returns_empty_result(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_preserves_input_order_and_wraps_exceptions(self):
        calls = [
            lambda: {"name": "first"},
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            lambda: {"name": "third"},
        ]

        results = parallel_fetch(calls)

        self.assertEqual(results[0], {"name": "first"})
        self.assertEqual(results[2], {"name": "third"})
        self.assertIn("boom", results[1]["error"])
        self.assertEqual(results[1]["rows"], [])


class AppTrendRegressionTests(unittest.TestCase):
    def test_build_trend_data_derives_display_rate_metrics(self):
        trend = app_report_data.build_trend_data([
            {
                "ftime": "20260226",
                "amt": 1000,
                "pay_num": 10,
                "active_members": 100,
                "refund_money": 100,
                "retain_1d": 20,
                "retain_7d": 10,
                "mems": 100,
                "order_cnt": 50,
                "order_pay": 25,
                "fugou_amt": 300,
            },
            {
                "ftime": "20260227",
                "amt": 2000,
                "pay_num": 20,
                "active_members": 200,
                "refund_money": 200,
                "retain_1d": 40,
                "retain_7d": 20,
                "mems": 200,
                "order_cnt": 100,
                "order_pay": 80,
                "fugou_amt": 500,
            },
        ])

        self.assertEqual([row["dt"] for row in trend], ["2026-02-26", "2026-02-27"])
        self.assertEqual([row["refund_rate"] for row in trend], [10.0, 10.0])
        self.assertEqual([row["retain_rate_1d"] for row in trend], [20.0, 20.0])
        self.assertEqual([row["retain_rate_7d"] for row in trend], [10.0, 10.0])
        self.assertEqual([row["order_conv"] for row in trend], [50.0, 80.0])

    def test_kpi_sparklines_use_same_rate_metrics_as_displayed_cards(self):
        trends = app_report_data.build_trend_data([
            {
                "ftime": "20260226",
                "amt": 1000,
                "pay_num": 10,
                "active_members": 100,
                "refund_money": 100,
                "retain_1d": 20,
                "mems": 100,
                "order_cnt": 50,
                "order_pay": 25,
                "fugou_amt": 300,
            },
            {
                "ftime": "20260227",
                "amt": 2000,
                "pay_num": 20,
                "active_members": 200,
                "refund_money": 200,
                "retain_1d": 40,
                "mems": 200,
                "order_cnt": 100,
                "order_pay": 80,
                "fugou_amt": 500,
            },
        ])
        today = {
            "active": 200,
            "retain_rate_1d": 20.0,
            "retain_rate_7d": 0.0,
            "pay_rate": 10.0,
            "pay_num": 20,
            "arpu": 100.0,
            "total_rev": 2000.0,
            "fugou_amt": 500.0,
            "fugou_pct": 25.0,
            "refund_rate": 10.0,
            "order_conv": 80.0,
            "order_fail": 20,
            "zhenxin_pct": 70.0,
            "amt_m": 10000.0,
            "pay_m": 100,
        }
        captured_values = []

        def fake_sparkline(values, **kwargs):
            captured_values.append(list(values))
            return "<sparkline/>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            html = app_report_html.kpi_cards_html(today, {}, trends=trends)

        self.assertIn("<sparkline/>", html)
        self.assertIn([10.0, 10.0], captured_values)
        self.assertIn([20.0, 20.0], captured_values)
        self.assertNotIn([100.0, 200.0], captured_values)
        self.assertNotIn([20.0, 40.0], captured_values)

    def test_app_main_fetches_exact_ten_day_trend_without_unused_duplicate(self):
        calls = []

        def fake_daily(team, date):
            calls.append((team, date))
            return {"rows": [{"amt": 1}]}

        with patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-02-27"]), \
             patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
             patch.object(generate_app_full_report, "generate_html", return_value="<html/>"), \
             patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
             patch.object(generate_app_full_report, "send_report_email", return_value=True):
            generate_app_full_report.main()

        self.assertEqual(calls[:2], [("app", "20260227"), ("app", "20260226")])
        self.assertEqual(
            [date for _, date in calls[2:]],
            [
                "20260218",
                "20260219",
                "20260220",
                "20260221",
                "20260222",
                "20260223",
                "20260224",
                "20260225",
                "20260226",
                "20260227",
            ],
        )
        self.assertEqual(len(calls), 12)


class CollisionPersistenceTests(unittest.TestCase):
    def test_persistent_low_connect_detection_uses_department_history_and_seven_day_threshold(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清", "电销四部": "宋晓鹏"}
        depts = [
            {
                "dept_name": "电销六部",
                "connect_rate": 38,
                "allocated": 100,
                "avg_deal_amount": 1000,
            },
            {
                "dept_name": "电销四部",
                "connect_rate": 38,
                "allocated": 100,
                "avg_deal_amount": 1000,
            },
        ]
        trends = [
            {
                "cr": 30,
                "dept_trends": [
                    {"dept_name": "电销六部", "cr": 39},
                    {"dept_name": "电销四部", "cr": 45},
                ],
            }
            for _ in range(7)
        ]

        engine._collide_persistence_detection(depts, trends)
        findings = [finding.to_dict() for finding in engine.findings]

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["scope"], "dept")
        self.assertEqual(finding["dept_name"], "电销六部")
        self.assertEqual(finding["manager_name"], "游云清")
        self.assertEqual(finding["priority"], "P0")
        self.assertIn("连续约7天", finding["description"])
        self.assertIn("绩效分数扣减5分/日", " ".join(finding["recommendations"]))


if __name__ == "__main__":
    unittest.main()
