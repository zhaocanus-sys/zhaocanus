# -*- coding: utf-8 -*-
"""Regression coverage for APP retention matrix, knowledge collision, and AARRR gates."""
import math
import unittest
from unittest import mock

from app_report_html import (
    aarrr_html,
    knowledge_collision_html,
    platform_compare_html,
    retention_matrix_html,
)
from quality_supervision.transcript_api_client import is_api_configured


def _kpi(**overrides):
    base = {
        "mems": 1000,
        "retain": {1: 250, 2: 100, 3: 80, 4: 70, 5: 60, 6: 55, 7: 50, 15: 30, 30: 20},
        "active": 20000,
        "pay_rate": 3.5,
        "arpu": 30.0,
        "total_rev": 100000,
        "order_pay": 50,
        "order_fail": 45,
        "order_fail_rate": 47.0,
        "retain_rate_1d": 25.0,
        "anchmems": 12,
        "live_rev": 8000,
        "avg_anchtime": 1800,
        "fugou_pct": 40.0,
        "link_1d": 1200,
        "callout_1d": 800,
        "leads_online": 100,
        "leads_offline": 50,
    }
    base.update(overrides)
    return base


def _traffic(**overrides):
    base = {
        "total_cost": 10000,
        "total_reg": 500,
        "channels": [
            {
                "name": "亏损渠道",
                "cost": 5000,
                "amt_d": 500,
                "roi": 0.1,
            },
            {
                "name": "健康渠道",
                "cost": 5000,
                "amt_d": 8000,
                "roi": 1.6,
            },
        ],
    }
    base.update(overrides)
    return base


class RetentionMatrixHtmlTests(unittest.TestCase):
    def test_day1_below_30_marks_aha_gap_and_fast_decay(self):
        html = retention_matrix_html(_kpi())

        self.assertIn("次日留存25.0%低于30%基准", html)
        self.assertIn("首日Aha时刻未到达", html)
        # 1日250→2日100，衰减60% > 50%
        self.assertIn("衰减率60%", html)
        self.assertIn("衰减过快", html)
        self.assertIn("日增营收", html)
        self.assertNotIn("inf", html.lower())

    def test_day1_near_target_and_healthy_paths(self):
        near = retention_matrix_html(
            _kpi(
                retain={1: 350, 2: 300, 7: 200},
                mems=1000,
            )
        )
        healthy = retention_matrix_html(
            _kpi(
                retain={1: 450, 2: 400, 7: 300},
                mems=1000,
            )
        )

        self.assertIn("接近40%目标", near)
        self.assertNotIn("低于30%基准", near)
        self.assertNotIn("衰减过快", near)

        self.assertIn("表现良好", healthy)
        self.assertNotIn("低于30%基准", healthy)
        self.assertNotIn("接近40%目标", healthy)

    def test_zero_members_keeps_finite_zero_rates(self):
        html = retention_matrix_html(_kpi(mems=0, retain={1: 0, 2: 0, 7: 0}))

        self.assertIn("0.0%", html)
        self.assertIn("今日新注册 <b>0</b> 人", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())


class KnowledgeCollisionHtmlTests(unittest.TestCase):
    def test_payment_loss_and_live_uplift_estimates(self):
        html = knowledge_collision_html(_kpi())

        # loss = 100000/50*45 = 90000
        self.assertIn("日损失预估¥90,000", html)
        self.assertIn("成功率+10%", html)
        # pay_est = 45*0.1*(100000/50) = 9000
        self.assertIn("日增¥9,000", html)
        self.assertIn("直播营收+¥8,000/日", html)
        self.assertIn("次日留存25.0%", html)
        self.assertNotIn("inf", html.lower())

    def test_zero_order_pay_avoids_division_errors(self):
        html = knowledge_collision_html(
            _kpi(order_pay=0, order_fail=10, total_rev=50000, live_rev=0)
        )

        self.assertIn("日损失预估¥0", html)
        self.assertIn("日增¥0", html)
        self.assertIn("直播营收+¥0/日", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())


