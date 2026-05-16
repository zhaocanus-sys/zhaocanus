import sys
import unittest
from unittest.mock import patch

import app_report_data
import app_report_html
import generate_app_full_report
from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_groups_by_day_sorts_and_derives_rates(self):
        rows = [
            {
                "ftime": "20260228090000",
                "amt": "100",
                "pay_num": "2",
                "active_members": "20",
                "order_cnt": "4",
                "order_pay": "2",
                "refund_money": "1",
                "retain_1d": "3",
                "anchmems": "1",
                "giftmems": "2",
                "fugou_amt": "10",
            },
            {
                "ftime": "20260227090000",
                "amt": "90",
                "pay_num": "3",
                "active_members": "30",
                "order_cnt": "0",
                "order_pay": "0",
            },
            {
                "ftime": "20260228120000",
                "amt": "50",
                "pay_num": "1",
                "active_members": "10",
                "order_cnt": "2",
                "order_pay": "2",
                "refund_money": "2",
                "retain_1d": "1",
                "anchmems": "3",
                "giftmems": "4",
                "fugou_amt": "5",
            },
        ]

        trend = app_report_data.build_trend_data(rows)

        self.assertEqual([day["dt"] for day in trend], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trend[0]["amt"], 90.0)
        self.assertEqual(trend[0]["order_conv"], 0)
        self.assertEqual(trend[1]["amt"], 150.0)
        self.assertEqual(trend[1]["pay_num"], 3.0)
        self.assertEqual(trend[1]["active_members"], 30.0)
        self.assertEqual(trend[1]["arpu"], 50.0)
        self.assertEqual(trend[1]["pay_rate"], 10.0)
        self.assertEqual(trend[1]["order_conv"], 66.66666666666666)
        self.assertEqual(trend[1]["fugou_amt"], 15.0)


class AppReportRenderingTests(unittest.TestCase):
    def _base_kpis(self):
        return {
            "active": 200000,
            "retain_rate_1d": 42.0,
            "retain_rate_7d": 24.0,
            "pay_rate": 5.5,
            "pay_num": 11000,
            "arpu": 36.0,
            "total_rev": 396000.0,
            "fugou_amt": 80000.0,
            "fugou_pct": 20.2,
            "refund_rate": 1.2,
            "order_conv": 72.0,
            "order_fail": 140,
            "zhenxin_pct": 63.0,
            "amt_m": 5000000.0,
            "pay_m": 100000,
        }

    def test_kpi_cards_render_last_10_trend_values_for_all_trend_cards(self):
        trends = []
        for i in range(1, 12):
            trends.append(
                {
                    "active_members": i,
                    "pay_rate": i + 10,
                    "arpu": i + 20,
                    "amt": i + 30,
                    "fugou_amt": i + 40,
                    "refund_money": i + 50,
                    "order_conv": i + 60,
                    "retain_1d": i + 70,
                }
            )
        captured = []

        def fake_sparkline(values, **kwargs):
            captured.append(list(values))
            return "<svg data-test='spark'></svg>"

        with patch("agent_system.actions.report_sparkline.sparkline_svg", side_effect=fake_sparkline):
            html = app_report_html.kpi_cards_html(self._base_kpis(), {"active": 190000}, trends)

        self.assertEqual(len(captured), 8)
        self.assertEqual(captured[0], list(range(2, 12)))
        self.assertEqual(captured[3], list(range(22, 32)))
        self.assertEqual(captured[4], list(range(32, 42)))
        self.assertEqual(captured[6], list(range(52, 62)))
        self.assertEqual(html.count("data-test='spark'"), 8)


class AppReportMainTests(unittest.TestCase):
    def test_main_fetches_10_daily_trend_dates_and_passes_ftime_rows(self):
        old_date = generate_app_full_report.DATE
        old_display = generate_app_full_report.DATE_DISPLAY

        def fake_daily(team, date):
            self.assertEqual(team, "app")
            return {"rows": [{"amt": "1", "pay_num": "1", "active_members": "10"}]}

        try:
            with patch.object(sys, "argv", ["generate_app_full_report.py", "--date", "2026-03-05"]), \
                    patch.object(generate_app_full_report, "daily", side_effect=fake_daily), \
                    patch.object(generate_app_full_report, "generate_html", return_value="<html>ok</html>") as generate_html, \
                    patch.object(generate_app_full_report, "export_html", return_value="/tmp/report.html"), \
                    patch.object(generate_app_full_report, "send_report_email", return_value=True):
                generate_app_full_report.main()
        finally:
            generate_app_full_report.DATE = old_date
            generate_app_full_report.DATE_DISPLAY = old_display

        trend_rows = generate_html.call_args.args[2]
        self.assertEqual(
            [row["ftime"] for row in trend_rows],
            [
                "20260224",
                "20260225",
                "20260226",
                "20260227",
                "20260228",
                "20260301",
                "20260302",
                "20260303",
                "20260304",
                "20260305",
            ],
        )


class SparklineTests(unittest.TestCase):
    def test_sparkline_requires_two_non_null_points(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 5]), "")

    def test_sparkline_renders_drop_as_red_last_dot_without_fill_when_disabled(self):
        html = sparkline_svg([3, 1], width=10, height=6, color="#000", fill=False)

        self.assertIn('<svg width="10" height="6"', html)
        self.assertIn('fill="#dc2626"', html)
        self.assertNotIn("<polygon", html)

    def test_extract_trend_values_reverses_history_and_uses_zero_for_missing_values(self):
        history = [
            {"date": "2026-03-03", "metrics": {"rev": 30}},
            {"date": "2026-03-02", "metrics": {"rev": None}},
            {"date": "2026-03-01", "metrics": {"rev": 10}},
        ]

        self.assertEqual(extract_trend_values(history, "rev", today_val=40), [10.0, 0.0, 30.0, 40.0])
        self.assertEqual(extract_trend_values([], "rev", today_val=9, prev_val=7), [7.0, 9.0])


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_returns_empty_list_for_no_calls(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_converts_exceptions(self):
        def first():
            return {"rows": [1]}

        def boom():
            raise ValueError("bad fetch")

        def third():
            return {"rows": [3]}

        result = parallel_fetch([first, boom, third])

        self.assertEqual(result[0], {"rows": [1]})
        self.assertEqual(result[2], {"rows": [3]})
        self.assertEqual(result[1]["rows"], [])
        self.assertIn("bad fetch", result[1]["error"])


if __name__ == "__main__":
    unittest.main()
