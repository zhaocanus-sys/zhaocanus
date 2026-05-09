import sys
import unittest
from unittest.mock import patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from agent_system.engines.collision_engine import DataCollisionEngine


class AppTrendRegressionTests(unittest.TestCase):
    def test_app_trend_data_groups_sorts_and_computes_rates(self):
        rows = [
            {
                "ftime": "20260227 10:00:00",
                "amt": "100",
                "pay_num": "10",
                "active_members": "1000",
                "refund_money": "3",
                "retain_1d": "100",
                "order_cnt": "20",
                "order_pay": "10",
                "anchmems": "2",
                "giftmems": "4",
                "fugou_amt": "25",
            },
            {
                "ftime": "20260226",
                "amt": "0",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "0",
                "retain_1d": "0",
                "order_cnt": "0",
                "order_pay": "0",
                "anchmems": "0",
                "giftmems": "0",
                "fugou_amt": "0",
            },
            {
                "ftime": "20260227 12:00:00",
                "amt": "50",
                "pay_num": "5",
                "active_members": "500",
                "refund_money": "2",
                "retain_1d": "50",
                "order_cnt": "5",
                "order_pay": "5",
                "anchmems": "1",
                "giftmems": "1",
                "fugou_amt": "5",
            },
        ]

        trends = app_report_data.build_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)
        self.assertEqual(trends[1]["amt"], 150)
        self.assertEqual(trends[1]["pay_num"], 15)
        self.assertEqual(trends[1]["active_members"], 1500)
        self.assertEqual(trends[1]["order_cnt"], 25)
        self.assertEqual(trends[1]["order_pay"], 15)
        self.assertEqual(trends[1]["arpu"], 10)
        self.assertEqual(trends[1]["pay_rate"], 1)
        self.assertEqual(trends[1]["order_conv"], 60)

    def test_generate_app_main_builds_exact_ten_day_trend_rows(self):
        captured = {}

        def fake_daily(team, date):
            return {"rows": [{"amt": date[-2:], "pay_num": "1", "active_members": "100"}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html>ok</html>"

        argv = ["generate_app_full_report.py", "--date", "2026-02-27"]
        with patch.object(sys, "argv", argv), \
                patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
                patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
                patch.object(generate_app_full_report, "send_report_email", return_value=True):
            generate_app_full_report.main()

        self.assertEqual(captured["date_display"], "2026-02-27")
        self.assertEqual(
            [row["ftime"] for row in captured["trend_rows"]],
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
        self.assertEqual([row["amt"] for row in captured["trend_rows"]], ["18", "19", "20", "21", "22", "23", "24", "25", "26", "27"])

    def test_kpi_cards_render_sparklines_for_trended_metrics_only(self):
        today = {
            "active": 200000,
            "retain_rate_1d": 38.5,
            "retain_rate_7d": 18.0,
            "pay_rate": 4.2,
            "pay_num": 8400,
            "arpu": 32.5,
            "total_rev": 273000,
            "fugou_amt": 82000,
            "fugou_pct": 30.0,
            "refund_rate": 1.5,
            "order_conv": 75.0,
            "order_fail": 12,
            "zhenxin_pct": 78.0,
            "amt_m": 9000000,
            "pay_m": 120000,
        }
        previous = dict(today, active=190000, total_rev=250000)
        trends = [
            {
                "active_members": 100000 + i,
                "pay_rate": 3 + i * 0.1,
                "arpu": 20 + i,
                "amt": 200000 + i,
                "fugou_amt": 50000 + i,
                "refund_money": 1000 + i,
                "order_conv": 60 + i,
                "retain_1d": 1000 + i,
            }
            for i in range(10)
        ]

        html = app_report_html.kpi_cards_html(today, previous, trends)

        self.assertEqual(html.count("<svg "), 8)
        self.assertIn("日营收", html)
        self.assertIn("订单成功率", html)
        self.assertIn("月累营收", html)


class SparklineRegressionTests(unittest.TestCase):
    def test_sparkline_handles_sparse_constant_and_downward_values(self):
        self.assertEqual(sparkline_svg([None, 3]), "")

        flat = sparkline_svg([5, None, 5], width=10, height=6, fill=False)
        self.assertIn('<polyline points="1.0,1.0 9.0,1.0"', flat)
        self.assertIn('fill="#16a34a"', flat)
        self.assertNotIn("<polygon", flat)

        downward = sparkline_svg([5, 3], width=10, height=6)
        self.assertIn('fill="#dc2626"', downward)
        self.assertIn("<polygon", downward)

    def test_extract_trend_values_uses_chronological_history_and_fallback(self):
        history = [
            {"date": "20260227", "metrics": {"revenue": 30}},
            {"date": "20260226", "metrics": {"revenue": None}},
            {"date": "20260225", "metrics": {"revenue": 10}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=40),
            [10.0, 0.0, 30.0, 40.0],
        )
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=40, prev_val=20),
            [20.0, 40.0],
        )


class ParallelFetchRegressionTests(unittest.TestCase):
    def test_parallel_fetch_preserves_order_and_captures_errors(self):
        calls = [
            lambda: "first",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            lambda: "third",
        ]

        results = parallel_fetch(calls)

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])

    def test_parallel_fetch_returns_empty_list_for_no_calls(self):
        self.assertEqual(parallel_fetch([]), [])


class CollisionEngineRegressionTests(unittest.TestCase):
    def test_dept_finding_carries_scope_manager_and_management_gap(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}

        engine._add_finding(
            "metric_x_metric",
            "低接通",
            "电销六部接通率低",
            1000,
            "P0",
            scope="dept",
            dept_name="电销六部",
            gap_key="low_connect",
        )

        finding = engine.findings[0].to_dict()
        self.assertEqual(finding["scope"], "dept")
        self.assertEqual(finding["dept_name"], "电销六部")
        self.assertEqual(finding["manager_name"], "游云清")
        self.assertIn("号码健康度", finding["management_gap"])


if __name__ == "__main__":
    unittest.main()
