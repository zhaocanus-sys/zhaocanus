# -*- coding: utf-8 -*-
"""Exact-edge coverage for APP funnel chips, retention bands, AARRR, and improvement cards.

Interior samples already lock payment-failure outranking retention, and a
sub-3x LTV/CAC warning. These cases pin the operators that flip the named
bottleneck, chip color, and whether an action card is emitted.
"""
import unittest

from app_report_html import (
    aarrr_html,
    funnel_chain_html,
    improvements_html,
    retention_matrix_html,
)


def _kpi(**overrides):
    base = {
        "active": 1000,
        "mems": 1000,
        "pay_rate": 4.0,
        "arpu": 20.0,
        "total_rev": 20000,
        "retain_rate_1d": 50.0,
        "retain": {1: 500, 2: 400, 7: 200},
        "order_cnt": 100,
        "order_pay": 60,
        "order_fail": 40,
        "order_fail_rate": 10.0,
        "order_conv": 60.0,
        "zhenxin_pct": 70.0,
        "avg_anchtime": 3600,
        "live_rev": 8000,
        "fugou_pct": 40.0,
        "link_1d": 10,
        "callout_1d": 5,
        "leads_online": 4,
        "leads_offline": 2,
    }
    base.update(overrides)
    return base


def _traffic(**overrides):
    base = {
        "total_cost": 1000,
        "total_reg": 10,
        "channels": [],
    }
    base.update(overrides)
    return base


def _chunk(html, label):
    idx = html.find(label)
    if idx < 0:
        raise AssertionError(f"missing label: {label}")
    start = html.rfind("<div", 0, idx)
    end = html.find("</div>", idx)
    return html[start:end]


def _retain_cell(html, day):
    """Background lives on the wrapper div, one level above the day label."""
    token = f">{day}日留存"
    idx = html.find(token)
    if idx < 0:
        raise AssertionError(f"missing retain cell: {token}")
    inner = html.rfind("<div", 0, idx)
    outer = html.rfind("<div", 0, inner)
    end = idx
    for _ in range(2):
        end = html.find("</div>", end)
        if end < 0:
            break
        end += len("</div>")
    return html[outer:end]


