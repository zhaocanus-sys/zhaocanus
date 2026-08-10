# -*- coding: utf-8 -*-
"""Regression coverage for APP product mix, user structure, and funnel bottleneck gates."""
import unittest

from app_report_data import PRODUCTS
from app_report_html import (
    _product_diag,
    funnel_chain_html,
    product_mix_html,
    user_structure_html,
)


def _prod_vals(**overrides):
    vals = {key: 0 for key, _, _, _ in PRODUCTS}
    vals.update(overrides)
    return vals


def _kpi(**overrides):
    base = {
        "total_rev": 100000,
        "pay_num": 200,
        "prod_vals": _prod_vals(
            zhenxin_member=90000,
            super_member_full=5000,
            live_guard=3000,
            other=2000,
        ),
        "fugou_amt": 60000,
        "fugou_pct": 60.0,
        "new_pay": 40,
        "pay_d_lj": 10,
        "order_fail_rate": 47.0,
        "retain_rate_1d": 32.0,
        "pay_rate": 3.5,
        "active": 10000,
        "order_cnt": 100,
        "order_pay": 53,
        "order_conv": 53.0,
        "order_fail": 47,
        "arpu": 30.0,
    }
    base.update(overrides)
    return base


class ProductMixGateTests(unittest.TestCase):
    def test_zhenxin_over_80_marks_redline_and_structure_risk(self):
        html = product_mix_html(_kpi())

        self.assertIn("⚠ 超80%红线", html)
        self.assertIn("产品结构高风险", html)
        self.assertIn("核心产品，但占比过高有结构风险", html)
        self.assertIn("产品多元化新增", html)

    def test_healthy_product_mix_skips_redline_badge(self):
        html = product_mix_html(
            _kpi(
                prod_vals=_prod_vals(
                    zhenxin_member=50000,
                    super_member_full=20000,
                    live_guard=15000,
                    other=15000,
                )
            )
        )

        self.assertNotIn("⚠ 超80%红线", html)
        self.assertIn("结构相对健康", html)
        self.assertIn("核心产品，占比健康", html)

    def test_product_diag_tiers_by_share_and_amount(self):
        self.assertEqual(
            _product_diag("zhenxin_member", 81, 81000),
            "核心产品，但占比过高有结构风险",
        )
        self.assertEqual(
            _product_diag("zhenxin_member", 60, 60000),
            "核心产品，占比健康",
        )
        self.assertEqual(
            _product_diag("live_guard", 12, 12000),
            "第二梯队，具有独立增长潜力",
        )
        self.assertEqual(
            _product_diag("super_remind", 5, 5000),
            "有一定基础，提升曝光可加速增长",
        )
        self.assertEqual(
            _product_diag("star_privilege", 1, 1500),
            "占比偏低，需优化入口和价值感知",
        )
        self.assertEqual(
            _product_diag("other", 0.5, 500),
            "待激活，考虑捆绑推荐或场景教育",
        )


class UserStructureGateTests(unittest.TestCase):
    def test_risk_users_trigger_fraud_monitor_and_high_repurchase_copy(self):
        orders = {
            "by_utype": [
                ("风险用户A", {"cnt": 3, "pay": 1, "amt": 9000}),
                ("普通", {"cnt": 10, "pay": 8, "amt": 50000}),
            ]
        }
        html = user_structure_html(_kpi(), orders)

        self.assertIn("风险用户交易监控", html)
        self.assertIn("风险用户A：3笔订单，金额¥9,000", html)
        self.assertIn("风险用户总交易: ¥9,000", html)
        self.assertIn("复购是营收主力引擎", html)

    def test_low_repurchase_without_risk_users_skips_monitor(self):
        html = user_structure_html(
            _kpi(fugou_amt=20000, fugou_pct=20.0),
            {"by_utype": [("普通", {"cnt": 8, "pay": 6, "amt": 40000})]},
        )

        self.assertNotIn("风险用户交易监控", html)
        self.assertIn("复购占比偏低", html)
        self.assertIn("复购率提至50%", html)


class FunnelBottleneckGateTests(unittest.TestCase):
    def test_payment_failure_outranks_retention_and_pay_rate(self):
        html = funnel_chain_html(
            _kpi(order_fail_rate=47.0, retain_rate_1d=32.0, pay_rate=3.0)
        )
        self.assertIn("最大瓶颈：支付成功率", html)
        self.assertIn("失败率47.0%", html)

    def test_retention_bottleneck_when_payment_healthy(self):
        html = funnel_chain_html(
            _kpi(order_fail_rate=10.0, retain_rate_1d=32.0, pay_rate=3.0)
        )
        self.assertIn("最大瓶颈：次日留存率", html)
        self.assertIn("低于40%目标", html)

    def test_pay_rate_bottleneck_when_payment_and_retention_healthy(self):
        html = funnel_chain_html(
            _kpi(order_fail_rate=10.0, retain_rate_1d=50.0, pay_rate=3.0)
        )
        self.assertIn("最大瓶颈：付费率", html)
        self.assertIn("低于5%目标", html)


if __name__ == "__main__":
    unittest.main()
