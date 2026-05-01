import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_data import build_trend_data as build_app_report_trend_data
from generate_app_full_report import build_trend_data as build_full_report_trend_data


class SparklineTests(unittest.TestCase):
    def test_sparkline_requires_at_least_two_non_null_points(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 10, None]), "")

    def test_sparkline_ignores_none_values_and_marks_downtrend(self):
        svg = sparkline_svg([100, None, 80], width=40, height=20, color="#123456", fill=False)

        self.assertIn('<svg width="40" height="20"', svg)
        self.assertIn('<polyline points="1.0,1.0 39.0,19.0"', svg)
        self.assertIn('stroke="#123456"', svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertNotIn("<polygon", svg)

    def test_extract_trend_values_preserves_chronological_order_with_fallback(self):
        history = [
            {"date": "2026-02-27", "metrics": {"revenue": "300"}},
            {"date": "2026-02-26", "metrics": {"revenue": None}},
            {"date": "2026-02-25", "metrics": {"revenue": "100.5"}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val="400"),
            [100.5, 0.0, 300.0, 400.0],
        )
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=20, prev_val=10),
            [10.0, 20.0],
        )


class AppTrendAggregationTests(unittest.TestCase):
    def test_full_report_trend_groups_unsorted_rows_and_calculates_rates(self):
        rows = [
            {"ftime": "20260227090000", "amt": "1,200", "pay_num": "12", "active_members": "240", "refund_money": "30", "retain_1d": "60"},
            {"ftime": "20260226090000", "amt": "500", "pay_num": "0", "active_members": "0", "refund_money": None, "retain_1d": "5"},
            {"ftime": "20260227120000", "amt": "800", "pay_num": "8", "active_members": "160", "refund_money": "20", "retain_1d": "40"},
        ]

        result = build_full_report_trend_data(rows)

        self.assertEqual([row["dt"] for row in result], ["2026-02-26", "2026-02-27"])
        self.assertEqual(result[0]["amt"], 500.0)
        self.assertEqual(result[0]["arpu"], 0)
        self.assertEqual(result[0]["pay_rate"], 0)
        self.assertEqual(result[1]["amt"], 2000.0)
        self.assertEqual(result[1]["pay_num"], 20.0)
        self.assertEqual(result[1]["refund_money"], 50.0)
        self.assertEqual(result[1]["arpu"], 100.0)
        self.assertEqual(result[1]["pay_rate"], 5.0)

    def test_app_report_trend_includes_order_and_repurchase_metrics(self):
        rows = [
            {"ftime": "20260227", "amt": "1000", "pay_num": "10", "active_members": "200", "order_cnt": "50", "order_pay": "25", "fugou_amt": "300"},
            {"ftime": "20260227", "amt": "500", "pay_num": "5", "active_members": "100", "order_cnt": "50", "order_pay": "35", "fugou_amt": "200"},
            {"ftime": "20260226", "amt": "200", "pay_num": "0", "active_members": "100", "order_cnt": "0", "order_pay": "0", "fugou_amt": "0"},
        ]

        result = build_app_report_trend_data(rows)

        self.assertEqual([row["dt"] for row in result], ["2026-02-26", "2026-02-27"])
        self.assertEqual(result[1]["amt"], 1500.0)
        self.assertEqual(result[1]["arpu"], 100.0)
        self.assertEqual(result[1]["pay_rate"], 5.0)
        self.assertEqual(result[1]["order_conv"], 60.0)
        self.assertEqual(result[1]["fugou_amt"], 500.0)
        self.assertEqual(result[0]["order_conv"], 0)


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_preserves_order_and_converts_exceptions(self):
        def first():
            return {"rows": [1]}

        def failing():
            raise RuntimeError("boom")

        def third():
            return {"rows": [3]}

        result = parallel_fetch([first, failing, third])

        self.assertEqual(result[0], {"rows": [1]})
        self.assertEqual(result[2], {"rows": [3]})
        self.assertEqual(result[1]["rows"], [])
        self.assertEqual(result[1]["row_count"], 0)
        self.assertIn("boom", result[1]["error"])

    def test_parallel_fetch_accepts_empty_call_list(self):
        self.assertEqual(parallel_fetch([]), [])


if __name__ == "__main__":
    unittest.main()
