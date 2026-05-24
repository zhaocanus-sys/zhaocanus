import datetime
import unittest
from unittest import mock

import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from agent_system.engines.collision_engine import DataCollisionEngine
from app_report_data import build_trend_data


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_empty_order_and_exception_results(self):
        self.assertEqual(parallel_fetch([]), [])

        calls = [
            lambda: "first",
            lambda: "second",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        ]

        results = parallel_fetch(calls)

        self.assertEqual(results[0], "first")
        self.assertEqual(results[1], "second")
        self.assertEqual(results[2]["rows"], [])
        self.assertIn("boom", results[2]["error"])


class SparklineTests(unittest.TestCase):
    def test_sparkline_handles_sparse_constant_and_directional_values(self):
        self.assertEqual(sparkline_svg([None, 7, None]), "")

        flat_svg = sparkline_svg([5, 5, 5])
        self.assertIn("<polyline", flat_svg)
        self.assertIn("<circle", flat_svg)
        self.assertIn("#16a34a", flat_svg)

        down_svg = sparkline_svg([10, 5], fill=False)
        self.assertIn("#dc2626", down_svg)
        self.assertNotIn("<polygon", down_svg)

    def test_extract_trend_values_returns_chronological_series_with_fallbacks(self):
        newest_first_history = [
            {"date": "20260226", "metrics": {"revenue": 20}},
            {"date": "20260225", "metrics": {"revenue": 10}},
        ]

        self.assertEqual(
            extract_trend_values(newest_first_history, "revenue", today_val=30),
            [10.0, 20.0, 30.0],
        )
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=9, prev_val=8),
            [8.0, 9.0],
        )


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_groups_sorts_and_guards_zero_denominators(self):
        rows = [
            {
                "ftime": "20260227000000",
                "amt": 0,
                "pay_num": 0,
                "active_members": 0,
                "refund_money": 0,
                "retain_1d": 0,
                "order_cnt": 0,
                "order_pay": 0,
                "anchmems": 0,
                "giftmems": 0,
                "fugou_amt": 0,
            },
            {
                "ftime": "20260226000000",
                "amt": "100",
                "pay_num": "5",
                "active_members": "100",
                "refund_money": "1",
                "retain_1d": "3",
                "order_cnt": "10",
                "order_pay": "4",
                "anchmems": "2",
                "giftmems": "1",
                "fugou_amt": "20",
            },
            {
                "ftime": "20260226120000",
                "amt": "200",
                "pay_num": "5",
                "active_members": "100",
                "refund_money": "2",
                "retain_1d": "4",
                "order_cnt": "10",
                "order_pay": "6",
                "anchmems": "3",
                "giftmems": "2",
                "fugou_amt": "30",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[0]["amt"], 300)
        self.assertEqual(trends[0]["pay_num"], 10)
        self.assertEqual(trends[0]["arpu"], 30)
        self.assertEqual(trends[0]["pay_rate"], 5)
        self.assertEqual(trends[0]["order_conv"], 50)
        self.assertEqual(trends[0]["fugou_amt"], 50)
        self.assertEqual(trends[1]["arpu"], 0)
        self.assertEqual(trends[1]["pay_rate"], 0)
        self.assertEqual(trends[1]["order_conv"], 0)


class AppFullReportTests(unittest.TestCase):
    def test_product_comparison_renders_real_names_instead_of_placeholders(self):
        row = {
            "amt": 242000,
            "pay_num": 100,
            "active_members": 1000,
            "refund_money": 1000,
            "retain_1d": 450,
            "retain_7d": 300,
            "order_cnt": 120,
            "order_pay": 100,
            "reg_num_m": 1000,
            "pay_num_m": 200,
            "pay_amt_m": 500000,
            "mems": 1000,
            "pay_amt": 242000,
            "zhenxin_member": 90000,
            "super_member_full": 80000,
            "live_guard": 70000,
            "super_member_plus": 500,
            "zhenai_coin": 400,
            "super_remind": 350,
            "star_privilege": 300,
            "super_recommend": 250,
            "other": 200,
        }

        html = generate_app_full_report.generate_html([row], [row], [row], "2026-02-27")

        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)
        self.assertIn("珍心会员设计值得珍爱币借鉴", html)

    def test_main_fetches_exact_ten_day_trend_window_without_unused_duplicate(self):
        daily_dates = []
        captured = {}

        def fake_daily(team, date):
            self.assertEqual(team, "app")
            daily_dates.append(date)
            return {"rows": [{"amt": 1, "pay_num": 1, "active_members": 1}]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html></html>"

        with mock.patch.object(generate_app_full_report.sys, "argv", ["cmd", "--date", "2026-02-27"]), \
             mock.patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
             mock.patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
             mock.patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
             mock.patch.object(generate_app_full_report, "send_report_email", return_value=True):
            generate_app_full_report.main()

        expected_trend_dates = [
            (datetime.datetime(2026, 2, 27) - datetime.timedelta(days=delta)).strftime("%Y%m%d")
            for delta in range(9, -1, -1)
        ]
        self.assertEqual(daily_dates, ["20260227", "20260226", *expected_trend_dates])
        self.assertEqual([row["ftime"] for row in captured["trend_rows"]], expected_trend_dates)
        self.assertEqual(captured["date_display"], "2026-02-27")


class CollisionPersistenceTests(unittest.TestCase):
    def test_persistence_detection_requires_history_and_adds_dept_management_metadata(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        dept = {
            "dept_name": "电销六部",
            "connect_rate": 39,
            "allocated": 100,
            "avg_deal_amount": 5000,
        }

        engine._collide_persistence_detection([dept], [{"cr": 40}] * 4)
        self.assertEqual(engine.findings, [])

        engine._collide_persistence_detection([dept], [{"cr": 40}] * 5)
        finding = engine.findings[0].to_dict()

        self.assertEqual(finding["priority"], "P0")
        self.assertEqual(finding["scope"], "dept")
        self.assertEqual(finding["dept_name"], "电销六部")
        self.assertEqual(finding["manager_name"], "游云清")
        self.assertIn("连续多日", finding["management_gap"])
        self.assertIn("5天", finding["evidence"][1])


if __name__ == "__main__":
    unittest.main()
