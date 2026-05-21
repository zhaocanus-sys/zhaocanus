import unittest

from app_report_data import agg_app, agg_orders, agg_traffic, build_trend_data


class AppReportDataAggregationTests(unittest.TestCase):
    def test_agg_app_derives_core_revenue_funnel_and_retention_metrics(self):
        metrics = agg_app([{
            "amt": "100,000",
            "pay_num": "100",
            "active_members": "200000",
            "refund_money": "2,500",
            "pay_num_new": "25",
            "order_cnt": "1000",
            "order_pay": "530",
            "order_num": "900",
            "mems": "5000",
            "fugou_amt": "30000",
            "pay_amt": "95000",
            "zhenxin_member": "85000",
            "super_member_full": "5000",
            "live_guard": "7000",
            "zhenai_coin": "3000",
            "anchmems": "10",
            "anchtime": "36000",
            "giftmems": "50",
            "costmoney": "15000",
            "retain_1d": "2000",
            "retain_7d": "1000",
        }])

        self.assertEqual(metrics["total_rev"], 100000.0)
        self.assertEqual(metrics["arpu"], 1000.0)
        self.assertEqual(metrics["pay_rate"], 0.05)
        self.assertEqual(metrics["refund_rate"], 2.5)
        self.assertEqual(metrics["order_conv"], 53.0)
        self.assertEqual(metrics["order_fail"], 470)
        self.assertEqual(metrics["order_fail_rate"], 47.0)
        self.assertEqual(metrics["retain_rate_1d"], 40.0)
        self.assertEqual(metrics["retain_rate_7d"], 20.0)
        self.assertEqual(metrics["zhenxin_pct"], 85.0)
        self.assertEqual(metrics["fugou_pct"], 30.0)
        self.assertEqual(metrics["live_rev"], 10000.0)
        self.assertEqual(metrics["avg_anchtime"], 3600.0)
        self.assertEqual(metrics["gift_per_viewer"], 300.0)

    def test_agg_app_zero_denominators_do_not_raise_or_inflate_rates(self):
        metrics = agg_app([{
            "amt": "0",
            "pay_num": "0",
            "active_members": "0",
            "refund_money": "100",
            "order_cnt": "0",
            "order_pay": "0",
            "mems": "0",
            "retain_1d": "10",
            "retain_7d": "5",
            "fugou_amt": "10",
            "zhenxin_member": "20",
        }])

        for key in (
            "arpu",
            "pay_rate",
            "refund_rate",
            "order_conv",
            "order_fail_rate",
            "retain_rate_1d",
            "retain_rate_7d",
            "zhenxin_pct",
            "fugou_pct",
        ):
            self.assertEqual(metrics[key], 0)

    def test_agg_orders_keeps_live_breakdowns_separate_and_preserves_totals(self):
        orders = agg_orders([
            {
                "order_cnt": "10",
                "order_pay": "6",
                "amt": "1000",
                "pay_num": "5",
                "entrance1": "直播",
                "entrance2": "牵线房",
                "channelname": "微信",
                "platformname": "iOS",
                "producttype": "守护",
                "is_trial": "是",
            },
            {
                "order_cnt": "20",
                "order_pay": "5",
                "amt": "500",
                "pay_num": "4",
                "entrance1": "首页",
                "entrance2": "资料页",
                "channelname": "支付宝",
                "platformname": "Android",
                "producttype": "会员",
                "is_trial": "否",
            },
            {
                "order_cnt": "5",
                "order_pay": "5",
                "amt": "800",
                "pay_num": "5",
                "entrance1": "直播",
                "entrance2": "直播间",
                "channelname": "微信",
                "platformname": "iOS",
                "producttype": "珍爱币",
                "is_trial": "是",
            },
        ])

        self.assertEqual(orders["total_cnt"], 35)
        self.assertEqual(orders["total_pay"], 16)
        self.assertEqual(orders["total_amt"], 2300.0)
        self.assertEqual(orders["by_entrance1"][0][0], "直播")
        self.assertEqual(orders["by_entrance1"][0][1]["amt"], 1800.0)
        self.assertEqual({name for name, _ in orders["by_live_e2"]}, {"牵线房", "直播间"})
        self.assertEqual(dict(orders["by_trial"])["是"]["cnt"], 15)
        self.assertEqual(dict(orders["by_trial"])["否"]["cnt"], 20)

    def test_agg_traffic_computes_roi_cpa_and_zero_cost_boundaries(self):
        traffic = agg_traffic([
            {
                "parent_name": "渠道A",
                "parents": "子A1",
                "regnum": "100",
                "num_pay_online_d": "5",
                "amt_pay_d_online": "500",
                "amt_pay_m_online1": "1500",
                "real_cost": "1000",
                "validnum": "90",
                "pay_d_lj_mems": "2",
                "regnew_mems": "80",
            },
            {
                "parent_name": "渠道A",
                "parents": "子A2",
                "regnum": "50",
                "num_pay_online_d": "10",
                "amt_pay_d_online": "700",
                "amt_pay_m_online1": "900",
                "real_cost": "300",
                "validnum": "40",
                "pay_d_lj_mems": "3",
                "regnew_mems": "30",
            },
            {
                "parent_name": "渠道B",
                "parents": "子B1",
                "regnum": "0",
                "num_pay_online_d": "0",
                "amt_pay_d_online": "100",
                "amt_pay_m_online1": "200",
                "real_cost": "0",
                "validnum": "0",
                "pay_d_lj_mems": "0",
                "regnew_mems": "0",
            },
        ])

        self.assertEqual(traffic["total_cost"], 1300.0)
        self.assertEqual(traffic["total_reg"], 150)
        self.assertEqual(traffic["total_pay"], 15)
        self.assertEqual(traffic["total_amt_d"], 1300.0)
        self.assertEqual(traffic["overall_roi"], 1.0)

        channel_a = traffic["channels"][0]
        self.assertEqual(channel_a["name"], "渠道A")
        self.assertAlmostEqual(channel_a["roi"], 1200 / 1300)
        self.assertEqual(channel_a["pay_rate"], 10.0)
        self.assertAlmostEqual(channel_a["cpa"], 1300 / 150)

        channel_b = next(ch for ch in traffic["channels"] if ch["name"] == "渠道B")
        self.assertEqual(channel_b["roi"], 0)
        self.assertEqual(channel_b["cpa"], 0)

    def test_build_trend_data_groups_by_day_and_sorts_chronologically(self):
        trends = build_trend_data([
            {
                "ftime": "2026022702",
                "amt": "500",
                "pay_num": "5",
                "active_members": "100",
                "order_cnt": "10",
                "order_pay": "8",
            },
            {
                "ftime": "2026022601",
                "amt": "0",
                "pay_num": "0",
                "active_members": "0",
                "order_cnt": "0",
                "order_pay": "0",
            },
            {
                "ftime": "2026022701",
                "amt": "1500",
                "pay_num": "15",
                "active_members": "200",
                "order_cnt": "30",
                "order_pay": "12",
                "fugou_amt": "300",
            },
        ])

        self.assertEqual([row["dt"] for row in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[0]["order_conv"], 0)

        self.assertEqual(trends[1]["amt"], 2000.0)
        self.assertEqual(trends[1]["pay_num"], 20.0)
        self.assertEqual(trends[1]["active_members"], 300.0)
        self.assertEqual(trends[1]["arpu"], 100.0)
        self.assertAlmostEqual(trends[1]["pay_rate"], 20 / 300 * 100)
        self.assertEqual(trends[1]["order_conv"], 50.0)
        self.assertEqual(trends[1]["fugou_amt"], 300.0)


if __name__ == "__main__":
    unittest.main()
