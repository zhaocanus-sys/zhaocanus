# -*- coding: utf-8 -*-
import sys
import unittest
from unittest.mock import patch


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_empty_order_and_error_shape(self):
        from agent_system.actions.api_client import parallel_fetch

        self.assertEqual(parallel_fetch([]), [])

        def boom():
            raise RuntimeError("upstream unavailable")

        results = parallel_fetch([
            lambda: {"rows": [1]},
            boom,
            lambda: {"rows": [3]},
        ])

        self.assertEqual(results[0], {"rows": [1]})
        self.assertEqual(results[2], {"rows": [3]})
        self.assertIn("upstream unavailable", results[1]["error"])
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertEqual(results[1]["columns"], [])


class AppTrendTests(unittest.TestCase):
    def test_trend_data_derives_displayed_rate_metrics(self):
        from app_report_data import build_trend_data

        trends = build_trend_data([
            {
                "ftime": "20260226",
                "amt": "1000",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "10",
                "retain_1d": "30",
                "retain_7d": "20",
                "mems": "100",
                "order_cnt": "50",
                "order_pay": "25",
            },
            {
                "ftime": "20260227",
                "amt": "2000",
                "pay_num": "20",
                "active_members": "200",
                "refund_money": "40",
                "retain_1d": "80",
                "retain_7d": "60",
                "mems": "200",
                "order_cnt": "0",
                "order_pay": "0",
            },
        ])

        self.assertEqual([t["dt"] for t in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual([t["refund_rate"] for t in trends], [1.0, 2.0])
        self.assertEqual([t["retain_rate_1d"] for t in trends], [30.0, 40.0])
        self.assertEqual([t["retain_rate_7d"] for t in trends], [20.0, 30.0])
        self.assertEqual([t["order_conv"] for t in trends], [50.0, 0])

    def test_kpi_cards_use_rate_trends_not_raw_counts(self):
        import app_report_html
        from app_report_data import build_trend_data

        captured = []

        def fake_sparkline(values, **kwargs):
            captured.append(tuple(float(v) for v in values))
            return "<spark/>"

        t = {
            "active": 200,
            "retain_rate_1d": 40.0,
            "retain_rate_7d": 30.0,
            "pay_rate": 10.0,
            "pay_num": 20,
            "arpu": 100.0,
            "total_rev": 2000.0,
            "fugou_amt": 500.0,
            "fugou_pct": 25.0,
            "refund_rate": 2.0,
            "order_conv": 50.0,
            "order_fail": 5,
            "zhenxin_pct": 50.0,
            "amt_m": 10000.0,
            "pay_m": 100,
        }
        trends = build_trend_data([
            {
                "ftime": "20260226",
                "amt": "1000",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "10",
                "retain_1d": "30",
                "mems": "100",
                "order_cnt": "50",
                "order_pay": "25",
                "fugou_amt": "200",
            },
            {
                "ftime": "20260227",
                "amt": "2000",
                "pay_num": "20",
                "active_members": "200",
                "refund_money": "40",
                "retain_1d": "80",
                "mems": "200",
                "order_cnt": "100",
                "order_pay": "50",
                "fugou_amt": "500",
            },
        ])

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            app_report_html.kpi_cards_html(t, {}, trends)

        self.assertIn((1.0, 2.0), captured)
        self.assertIn((30.0, 40.0), captured)
        self.assertNotIn((10.0, 40.0), captured)
        self.assertNotIn((30.0, 80.0), captured)

    def test_app_main_fetches_exact_ten_day_window_without_duplicate_daily(self):
        import generate_app_full_report as report

        calls = []
        html_inputs = {}

        def fake_daily(team, date):
            calls.append((team, date))
            return {"rows": [{"amt": 1}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            html_inputs["today_rows"] = today_rows
            html_inputs["prev_rows"] = prev_rows
            html_inputs["trend_rows"] = trend_rows
            html_inputs["date_display"] = date_display
            return "<html>ok</html>"

        old_date, old_date_display = report.DATE, report.DATE_DISPLAY
        try:
            with patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-02-27"]), \
                 patch.object(report, "daily", side_effect=fake_daily), \
                 patch.object(report, "generate_html", side_effect=fake_generate_html), \
                 patch.object(report, "export_html", return_value="/tmp/report.html"), \
                 patch.object(report, "send_report_email", return_value=True):
                report.main()
        finally:
            report.DATE, report.DATE_DISPLAY = old_date, old_date_display

        self.assertEqual(calls[:2], [("app", "20260227"), ("app", "20260226")])
        self.assertEqual(
            [date for _, date in calls[2:]],
            ["20260218", "20260219", "20260220", "20260221", "20260222",
             "20260223", "20260224", "20260225", "20260226", "20260227"],
        )
        self.assertEqual(len(calls), 12)
        self.assertEqual([row["ftime"] for row in html_inputs["trend_rows"]],
                         ["20260218", "20260219", "20260220", "20260221", "20260222",
                          "20260223", "20260224", "20260225", "20260226", "20260227"])
        self.assertEqual(html_inputs["date_display"], "2026-02-27")


class CollisionPersistenceTests(unittest.TestCase):
    def test_persistence_requires_seven_department_specific_low_days(self):
        from agent_system.engines.collision_engine import DataCollisionEngine

        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清", "电销四部": "宋晓鹏"}
        depts = [
            {
                "dept_name": "电销六部",
                "connect_rate": 40,
                "allocated": 1000,
                "avg_deal_amount": 2000,
            },
            {
                "dept_name": "电销四部",
                "connect_rate": 39,
                "allocated": 1000,
                "avg_deal_amount": 2000,
            },
        ]
        trends = [
            {
                "cr": 40,
                "dept_trends": [
                    {"dept_name": "电销六部", "cr": 40},
                    {"dept_name": "电销四部", "cr": 45},
                ],
            }
            for _ in range(7)
        ]

        engine._collide_persistence_detection(depts, trends)

        persistence = [f for f in engine.findings if f.tag == "持续不达标预警"]
        self.assertEqual(len(persistence), 1)
        finding = persistence[0].to_dict()
        self.assertEqual(finding["priority"], "P0")
        self.assertEqual(finding["scope"], "dept")
        self.assertEqual(finding["dept_name"], "电销六部")
        self.assertEqual(finding["manager_name"], "游云清")
        self.assertIn("执行力", finding["management_gap"])
        self.assertIn("7天", "".join(finding["evidence"]))

    def test_persistence_does_not_escalate_before_seven_days(self):
        from agent_system.engines.collision_engine import DataCollisionEngine

        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        depts = [{
            "dept_name": "电销六部",
            "connect_rate": 40,
            "allocated": 1000,
            "avg_deal_amount": 2000,
        }]
        trends = [
            {"dept_trends": [{"dept_name": "电销六部", "cr": 40}]}
            for _ in range(6)
        ]

        engine._collide_persistence_detection(depts, trends)

        self.assertEqual([f for f in engine.findings if f.tag == "持续不达标预警"], [])


if __name__ == "__main__":
    unittest.main()
