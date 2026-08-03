# -*- coding: utf-8 -*-
"""Regression tests for APP HTML sections that consume orders/traffic aggregates."""
import math
import unittest
from unittest import mock

from app_report_html import (
    channel_roi_html,
    improvements_html,
    live_section_html,
    payment_funnel_html,
)


def _live_metrics(**overrides):
    base = {
        "anchmems": 10,
        "anchtime": 36000,  # 10 hours total
        "avg_anchtime": 1800,  # 30 minutes — below 60m baseline
        "giftmems": 20,
        "costmoney": 5000,
        "gift_per_viewer": 250,
    }
    base.update(overrides)
    return base


def _orders(**overrides):
    base = {
        "by_live_e2": [
            ("牵线房", {"cnt": 100, "pay": 40, "amt": 8000}),
            ("守护房", {"cnt": 50, "pay": 45, "amt": 9000}),
        ],
        "by_live_prod": [
            ("直播守护", {"cnt": 80, "pay": 50, "amt": 10000}),
            ("珍心会员", {"cnt": 70, "pay": 35, "amt": 7000}),
        ],
        "by_channel": [
            ("微信", {"cnt": 100, "pay": 80, "amt": 16000}),
            ("银联", {"cnt": 20, "pay": 4, "amt": 800}),  # 20% success, risk
            ("扫码", {"cnt": 5, "pay": 1, "amt": 100}),  # low volume, not risk
        ],
        "by_trial": [("是", {"cnt": 10, "pay": 8, "amt": 500}), ("否", {"cnt": 115, "pay": 77, "amt": 16300})],
        "total_cnt": 125,
        "total_pay": 85,
        "total_amt": 16800,
    }
    base.update(overrides)
    return base


def _kpi(**overrides):
    base = {
        "total_rev": 100000,
        "order_pay": 85,
        "order_fail": 40,
        "order_fail_rate": 47,
        "arpu": 30,
        "zhenxin_pct": 84,
        "retain_rate_1d": 32,
        "pay_rate": 3.5,
        "active": 200000,
        "avg_anchtime": 1800,
        "live_rev": 17000,
    }
    base.update(overrides)
    return base


def _traffic(**overrides):
    base = {
        "channels": [
            {
                "name": "抖音-信息流",
                "reg": 100,
                "pay": 10,
                "pay_rate": 10,
                "amt_d": 200,
                "cost": 1000,
                "roi": 0.2,
                "cpa": 100,
            },
            {
                "name": "品牌广告",
                "reg": 80,
                "pay": 20,
                "pay_rate": 25,
                "amt_d": 2000,
                "cost": 1000,
                "roi": 2.0,
                "cpa": 50,
            },
            {
                "name": "自然量",
                "reg": 50,
                "pay": 5,
                "pay_rate": 10,
                "amt_d": 500,
                "cost": 0,
                "roi": 0,
                "cpa": 0,
            },
        ],
        "total_cost": 2000,
        "total_amt_d": 2700,
        "overall_roi": 1.35,
        "total_reg": 230,
    }
    base.update(overrides)
    return base


class LiveSectionHtmlTests(unittest.TestCase):
    def test_live_section_computes_conversion_and_warns_on_low_duration(self):
        html = live_section_html(_live_metrics(), _orders())

        # Combined live conversion: (40+45)/(100+50)=56.7% → below 60% warning
        self.assertIn("56.7%", html)
        self.assertIn("支付成功率", html)
        self.assertIn("低于60分钟基准", html)
        self.assertIn("直播支付成功率56.7%偏低", html)
        self.assertIn("牵线房", html)
        self.assertIn("守护房", html)
        # Product share of live_total_amt=17000 → 直播守护 58.8%
        self.assertIn("58.8%", html)
        self.assertNotIn("inf", html.lower())
        self.assertTrue(all(math.isfinite(x) for x in (56.7, 58.8)))

    def test_live_section_empty_orders_keeps_finite_zero_conversion(self):
        orders = _orders(by_live_e2=[], by_live_prod=[])
        html = live_section_html(_live_metrics(avg_anchtime=7200), orders)

        self.assertIn("0.0%", html)
        self.assertNotIn("偏低", html)
        self.assertNotIn("低于60分钟基准", html)
        self.assertNotIn("inf", html.lower())


class PaymentFunnelHtmlTests(unittest.TestCase):
    def test_payment_funnel_marks_p0_and_flags_low_success_channels(self):
        t = _kpi(total_rev=17000, order_pay=85)
        html = payment_funnel_html(t, _orders())

        # fail_rate = 40/125 = 32% → 需关注 (25-40), not P0
        self.assertIn("需关注", html)
        self.assertNotIn("P0 严重", html)

        # High-volume low-success channel (银联 4/20) must be called out
        self.assertIn("银联", html)
        self.assertIn("支付渠道风险点", html)
        self.assertIn("成功率仅20.0%", html)
        # Low-volume 扫码 (cnt=5) must NOT enter risk list
        risk_block = html.split("支付渠道风险点")[1]
        self.assertNotIn("扫码", risk_block)

    def test_payment_funnel_zero_orders_is_safe_and_normal(self):
        orders = _orders(
            by_channel=[],
            by_trial=[],
            total_cnt=0,
            total_pay=0,
            total_amt=0,
        )
        html = payment_funnel_html(_kpi(total_rev=0, order_pay=0), orders)

        self.assertIn("正常", html)
        self.assertIn("失败 0笔（0.0%）", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())


class ChannelRoiHtmlTests(unittest.TestCase):
    def test_channel_roi_separates_paid_free_and_sums_losing_waste(self):
        html = channel_roi_html(_traffic())

        self.assertIn("付费渠道", html)
        self.assertIn("抖音-信息流", html)
        self.assertIn("品牌广告", html)
        self.assertIn("自然/免费渠道", html)
        self.assertIn("自然量", html)

        # Losing channel (ROI 0.2): cost 1000 - amt_d 200 = 800 waste
        self.assertIn("亏损渠道预警", html)
        self.assertIn("净亏¥800", html)
        self.assertIn("亏损渠道日亏损合计: ¥800", html)
        self.assertIn("整体ROI=1.35", html)


class ImprovementsHtmlTests(unittest.TestCase):
    def test_improvements_prioritize_p0_triggers_and_sort_by_uplift(self):
        import datetime as real_datetime

        fixed_now = real_datetime.datetime(2026, 8, 3, 12, 0, 0)
        with mock.patch("app_report_html.datetime.datetime") as mock_dt_cls:
            mock_dt_cls.now.return_value = fixed_now
            html = improvements_html(_kpi(), _orders(), _traffic())

        self.assertIn("部署: 2026-08-04", html)
        self.assertIn("支付成功率治理", html)
        self.assertIn("珍心占比治理", html)
        self.assertIn("次日留存提升", html)
        self.assertIn("亏损渠道优化", html)

        # Sorted by estimated uplift descending: payment P0 should outrank always-on live P1.
        pay_pos = html.find("支付成功率治理")
        live_pos = html.find("直播运营密度提升")
        self.assertGreater(pay_pos, 0)
        self.assertGreater(live_pos, 0)
        self.assertLess(pay_pos, live_pos)


if __name__ == "__main__":
    unittest.main()
