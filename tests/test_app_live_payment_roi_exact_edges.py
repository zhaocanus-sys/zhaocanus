# -*- coding: utf-8 -*-
"""Exact-boundary regression tests for APP live, payment, and channel ROI alerts.

Locks operators that change the alert a manager sees:

- live duration warning is ``avg_anchtime/60 < 60`` (60 minutes silent, 59 warns)
- live pay-success color is ``_c(conv, 70, 50)`` and the low-conversion
  warning is ``live_conv < 60``
- payment alert is ``fail_rate > 40`` P0, ``> 25`` watch, else normal
- channel risk list requires ``cnt > 10`` and ``pay/cnt < 0.5``;
  the red row is ``conv < 50`` even below that volume
- a trial block with no formal orders must not divide by zero
- channel ROI color is ``>= 1`` green, ``< 0.5`` red, else amber;
  loss warning and red row are ``roi < 0.3``; reallocation uses ``roi >= 0.5``

Does not retest the interior samples already locked elsewhere
(30-minute live warning, 32% payment watch, 20% channel risk, ROI 0.2 waste).
"""
import unittest

from app_report_html import channel_roi_html, live_section_html, payment_funnel_html


def _live(**overrides):
    base = {
        "anchmems": 8,
        "anchtime": 28800,
        "avg_anchtime": 7200,
        "giftmems": 12,
        "costmoney": 2400,
        "gift_per_viewer": 200,
    }
    base.update(overrides)
    return base


def _live_orders(cnt, pay, amt=1000):
    return {
        "by_live_e2": [("牵线房", {"cnt": cnt, "pay": pay, "amt": amt})],
        "by_live_prod": [],
        "by_channel": [],
        "by_trial": [],
        "total_cnt": cnt,
        "total_pay": pay,
        "total_amt": amt,
    }


def _pay_orders(**overrides):
    base = {
        "by_live_e2": [],
        "by_live_prod": [],
        "by_channel": [],
        "by_trial": [],
        "total_cnt": 100,
        "total_pay": 90,
        "total_amt": 9000,
    }
    base.update(overrides)
    return base


def _kpi(**overrides):
    base = {"total_rev": 9000, "arpu": 100}
    base.update(overrides)
    return base


class LiveExactEdgeTests(unittest.TestCase):
    def test_duration_warns_at_59_minutes_and_stays_silent_at_60(self):
        silent = live_section_html(
            _live(avg_anchtime=3600), _live_orders(100, 100)
        )
        warned = live_section_html(
            _live(avg_anchtime=3540), _live_orders(100, 100)
        )

        self.assertIn("人均60分钟", silent)
        self.assertNotIn("低于60分钟基准", silent)
        self.assertNotIn("偏低", silent)

        self.assertIn("人均直播仅59分钟，低于60分钟基准", warned)
        self.assertNotIn("偏低", warned)

    def test_conversion_color_and_warning_switch_at_70_60_and_50(self):
        green = live_section_html(_live(), _live_orders(100, 70))
        at_sixty = live_section_html(_live(), _live_orders(100, 60))
        at_fifty = live_section_html(_live(), _live_orders(100, 50))
        just_under = live_section_html(_live(), _live_orders(1000, 499))

        self.assertIn('color:#16a34a">70.0%', green)
        self.assertNotIn("偏低", green)

        self.assertIn('color:#d97706">60.0%', at_sixty)
        self.assertNotIn("偏低", at_sixty)
        self.assertNotIn('color:#16a34a">60.0%', at_sixty)

        self.assertIn('color:#d97706">50.0%', at_fifty)
        self.assertIn("直播支付成功率50.0%偏低", at_fifty)
        self.assertNotIn('color:#dc2626">50.0%', at_fifty)

        self.assertIn('color:#dc2626">49.9%', just_under)
        self.assertIn("直播支付成功率49.9%偏低", just_under)
        self.assertNotIn('color:#d97706">49.9%', just_under)


