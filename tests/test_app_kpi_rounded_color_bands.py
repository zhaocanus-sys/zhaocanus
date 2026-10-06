# -*- coding: utf-8 -*-
"""APP KPI 色带不跟随一位小数展示升级。

HTML 卡片和全量报告都按原始值切绿/琥珀/红，数字却印成一位小数。
79.04% 与 79.0%、80.04% 与 80.0%、44.96% 与 45.0%、4.96% 与 5.0%、
2.04% 与 2.0%、29.96 与 30.0 会印成同一个标签。色带、诊断句和改善卡
必须留在原始门槛的一侧。
"""
import unittest

from app_report_html import kpi_cards_html
from generate_app_full_report import generate_html


GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"


def _html_kpi(**overrides):
    base = {
        "active": 180_000,
        "retain_rate_1d": 50.0,
        "retain_rate_7d": 20.0,
        "pay_rate": 6.0,
        "pay_num": 1_000,
        "arpu": 40.0,
        "total_rev": 1_000_000,
        "fugou_amt": 100_000,
        "fugou_pct": 10.0,
        "refund_rate": 1.0,
        "order_conv": 80.0,
        "order_fail": 10,
        "zhenxin_pct": 70.0,
        "amt_m": 9_000_000,
        "pay_m": 8_000,
    }
    base.update(overrides)
    return kpi_cards_html(base, None, None)


def _html_card(label, value, color):
    return (
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-val" style="color:{color}">{value}</div>'
    )


def _report_row(**overrides):
    base = {
        "amt": 1_000_000,
        "pay_num": 1_000,
        "active_members": 10_000,
        "refund_money": 0,
        "pay_num_new": 10,
        "retain_1d": 5_000,
        "retain_7d": 2_000,
        "order_cnt": 100,
        "order_pay": 80,
        "reg_num_m": 10,
        "pay_num_m": 80,
        "pay_amt_m": 9_000_000,
        "mems": 10_000,
        "zhenxin_member": 0,
        "pay_amt": 1_000_000,
        "super_member_full": 0,
        "live_guard": 0,
        "super_member_plus": 0,
        "zhenai_coin": 0,
        "super_remind": 0,
        "star_privilege": 0,
        "super_recommend": 0,
        "other": 0,
    }
    base.update(overrides)
    return base


def _report(**overrides):
    return generate_html([_report_row(**overrides)], [], [], "2026-02-27")


def _report_kpi(label, color, value):
    return (
        f"{label}</div>\n"
        f'<div style="font-size:20px;font-weight:800;color:{color}">{value}</div>'
    )


class HtmlKpiRoundedLabelTests(unittest.TestCase):
    def test_lower_is_better_cards_keep_raw_band(self):
        at_green = _html_kpi(zhenxin_pct=79.0, refund_rate=2.0)
        just_amber = _html_kpi(zhenxin_pct=79.04, refund_rate=2.04)
        at_amber = _html_kpi(zhenxin_pct=80.0, refund_rate=4.0)
        just_red = _html_kpi(zhenxin_pct=80.04, refund_rate=4.04)

        self.assertIn(_html_card("珍心占比", "79.0%", GREEN), at_green)
        self.assertIn(_html_card("珍心占比", "79.0%", AMBER), just_amber)
        self.assertIn(_html_card("珍心占比", "80.0%", AMBER), at_amber)
        self.assertIn(_html_card("珍心占比", "80.0%", RED), just_red)

        self.assertIn(_html_card("退款率", "2.0%", GREEN), at_green)
        self.assertIn(_html_card("退款率", "2.0%", AMBER), just_amber)
        self.assertIn(_html_card("退款率", "4.0%", AMBER), at_amber)
        self.assertIn(_html_card("退款率", "4.0%", RED), just_red)

    def test_higher_is_better_cards_keep_raw_band(self):
        at_green = _html_kpi(retain_rate_1d=45.0, pay_rate=5.0, order_conv=70.0, arpu=30.0)
        just_amber = _html_kpi(retain_rate_1d=44.96, pay_rate=4.96, order_conv=69.96, arpu=29.96)
        at_amber = _html_kpi(retain_rate_1d=35.0, pay_rate=3.0, order_conv=50.0, arpu=20.0)
        just_red = _html_kpi(retain_rate_1d=34.96, pay_rate=2.96, order_conv=49.96, arpu=19.96)

        pairs = (
            ("次日留存", "45.0%", "35.0%"),
            ("付费率", "5.0%", "3.0%"),
            ("订单成功率", "70.0%", "50.0%"),
            ("ARPU", "¥30.0", "¥20.0"),
        )
        for label, hi, lo in pairs:
            self.assertIn(_html_card(label, hi, GREEN), at_green)
            self.assertIn(_html_card(label, hi, AMBER), just_amber)
            self.assertIn(_html_card(label, lo, AMBER), at_amber)
            self.assertIn(_html_card(label, lo, RED), just_red)


