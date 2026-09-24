# -*- coding: utf-8 -*-
"""门店全局诊断退费展示档的贴线合同。

展示文案用 >8 启动话术合规审查、>4 分门店追因。
既有用例只覆盖了 1% 与 6%，没有锁住 4 和 8 的等于线，
也没有证明刚过 8% 会写出合规审查。
"""
import unittest

from generate_shop_full_report import generate_html


def _shop_row(**overrides):
    row = {
        "dept_name": "深圳门店A",
        "level2": "深圳",
        "dept_worker_name": "店长A",
        "area_worker_name": "区长A",
        "total_realpay": "100000",
        "sale_realpay": "80000",
        "deptsale_realpay": "80000",
        "invite_realpay": "10000",
        "hn_realpay": "10000",
        "total_pay_num": "4",
        "sale_pay_num_all": "3",
        "invite_pay_num": "1",
        "deptsale_shop_num": "8",
        "sg_num": "20",
        "link_num": "40",
        "call_times": "50",
        "zaigang_rs": "4",
        "refund_money_d": "1000",
        "complain_400_num_day": "0",
        "leads_xyzout_3day": "10",
        "leads_3day_allot_0day": "9",
        "leads_xyzout_1day": "10",
        "leads_1day_allot_0day": "9",
        "total_realpay_m": "400000",
        "deptsale_realpay_m": "300000",
        "worker_num_call": "4",
    }
    row.update(overrides)
    return row


def _html(refund):
    return generate_html([_shop_row(refund_money_d=str(refund))], [], "2026-02-27")


class ShopRefundDisplayBandTests(unittest.TestCase):
    def test_refund_exactly_4_and_exactly_8_stay_off_the_next_band(self):
        # 4000/100000 == 4; mid copy needs > 4
        at_four = _html(4000)
        self.assertIn("退费率 4.0%", at_four)
        self.assertIn("✅ 退费控制良好", at_four)
        self.assertNotIn("超4%红线，分门店追因", at_four)
        self.assertNotIn("超8%，退费金额大", at_four)

        # 8000/100000 == 8; compliance copy needs > 8
        at_eight = _html(8000)
        self.assertIn("退费率 8.0%", at_eight)
        self.assertIn("⚠ 超4%红线，分门店追因", at_eight)
        self.assertNotIn("🚨 超8%，退费金额大，需立即启动话术合规审查", at_eight)
        self.assertNotIn("✅ 退费控制良好", at_eight)

    def test_refund_just_over_8_fires_compliance_review(self):
        # 8100/100000 == 8.1 is the first tick of the compliance band
        html = _html(8100)
        self.assertIn("退费率 8.1%", html)
        self.assertIn("🚨 超8%，退费金额大，需立即启动话术合规审查", html)
        self.assertNotIn("超4%红线，分门店追因", html)
        self.assertNotIn("✅ 退费控制良好", html)


if __name__ == "__main__":
    unittest.main()
