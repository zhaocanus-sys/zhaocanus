# -*- coding: utf-8 -*-
"""Regression coverage for APP header, DoD, KPI cards, and full HTML assembly."""
import math
import unittest

from app_report_data import PRODUCTS
from app_report_html import (
    _c,
    _dod,
    assemble_full_html,
    header_html,
    kpi_cards_html,
)


def _kpi(**overrides):
    prod_vals = {key: 0 for key, _, _, _ in PRODUCTS}
    prod_vals.update({
        "zhenxin_member": 85000,
        "super_member_full": 10000,
        "live_guard": 5000,
    })
    base = {
        "active": 200000,
        "pay_num": 8000,
        "total_rev": 240000,
        "amt_m": 7200000,
        "pay_m": 180000,
        "anchmems": 42,
        "anchtime": 151200,
        "avg_anchtime": 3600,
        "order_conv": 53.0,
        "fugou_pct": 55.0,
        "fugou_amt": 132000,
        "order_fail_rate": 47.0,
        "order_fail": 470,
        "order_cnt": 1000,
        "order_pay": 530,
        "retain_rate_1d": 32.0,
        "retain_rate_7d": 18.0,
        "pay_rate": 4.0,
        "arpu": 30.0,
        "refund_rate": 1.5,
        "zhenxin_pct": 85.0,
        "giftmems": 300,
        "costmoney": 9000,
        "gift_per_viewer": 30,
        "live_rev": 15000,
        "mems": 10000,
        "new_pay": 1200,
        "pay_d_lj": 80,
        "leads_online": 200,
        "leads_offline": 100,
        "allot": 150,
        "laoqu": 40,
        "link_1d": 1200,
        "callout_1d": 800,
        "prod_vals": prod_vals,
        "retain": {d: 0 for d in (1, 2, 3, 4, 5, 6, 7, 15, 30)},
    }
    base["retain"][1] = 3200
    base["retain"][2] = 1400
    base["retain"][7] = 1800
    base.update(overrides)
    return base


def _orders(**overrides):
    base = {
        "total_cnt": 125,
        "total_pay": 85,
        "total_amt": 16800,
        "by_live_e2": [("牵线房", {"cnt": 100, "pay": 40, "amt": 8000})],
        "by_live_prod": [("直播守护", {"cnt": 80, "pay": 50, "amt": 10000})],
        "by_channel": [("微信", {"cnt": 100, "pay": 80, "amt": 16000})],
        "by_trial": [],
        "by_entrance1": [("直播", {"cnt": 80, "pay": 40, "amt": 10000})],
        "by_entrance2": [("牵线房", {"cnt": 50, "pay": 20, "amt": 5000})],
        "by_prodname": [("珍心会员-¥98", {"cnt": 40, "pay": 30, "amt": 2940})],
        "by_platform": [
            ("iOS", {"cnt": 60, "pay": 20, "amt": 6000, "pay_num": 18}),
            ("Android", {"cnt": 65, "pay": 45, "amt": 10800, "pay_num": 40}),
        ],
        "by_utype": [("新客", {"cnt": 70, "pay": 40, "amt": 8000})],
        "by_version": [("8.2.1", {"cnt": 80, "pay": 50, "amt": 12000})],
    }
    base.update(overrides)
    return base


def _traffic(**overrides):
    base = {
        "channels": [
            {
                "name": "品牌广告",
                "reg": 80,
                "pay": 20,
                "pay_rate": 25.0,
                "amt_d": 2000,
                "cost": 1000,
                "roi": 2.0,
                "cpa": 12.5,
            }
        ],
        "total_cost": 1000,
        "total_amt_d": 2000,
        "overall_roi": 2.0,
        "total_reg": 80,
    }
    base.update(overrides)
    return base


def _empty_orders():
    return {
        "total_cnt": 0,
        "total_pay": 0,
        "total_amt": 0,
        "by_live_e2": [],
        "by_live_prod": [],
        "by_channel": [],
        "by_trial": [],
        "by_entrance1": [],
        "by_entrance2": [],
        "by_prodname": [],
        "by_platform": [],
        "by_utype": [],
        "by_version": [],
    }


