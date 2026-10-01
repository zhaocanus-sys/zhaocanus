# -*- coding: utf-8 -*-
"""建信日报 KPI 卡片色带贴线。

卡片颜色走 color_kpi 的双门槛，和部门表「回复率 < 5% 才红」不是同一套规则。
金额和比率先按原始值着色，再四舍五入成卡片文案。文案刚好写成绿线或红线时，
颜色不能跟着文案升级。

- 切面业绩：≥30万绿，≥20万琥珀，否则红。
- 人均切面：≥5000 绿，≥3000 琥珀，否则红。
- 回复率：≥8% 绿，≥5% 琥珀，否则红。
- 企微添加：≥5000 绿，≥3000 琥珀，否则红。
- 调配人数：≥500 绿，≥300 琥珀，否则红。
- 调配转化率：≥10% 绿，≥6% 琥珀，否则红。分母为 0 时比率保持 0，不改用 1。
"""
import re
import unittest

from generate_jianxin_full_report import generate_html


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")
_CARD = re.compile(
    r'<div style="font-size:10px;color:#94a3b8;">(?P<label>[^<]+)</div>\s*'
    r'<div style="font-size:22px;font-weight:700;color:(?P<color>#[0-9a-fA-F]{6});">(?P<value>[^<]*)</div>'
)

GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"


def _row(**overrides):
    row = {
        "worker_id": "w-card",
        "name": "卡片样本",
        "dept_name": "建信二部",
        "channel_name": "自然流量",
        "assign_1d_num": 0,
        "send_msg_1d_num": 100,
        "reply_1d_num": 8,
        "wechat_add_1d_num": 4000,
        "transfer_1d_num": 400,
        "pay_1d_num": 1,
        "pay_1d_amt": 250000,
        "pay_1m_amt": 250000,
        "worker_nums": 1,
        "new_worker_num": 0,
    }
    row.update(overrides)
    return row


def _html(row):
    return generate_html([row], [], "2026-02-27")


def _card(html, label):
    for match in _CARD.finditer(html):
        if match.group("label") == label:
            return match.group("color").lower(), match.group("value").strip()
    raise AssertionError(f"未找到 KPI 卡片：{label}")


