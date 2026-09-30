# -*- coding: utf-8 -*-
"""门店 KPI 卡片与明细行的贴线色带。

全局诊断用的是另一套比较符（签单 <25/<30，退费 >4/>8，线索文案 >=80）。
卡片本身是 color_kpi 的含等号三档，此前没有钉在渲染结果上：
签单 35/30、日营收 20万/10万、人均 15000/8000、团队退费 4/7、线索 80/60。
明细行退费是 3/6，和团队卡片的 4/7 不是同一条线。

接通→到店的 ic_c（35/25）算出来后没有写进卡片，这里不把它当成已渲染色。
明细退费率的分母含当前 total_realpay 双计；夹具按双计后的展示值对齐色带，
不把双计金额当作真实营收。
"""
import re
import unittest

from generate_shop_full_report import generate_html

GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"


def _shop_row(**overrides):
    row = {
        "dept_name": "深圳门店A",
        "level2": "深圳",
        "dept_worker_name": "店长A",
        "area_worker_name": "区长A",
        "total_realpay": "200000",
        "sale_realpay": "150000",
        "deptsale_realpay": "150000",
        "invite_realpay": "30000",
        "hn_realpay": "20000",
        "total_pay_num": "4",
        "sale_pay_num_all": "3",
        "invite_pay_num": "1",
        "deptsale_shop_num": "35",
        "sg_num": "100",
        "link_num": "200",
        "call_times": "400",
        "zaigang_rs": "2",
        "refund_money_d": "0",
        "complain_400_num_day": "0",
        "leads_xyzout_3day": "10",
        "leads_3day_allot_0day": "9",
        "leads_xyzout_1day": "10",
        "leads_1day_allot_0day": "8",
        "total_realpay_m": "800000",
        "deptsale_realpay_m": "600000",
        "worker_num_call": "2",
    }
    row.update(overrides)
    return row


def _html(**overrides):
    return generate_html([_shop_row(**overrides)], [], "2026-02-27")


def _kpi(html):
    return html.split("KPI卡片", 1)[1].split("业务定位", 1)[0]


def _detail(html):
    return html.split("门店明细（按营收排序", 1)[1].split("</tbody>", 1)[0]


def _card_color(html, label):
    block = _kpi(html)
    idx = block.find(f">{label}</div>")
    if idx < 0:
        raise AssertionError(f"missing KPI label {label}")
    snippet = block[idx:idx + 320]
    match = re.search(r"font-weight:800;color:(#[0-9a-fA-F]{6})", snippet)
    if not match:
        raise AssertionError(snippet)
    return match.group(1)


def _card_value(html, label):
    block = _kpi(html)
    idx = block.find(f">{label}</div>")
    snippet = block[idx:idx + 320]
    match = re.search(r"font-weight:800;color:#[0-9a-fA-F]{6}\">([^<]+)</div>", snippet)
    if not match:
        raise AssertionError(snippet)
    return match.group(1)


