import datetime
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions import api_client
from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    validate_feasibility,
)


class RecentRegressionCoverageTest(unittest.TestCase):
    def test_parallel_fetch_handles_empty_call_list(self):
        self.assertEqual(api_client.parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_wraps_exceptions(self):
        def first():
            return {"name": "first"}

        def broken():
            raise RuntimeError("network down")

        def third():
            return {"name": "third"}

        results = api_client.parallel_fetch([first, broken, third])

        self.assertEqual(results[0], {"name": "first"})
        self.assertEqual(results[2], {"name": "third"})
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("network down", results[1]["error"])

    def test_app_trend_data_groups_days_and_computes_derived_rates(self):
        rows = [
            {
                "ftime": "20260228",
                "amt": "200",
                "pay_num": "4",
                "active_members": "100",
                "refund_money": "10",
                "order_cnt": "8",
                "order_pay": "4",
                "retain_1d": "50",
                "anchmems": "2",
                "giftmems": "3",
                "fugou_amt": "20",
            },
            {
                "ftime": "20260227",
                "amt": "100",
                "pay_num": "5",
                "active_members": "50",
                "refund_money": "2",
                "order_cnt": "4",
                "order_pay": "2",
                "retain_1d": "10",
                "anchmems": "1",
                "giftmems": "1",
                "fugou_amt": "10",
            },
            {
                "ftime": "20260228",
                "amt": "300",
                "pay_num": "6",
                "active_members": "100",
                "refund_money": "5",
                "order_cnt": "2",
                "order_pay": "2",
                "retain_1d": "10",
                "anchmems": "1",
                "giftmems": "1",
                "fugou_amt": "30",
            },
        ]

        trends = app_report_data.build_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trends[1]["amt"], 500)
        self.assertEqual(trends[1]["pay_num"], 10)
        self.assertEqual(trends[1]["active_members"], 200)
        self.assertEqual(trends[1]["refund_money"], 15)
        self.assertEqual(trends[1]["arpu"], 50)
        self.assertEqual(trends[1]["pay_rate"], 5)
        self.assertEqual(trends[1]["order_conv"], 60)
        self.assertEqual(trends[1]["refund_rate"], 3)

    def test_app_kpi_refund_sparkline_uses_refund_rate_not_raw_amount(self):
        today = {
            "active": 1000,
            "retain_rate_1d": 42,
            "retain_rate_7d": 30,
            "pay_rate": 5,
            "pay_num": 50,
            "arpu": 20,
            "total_rev": 1000,
            "fugou_amt": 200,
            "fugou_pct": 20,
            "refund_rate": 4,
            "order_conv": 70,
            "order_fail": 3,
            "zhenxin_pct": 60,
            "amt_m": 30000,
            "pay_m": 600,
        }
        trends = [
            {
                "active_members": 900,
                "pay_rate": 4,
                "arpu": 19,
                "amt": 900,
                "fugou_amt": 100,
                "refund_money": 1000,
                "refund_rate": 3.0,
                "order_conv": 60,
                "retain_1d": 35,
            },
            {
                "active_members": 1000,
                "pay_rate": 5,
                "arpu": 20,
                "amt": 1000,
                "fugou_amt": 200,
                "refund_money": 2000,
                "refund_rate": 4.0,
                "order_conv": 70,
                "retain_1d": 42,
            },
        ]

        def fake_sparkline(values, **_kwargs):
            values_text = ",".join(str(float(v)) for v in values)
            return f"<spark data='{values_text}'></spark>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg",
                   side_effect=fake_sparkline):
            html = app_report_html.kpi_cards_html(today, {}, trends)

        self.assertIn("<spark data='3.0,4.0'></spark>", html)
        self.assertNotIn("<spark data='1000.0,2000.0'></spark>", html)

    def test_app_main_fetches_today_previous_and_exact_ten_day_trend_window(self):
        original_argv = sys.argv[:]
        calls = []

        def fake_daily(team, date=None, page=1, size=500):
            calls.append((team, date, page, size))
            return {"rows": [{"ftime": date, "amt": "1"}]}

        try:
            sys.argv = ["generate_app_full_report.py", "--date", "2026-03-10"]
            with patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                    patch.object(generate_app_full_report, "generate_html",
                                 return_value="<html>ok</html>") as generate_html, \
                    patch.object(generate_app_full_report, "export_html",
                                 return_value="/tmp/app.html"), \
                    patch.object(generate_app_full_report, "send_report_email",
                                 return_value=True):
                generate_app_full_report.main()
        finally:
            sys.argv = original_argv

        trend_dates = [
            (datetime.datetime(2026, 3, 10) - datetime.timedelta(days=delta)).strftime("%Y%m%d")
            for delta in range(9, -1, -1)
        ]
        self.assertEqual(
            [call[1] for call in calls],
            ["20260310", "20260309"] + trend_dates,
        )
        trend_rows = generate_html.call_args.args[2]
        self.assertEqual([row["ftime"] for row in trend_rows], trend_dates)

    def test_persistent_detection_requires_seven_bad_days_before_p0(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        dept = {
            "dept_name": "电销六部",
            "connect_rate": 39,
            "allocated": 100,
            "avg_deal_amount": 5000,
        }
        six_bad_days = [
            {"dept_trends": [{"dept_name": "电销六部", "connect_rate": 40}]}
            for _ in range(6)
        ]

        engine._collide_persistence_detection([dept], six_bad_days)

        self.assertEqual(engine.findings, [])

    def test_persistent_detection_adds_manager_gap_after_seven_bad_days(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        dept = {
            "dept_name": "电销六部",
            "connect_rate": 39,
            "allocated": 100,
            "avg_deal_amount": 5000,
        }
        seven_bad_days = [
            {"dept_trends": [{"dept_name": "电销六部", "connect_rate": cr}]}
            for cr in [40, 40, 40, 40, 39.5, 39.2, 39]
        ]

        engine._collide_persistence_detection([dept], seven_bad_days)

        self.assertEqual(len(engine.findings), 1)
        finding = engine.findings[0].to_dict()
        self.assertEqual(finding["priority"], "P0")
        self.assertEqual(finding["scope"], "dept")
        self.assertEqual(finding["dept_name"], "电销六部")
        self.assertEqual(finding["manager_name"], "游云清")
        self.assertIn("连续约7天", finding["description"])
        self.assertIn("有效管理动作", finding["management_gap"])

    def test_validate_feasibility_flags_operational_risks(self):
        cross_dept = validate_feasibility({"title": "系统升级", "act": "需要技术部联调"})
        overload = validate_feasibility({"title": "提高拨打量", "daily_action": "人均拨打提至200通"})
        safe = validate_feasibility({"title": "晨会复盘", "daily_action": "播放标杆录音"})

        self.assertEqual(cross_dept["dependency"], "cross_dept")
        self.assertEqual(cross_dept["feasibility"], "medium")
        self.assertEqual(overload["feasibility"], "low")
        self.assertEqual(safe["dependency"], "self_contained")
        self.assertEqual(safe["feasibility"], "high")


if __name__ == "__main__":
    unittest.main()
