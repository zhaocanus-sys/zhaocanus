import unittest
from unittest.mock import patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from agent_system.engines.collision_engine import DataCollisionEngine


def app_daily_row(**overrides):
    row = {
        "amt": 1000,
        "pay_num": 10,
        "active_members": 100,
        "refund_money": 20,
        "retain_1d": 30,
        "retain_7d": 15,
        "order_cnt": 50,
        "order_pay": 25,
        "anchmems": 2,
        "giftmems": 5,
        "fugou_amt": 100,
        "mems": 100,
        "pay_amt_m": 5000,
        "pay_num_m": 30,
        "zhenxin_member": 400,
    }
    row.update(overrides)
    return row


class AppTrendDataTests(unittest.TestCase):
    def test_app_trend_data_groups_sorts_and_derives_rates(self):
        rows = [
            app_daily_row(ftime="20260227", amt="1,000", pay_num="10", active_members="100", order_cnt="20", order_pay="10"),
            app_daily_row(ftime="20260226", amt=500, pay_num=5, active_members=50, order_cnt=10, order_pay=8),
            app_daily_row(ftime="20260227", amt=250, pay_num=5, active_members=25, order_cnt=5, order_pay=5),
        ]

        trends = app_report_data.build_trend_data(rows)

        self.assertEqual([tr["dt"] for tr in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[1]["amt"], 1250)
        self.assertEqual(trends[1]["pay_num"], 15)
        self.assertAlmostEqual(trends[1]["arpu"], 1250 / 15)
        self.assertAlmostEqual(trends[1]["pay_rate"], 12.0)
        self.assertAlmostEqual(trends[1]["order_conv"], 60.0)

    def test_app_trend_data_zero_denominators_are_safe(self):
        trends = app_report_data.build_trend_data([
            app_daily_row(ftime="20260227", amt=100, pay_num=0, active_members=0, order_cnt=0, order_pay=0)
        ])

        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)

    def test_generate_app_trend_builder_matches_current_report_contract(self):
        rows = [
            app_daily_row(ftime="20260227", amt=800, pay_num=8, active_members=80, refund_money=16, retain_1d=20),
            app_daily_row(ftime="20260227", amt=200, pay_num=2, active_members=20, refund_money=4, retain_1d=5),
        ]

        trends = generate_app_full_report.build_trend_data(rows)

        self.assertEqual(trends, [{
            "dt": "2026-02-27",
            "amt": 1000,
            "pay_num": 10,
            "active_members": 100,
            "refund_money": 20,
            "retain_1d": 25,
            "arpu": 100,
            "pay_rate": 10,
        }])

    def test_app_main_fetches_each_of_the_last_ten_days_for_trends(self):
        captured = {}

        def fake_daily(team, date):
            return {"rows": [app_daily_row(amt=int(date[-2:]), pay_num=1, active_members=10)]}

        def fake_generate_html(today_rows, prev_rows, trend_rows, date_display):
            captured["today_rows"] = today_rows
            captured["prev_rows"] = prev_rows
            captured["trend_rows"] = trend_rows
            captured["date_display"] = date_display
            return "<html>ok</html>"

        with patch.object(generate_app_full_report, "daily", side_effect=fake_daily) as daily_mock, \
             patch.object(generate_app_full_report, "generate_html", side_effect=fake_generate_html), \
             patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
             patch.object(generate_app_full_report, "send_report_email", return_value=True), \
             patch.object(generate_app_full_report.sys, "argv", ["generate_app_full_report.py", "--date", "2026-02-27"]):
            generate_app_full_report.main()

        self.assertEqual(captured["date_display"], "2026-02-27")
        self.assertEqual(len(captured["today_rows"]), 1)
        self.assertEqual(len(captured["prev_rows"]), 1)
        self.assertEqual(
            [row["ftime"] for row in captured["trend_rows"]],
            ["20260218", "20260219", "20260220", "20260221", "20260222",
             "20260223", "20260224", "20260225", "20260226", "20260227"],
        )
        called_dates = [call.args[1] for call in daily_mock.call_args_list]
        for expected_date in ("20260218", "20260219", "20260220", "20260221", "20260222",
                              "20260223", "20260224", "20260225", "20260226", "20260227"):
            self.assertIn(expected_date, called_dates)


class SparklineAndHtmlTests(unittest.TestCase):
    def test_sparkline_handles_empty_constant_and_downward_values(self):
        self.assertEqual(sparkline_svg([None, 5]), "")

        flat = sparkline_svg([5, 5, 5], width=30, height=10)
        self.assertIn("<svg", flat)
        self.assertIn('fill="#16a34a"', flat)

        down = sparkline_svg([10, None, 7], width=30, height=10, fill=False)
        self.assertIn('fill="#dc2626"', down)
        self.assertNotIn("<polygon", down)
        self.assertNotIn("None", down)

    def test_extract_trend_values_returns_time_order_with_fallback(self):
        history = [
            {"date": "20260227", "metrics": {"revenue": 30}},
            {"date": "20260226", "metrics": {"revenue": None}},
            {"date": "20260225", "metrics": {"revenue": 10}},
        ]

        self.assertEqual(extract_trend_values(history, "revenue", today_val=40), [10.0, 0.0, 30.0, 40.0])
        self.assertEqual(extract_trend_values([], "revenue", today_val=5, prev_val=3), [3.0, 5.0])

    def test_kpi_cards_render_sparklines_only_with_meaningful_trend_values(self):
        today = app_report_data.agg_app([app_daily_row(amt=2000, pay_num=20, active_members=200)])
        prev = app_report_data.agg_app([app_daily_row(amt=1000, pay_num=10, active_members=100)])
        trends = app_report_data.build_trend_data([
            app_daily_row(ftime="20260226", amt=1000, pay_num=10, active_members=100, order_cnt=10, order_pay=5),
            app_daily_row(ftime="20260227", amt=2000, pay_num=20, active_members=200, order_cnt=10, order_pay=8),
        ])

        html = app_report_html.kpi_cards_html(today, prev, trends)

        self.assertIn("<svg", html)
        self.assertIn("DAU", html)
        self.assertIn("日营收", html)
        self.assertIn("▲100.0%", html)


class SharedUtilityAndDiagnosisTests(unittest.TestCase):
    def test_parallel_fetch_preserves_order_and_wraps_exceptions(self):
        results = parallel_fetch([
            lambda: "first",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            lambda: "third",
        ])

        self.assertEqual(results[0], "first")
        self.assertEqual(results[2], "third")
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])

    def test_parallel_fetch_empty_call_list_is_noop(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_department_findings_include_scope_manager_and_management_gap(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}

        engine._add_finding(
            "metric_x_metric",
            "低接通",
            "电销六部接通率持续偏低",
            5200,
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
