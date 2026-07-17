import math
import unittest

from generate_app_full_report import agg_app, build_trend_data


class AppReportAggregationTests(unittest.TestCase):
    def test_agg_app_calculates_core_rates_from_api_strings(self):
        metrics = agg_app(
            [
                {
                    "amt": "1,000.00",
                    "pay_num": "50",
                    "active_members": "200",
                    "refund_money": "20",
                    "mems": "100",
                    "retain_1d": "40",
                    "retain_7d": "20",
                    "order_cnt": "20",
                    "order_pay": "15",
                    "zhenxin_member": "600",
                    "super_member_full": "250",
                    "live_guard": "150",
                }
            ]
        )

        self.assertEqual(metrics["total_rev"], 1000)
        self.assertEqual(metrics["prod_total"], 1000)
        self.assertEqual(metrics["arpu"], 20)
        self.assertEqual(metrics["pay_rate"], 25)
        self.assertEqual(metrics["refund_rate"], 2)
        self.assertEqual(metrics["zhenxin_pct"], 60)
        self.assertEqual(metrics["retain_rate_1d"], 40)
        self.assertEqual(metrics["retain_rate_7d"], 20)
        self.assertEqual(metrics["order_conv"], 75)

    def test_agg_app_zero_denominators_produce_finite_zero_rates(self):
        metrics = agg_app(
            [
                {
                    "amt": "invalid",
                    "pay_num": None,
                    "active_members": 0,
                    "refund_money": 100,
                    "mems": 0,
                    "retain_1d": 10,
                    "retain_7d": 5,
                    "order_cnt": 0,
                    "order_pay": 3,
                    "zhenxin_member": 50,
                }
            ]
        )

        for key in (
            "arpu",
            "pay_rate",
            "refund_rate",
            "zhenxin_pct",
            "retain_rate_1d",
            "retain_rate_7d",
            "order_conv",
        ):
            self.assertEqual(metrics[key], 0, key)
            self.assertTrue(math.isfinite(metrics[key]), key)

    def test_build_trend_data_groups_days_sorts_and_uses_weighted_rates(self):
        trends = build_trend_data(
            [
                {
                    "ftime": "20260302 00:00:00",
                    "amt": "300",
                    "pay_num": "6",
                    "active_members": "60",
                    "refund_money": "3",
                    "retain_1d": "12",
                },
                {
                    "ftime": "20260301",
                    "amt": "100",
                    "pay_num": "2",
                    "active_members": "20",
                    "refund_money": "1",
                    "retain_1d": "4",
                },
                {
                    "ftime": "20260301",
                    "amt": "200",
                    "pay_num": "8",
                    "active_members": "80",
                    "refund_money": "2",
                    "retain_1d": "16",
                },
                {
                    "ftime": "20260228",
                    "amt": "50",
                    "pay_num": 0,
                    "active_members": 0,
                },
            ]
        )

        self.assertEqual(
            [point["dt"] for point in trends],
            ["2026-02-28", "2026-03-01", "2026-03-02"],
        )
        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[1]["amt"], 300)
        self.assertEqual(trends[1]["pay_num"], 10)
        self.assertEqual(trends[1]["active_members"], 100)
        self.assertEqual(trends[1]["arpu"], 30)
        self.assertEqual(trends[1]["pay_rate"], 10)


if __name__ == "__main__":
    unittest.main()