class FunnelExactEdgeTests(unittest.TestCase):
    def test_fail_rate_40_stays_on_retention_and_40_1_names_payment(self):
        at_line = funnel_chain_html(_kpi(
            order_fail_rate=40.0,
            retain_rate_1d=39.9,
            pay_rate=4.0,
            active=1000,
            arpu=20.0,
        ))
        self.assertIn("最大瓶颈：次日留存率", at_line)
        self.assertNotIn("最大瓶颈：支付成功率", at_line)
        self.assertIn("低于40%目标", at_line)
        self.assertIn("付费池+50人", at_line)
        self.assertIn("日增¥40", at_line)

        over = funnel_chain_html(_kpi(
            order_fail_rate=40.1,
            retain_rate_1d=50.0,
            pay_rate=6.0,
            order_fail=100,
            arpu=20.0,
        ))
        self.assertIn("最大瓶颈：支付成功率", over)
        self.assertIn("失败率40.1%", over)
        self.assertIn("日增10笔", over)
        self.assertIn("约¥200/日", over)
        self.assertNotIn("最大瓶颈：次日留存率", over)
        self.assertNotIn("最大瓶颈：付费率", over)

    def test_retain_40_switches_bottleneck_to_pay_rate(self):
        at_line = funnel_chain_html(_kpi(
            order_fail_rate=10.0,
            retain_rate_1d=40.0,
            pay_rate=4.9,
            active=1000,
            arpu=20.0,
        ))
        self.assertIn("最大瓶颈：付费率", at_line)
        self.assertIn("付费率4.9%，低于5%目标", at_line)
        self.assertIn("新增10付费用户", at_line)
        self.assertIn("日增¥200", at_line)
        self.assertNotIn("最大瓶颈：次日留存率", at_line)

        just_under = funnel_chain_html(_kpi(
            order_fail_rate=10.0,
            retain_rate_1d=39.9,
            pay_rate=4.9,
        ))
        self.assertIn("最大瓶颈：次日留存率", just_under)
        self.assertNotIn("最大瓶颈：付费率", just_under)

    def test_funnel_chip_colors_flip_on_exact_thresholds(self):
        retain_red = _chunk(
            funnel_chain_html(_kpi(retain_rate_1d=34.9)), "留存34.9%")
        self.assertIn("border:3px solid #dc2626", retain_red)
        self.assertIn("background:#fef2f2", retain_red)

        retain_amber_weak = _chunk(
            funnel_chain_html(_kpi(retain_rate_1d=35.0)), "留存35.0%")
        self.assertIn("border:3px solid #d97706", retain_amber_weak)
        self.assertIn("background:#fef2f2", retain_amber_weak)
        self.assertNotIn("#dc2626", retain_amber_weak)

        retain_amber_quiet = _chunk(
            funnel_chain_html(_kpi(retain_rate_1d=40.0)), "留存40.0%")
        self.assertIn("border:3px solid #d97706", retain_amber_quiet)
        self.assertNotIn("background:#fef2f2", retain_amber_quiet)

        pay_red = _chunk(funnel_chain_html(_kpi(pay_rate=2.9)), "付费率2.9%")
        self.assertIn("border:3px solid #dc2626", pay_red)
        self.assertIn("background:#fef2f2", pay_red)

        pay_amber_weak = _chunk(funnel_chain_html(_kpi(pay_rate=3.0)), "付费率3.0%")
        self.assertIn("border:3px solid #d97706", pay_amber_weak)
        self.assertIn("background:#fef2f2", pay_amber_weak)

        pay_quiet = _chunk(funnel_chain_html(_kpi(pay_rate=5.0)), "付费率5.0%")
        self.assertIn("border:3px solid #d97706", pay_quiet)
        self.assertNotIn("background:#fef2f2", pay_quiet)

        conv_red = _chunk(funnel_chain_html(_kpi(order_conv=54.9)), "支付成功54.9%")
        self.assertIn("border:3px solid #dc2626", conv_red)
        self.assertIn("background:#fef2f2", conv_red)

        conv_amber_weak = _chunk(
            funnel_chain_html(_kpi(order_conv=55.0)), "支付成功55.0%")
        self.assertIn("border:3px solid #d97706", conv_amber_weak)
        self.assertIn("background:#fef2f2", conv_amber_weak)

        conv_quiet = _chunk(funnel_chain_html(_kpi(order_conv=70.0)), "支付成功70.0%")
        self.assertIn("border:3px solid #d97706", conv_quiet)
        self.assertNotIn("background:#fef2f2", conv_quiet)

        arpu_amber = _chunk(funnel_chain_html(_kpi(arpu=29.9)), "ARPU¥29.9")
        self.assertIn("border:3px solid #d97706", arpu_amber)
        self.assertNotIn("#16a34a", arpu_amber)

        arpu_green = _chunk(funnel_chain_html(_kpi(arpu=30.0)), "ARPU¥30.0")
        self.assertIn("border:3px solid #16a34a", arpu_green)
        self.assertNotIn("#d97706", arpu_green)
        self.assertNotIn("background:#fef2f2", arpu_green)


class RetentionExactEdgeTests(unittest.TestCase):
    def test_day1_copy_and_cell_color_at_30_and_40(self):
        at_30 = retention_matrix_html(_kpi(mems=1000, retain={1: 300, 2: 0}))
        cell_30 = _retain_cell(at_30, 1)
        self.assertIn("background:#d97706", cell_30)
        self.assertNotIn("#16a34a", cell_30)
        self.assertNotIn("#dc2626", cell_30)
        self.assertIn("次日留存30.0%，接近40%目标", at_30)
        self.assertNotIn("低于30%基准", at_30)
        self.assertNotIn("表现良好", at_30)

        under_30 = retention_matrix_html(_kpi(mems=1000, retain={1: 299, 2: 0}))
        cell_under = _retain_cell(under_30, 1)
        self.assertIn("background:#d97706", cell_under)
        self.assertIn("次日留存29.9%低于30%基准", under_30)
        self.assertNotIn("接近40%目标", under_30)

        at_40 = retention_matrix_html(_kpi(mems=1000, retain={1: 400, 2: 0}))
        cell_40 = _retain_cell(at_40, 1)
        self.assertIn("background:#16a34a", cell_40)
        self.assertIn("次日留存40.0%表现良好", at_40)
        self.assertNotIn("接近40%目标", at_40)
        self.assertNotIn("低于30%基准", at_40)

        just_under_40 = retention_matrix_html(_kpi(mems=1000, retain={1: 399, 2: 0}))
        self.assertIn("次日留存39.9%，接近40%目标", just_under_40)
        self.assertNotIn("表现良好", just_under_40)

    def test_cell_turns_red_at_15_and_gray_when_zero(self):
        at_15 = retention_matrix_html(_kpi(mems=1000, retain={1: 150, 2: 0}))
        cell = _retain_cell(at_15, 1)
        self.assertIn("background:#dc2626", cell)
        self.assertIn("15.0%", cell)
        self.assertNotIn("#d97706", cell)

        just_over = retention_matrix_html(_kpi(mems=1000, retain={1: 151, 2: 0}))
        cell_over = _retain_cell(just_over, 1)
        self.assertIn("background:#d97706", cell_over)
        self.assertNotIn("#dc2626", cell_over)

        zero = retention_matrix_html(_kpi(mems=1000, retain={1: 0, 2: 0}))
        cell_zero = _retain_cell(zero, 1)
        self.assertIn("background:#e2e8f0", cell_zero)
        self.assertIn("color:#94a3b8", cell_zero)
        self.assertNotIn("#dc2626", cell_zero)
        self.assertIn("次日留存0.0%低于30%基准", zero)

    def test_decay_exact_50_stays_quiet_while_displayed_50_can_still_flag(self):
        exact = retention_matrix_html(_kpi(mems=1000, retain={1: 400, 2: 200}))
        self.assertIn("衰减率50%", exact)
        self.assertNotIn("衰减过快", exact)

        just_over = retention_matrix_html(_kpi(mems=1000, retain={1: 400, 2: 199}))
        self.assertIn("衰减率50%", just_over)
        self.assertIn("衰减过快", just_over)


