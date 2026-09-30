# -*- coding: utf-8 -*-
"""电话红娘 KPI 卡片贴线色带。

诊断条用 jm>=1.0 / >=0.8 和退费 >5 / >10。卡片是另一套含等号三档，
此前没有钉在渲染结果上：见面安排率 1.2/0.8、今日营收 15万/8万、
人均 4000/2000、退费 5/10（越低越好）。
"""
import re
import unittest

from generate_hongniang_full_report import generate_html

GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"


def _hn_row(**overrides):
    row = {
        "dept_name": "厦门红娘一区一部",
        "staff_new": "10",
        "call_worker": "8",
        "on_vip": "100",
        "jm_n": "12",
        "jm_all": "20",
        "pay_1d_amt": "150000",
        "pay_1m_amt": "900000",
        "link_time_count": "80",
        "deep_count": "20",
        "love_cnt_m": "3",
        "tousu_n": "0",
        "pay_1d_num": "4",
        "zhenai_back": "0",
        "zhenaigd_back": "0",
        "zhenai_hz_back": "0",
        "zhenai_xfh_back": "0",
        "zhenai_md_back": "0",
    }
    row.update(overrides)
    return row


def _html(**overrides):
    return generate_html([_hn_row(**overrides)], [], [], "2026-02-27")


def _kpi(html):
    return html.split("KPI卡片", 1)[1].split("业务定位", 1)[0]


def _card_color(html, label):
    block = _kpi(html)
    idx = block.find(f">{label}</div>")
    if idx < 0:
        raise AssertionError(f"missing KPI label {label}")
    snippet = block[idx:idx + 360]
    match = re.search(r"font-weight:800;color:(#[0-9a-fA-F]{6})", snippet)
    if not match:
        raise AssertionError(snippet)
    return match.group(1)


def _card_value(html, label):
    block = _kpi(html)
    idx = block.find(f">{label}</div>")
    snippet = block[idx:idx + 360]
    match = re.search(r"font-weight:800;color:#[0-9a-fA-F]{6}\">([^<]+)</div>", snippet)
    if not match:
        raise AssertionError(snippet)
    return match.group(1)


class HongniangKpiCardColorBands(unittest.TestCase):
    def test_jm_card_is_green_at_1_2_and_amber_through_0_8(self):
        green = _html(staff_new="100", jm_n="120")
        self.assertEqual(_card_color(green, "见面安排"), GREEN)
        self.assertEqual(_card_value(green, "见面安排"), "120")
        self.assertIn("安排率 1.20", _kpi(green))

        amber_high = _html(staff_new="100", jm_n="119")
        self.assertEqual(_card_color(amber_high, "见面安排"), AMBER)
        self.assertIn("安排率 1.19", _kpi(amber_high))

        amber_low = _html(staff_new="100", jm_n="80")
        self.assertEqual(_card_color(amber_low, "见面安排"), AMBER)
        self.assertIn("安排率 0.80", _kpi(amber_low))

        red = _html(staff_new="100", jm_n="79")
        self.assertEqual(_card_color(red, "见面安排"), RED)
        self.assertIn("安排率 0.79", _kpi(red))

    def test_revenue_card_150k_green_and_displayed_15_wan_can_stay_amber(self):
        exact = _html(pay_1d_amt="150000")
        self.assertEqual(_card_color(exact, "今日营收"), GREEN)
        self.assertEqual(_card_value(exact, "今日营收"), "¥15.0万")

        # 149999/10000 显示 ¥15.0万，但 <150000 保持琥珀。
        shown = _html(pay_1d_amt="149999")
        self.assertEqual(_card_value(shown, "今日营收"), "¥15.0万")
        self.assertEqual(_card_color(shown, "今日营收"), AMBER)

        floor = _html(pay_1d_amt="80000")
        self.assertEqual(_card_color(floor, "今日营收"), AMBER)
        self.assertEqual(_card_value(floor, "今日营收"), "¥8.0万")

        under = _html(pay_1d_amt="79999")
        self.assertEqual(_card_value(under, "今日营收"), "¥8.0万")
        self.assertEqual(_card_color(under, "今日营收"), RED)

    def test_per_capita_card_4000_and_2000_are_inclusive(self):
        self.assertEqual(_card_color(_html(staff_new="10", pay_1d_amt="40000"), "人均产值"), GREEN)
        self.assertEqual(_card_value(_html(staff_new="10", pay_1d_amt="40000"), "人均产值"), "¥4,000")

        self.assertEqual(_card_color(_html(staff_new="10", pay_1d_amt="39990"), "人均产值"), AMBER)
        self.assertEqual(_card_value(_html(staff_new="10", pay_1d_amt="39990"), "人均产值"), "¥3,999")

        self.assertEqual(_card_color(_html(staff_new="10", pay_1d_amt="20000"), "人均产值"), AMBER)
        self.assertEqual(_card_value(_html(staff_new="10", pay_1d_amt="20000"), "人均产值"), "¥2,000")

        self.assertEqual(_card_color(_html(staff_new="10", pay_1d_amt="19990"), "人均产值"), RED)
        self.assertEqual(_card_value(_html(staff_new="10", pay_1d_amt="19990"), "人均产值"), "¥1,999")

    def test_refund_card_is_green_at_5_and_amber_through_10(self):
        green = _html(pay_1d_amt="100000", zhenai_back="5000")
        self.assertEqual(_card_color(green, "退费率"), GREEN)
        self.assertEqual(_card_value(green, "退费率"), "5.0%")

        amber_low = _html(pay_1d_amt="100000", zhenai_back="5100")
        self.assertEqual(_card_color(amber_low, "退费率"), AMBER)
        self.assertEqual(_card_value(amber_low, "退费率"), "5.1%")

        amber_high = _html(pay_1d_amt="100000", zhenai_back="10000")
        self.assertEqual(_card_color(amber_high, "退费率"), AMBER)
        self.assertEqual(_card_value(amber_high, "退费率"), "10.0%")

        red = _html(pay_1d_amt="100000", zhenai_back="10100")
        self.assertEqual(_card_color(red, "退费率"), RED)
        self.assertEqual(_card_value(red, "退费率"), "10.1%")


if __name__ == "__main__":
    unittest.main()