class AarrrHtmlTests(unittest.TestCase):
    def test_ltv_cac_below_3x_and_payment_leverage(self):
        # CPA = 10000/500 = 20; LTV = 30*30 = 900; LTV/CAC = 45x → healthy
        # Force unhealthy CAC: cost high / reg low
        html = aarrr_html(
            _kpi(order_fail_rate=47.0, retain_rate_1d=25.0, pay_rate=3.5, arpu=20.0),
            {},
            _traffic(total_cost=20000, total_reg=100),  # CPA=200; LTV=600; 3.0x boundary
        )
        # 600/200 = 3.0 → healthy branch uses >=3 as healthy via "else"
        self.assertIn("健康，>3x", html)
        self.assertIn("支付成功率", html)

        unhealthy = aarrr_html(
            _kpi(order_fail_rate=47.0, arpu=10.0),
            {},
            _traffic(total_cost=20000, total_reg=100),  # LTV=300 / CPA=200 = 1.5x
        )
        self.assertIn("低于3x健康线", unhealthy)
        self.assertIn("最大杠杆：<b>支付成功率</b>", unhealthy)

    def test_max_leverage_falls_through_retain_then_pay_rate(self):
        retain_html = aarrr_html(
            _kpi(order_fail_rate=20.0, retain_rate_1d=30.0, pay_rate=3.0),
            {},
            _traffic(),
        )
        pay_html = aarrr_html(
            _kpi(order_fail_rate=20.0, retain_rate_1d=45.0, pay_rate=4.0),
            {},
            _traffic(),
        )

        self.assertIn("最大杠杆：<b>留存率</b>", retain_html)
        self.assertIn("最大杠杆：<b>付费率</b>", pay_html)

    def test_zero_registration_keeps_finite_ltv_cac(self):
        html = aarrr_html(_kpi(), {}, _traffic(total_cost=1000, total_reg=0))

        self.assertIn("LTV/CAC", html)
        self.assertIn("低于3x健康线", html)  # cpa=0 → ltv_cac=0
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())
        self.assertTrue(math.isfinite(0.0))


class PlatformCompareHtmlTests(unittest.TestCase):
    def test_ios_significantly_below_android_triggers_iap_warning(self):
        orders = {
            "total_amt": 10000,
            "by_platform": [
                ("iOS", {"cnt": 100, "pay": 30, "amt": 3000, "pay_num": 25}),
                ("Android", {"cnt": 100, "pay": 70, "amt": 7000, "pay_num": 60}),
            ],
        }
        html = platform_compare_html(orders)

        self.assertIn("iOS成功率(30%)显著低于Android(70%)", html)
        self.assertIn("排查IAP/Apple Pay回调", html)
        self.assertNotIn("差距正常范围", html)

    def test_normal_gap_and_zero_denominator_safety(self):
        orders = {
            "total_amt": 0,
            "by_platform": [
                ("iOS", {"cnt": 0, "pay": 0, "amt": 0, "pay_num": 0}),
                ("Android", {"cnt": 10, "pay": 8, "amt": 800, "pay_num": 8}),
            ],
        }
        html = platform_compare_html(orders)

        self.assertIn("差距正常范围", html)
        self.assertIn("0.0%", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())


class TranscriptApiConfigTests(unittest.TestCase):
    def test_is_api_configured_requires_nonempty_base_url(self):
        with mock.patch(
            "quality_supervision.transcript_api_client.facts",
            return_value={"transcript_api": {"base_url": "  "}},
        ):
            self.assertFalse(is_api_configured())

        with mock.patch(
            "quality_supervision.transcript_api_client.facts",
            return_value={"transcript_api": {"base_url": "https://example.local"}},
        ):
            self.assertTrue(is_api_configured())

        with mock.patch(
            "quality_supervision.transcript_api_client.facts",
            return_value={},
        ):
            self.assertFalse(is_api_configured())


if __name__ == "__main__":
    unittest.main()
