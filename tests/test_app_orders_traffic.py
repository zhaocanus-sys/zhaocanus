# -*- coding: utf-8 -*-
"""Regression tests for APP orders/traffic aggregators with large blast radius."""
import math
import unittest

from app_report_data import agg_orders, agg_traffic


class AppOrdersAggregatorTests(unittest.TestCase):
    def test_agg_orders_groups_live_buckets_and_totals(self):
        rows = [
            {
                "entrance1": "直播",
                "entrance2": "直播间A",
                "channelname": "抖音",
                "platformname": "iOS",
                "producttype": "珍心会员",
                "user_type": "新用户",
                "app_version": "1.0",
                "iscallback": 0,
                "entrance3": "入口3",
                "productfullname": "珍心月卡",
                "channelname2": "信息流",
                "is_trial": "否",
                "order_cnt": 10,
                "order_pay": 6,
                "amt": "1000.5",
                "pay_num": 5,
            },
            {
                "entrance1": "直播",
                "entrance2": "直播间A",
                "channelname": "抖音",
                "platformname": "iOS",
                "producttype": "珍心会员",
                "user_type": "新用户",
                "app_version": "1.0",
                "iscallback": 0,
                "entrance3": "入口3",
                "productfullname": "珍心月卡",
                "channelname2": "信息流",
                "is_trial": "否",
                "order_cnt": 4,
                "order_pay": 2,
                "amt": "500",
                "pay_num": 2,
            },
            {
                "entrance1": "商城",
                "entrance2": "首页",
                "channelname": "自然量",
                "platformname": "Android",
                "producttype": "珍爱币",
                "user_type": "老用户",
                "app_version": "1.1",
                "iscallback": 1,
                "entrance3": "商城页",
                "productfullname": "币包",
                "channelname2": "自然",
                "is_trial": "是",
                "order_cnt": 3,
                "order_pay": 1,
                "amt": "200",
                "pay_num": 1,
            },
        ]

        result = agg_orders(rows)

        self.assertEqual(result["total_cnt"], 17)
        self.assertEqual(result["total_pay"], 9)
        self.assertAlmostEqual(result["total_amt"], 1700.5)

        live_e2 = dict(result["by_live_e2"])
        self.assertEqual(set(live_e2), {"直播间A"})
        self.assertEqual(live_e2["直播间A"]["cnt"], 14)
        self.assertEqual(live_e2["直播间A"]["pay"], 8)
        self.assertAlmostEqual(live_e2["直播间A"]["amt"], 1500.5)

        # Non-live rows must not pollute live product buckets.
        live_prod = dict(result["by_live_prod"])
        self.assertEqual(set(live_prod), {"珍心会员"})
        self.assertNotIn("珍爱币", live_prod)

        # Parent entrance ordering is revenue-desc.
        self.assertEqual(
            [name for name, _ in result["by_entrance1"]],
            ["直播", "商城"],
        )

    def test_agg_orders_empty_rows_are_safe(self):
        result = agg_orders([])
        self.assertEqual(result["total_cnt"], 0)
        self.assertEqual(result["total_pay"], 0)
        self.assertEqual(result["total_amt"], 0)
        self.assertEqual(result["by_live_e2"], [])
        self.assertEqual(result["by_entrance1"], [])


class AppTrafficAggregatorTests(unittest.TestCase):
    def test_agg_traffic_roi_cpa_and_zero_cost_safety(self):
        rows = [
            {
                "parent_name": "信息流",
                "parents": "抖音-信息流",
                "regnum": "100",
                "num_pay_online_d": "10",
                "amt_pay_d_online": "2000",
                "amt_pay_m_online1": "8000",
                "real_cost": "1000",
                "validnum": "80",
                "pay_d_lj_mems": "9",
                "regnew_mems": "70",
            },
            {
                "parent_name": "信息流",
                "parents": "快手-信息流",
                "regnum": 50,
                "num_pay_online_d": 5,
                "amt_pay_d_online": 500,
                "amt_pay_m_online1": 1500,
                "real_cost": 500,
                "validnum": 40,
                "pay_d_lj_mems": 4,
                "regnew_mems": 30,
            },
            {
                "parent_name": "品牌",
                "parents": "品牌投放",
                "regnum": 20,
                "num_pay_online_d": 2,
                "amt_pay_d_online": 300,
                "amt_pay_m_online1": 900,
                "real_cost": 0,  # zero cost must not raise / yield inf
                "validnum": 15,
                "pay_d_lj_mems": 2,
                "regnew_mems": 10,
            },
        ]

        result = agg_traffic(rows)

        self.assertEqual(result["total_reg"], 170)
        self.assertEqual(result["total_pay"], 17)
        self.assertAlmostEqual(result["total_amt_d"], 2800.0)
        self.assertAlmostEqual(result["total_cost"], 1500.0)
        self.assertAlmostEqual(result["overall_roi"], 2800.0 / 1500.0)
        self.assertTrue(math.isfinite(result["overall_roi"]))

        channels = {c["name"]: c for c in result["channels"]}
        self.assertAlmostEqual(channels["信息流"]["amt_d"], 2500.0)
        self.assertAlmostEqual(channels["信息流"]["cost"], 1500.0)
        self.assertAlmostEqual(channels["信息流"]["roi"], 2500.0 / 1500.0)
        self.assertAlmostEqual(channels["信息流"]["pay_rate"], 15 / 150 * 100)
        self.assertAlmostEqual(channels["信息流"]["cpa"], 1500.0 / 150.0)

        brand = channels["品牌"]
        self.assertEqual(brand["roi"], 0)
        self.assertEqual(brand["cpa"], 0)
        self.assertTrue(math.isfinite(brand["roi"]))
        self.assertTrue(math.isfinite(brand["pay_rate"]))

        # Parent channels sorted by daily amount desc.
        self.assertEqual(
            [c["name"] for c in result["channels"]],
            ["信息流", "品牌"],
        )
        # Sub-channels remain distinct and sorted by amount.
        self.assertEqual(
            [c["name"] for c in result["sub_channels"][:2]],
            ["抖音-信息流", "快手-信息流"],
        )

    def test_agg_traffic_empty_rows_are_safe(self):
        result = agg_traffic([])
        self.assertEqual(result["channels"], [])
        self.assertEqual(result["sub_channels"], [])
        self.assertEqual(result["total_cost"], 0)
        self.assertEqual(result["overall_roi"], 0)
        self.assertTrue(math.isfinite(result["overall_roi"]))


if __name__ == "__main__":
    unittest.main()
