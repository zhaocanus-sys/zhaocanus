import unittest

from agent_system.actions.api_client import parallel_fetch
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from generate_shop_full_report import build_shop_data
from generate_telesale_full_report import generate_html as generate_telesale_html


class ParallelFetchTests(unittest.TestCase):
    def test_parallel_fetch_empty_input_returns_empty_list(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_isolates_errors(self):
        def fail():
            raise RuntimeError("boom")

        results = parallel_fetch([
            lambda: {"name": "first"},
            fail,
            lambda: {"name": "third"},
        ])

        self.assertEqual(results[0], {"name": "first"})
        self.assertEqual(results[2], {"name": "third"})
        self.assertEqual(results[1]["rows"], [])
        self.assertIn("boom", results[1]["error"])


class SparklineTests(unittest.TestCase):
    def test_sparkline_requires_at_least_two_real_points(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 7]), "")

    def test_sparkline_handles_flat_series_and_marks_latest_point(self):
        svg = sparkline_svg([5, 5, 5], color="#123456")

        self.assertIn("<svg", svg)
        self.assertIn("<polyline", svg)
        self.assertIn('fill="#16a34a"', svg)
        self.assertIn('stroke="#123456"', svg)

    def test_extract_trend_values_uses_history_then_prev_today_fallbacks(self):
        history = [
            {"metrics": {"pay_amt": 300}},
            {"metrics": {"pay_amt": 200}},
        ]

        self.assertEqual(
            extract_trend_values(history, "pay_amt", today_val=400, prev_val=100),
            [200.0, 300.0, 400.0],
        )
        self.assertEqual(
            extract_trend_values([], "pay_amt", today_val=400, prev_val=100),
            [100.0, 400.0],
        )


class ShopAggregationTests(unittest.TestCase):
    def test_build_shop_data_accumulates_money_fields_once(self):
        shops = build_shop_data([
            {
                "dept_name": "深圳门店A",
                "level2": "深圳",
                "dept_worker_name": "负责人A",
                "area_worker_name": "区域A",
                "total_realpay": "12345.67",
                "deptsale_realpay": "10000.25",
                "invite_realpay": "2000.50",
                "hn_realpay": "345.75",
                "total_pay_num": "3",
                "deptsale_shop_num": "2",
                "sg_num": "4",
                "link_num": "8",
                "call_times": "20",
                "zaigang_rs": "2",
                "refund_money_d": "123.45",
                "total_realpay_m": "50000.00",
            }
        ])

        self.assertEqual(len(shops), 1)
        shop = shops[0]
        self.assertAlmostEqual(shop["total_realpay"], 12345.67)
        self.assertAlmostEqual(shop["hn_realpay"], 345.75)
        self.assertEqual(shop["total_pay_num"], 3)
        self.assertAlmostEqual(shop["sign_rate"], 50.0)
        self.assertAlmostEqual(shop["invite_conv"], 50.0)
        self.assertAlmostEqual(shop["per_rev"], 6172.835)

    def test_build_shop_data_zero_denominators_do_not_create_fake_rates(self):
        shop = build_shop_data([
            {
                "dept_name": "零业务门店",
                "deptsale_shop_num": "3",
                "sg_num": "0",
                "link_num": "0",
                "zaigang_rs": "0",
                "total_realpay": "0",
                "refund_money_d": "100",
            }
        ])[0]

        self.assertEqual(shop["sign_rate"], 0)
        self.assertEqual(shop["invite_conv"], 0)
        self.assertEqual(shop["per_rev"], 0)
        self.assertEqual(shop["refund_rate"], 0)


class TelesaleFunnelTests(unittest.TestCase):
    def test_funnel_bottleneck_uses_rate_against_threshold_not_raw_output(self):
        html = generate_telesale_html(
            [
                {
                    "dept_name": "电销一部",
                    "worker_nums": "10",
                    "pay_1d_amt": "90000",
                    "callout_1d_num": "1000",
                    "link_1d_num": "100",
                    "linkmems_deeptalk_10_1d_num": "90",
                    "pay_1d_num": "9",
                    "pay_1m_amt": "300000",
                    "ai_score": "80",
                }
            ],
            [],
            "2026-02-27",
        )

        self.assertIn("外呼→接通", html)
        self.assertIn("外呼→接通<span", html)
        self.assertIn("最大瓶颈", html)
        self.assertNotIn("深沟→签单<span", html)


if __name__ == "__main__":
    unittest.main()
