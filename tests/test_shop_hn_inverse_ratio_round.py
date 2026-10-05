# -*- coding: utf-8 -*-
"""门店 / 红娘 TOP 对 BOTTOM 的逆向倍数贴线。

退费是越低越好。颜色用 <=0.7 绿、<=1.0 琥珀、否则红。
展示保留 1 位小数后，0.695 与 0.705 都印成 0.7x，1.000 与 1.004 都印成 1.0x。
颜色必须跟严格比较走，不能跟着印出来的倍数升级或降级。

更高越好的 1.5 / 1.1（>= 着色、> 文案）已在其他用例锁过，这里不再覆盖。
"""
import unittest

from generate_hongniang_full_report import generate_html as hn_html
from generate_shop_full_report import generate_html as shop_html


def _shop_rows(top_refund, bot_refund=100):
    """10 家门店，前 5 与后 5 营收分层，退费率倍数由退费金额决定。

    整数营收目前会被累加两次，退费率绝对值减半，但倍数分子分母同比，
    比较结果不变。不用 700 这个点：双倍分母会把 3.5/5.0 抬成
    0.7000000000000002，印成 0.7x 却落到琥珀。那是累加误差，不拿来当门槛。
    """
    rows = []
    for i in range(5):
        rows.append({
            "dept_name": f"高营收店{i}",
            "dept_worker_name": f"高负责人{i}",
            "total_realpay": 10000,
            "refund_money_d": top_refund,
            "zaigang_rs": 2,
            "sg_num": 10,
            "deptsale_shop_num": 4,
            "link_num": 20,
            "total_pay_num": 4,
        })
    for i in range(5):
        rows.append({
            "dept_name": f"低营收店{i}",
            "dept_worker_name": f"低负责人{i}",
            "total_realpay": 1000,
            "refund_money_d": bot_refund,
            "zaigang_rs": 2,
            "sg_num": 10,
            "deptsale_shop_num": 4,
            "link_num": 20,
            "total_pay_num": 4,
        })
    return rows


def _hn_hourly(top_refund, bot_refund=100):
    rows = []
    for i in range(5):
        rows.append({
            "worker_name": f"高分红娘{i}",
            "dept_name": "深圳红娘一部",
            "jm_n": 10,
            "zhenai_back": top_refund,
        })
    for i in range(5):
        rows.append({
            "worker_name": f"低分红娘{i}",
            "dept_name": "深圳红娘一部",
            "jm_n": 1,
            "zhenai_back": bot_refund,
        })
    return rows


def _hn_today():
    return [{
        "dept_name": "深圳红娘一部",
        "staff_new": 10,
        "pay_1d_amt": 100000,
        "jm_n": 10,
        "link_time_count": 100,
        "deep_count": 40,
    }]


def _ratio_row(html, label):
    return html.split(f">{label}</td>", 1)[1].split("</tr>", 1)[0]


class ShopRefundRatioRoundedTests(unittest.TestCase):
    def test_printed_0_7x_stays_green_only_at_exact_line(self):
        # 695/1000=0.695，705/1000=0.705。两边都印成 0.7x。
        at_line = _ratio_row(shop_html(_shop_rows(695), [], "2026-02-27"), "退费率")
        just_over = _ratio_row(shop_html(_shop_rows(705), [], "2026-02-27"), "退费率")

        self.assertIn('color:#16a34a">0.7x', at_line)
        self.assertIn("差距较小", at_line)
        self.assertNotIn("差距显著", at_line)
        self.assertNotIn("差距可控", at_line)

        self.assertIn('color:#d97706">0.7x', just_over)
        self.assertNotIn('color:#16a34a">0.7x', just_over)
        self.assertIn("差距较小", just_over)
        self.assertNotIn("差距显著", just_over)

    def test_printed_1_0x_turns_red_once_ratio_exceeds_one(self):
        # 1000/1000=1.0 仍属琥珀；1004/1000=1.004 印成同一个 1.0x，已经是红。
        at_line = _ratio_row(shop_html(_shop_rows(1000), [], "2026-02-27"), "退费率")
        just_over = _ratio_row(shop_html(_shop_rows(1004), [], "2026-02-27"), "退费率")

        self.assertIn('color:#d97706">1.0x', at_line)
        self.assertNotIn('color:#dc2626">1.0x', at_line)
        self.assertIn("差距较小", at_line)

        self.assertIn('color:#dc2626">1.0x', just_over)
        self.assertNotIn('color:#d97706">1.0x', just_over)
        self.assertIn("差距较小", just_over)
        self.assertNotIn("差距可控", just_over)


class HongniangRefundRatioRoundedTests(unittest.TestCase):
    def test_printed_0_7x_stays_green_only_at_exact_line(self):
        at_line = _ratio_row(
            hn_html(_hn_today(), [], _hn_hourly(70), "2026-02-27"), "退费总额")
        just_over = _ratio_row(
            hn_html(_hn_today(), [], _hn_hourly(74), "2026-02-27"), "退费总额")

        self.assertIn('color:#16a34a">0.7x', at_line)
        self.assertIn("差距较小", at_line)
        self.assertNotIn('color:#d97706">0.7x', at_line)

        self.assertIn('color:#d97706">0.7x', just_over)
        self.assertNotIn('color:#16a34a">0.7x', just_over)
        self.assertIn("差距较小", just_over)

    def test_printed_1_0x_turns_red_once_ratio_exceeds_one(self):
        at_line = _ratio_row(
            hn_html(_hn_today(), [], _hn_hourly(100), "2026-02-27"), "退费总额")
        just_over = _ratio_row(
            hn_html(_hn_today(), [], _hn_hourly(104), "2026-02-27"), "退费总额")

        self.assertIn('color:#d97706">1.0x', at_line)
        self.assertNotIn('color:#dc2626">1.0x', at_line)

        self.assertIn('color:#dc2626">1.0x', just_over)
        self.assertNotIn('color:#d97706">1.0x', just_over)
        self.assertIn("差距较小", just_over)