class JianxinKpiCardColorBandTests(unittest.TestCase):
    def test_pay_card_keeps_raw_color_when_wan_label_rounds_onto_the_line(self):
        # 299999 展示成 ¥30.0万，仍低于 30 万绿线；199999 展示成 ¥20.0万，仍低于 20 万琥珀线。
        cases = (
            (300000, GREEN, "¥30.0万"),
            (299999, AMBER, "¥30.0万"),
            (200000, AMBER, "¥20.0万"),
            (199999, RED, "¥20.0万"),
        )
        for pay_amt, color, label in cases:
            with self.subTest(pay_amt=pay_amt):
                html = _html(_row(pay_1d_amt=pay_amt, worker_nums=1))
                self.assertEqual((color, label), _card(html, "切面业绩"))
                # 人均 = 切面 / 1，这四档都远高于 5000，用来证明两张卡不是同一个阈值。
                per_color, _per_label = _card(html, "人均切面")
                self.assertEqual(GREEN, per_color)
                self.assertIsNone(_INF_NAN.search(html))
                self.assertNotIn("躺平", html)

    def test_per_capita_card_keeps_raw_color_when_yuan_label_rounds_up(self):
        # 4999.5 和 2999.5 都进位成整数线，颜色仍看未进位的原始人均。
        cases = (
            (5000, GREEN, "¥5,000"),
            (4999.5, AMBER, "¥5,000"),
            (3000, AMBER, "¥3,000"),
            (2999.5, RED, "¥3,000"),
        )
        for pay_amt, color, label in cases:
            with self.subTest(pay_amt=pay_amt):
                html = _html(_row(pay_1d_amt=pay_amt, worker_nums=1))
                self.assertEqual((color, label), _card(html, "人均切面"))
                pay_color, pay_label = _card(html, "切面业绩")
                self.assertEqual(RED, pay_color)
                self.assertEqual("¥0.5万" if pay_amt >= 4500 else "¥0.3万", pay_label)
                self.assertIsNone(_INF_NAN.search(html))

    def test_reply_card_uses_8_and_5_lines_while_dept_cell_stays_binary_at_5(self):
        # 卡片 8/5 三档；部门单元格只在 <5% 变红。同一 5.0% 在两处颜色不同。
        cases = (
            (8, 100, GREEN, "8.0%", f'color:{GREEN}">8(8.0%)'),
            (795, 10000, AMBER, "8.0%", f'color:{GREEN}">795(8.0%)'),
            (5, 100, AMBER, "5.0%", f'color:{GREEN}">5(5.0%)'),
            (495, 10000, RED, "5.0%", f'color:{RED}">495(5.0%)'),
        )
        for reply, send_msg, color, label, dept_cell in cases:
            with self.subTest(reply=reply, send_msg=send_msg):
                html = _html(_row(reply_1d_num=reply, send_msg_1d_num=send_msg))
                self.assertEqual((color, label), _card(html, "回复率"))
                self.assertIn(dept_cell, html)
                self.assertIsNone(_INF_NAN.search(html))

    def test_wechat_and_transfer_counts_flip_on_the_exact_integer_line(self):
        wechat_cases = (
            (5000, GREEN, "5,000"),
            (4999, AMBER, "4,999"),
            (3000, AMBER, "3,000"),
            (2999, RED, "2,999"),
        )
        for wechat, color, label in wechat_cases:
            with self.subTest(metric="wechat", value=wechat):
                html = _html(_row(wechat_add_1d_num=wechat))
                self.assertEqual((color, label), _card(html, "企微添加"))

        transfer_cases = (
            (500, GREEN, "500"),
            (499, AMBER, "499"),
            (300, AMBER, "300"),
            (299, RED, "299"),
        )
        for transfer, color, label in transfer_cases:
            with self.subTest(metric="transfer", value=transfer):
                html = _html(_row(transfer_1d_num=transfer, wechat_add_1d_num=4000))
                self.assertEqual((color, label), _card(html, "调配人数"))
                self.assertIsNone(_INF_NAN.search(html))

    def test_transfer_rate_card_keeps_raw_color_when_percent_label_rounds_up(self):
        # 995/10000=9.95% 展示 10.0% 仍琥珀；599/10000=5.99% 展示 6.0% 仍红。
        # 企微人数保持在绿线之上，避免和添加量色带缠在一起。
        cases = (
            (1000, GREEN, "10.0%"),
            (995, AMBER, "10.0%"),
            (600, AMBER, "6.0%"),
            (599, RED, "6.0%"),
        )
        for transfer, color, label in cases:
            with self.subTest(transfer=transfer):
                html = _html(_row(
                    transfer_1d_num=transfer,
                    wechat_add_1d_num=10000,
                ))
                self.assertEqual((color, label), _card(html, "调配转化率"))
                self.assertEqual((GREEN, "10,000"), _card(html, "企微添加"))
                self.assertEqual(GREEN, _card(html, "调配人数")[0])
                self.assertIsNone(_INF_NAN.search(html))

    def test_zero_denominators_do_not_promote_rate_or_per_capita_cards(self):
        # 切面已过绿线、调配人数已过绿线、回复条数非 0，但在岗/发信/企微为 0。
        # 团队汇总分母为 0 时比率和人均必须保持 0，不能退回除以 1。
        html = _html(_row(
            pay_1d_amt=300000,
            worker_nums=0,
            send_msg_1d_num=0,
            reply_1d_num=8,
            wechat_add_1d_num=0,
            transfer_1d_num=500,
        ))
        self.assertEqual((GREEN, "¥30.0万"), _card(html, "切面业绩"))
        self.assertEqual((RED, "¥0"), _card(html, "人均切面"))
        self.assertEqual((RED, "0.0%"), _card(html, "回复率"))
        self.assertEqual((GREEN, "500"), _card(html, "调配人数"))
        self.assertEqual((RED, "0.0%"), _card(html, "调配转化率"))
        self.assertEqual((RED, "0"), _card(html, "企微添加"))
        self.assertIsNone(_INF_NAN.search(html))
        self.assertNotIn("躺平", html)


if __name__ == "__main__":
    unittest.main()
