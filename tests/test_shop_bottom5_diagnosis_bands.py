# -*- coding: utf-8 -*-
"""Regression coverage for shop BOTTOM5 issue bands and MGMT_GAP priority.

Open PR #89 covers lead-speed / sale_rev fallback, manager naming, and
P0/P1 improvement cards (including low_sign_rate department diagnosis).
Open PR #102 covers why_shop_good bands and TOP/BOTTOM 99x sentinels.
This file locks the remaining BOTTOM5 issue texts and management-gap
key selection that decide same-day store coaching.
"""
import re
import unittest

from generate_shop_full_report import MGMT_GAP_RULES, generate_html


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


def _shop_row(**overrides):
    row = {
        "dept_name": "深圳门店A",
        "level2": "深圳",
        "dept_worker_name": "店长A",
        "area_worker_name": "区长A",
        "total_realpay": "20000",
        "sale_realpay": "15000",
        "deptsale_realpay": "15000",
        "invite_realpay": "3000",
        "hn_realpay": "2000",
        "total_pay_num": "4",
        "sale_pay_num_all": "3",
        "invite_pay_num": "1",
        "deptsale_shop_num": "6",
        "sg_num": "20",
        "link_num": "50",
        "call_times": "80",
        "zaigang_rs": "2",
        "refund_money_d": "400",
        "complain_400_num_day": "0",
        "leads_xyzout_3day": "10",
        "leads_3day_allot_0day": "9",
        "leads_xyzout_1day": "5",
        "leads_1day_allot_0day": "5",
        "total_realpay_m": "80000",
        "deptsale_realpay_m": "60000",
        "worker_num_call": "2",
    }
    row.update(overrides)
    return row


class ShopBottom5DiagnosisTests(unittest.TestCase):
    def test_low_invite_conv_issue_and_gap_when_sign_is_healthy(self):
        # 签单 6/20=30% >=25；接通→到店 10/80=12.5% <20；退费 400/20000=2%
        html = generate_html(
            [_shop_row(sg_num="10", deptsale_shop_num="3", link_num="80")],
            [],
            "2026-02-27",
        )
        self.assertIn("接通→到店转化12.5%，邀约话术或邀约时机有问题", html)
        self.assertIn(MGMT_GAP_RULES["low_invite_conv"], html)
        self.assertNotIn("严重低于30%合格线", html)
        self.assertIsNone(_INF_NAN.search(html))

    def test_high_refund_issue_wins_gap_over_invite(self):
        # 签单 3/10=30% >=25；到店 10/80=12.5%<20。
        # main 上 total_realpay 被 int+float 双重累加，20000→40000；
        # 退费 4000/40000=10%>8。mgap 优先 high_refund。
        html = generate_html(
            [_shop_row(
                sg_num="10",
                deptsale_shop_num="3",
                link_num="80",
                refund_money_d="4000",
            )],
            [],
            "2026-02-27",
        )
        self.assertIn("退费率10.0%，签单话术可能存在过度承诺", html)
        self.assertIn("接通→到店转化12.5%，邀约话术或邀约时机有问题", html)
        self.assertIn(MGMT_GAP_RULES["high_refund"], html)
        self.assertNotIn(MGMT_GAP_RULES["low_invite_conv"], html)

    def test_complaint_issue_is_appended(self):
        html = generate_html(
            [_shop_row(complain_400_num_day="2")],
            [],
            "2026-02-27",
        )
        self.assertIn("当日投诉2单，客户体验存在系统性问题", html)

    def test_fallback_issue_and_low_per_rev_gap(self):
        # 签单 6/20=30%；到店 15/50=30%；退费 2%；零投诉 → 无具体问题带
        html = generate_html(
            [_shop_row(
                deptsale_shop_num="6",
                sg_num="20",
                link_num="50",
                refund_money_d="400",
                complain_400_num_day="0",
            )],
            [],
            "2026-02-27",
        )
        self.assertIn("综合指标偏弱，需全面诊断门店运营机制", html)
        self.assertIn(MGMT_GAP_RULES["low_per_rev"], html)
        self.assertNotIn("严重低于30%合格线", html)
        self.assertNotIn("邀约话术或邀约时机有问题", html)
        self.assertNotIn("签单话术可能存在过度承诺", html)
        self.assertNotIn("客户体验存在系统性问题", html)


if __name__ == "__main__":
    unittest.main()