class ShopKpiCardColorBands(unittest.TestCase):
    def test_sign_card_and_detail_use_35_and_30_not_diagnosis_25(self):
        # 35.0 含等号进绿；34.9 仍是琥珀。明细行与卡片同一条线。
        green = _html(deptsale_shop_num="35", sg_num="100")
        self.assertEqual(_card_color(green, "签单数"), GREEN)
        self.assertEqual(_card_value(green, "签单数"), "35")
        self.assertIn("签单率35.0%", _kpi(green))
        self.assertEqual(_detail_sign(green), (GREEN, "35.0"))

        amber_high = _html(deptsale_shop_num="349", sg_num="1000")
        self.assertEqual(_card_color(amber_high, "签单数"), AMBER)
        self.assertIn("签单率34.9%", _kpi(amber_high))
        self.assertEqual(_detail_sign(amber_high), (AMBER, "34.9"))

        # 30.0 含等号仍是琥珀，不是绿。29.9 才跌进红。
        amber_low = _html(deptsale_shop_num="30", sg_num="100")
        self.assertEqual(_card_color(amber_low, "签单数"), AMBER)
        self.assertIn("签单率30.0%", _kpi(amber_low))
        self.assertEqual(_detail_sign(amber_low), (AMBER, "30.0"))

        red = _html(deptsale_shop_num="299", sg_num="1000")
        self.assertEqual(_card_color(red, "签单数"), RED)
        self.assertIn("签单率29.9%", _kpi(red))
        self.assertEqual(_detail_sign(red), (RED, "29.9"))

    def test_revenue_card_200k_green_and_displayed_20_wan_can_stay_amber(self):
        exact = _html(total_realpay="200000", zaigang_rs="2")
        self.assertEqual(_card_color(exact, "日营收"), GREEN)
        self.assertEqual(_card_value(exact, "日营收"), "¥20万")

        # 199999/10000 四舍五入仍显示 ¥20万，但 <200000 保持琥珀。
        shown = _html(total_realpay="199999", zaigang_rs="2")
        self.assertEqual(_card_value(shown, "日营收"), "¥20万")
        self.assertEqual(_card_color(shown, "日营收"), AMBER)

        floor = _html(total_realpay="100000", zaigang_rs="2")
        self.assertEqual(_card_color(floor, "日营收"), AMBER)
        self.assertEqual(_card_value(floor, "日营收"), "¥10万")

        # 99999 显示 ¥10万，颜色仍是红，不因为四舍五入升到琥珀。
        under = _html(total_realpay="99999", zaigang_rs="2")
        self.assertEqual(_card_value(under, "日营收"), "¥10万")
        self.assertEqual(_card_color(under, "日营收"), RED)

    def test_per_capita_card_15000_and_8000_are_inclusive(self):
        self.assertEqual(_card_color(_html(total_realpay="15000", zaigang_rs="1"), "人均产值"), GREEN)
        self.assertEqual(_card_value(_html(total_realpay="15000", zaigang_rs="1"), "人均产值"), "¥15,000")

        self.assertEqual(_card_color(_html(total_realpay="14999", zaigang_rs="1"), "人均产值"), AMBER)
        self.assertEqual(_card_value(_html(total_realpay="14999", zaigang_rs="1"), "人均产值"), "¥14,999")

        self.assertEqual(_card_color(_html(total_realpay="8000", zaigang_rs="1"), "人均产值"), AMBER)
        self.assertEqual(_card_value(_html(total_realpay="8000", zaigang_rs="1"), "人均产值"), "¥8,000")

        self.assertEqual(_card_color(_html(total_realpay="7999", zaigang_rs="1"), "人均产值"), RED)
        self.assertEqual(_card_value(_html(total_realpay="7999", zaigang_rs="1"), "人均产值"), "¥7,999")

    def test_team_refund_card_4_is_green_and_displayed_7_can_stay_red(self):
        # 团队退费看 agg_shop 的单次合计，不走明细双计。
        green = _html(total_realpay="10000", refund_money_d="400")
        self.assertEqual(_card_color(green, "退费率"), GREEN)
        self.assertEqual(_card_value(green, "退费率"), "4.0%")

        amber_low = _html(total_realpay="10000", refund_money_d="410")
        self.assertEqual(_card_color(amber_low, "退费率"), AMBER)
        self.assertEqual(_card_value(amber_low, "退费率"), "4.1%")

        # 699/10000 = 6.99，显示 7.0% 且原始值仍 <=7，卡片保持琥珀。
        amber_high = _html(total_realpay="10000", refund_money_d="699")
        self.assertEqual(_card_value(amber_high, "退费率"), "7.0%")
        self.assertEqual(_card_color(amber_high, "退费率"), AMBER)

        # 700/10000 数学上是 7%，浮点是 7.000000000000001，<=7 失败。
        # 卡片仍显示 7.0%，但颜色已经是红，不能按展示值回推成琥珀。
        spilled = _html(total_realpay="10000", refund_money_d="700")
        self.assertEqual(_card_value(spilled, "退费率"), "7.0%")
        self.assertEqual(_card_color(spilled, "退费率"), RED)

        red = _html(total_realpay="10000", refund_money_d="710")
        self.assertEqual(_card_color(red, "退费率"), RED)
        self.assertEqual(_card_value(red, "退费率"), "7.1%")

    def test_detail_refund_row_uses_3_and_6_not_the_team_4_and_7(self):
        # 夹具按双计后的展示值取点：10000 入账后明细分母为 20000。
        green = _html(total_realpay="10000", refund_money_d="600")
        self.assertEqual(_detail_refund(green), (GREEN, "3.0"))

        amber_low = _html(total_realpay="10000", refund_money_d="620")
        self.assertEqual(_detail_refund(amber_low), (AMBER, "3.1"))

        amber_high = _html(total_realpay="10000", refund_money_d="1200")
        self.assertEqual(_detail_refund(amber_high), (AMBER, "6.0"))

        red = _html(total_realpay="10000", refund_money_d="1220")
        self.assertEqual(_detail_refund(red), (RED, "6.1"))

    def test_lead_card_80_and_60_inclusive_and_rounded_display_does_not_promote(self):
        exact = _html(leads_xyzout_1day="10", leads_1day_allot_0day="8")
        self.assertEqual(_card_color(exact, "线索即日分配"), GREEN)
        self.assertEqual(_card_value(exact, "线索即日分配"), "80%")

        # 159/200 = 79.5，卡片四舍五入成 80%，颜色仍按 <80 保持琥珀。
        rounded = _html(leads_xyzout_1day="200", leads_1day_allot_0day="159")
        self.assertEqual(_card_value(rounded, "线索即日分配"), "80%")
        self.assertEqual(_card_color(rounded, "线索即日分配"), AMBER)

        floor = _html(leads_xyzout_1day="100", leads_1day_allot_0day="60")
        self.assertEqual(_card_color(floor, "线索即日分配"), AMBER)
        self.assertEqual(_card_value(floor, "线索即日分配"), "60%")

        # 119/200 = 59.5，显示 60% 但仍是红，不能因为舍入升到琥珀。
        under = _html(leads_xyzout_1day="200", leads_1day_allot_0day="119")
        self.assertEqual(_card_value(under, "线索即日分配"), "60%")
        self.assertEqual(_card_color(under, "线索即日分配"), RED)


def _detail_sign(html):
    match = re.search(
        r'font-weight:600;color:(#[0-9a-fA-F]{6})">(\d+\.\d)%</td>',
        _detail(html),
    )
    if not match:
        raise AssertionError(_detail(html)[:500])
    return match.group(1), match.group(2)


def _detail_refund(html):
    match = re.search(
        r'text-align:center;font-size:12px;color:(#[0-9a-fA-F]{6})">(\d+\.\d)%</td>',
        _detail(html),
    )
    if not match:
        raise AssertionError(_detail(html)[:500])
    return match.group(1), match.group(2)


if __name__ == "__main__":
    unittest.main()