def _empty_traffic():
    return {
        "channels": [],
        "total_cost": 0,
        "total_amt_d": 0,
        "overall_roi": 0,
        "total_reg": 0,
    }


class ColorThresholdTests(unittest.TestCase):
    def test_higher_and_lower_is_better_bands(self):
        self.assertEqual(_c(200000, 200000, 150000), "#16a34a")
        self.assertEqual(_c(150000, 200000, 150000), "#d97706")
        self.assertEqual(_c(149999, 200000, 150000), "#dc2626")

        # 退款率 / 珍心占比：越低越好
        self.assertEqual(_c(2.0, 2, 4, False), "#16a34a")
        self.assertEqual(_c(4.0, 2, 4, False), "#d97706")
        self.assertEqual(_c(4.1, 2, 4, False), "#dc2626")
        self.assertEqual(_c(79.0, 79, 80, False), "#16a34a")
        self.assertEqual(_c(80.0, 79, 80, False), "#d97706")
        self.assertEqual(_c(81.0, 79, 80, False), "#dc2626")


class DayOverDayTests(unittest.TestCase):
    def test_dod_empty_or_zero_previous_returns_blank(self):
        self.assertEqual(_dod({"active": 10}, None, "active"), "")
        self.assertEqual(_dod({"active": 10}, {}, "active"), "")
        self.assertEqual(_dod({"active": 10}, {"active": 0}, "active"), "")
        self.assertEqual(_dod({"active": 10}, {"other": 5}, "active"), "")

    def test_dod_direction_and_lower_is_better_colors(self):
        up = _dod({"active": 200}, {"active": 100}, "active")
        self.assertIn("▲100.0%", up)
        self.assertIn("#16a34a", up)
        self.assertNotIn("▼", up)

        down = _dod({"active": 80}, {"active": 100}, "active")
        self.assertIn("▼20.0%", down)
        self.assertIn("#dc2626", down)

        # 退款上升 = 变差（红）；退款下降 = 变好（绿）
        refund_up = _dod({"refund_rate": 3}, {"refund_rate": 2}, "refund_rate", higher=False)
        self.assertIn("▲50.0%", refund_up)
        self.assertIn("#dc2626", refund_up)

        refund_down = _dod({"refund_rate": 1}, {"refund_rate": 2}, "refund_rate", higher=False)
        self.assertIn("▼50.0%", refund_down)
        self.assertIn("#16a34a", refund_down)


class HeaderHtmlTests(unittest.TestCase):
    def test_header_formats_kpis_and_flags_high_fail_rate(self):
        html = header_html(_kpi(), "2026-08-13")

        self.assertIn("2026-08-13", html)
        self.assertIn("APP产品运营负责人", html)
        self.assertIn("DAU:200,000", html)
        self.assertIn("付费:8,000人", html)
        self.assertIn("日营收:¥24.0万", html)
        self.assertIn("月累:¥720万", html)
        self.assertIn("直播主播42人", html)
        self.assertIn("订单成功率53.0%", html)
        self.assertIn("复购占比55.0%", html)
        self.assertIn("支付失败率47.0%", html)
        self.assertIn("rgba(220,38,38,.4)", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())

    def test_header_healthy_fail_rate_skips_red_background(self):
        html = header_html(_kpi(order_fail_rate=40.0), "2026-08-13")

        self.assertIn("支付失败率40.0%", html)
        self.assertNotIn("rgba(220,38,38,.4)", html)
        self.assertIn("rgba(255,255,255,.15)", html)