class AarrrAndImprovementExactEdgeTests(unittest.TestCase):
    def test_ltv_cac_exact_3_is_healthy_and_displayed_3_can_still_warn(self):
        healthy = aarrr_html(
            _kpi(arpu=10.0, order_fail_rate=10.0, retain_rate_1d=50.0, pay_rate=6.0),
            {},
            _traffic(total_cost=1000, total_reg=10),
        )
        self.assertIn("LTV/CAC = ¥300 / ¥100 = 3.0x", healthy)
        self.assertIn("健康，>3x", healthy)
        self.assertNotIn("低于3x健康线", healthy)

        displayed_three = aarrr_html(
            _kpi(arpu=2.95, order_fail_rate=10.0, retain_rate_1d=50.0, pay_rate=6.0),
            {},
            _traffic(total_cost=300, total_reg=10),
        )
        self.assertIn("= 3.0x", displayed_three)
        self.assertIn("低于3x健康线", displayed_three)
        self.assertNotIn("健康，>3x", displayed_three)

    def test_aarrr_leverage_uses_same_exclusive_40_line_as_funnel(self):
        at_fail = aarrr_html(
            _kpi(order_fail_rate=40.0, retain_rate_1d=39.9, pay_rate=4.0),
            {},
            _traffic(),
        )
        self.assertIn("最大杠杆：<b>留存率</b>", at_fail)
        self.assertNotIn("最大杠杆：<b>支付成功率</b>", at_fail)

        over_fail = aarrr_html(
            _kpi(order_fail_rate=40.1, retain_rate_1d=50.0, pay_rate=6.0),
            {},
            _traffic(),
        )
        self.assertIn("最大杠杆：<b>支付成功率</b>", over_fail)

        at_retain = aarrr_html(
            _kpi(order_fail_rate=10.0, retain_rate_1d=40.0, pay_rate=4.9),
            {},
            _traffic(),
        )
        self.assertIn("最大杠杆：<b>付费率</b>", at_retain)
        self.assertNotIn("最大杠杆：<b>留存率</b>", at_retain)

    def test_improvement_cards_stay_silent_until_strict_thresholds(self):
        quiet = improvements_html(
            _kpi(
                order_fail_rate=40.0,
                zhenxin_pct=80.0,
                retain_rate_1d=40.0,
                pay_rate=5.0,
            ),
            {},
            _traffic(channels=[{"cost": 100, "amt_d": 30, "roi": 0.3}]),
        )
        self.assertIn("直播运营密度提升", quiet)
        self.assertNotIn("支付成功率治理", quiet)
        self.assertNotIn("珍心占比治理", quiet)
        self.assertNotIn("次日留存提升", quiet)
        self.assertNotIn("付费率从", quiet)
        self.assertNotIn("亏损渠道优化", quiet)

        fired = improvements_html(
            _kpi(
                order_fail_rate=40.1,
                zhenxin_pct=80.1,
                retain_rate_1d=39.9,
                pay_rate=4.9,
                order_pay=10,
                order_fail=4,
                total_rev=1000,
                active=1000,
                arpu=20.0,
            ),
            {},
            _traffic(channels=[{"cost": 100, "amt_d": 29, "roi": 0.29}]),
        )
        self.assertIn("支付成功率治理", fired)
        self.assertIn("珍心占比治理（80.1%→<80%）", fired)
        self.assertIn("次日留存提升至40%（当前39.9%）", fired)
        self.assertIn("付费率从4.9%提升至5%", fired)
        self.assertIn("亏损渠道优化", fired)
        self.assertIn("日省¥71", fired)


if __name__ == "__main__":
    unittest.main()