class FullReportRenderedRoundedBandTests(unittest.TestCase):
    def test_zhenxin_eighty_line_keeps_health_copy_when_label_matches(self):
        at_line = _report(zhenxin_member=800_000)
        just_over = _report(zhenxin_member=800_400)

        self.assertIn(_report_kpi("珍心占比", AMBER, "80.0%"), at_line)
        self.assertIn("珍心会员占比 80.0%</strong> — ✅ 产品结构健康，珍心占比合理", at_line)
        self.assertNotIn("🚨 超80%红线", at_line)
        self.assertNotIn("⚠ 超80%红线", at_line)
        self.assertNotIn("珍心占比治理", at_line)

        self.assertIn(_report_kpi("珍心占比", RED, "80.0%"), just_over)
        self.assertIn("珍心会员占比 80.0%</strong> — 🚨 超80%红线！产品结构过度集中", just_over)
        self.assertIn("⚠ 超80%红线", just_over)
        self.assertIn("珍心占比治理（从80.0%→<80%）", just_over)
        self.assertNotIn("产品结构健康，珍心占比合理", just_over)

    def test_zhenxin_seventy_nine_line_keeps_card_color(self):
        at_line = _report(zhenxin_member=790_000)
        just_over = _report(zhenxin_member=790_400)

        self.assertIn(_report_kpi("珍心占比", GREEN, "79.0%"), at_line)
        self.assertIn(_report_kpi("珍心占比", AMBER, "79.0%"), just_over)
        self.assertIn("产品结构健康，珍心占比合理", at_line)
        self.assertIn("产品结构健康，珍心占比合理", just_over)
        self.assertNotIn("珍心占比治理", at_line)
        self.assertNotIn("珍心占比治理", just_over)

    def test_retain_forty_five_and_thirty_five_keep_banner(self):
        at_good = _report(mems=10_000, retain_1d=4_500)
        just_under_good = _report(mems=10_000, retain_1d=4_496)
        at_watch = _report(mems=10_000, retain_1d=3_500)
        just_under_watch = _report(mems=10_000, retain_1d=3_496)

        self.assertIn(_report_kpi("次日留存率", GREEN, "45.0%"), at_good)
        self.assertIn("次日留存率 45.0%</strong> — ✅ 留存良好", at_good)
        self.assertNotIn("偏低，需优化首日Hook机制", at_good)

        self.assertIn(_report_kpi("次日留存率", AMBER, "45.0%"), just_under_good)
        self.assertIn("次日留存率 45.0%</strong> — ⚠ 偏低，需优化首日Hook机制", just_under_good)
        self.assertNotIn("✅ 留存良好", just_under_good)
        self.assertNotIn("严重偏低", just_under_good)

        self.assertIn(_report_kpi("次日留存率", AMBER, "35.0%"), at_watch)
        self.assertIn("次日留存率 35.0%</strong> — ⚠ 偏低，需优化首日Hook机制", at_watch)
        self.assertNotIn("严重偏低", at_watch)

        self.assertIn(_report_kpi("次日留存率", RED, "35.0%"), just_under_watch)
        self.assertIn("次日留存率 35.0%</strong> — 🚨 严重偏低", just_under_watch)
        self.assertNotIn("偏低，需优化首日Hook机制", just_under_watch)

    def test_pay_rate_five_percent_label_still_opens_improvement_just_under(self):
        at_line = _report(active_members=10_000, pay_num=500)
        just_under = _report(active_members=10_000, pay_num=496)

        self.assertIn(_report_kpi("付费率", GREEN, "5.0%"), at_line)
        self.assertNotIn("付费率从5.0%提升至5%", at_line)

        self.assertIn(_report_kpi("付费率", AMBER, "5.0%"), just_under)
        self.assertIn("付费率从5.0%提升至5%", just_under)

    def test_pay_rate_three_percent_label_stays_red_just_under(self):
        at_line = _report(active_members=10_000, pay_num=300)
        just_under = _report(active_members=10_000, pay_num=296)

        self.assertIn(_report_kpi("付费率", AMBER, "3.0%"), at_line)
        self.assertIn(_report_kpi("付费率", RED, "3.0%"), just_under)
        self.assertIn("付费率从3.0%提升至5%", at_line)
        self.assertIn("付费率从3.0%提升至5%", just_under)

    def test_refund_two_and_four_percent_labels_keep_severity(self):
        at_two = _report(refund_money=20_000)
        just_over_two = _report(refund_money=20_400)
        at_four = _report(refund_money=40_000)
        just_over_four = _report(refund_money=40_400)

        self.assertIn(_report_kpi("退款率", GREEN, "2.0%"), at_two)
        self.assertIn("退款率 2.0%</strong>（¥2.0万/¥100万）— ✅ 退款控制良好", at_two)
        self.assertNotIn("退款率控制至<2%", at_two)
        self.assertNotIn("超2%红线，需分产品追因", at_two)

        self.assertIn(_report_kpi("退款率", AMBER, "2.0%"), just_over_two)
        self.assertIn("退款率 2.0%</strong>（¥2.0万/¥100万）— ⚠ 超2%红线，需分产品追因", just_over_two)
        self.assertIn("退款率控制至<2%（当前2.0%）", just_over_two)
        self.assertNotIn("退款控制良好", just_over_two)
        self.assertNotIn("超4%", just_over_two)

        self.assertIn(_report_kpi("退款率", AMBER, "4.0%"), at_four)
        self.assertIn("退款率 4.0%</strong>（¥4.0万/¥100万）— ⚠ 超2%红线，需分产品追因", at_four)
        self.assertNotIn("超4%，退款规模大", at_four)

        self.assertIn(_report_kpi("退款率", RED, "4.0%"), just_over_four)
        self.assertIn("退款率 4.0%</strong>（¥4.0万/¥100万）— 🚨 超4%，退款规模大，需专项治理", just_over_four)
        self.assertNotIn("超2%红线，需分产品追因", just_over_four)

    def test_arpu_thirty_and_twenty_keep_copy_when_yuan_label_matches(self):
        at_thirty = _report(amt=300_000, pay_num=10_000, active_members=100_000)
        just_under_thirty = _report(amt=299_600, pay_num=10_000, active_members=100_000)
        at_twenty = _report(amt=200_000, pay_num=10_000, active_members=100_000)
        just_under_twenty = _report(amt=199_600, pay_num=10_000, active_members=100_000)

        self.assertIn(_report_kpi("ARPU", GREEN, "¥30.0"), at_thirty)
        self.assertIn("ARPU ¥30.0</strong> / 付费率 10.0% — ARPU良好，聚焦付费率提升", at_thirty)
        self.assertNotIn("ARPU有提升空间", at_thirty)

        self.assertIn(_report_kpi("ARPU", AMBER, "¥30.0"), just_under_thirty)
        self.assertIn("ARPU ¥30.0</strong> / 付费率 10.0% — ARPU有提升空间（目标¥30）", just_under_thirty)
        self.assertNotIn("ARPU良好", just_under_thirty)

        self.assertIn(_report_kpi("ARPU", AMBER, "¥20.0"), at_twenty)
        self.assertIn(_report_kpi("ARPU", RED, "¥20.0"), just_under_twenty)
        self.assertIn("ARPU ¥20.0</strong> / 付费率 10.0% — ARPU有提升空间（目标¥30）", at_twenty)
        self.assertIn("ARPU ¥20.0</strong> / 付费率 10.0% — ARPU有提升空间（目标¥30）", just_under_twenty)


if __name__ == "__main__":
    unittest.main()
