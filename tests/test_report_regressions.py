import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import sparkline_svg
from app_report_data import build_trend_data


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_groups_sorts_and_derives_metrics(self):
        rows = [
            {
                "ftime": "20260302",
                "amt": "300",
                "pay_num": "3",
                "active_members": "30",
                "refund_money": "5",
                "retain_1d": "7",
                "order_cnt": "10",
                "order_pay": "8",
                "fugou_amt": "90",
            },
            {
                "ftime": "20260301",
                "amt": "1,000",
                "pay_num": "10",
                "active_members": "200",
                "refund_money": "10",
                "retain_1d": "20",
                "order_cnt": "50",
                "order_pay": "25",
                "fugou_amt": "300",
            },
            {
                "ftime": "20260301",
                "amt": "500",
                "pay_num": "5",
                "active_members": "100",
                "refund_money": "5",
                "retain_1d": "10",
                "order_cnt": "50",
                "order_pay": "50",
                "fugou_amt": "150",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([t["dt"] for t in trends], ["2026-03-01", "2026-03-02"])
        self.assertEqual(trends[0]["amt"], 1500)
        self.assertEqual(trends[0]["pay_num"], 15)
        self.assertEqual(trends[0]["active_members"], 300)
        self.assertEqual(trends[0]["refund_money"], 15)
        self.assertEqual(trends[0]["fugou_amt"], 450)
        self.assertEqual(trends[0]["arpu"], 100)
        self.assertEqual(trends[0]["pay_rate"], 5)
        self.assertEqual(trends[0]["order_conv"], 75)

    def test_build_trend_data_handles_zero_denominators(self):
        trends = build_trend_data([
            {
                "ftime": "20260303",
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


class SparklineTests(unittest.TestCase):
    def test_sparkline_requires_at_least_two_values(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([123]), "")

    def test_sparkline_renders_flat_and_downward_series(self):
        flat = sparkline_svg([5, 5, 5], color="#111111")
        down = sparkline_svg([10, 7], fill=False)

        self.assertIn("<svg", flat)
        self.assertIn('fill="#111111"', flat)
        self.assertIn('fill="#16a34a"', flat)
        self.assertIn("<svg", down)
        self.assertNotIn("<polygon", down)
        self.assertIn('fill="#dc2626"', down)


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_empty_calls_returns_empty_list(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_wraps_errors(self):
        def first():
            return {"rows": [1]}

        def boom():
            raise RuntimeError("network timeout")

        def third():
            return {"rows": [3]}

        results = parallel_fetch([first, boom, third])

        self.assertEqual(results[0], {"rows": [1]})
        self.assertEqual(results[2], {"rows": [3]})
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("network timeout", results[1]["error"])


if __name__ == "__main__":
    unittest.main()