class KpiCardsHtmlTests(unittest.TestCase):
    def test_kpi_cards_render_dod_funnel_and_skip_short_trends(self):
        today = _kpi()
        prev = _kpi(active=100000, total_rev=120000, zhenxin_pct=60.0)
        html = kpi_cards_html(today, prev, trends=[{"active_members": 1}])

        self.assertIn("DAU", html)
        self.assertIn("200,000", html)
        self.assertIn("▲100.0%", html)  # DAU 200k vs 100k
        self.assertIn("▲100.0%", html)  # 营收 24万 vs 12万 同为翻倍
        self.assertIn("次日留存", html)
        self.assertIn("32.0%", html)
        self.assertIn("付费率", html)
        self.assertIn("4.0%", html)
        self.assertIn("珍心占比", html)
        self.assertIn("85.0%", html)
        # 珍心 85% > 80 红线 → 红色
        self.assertIn("#dc2626", html)
        self.assertIn("流转: DAU200,000→留存32.0%→付费率4.0%(8,000人)", html)
        self.assertNotIn("<svg", html)
        self.assertNotIn("inf", html.lower())

        empty_prev = kpi_cards_html(today, {}, trends=None)
        self.assertNotIn("▲", empty_prev)
        self.assertNotIn("▼", empty_prev)
        self.assertNotIn("<svg", empty_prev)

    def test_kpi_cards_embed_sparkline_when_trend_window_has_signal(self):
        trends = [
            {
                "active_members": 100000 + i * 1000,
                "pay_rate": 3.0,
                "arpu": 25.0,
                "amt": 100000,
                "fugou_amt": 50000,
                "refund_money": 1000,
                "order_conv": 50.0,
                "retain_1d": 2000,
            }
            for i in range(10)
        ]
        html = kpi_cards_html(_kpi(), _kpi(active=190000), trends)

        self.assertIn("<svg", html)
        self.assertIn("<polyline", html)
        self.assertIn("▲5.3%", html)  # DAU 200000 vs 190000


class AssembleFullHtmlTests(unittest.TestCase):
    def test_assemble_includes_all_modules_and_footer_channel_count(self):
        html = assemble_full_html(
            _kpi(),
            _kpi(active=180000, total_rev=200000),
            _orders(),
            _traffic(),
            [{"dt": "2026-08-13", "amt": 240000, "pay_rate": 4.0, "order_conv": 53.0}],
            "2026-08-13",
        )

        for title in (
            "APP 全量运营深度体检报告",
            "直播运营深度分析",
            "支付漏斗全量分析",
            "入口场景转化分析",
            "多平台对比分析",
            "用户留存矩阵",
            "渠道获客质量",
            "产品品类收入明细",
            "用户结构分析",
            "跨业务线协同",
            "因果链推断",
            "跨领域知识对撞",
            "改善建议",
            "10日营收趋势",
            "APP版本分布",
            "AARRR增长模型",
        ):
            self.assertIn(title, html)

        self.assertIn("APP 全量深度体检报告 2026-08-13", html)
        self.assertIn("覆盖20+诊断模块", html)
        self.assertIn("traffic(16字段×1渠道)", html)
        self.assertIn("rgba(220,38,38,.4)", html)
        self.assertIn("部署:", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())

    def test_assemble_zero_payload_stays_finite_and_skips_empty_sections(self):
        zero = _kpi(
            active=0,
            pay_num=0,
            total_rev=0,
            amt_m=0,
            pay_m=0,
            anchmems=0,
            anchtime=0,
            avg_anchtime=0,
            order_conv=0,
            fugou_pct=0,
            fugou_amt=0,
            order_fail_rate=0,
            order_fail=0,
            order_cnt=0,
            order_pay=0,
            retain_rate_1d=0,
            retain_rate_7d=0,
            pay_rate=0,
            arpu=0,
            refund_rate=0,
            zhenxin_pct=0,
            giftmems=0,
            costmoney=0,
            gift_per_viewer=0,
            live_rev=0,
            mems=0,
            new_pay=0,
            pay_d_lj=0,
            leads_online=0,
            leads_offline=0,
            allot=0,
            laoqu=0,
            link_1d=0,
            callout_1d=0,
            prod_vals={key: 0 for key, _, _, _ in PRODUCTS},
            retain={d: 0 for d in (1, 2, 3, 4, 5, 6, 7, 15, 30)},
        )
        html = assemble_full_html(zero, {}, _empty_orders(), _empty_traffic(), [], "2026-08-13")

        self.assertIn("APP 全量运营深度体检报告", html)
        self.assertIn("DAU:0", html)
        self.assertIn("支付失败率0.0%", html)
        self.assertNotIn("rgba(220,38,38,.4)", html)
        # 空 trends / 空 version → 对应模块不渲染
        self.assertNotIn("10日营收趋势", html)
        self.assertNotIn("APP版本分布", html)
        self.assertIn("traffic(16字段×0渠道)", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())
        self.assertTrue(math.isfinite(0.0))


if __name__ == "__main__":
    unittest.main()
