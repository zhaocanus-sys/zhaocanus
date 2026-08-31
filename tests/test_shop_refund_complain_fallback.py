"""Regression coverage for shop refund/complaint field fallbacks.

PR #89 locked sale_rev (`sale_realpay` or `deptsale_realpay`) and the
double-count fix on `total_realpay`/`hn_realpay`. It did not lock the
complaint/refund alias contract used by both `agg_shop` and
`build_shop_data`:

- refund_money_d if truthy, else refundmoney_7d
- complain_400_num_day if truthy, else complain_400_num

A silent swap to the 7-day refund column (or dropping 400 投诉) would
mis-paint 退费率/投诉诊断 for every shop in the daily HTML. Tests lock
the current `or`-chain contract, including that a present 0 is falsy
and therefore falls through — that is production behavior on main,
not a new fix.

Does not re-fix shop money double-count (open PR #89).
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from generate_shop_full_report import agg_shop, build_shop_data


class ShopRefundComplainFallbackTests(unittest.TestCase):
    def test_agg_shop_prefers_daily_refund_and_falls_back_to_7d(self):
        preferred = agg_shop(
            [
                {
                    "refund_money_d": "1,200",
                    "refundmoney_7d": "9,999",
                    "total_realpay": "10,000",
                }
            ]
        )
        self.assertEqual(1200.0, preferred["refund_d"])
        self.assertEqual(12.0, preferred["refund_rate"])

        fallback = agg_shop(
            [
                {
                    "refundmoney_7d": "800",
                    "total_realpay": "8,000",
                }
            ]
        )
        self.assertEqual(800.0, fallback["refund_d"])
        self.assertEqual(10.0, fallback["refund_rate"])

        zero_daily = agg_shop(
            [
                {
                    "refund_money_d": 0,
                    "refundmoney_7d": "500",
                    "total_realpay": "5,000",
                }
            ]
        )
        self.assertEqual(500.0, zero_daily["refund_d"])

    def test_agg_shop_prefers_daily_complain_and_falls_back_to_alias(self):
        preferred = agg_shop([{"complain_400_num_day": "3", "complain_400_num": "99"}])
        self.assertEqual(3, preferred["complain"])

        fallback = agg_shop([{"complain_400_num": "7"}])
        self.assertEqual(7, fallback["complain"])

        empty = agg_shop([{}])
        self.assertEqual(0, empty["complain"])
        self.assertEqual(0.0, empty["refund_d"])

    def test_build_shop_data_uses_same_refund_and_complain_aliases(self):
        shops = build_shop_data(
            [
                {
                    "dept_name": "深圳南山店",
                    "refundmoney_7d": "400",
                    "complain_400_num": "2",
                    "total_realpay": "4,000",
                    "sg_num": 10,
                    "deptsale_shop_num": 3,
                    "link_num": 20,
                    "zaigang_rs": 2,
                },
                {
                    "dept_name": "广州天河店",
                    "refund_money_d": "200",
                    "refundmoney_7d": "9,000",
                    "complain_400_num_day": "1",
                    "complain_400_num": "8",
                    "total_realpay": "8,000",
                    "sg_num": 8,
                    "deptsale_shop_num": 4,
                    "link_num": 16,
                    "zaigang_rs": 4,
                },
            ]
        )
        by_name = {s["dept_name"]: s for s in shops}
        nanshan = by_name["深圳南山店"]
        tianhe = by_name["广州天河店"]
        self.assertEqual(400.0, nanshan["refund_money_d"])
        self.assertEqual(2, nanshan["complain_400_num_day"])
        self.assertEqual(200.0, tianhe["refund_money_d"])
        self.assertEqual(1, tianhe["complain_400_num_day"])
        # refund_rate = refund / total_realpay; do not lock the
        # total_realpay double-count still present on main (open PR #89).
        self.assertAlmostEqual(
            nanshan["refund_money_d"] / nanshan["total_realpay"] * 100,
            nanshan["refund_rate"],
        )
        self.assertAlmostEqual(
            tianhe["refund_money_d"] / tianhe["total_realpay"] * 100,
            tianhe["refund_rate"],
        )
        self.assertEqual(["广州天河店", "深圳南山店"], [s["dept_name"] for s in shops])


if __name__ == "__main__":
    unittest.main()