class PaymentExactEdgeTests(unittest.TestCase):
    def test_fail_rate_40_stays_watch_and_40_1_is_p0(self):
        at_forty = payment_funnel_html(
            _kpi(), _pay_orders(total_cnt=250, total_pay=150)
        )
        just_over = payment_funnel_html(
            _kpi(), _pay_orders(total_cnt=1000, total_pay=599)
        )

        self.assertIn("失败 100笔（40.0%）", at_forty)
        self.assertIn("⚠ 需关注", at_forty)
        self.assertNotIn("P0 严重", at_forty)

        self.assertIn("失败 401笔（40.1%）", just_over)
        self.assertIn("🚨 P0 严重", just_over)
        self.assertNotIn("需关注", just_over)

    def test_fail_rate_25_stays_normal_and_25_1_is_watch(self):
        at_twenty_five = payment_funnel_html(
            _kpi(), _pay_orders(total_cnt=200, total_pay=150)
        )
        just_over = payment_funnel_html(
            _kpi(), _pay_orders(total_cnt=1000, total_pay=749)
        )

        self.assertIn("失败 50笔（25.0%）", at_twenty_five)
        self.assertIn("✅ 正常", at_twenty_five)
        self.assertNotIn("需关注", at_twenty_five)
        self.assertNotIn("P0 严重", at_twenty_five)

        self.assertIn("失败 251笔（25.1%）", just_over)
        self.assertIn("⚠ 需关注", just_over)
        self.assertNotIn("P0 严重", just_over)
        self.assertNotIn("✅ 正常", just_over)

    def test_channel_risk_requires_volume_above_10_and_success_below_half(self):
        orders = _pay_orders(
            by_channel=[
                ("贴线量", {"cnt": 10, "pay": 4, "amt": 400}),
                ("恰好五成", {"cnt": 20, "pay": 10, "amt": 2000}),
                ("健康七成", {"cnt": 10, "pay": 7, "amt": 700}),
                ("刚过线", {"cnt": 11, "pay": 5, "amt": 500}),
            ]
        )
        html = payment_funnel_html(_kpi(), orders)

        self.assertIn('color:#dc2626">40.0%', html)
        self.assertIn('color:#d97706">50.0%', html)
        self.assertIn('color:#16a34a">70.0%', html)
        self.assertIn('color:#dc2626">45.5%', html)

        self.assertIn(
            'style="background:#fef2f2;"><td style="padding:6px 10px;font-size:12px;font-weight:600">贴线量</td>',
            html,
        )
        self.assertIn(
            'style=""><td style="padding:6px 10px;font-size:12px;font-weight:600">恰好五成</td>',
            html,
        )
        self.assertIn(
            'style=""><td style="padding:6px 10px;font-size:12px;font-weight:600">健康七成</td>',
            html,
        )
        self.assertIn(
            'style="background:#fef2f2;"><td style="padding:6px 10px;font-size:12px;font-weight:600">刚过线</td>',
            html,
        )

        self.assertIn("支付渠道风险点", html)
        risk = html.split("支付渠道风险点", 1)[1]
        self.assertIn("刚过线", risk)
        self.assertIn("成功率仅45.5%", risk)
        self.assertNotIn("贴线量", risk)
        self.assertNotIn("恰好五成", risk)
        self.assertNotIn("健康七成", risk)

    def test_trial_unit_price_requires_both_denominators(self):
        missing_formal = payment_funnel_html(
            _kpi(),
            _pay_orders(by_trial=[("是", {"cnt": 4, "pay": 4, "amt": 200})]),
        )
        both = payment_funnel_html(
            _kpi(),
            _pay_orders(
                by_trial=[
                    ("是", {"cnt": 4, "pay": 4, "amt": 200}),
                    ("否", {"cnt": 10, "pay": 8, "amt": 1500}),
                ]
            ),
        )
        no_trial = payment_funnel_html(
            _kpi(),
            _pay_orders(by_trial=[("否", {"cnt": 10, "pay": 8, "amt": 1500})]),
        )

        self.assertIn("试用订单 4笔/¥200 vs 正式订单 0笔/¥0", missing_formal)
        self.assertNotIn("试用客单价", missing_formal)
        self.assertNotIn("正式客单价", missing_formal)
        self.assertIn("试用→正式的转化率决定LTV", missing_formal)

        self.assertIn("试用客单价¥50 vs 正式客单价¥150", both)

        self.assertNotIn("试用→正式转化分析", no_trial)
        self.assertNotIn("正式客单价", no_trial)


class ChannelRoiExactEdgeTests(unittest.TestCase):
    def test_roi_color_loss_and_reallocation_switch_at_0_3_0_5_and_1(self):
        traffic = {
            "channels": [
                {
                    "name": "贴线亏损",
                    "reg": 10,
                    "pay": 1,
                    "pay_rate": 10.0,
                    "amt_d": 290,
                    "cost": 1000,
                    "roi": 0.29,
                    "cpa": 100,
                },
                {
                    "name": "贴线持平",
                    "reg": 8,
                    "pay": 1,
                    "pay_rate": 12.5,
                    "amt_d": 240,
                    "cost": 800,
                    "roi": 0.30,
                    "cpa": 100,
                },
                {
                    "name": "贴线可转",
                    "reg": 6,
                    "pay": 1,
                    "pay_rate": 16.7,
                    "amt_d": 300,
                    "cost": 600,
                    "roi": 0.50,
                    "cpa": 100,
                },
                {
                    "name": "贴线健康",
                    "reg": 5,
                    "pay": 2,
                    "pay_rate": 40.0,
                    "amt_d": 500,
                    "cost": 500,
                    "roi": 1.00,
                    "cpa": 100,
                },
            ],
            "total_cost": 2900,
            "total_amt_d": 1330,
            "overall_roi": 0.46,
            "total_reg": 29,
        }
        html = channel_roi_html(traffic)

        self.assertIn('color:#dc2626">0.29', html)
        self.assertIn('color:#dc2626">0.30', html)
        self.assertIn('color:#d97706">0.50', html)
        self.assertIn('color:#16a34a">1.00', html)
        self.assertNotIn('color:#16a34a">0.30', html)
        self.assertNotIn('color:#d97706">0.29', html)

        self.assertIn(
            'style="background:#fef2f2;"><td style="padding:6px 10px;font-size:12px;font-weight:600">贴线亏损</td>',
            html,
        )
        self.assertIn(
            'style=""><td style="padding:6px 10px;font-size:12px;font-weight:600">贴线持平</td>',
            html,
        )
        self.assertIn(
            'style=""><td style="padding:6px 10px;font-size:12px;font-weight:600">贴线可转</td>',
            html,
        )

        self.assertIn("亏损渠道预警", html)
        loss = html.split("亏损渠道预警", 1)[1].split("自然/免费渠道", 1)[0]
        self.assertIn("贴线亏损", loss)
        self.assertIn("净亏¥710", loss)
        self.assertIn("亏损渠道日亏损合计: ¥710", loss)
        self.assertNotIn("贴线持平", loss)
        self.assertNotIn("贴线可转", loss)
        self.assertNotIn("贴线健康", loss)

        self.assertIn("将亏损渠道的¥1,000预算转移到ROI>0.5的渠道", html)
        self.assertIn("预估额外回收¥1,000/日，月增¥30,000", html)


if __name__ == "__main__":
    unittest.main()
