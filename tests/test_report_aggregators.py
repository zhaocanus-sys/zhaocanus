import unittest

from generate_hongniang_full_report import agg_hongniang, build_dept_data
from generate_shop_full_report import agg_shop, build_shop_data


class ShopAggregatorTests(unittest.TestCase):
    def test_build_shop_data_does_not_double_count_money_fields(self):
        rows = [
            {
                "dept_name": "深圳门店A",
                "level2": "深圳",
                "dept_worker_name": "店长A",
                "area_worker_name": "区长A",
                "total_realpay": "1000.50",
                "deptsale_realpay": "700.25",
                "invite_realpay": "100.00",
                "hn_realpay": "200.25",
                "total_pay_num": "2",
                "deptsale_shop_num": "1",
                "sg_num": "4",
                "link_num": "8",
                "call_times": "20",
                "zaigang_rs": "2",
                "refund_money_d": "50.00",
                "total_realpay_m": "3000.75",
                "deptsale_realpay_m": "2000.50",
            },
            {
                "dept_name": "深圳门店A",
                "total_realpay": "2000.25",
                "deptsale_realpay": "1500.75",
                "invite_realpay": "200.00",
                "hn_realpay": "300.25",
                "total_pay_num": "3",
                "deptsale_shop_num": "2",
                "sg_num": "6",
                "link_num": "12",
                "call_times": "30",
                "zaigang_rs": "3",
                "refundmoney_7d": "25.00",
                "total_realpay_m": "4000.25",
                "deptsale_realpay_m": "2500.50",
            },
        ]

        shop = build_shop_data(rows)[0]

        self.assertAlmostEqual(shop["total_realpay"], 3000.75)
        self.assertAlmostEqual(shop["hn_realpay"], 500.50)
        self.assertAlmostEqual(shop["refund_money_d"], 75.00)
        self.assertEqual(shop["total_pay_num"], 5)
        self.assertAlmostEqual(shop["sign_rate"], 30.0)
        self.assertAlmostEqual(shop["refund_rate"], 75.0 / 3000.75 * 100)

    def test_agg_shop_uses_zero_for_empty_denominators(self):
        result = agg_shop([
            {
                "total_realpay": "0",
                "total_pay_num": "0",
                "deptsale_shop_num": "3",
                "sg_num": "0",
                "link_num": "0",
                "zaigang_rs": "0",
                "refund_money_d": "15",
            }
        ])

        self.assertEqual(result["sign_rate"], 0)
        self.assertEqual(result["invite_conv"], 0)
        self.assertEqual(result["per_rev"], 0)
        self.assertEqual(result["refund_rate"], 0)
        self.assertEqual(result["avg_deal"], 0)


class HongniangAggregatorTests(unittest.TestCase):
    def test_agg_hongniang_sums_all_refund_channels(self):
        result = agg_hongniang([
            {
                "pay_1d_amt": "10000",
                "staff_new": "2",
                "link_time_count": "10",
                "deep_count": "5",
                "zhenai_back": "100",
                "zhenaigd_back": "200",
                "zhenai_hz_back": "300",
                "zhenai_xfh_back": "400",
                "zhenai_md_back": "500",
            }
        ])

        self.assertEqual(result["total_refund"], 1500)
        self.assertEqual(result["refund_rate"], 15)
        self.assertEqual(result["deep_rate"], 50)
        self.assertEqual(result["per_rev"], 5000)

    def test_build_dept_data_groups_suffixes_and_preserves_manager_lookup(self):
        rows = [
            {
                "dept_name": "厦门红娘一区一部 白班",
                "staff_new": "1",
                "jm_n": "2",
                "pay_1d_amt": "1000",
                "link_time_count": "4",
                "deep_count": "2",
                "zhenai_back": "50",
            },
            {
                "dept_name": "厦门红娘一区一部 晚班",
                "staff_new": "1",
                "jm_n": "1",
                "pay_1d_amt": "500",
                "link_time_count": "6",
                "deep_count": "3",
                "zhenaigd_back": "25",
            },
        ]

        dept = build_dept_data(rows)[0]

        self.assertEqual(dept["dept_name"], "厦门红娘一区一部")
        self.assertEqual(dept["manager"], "温方方（代）")
        self.assertEqual(dept["staff_new"], 2)
        self.assertEqual(dept["jm_n"], 3)
        self.assertEqual(dept["pay_1d_amt"], 1500)
        self.assertEqual(dept["total_refund"], 75)
        self.assertEqual(dept["deep_rate"], 50)
        self.assertEqual(dept["refund_rate"], 5)


if __name__ == "__main__":
    unittest.main()
