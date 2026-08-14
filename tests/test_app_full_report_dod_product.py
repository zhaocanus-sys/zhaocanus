# -*- coding: utf-8 -*-
"""Regression coverage for APP standalone report DoD, product ranks, and trend bars.

These paths live in generate_app_full_report.py (not app_report_html) and were
not covered by open PRs #95/#99: nested dod defaults a missing previous key to
the current value, product TOP/BOTTOM diagnosis bands, causal-chain bottleneck
selection, and the inline 10-day trend window.
"""
import unittest

from generate_app_full_report import (
    color_kpi,
    generate_html,
    parse_rows,
    prev_date,
)


def _app_row(**overrides):
    """Minimal daily-row fixture with string-like API values."""
    row = {
        "amt": "100000",
        "pay_num": "200",
        "active_members": "10000",
        "refund_money": "1000",
        "pay_num_new": "50",
        "retain_1d": "500",
        "retain_7d": "200",
        "order_cnt": "100",
        "order_pay": "70",
        "reg_num_m": "1000",
        "pay_num_m": "500",
        "pay_amt_m": "500000",
        "mems": "1000",
        "zhenxin_member": "50000",
        "pay_amt": "100000",
        "super_member_full": "20000",
        "live_guard": "12000",
        "super_member_plus": "8000",
        "zhenai_coin": "5000",
        "super_remind": "3000",
        "star_privilege": "1500",
        "super_recommend": "400",
        "other": "100",
    }
    row.update(overrides)
    return row


def _ranked_product_row():
    """Fixed mix so TOP/BOTTOM diagnosis bands and why-good copy are deterministic.

    total_rev = 400000
    珍心 200000 (50%) / 超级会员全 80000 (20%) / 直播守护 60000 (15%)
    超级会员+ 30000 / 珍爱币 16000 (4%) / 超级提醒 8000 (2%)
    星光特权 4000 (1%) / 超级推荐 1600 (0.4%) / 其他 400 (0.1%)
    """
    return _app_row(
        amt="400000",
        zhenxin_member="200000",
        super_member_full="80000",
        live_guard="60000",
        super_member_plus="30000",
        zhenai_coin="16000",
        super_remind="8000",
        star_privilege="4000",
        super_recommend="1600",
        other="400",
    )


class HelperBoundaryTests(unittest.TestCase):
    def test_prev_date_crosses_month_and_year(self):
        self.assertEqual(prev_date("20260227"), "20260226")
        self.assertEqual(prev_date("20260301"), "20260228")
        self.assertEqual(prev_date("20260101"), "20251231")

    def test_parse_rows_rejects_non_dict_and_missing_rows(self):
        self.assertEqual(parse_rows({"rows": [{"amt": 1}, {"amt": 2}]}), [{"amt": 1}, {"amt": 2}])
        self.assertEqual(parse_rows({"rows": []}), [])
        self.assertEqual(parse_rows({}), [])
        self.assertEqual(parse_rows([{"amt": 1}]), [])
        self.assertEqual(parse_rows(None), [])
        self.assertEqual(parse_rows("error"), [])

    def test_color_kpi_higher_and_lower_is_better_bands(self):
        self.assertEqual(color_kpi(200000, 200000, 150000), "#16a34a")
        self.assertEqual(color_kpi(150000, 200000, 150000), "#d97706")
        self.assertEqual(color_kpi(149999, 200000, 150000), "#dc2626")

        # 退款率 / 珍心占比：越低越好
        self.assertEqual(color_kpi(2.0, 2, 4, False), "#16a34a")
        self.assertEqual(color_kpi(4.0, 2, 4, False), "#d97706")
        self.assertEqual(color_kpi(4.1, 2, 4, False), "#dc2626")
        self.assertEqual(color_kpi(79.0, 79, 80, False), "#16a34a")
        self.assertEqual(color_kpi(80.0, 79, 80, False), "#d97706")
        self.assertEqual(color_kpi(81.0, 79, 80, False), "#dc2626")


class NestedDodTests(unittest.TestCase):
    def test_missing_prev_rows_omit_dod_arrows(self):
        html = generate_html([_app_row()], [], [], "2026-02-27")
        self.assertIn("日环比", html)
        self.assertNotIn("▲", html)
        self.assertNotIn("▼", html)

    def test_dod_direction_colors_for_active_and_revenue(self):
        today = [_app_row(amt="200000", active_members="200000")]
        prev = [_app_row(amt="100000", active_members="100000")]
        html = generate_html(today, prev, [], "2026-02-27")
        self.assertIn("▲100.0%", html)
        self.assertIn("#16a34a", html)
        self.assertNotIn("▼", html)

        down = generate_html(
            [_app_row(amt="80000", active_members="80000")],
            [_app_row(amt="100000", active_members="100000")],
            [],
            "2026-02-27",
        )
        self.assertIn("▼20.0%", down)
        self.assertIn("#dc2626", down)
        self.assertNotIn("▲", down)

    def test_zero_previous_revenue_skips_revenue_dod(self):
        html = generate_html(
            [_app_row(amt="100000", active_members="200000")],
            [_app_row(amt="0", active_members="100000")],
            [],
            "2026-02-27",
        )
        # DAU still has a previous baseline → ▲100.0%
        self.assertIn("▲100.0%", html)
        # prv total_rev == 0 → nested dod returns blank (no 0-division, no fake ▼)
        self.assertNotIn("▼", html)


class ProductRankDiagnosisTests(unittest.TestCase):
    def test_top_why_good_and_bottom_diagnosis_bands(self):
        html = generate_html([_ranked_product_row()], [], [], "2026-02-27")

        self.assertIn("核心收入引擎，用户首选付费路径", html)
        self.assertIn("占比健康，用户主动购买意愿强", html)
        self.assertIn("绝对金额可观，值得专项运营", html)

        self.assertIn("⚠ 超级提醒 · 占比2.0%", html)
        self.assertIn("占比偏低，激活场景单一", html)
        self.assertIn("⚠ 超级推荐 · 占比0.4%", html)
        self.assertIn("⚠ 其他 · 占比0.1%", html)
        self.assertIn("占比极低，付费路径可能存在障碍或用户感知价值不足", html)
        self.assertIn("⚠ 珍爱币 · 占比4.0%", html)
        self.assertIn("有一定基础，但增长潜力未释放", html)

        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())

    def test_compare_ratio_significant_moderate_and_zero_denominator(self):
        significant = generate_html([_ranked_product_row()], [], [], "2026-02-27")
        self.assertIn("12.5x", significant)
        self.assertIn("差距显著", significant)
        self.assertNotIn("适度差距", significant)

        close = [_app_row(
            amt="54000",
            zhenxin_member="10000",
            super_member_full="9000",
            live_guard="8000",
            super_member_plus="7000",
            zhenai_coin="6000",
            super_remind="5000",
            star_privilege="4000",
            super_recommend="3000",
            other="2000",
        )]
        moderate = generate_html(close, [], [], "2026-02-27")
        self.assertIn("2.0x", moderate)
        self.assertIn("适度差距", moderate)
        self.assertNotIn("差距显著", moderate)

        # Three zero-amount SKUs occupy the tail so bot5[:3] includes a 0
        # (zip third pair → 直播守护 / 星光特权, 99x sentinel, no ZeroDivision).
        zero_bot = [_app_row(
            amt="394000",
            zhenxin_member="200000",
            super_member_full="80000",
            live_guard="60000",
            super_member_plus="30000",
            zhenai_coin="16000",
            super_remind="8000",
            star_privilege="0",
            super_recommend="0",
            other="0",
        )]
        html = generate_html(zero_bot, [], [], "2026-02-27")
        self.assertIn("99.0x", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())


class CausalBottleneckTests(unittest.TestCase):
    def test_retain_below_40_beats_pay_rate_as_bottleneck(self):
        html = generate_html(
            [_app_row(retain_1d="300", mems="1000", pay_num="200", active_members="10000")],
            [],
            [],
            "2026-02-27",
        )
        self.assertIn("最大瓶颈：次日留存率环节", html)
        self.assertIn("次日留存30.0%，低于40%目标", html)
        self.assertNotIn("最大瓶颈：付费率环节", html)

    def test_healthy_retain_falls_through_to_pay_rate_bottleneck(self):
        html = generate_html(
            [_app_row(retain_1d="500", mems="1000", pay_num="200", active_members="10000")],
            [],
            [],
            "2026-02-27",
        )
        self.assertIn("最大瓶颈：付费率环节", html)
        self.assertIn("付费率2.0%，低于5%目标", html)
        self.assertNotIn("最大瓶颈：次日留存率环节", html)


class TrendBarTests(unittest.TestCase):
    def test_empty_trends_show_placeholder(self):
        html = generate_html([_app_row()], [], [], "2026-02-27")
        self.assertIn("趋势数据加载中...", html)
        # Trend date gutter is unique to rendered bars; product tables do not use it.
        self.assertNotIn("width:50px", html)
        self.assertNotIn("%付</div>", html)

    def test_last_ten_window_today_highlight_and_zero_max_rev(self):
        days = [
            {"ftime": f"202602{d:02d}", "amt": str(d * 1000),
             "pay_num": "10", "active_members": "100",
             "refund_money": "0", "retain_1d": "0"}
            for d in range(16, 28)
        ]
        html = generate_html([_app_row()], [], days, "2026-02-27")
        self.assertIn("02-18", html)
        self.assertIn("02-27", html)
        self.assertNotIn("02-16", html)
        self.assertNotIn("02-17", html)
        self.assertIn("#0f172a", html)
        self.assertIn("#3b82f6", html)

        zeros = [
            {"ftime": f"2026030{d}", "amt": "0", "pay_num": "0",
             "active_members": "0", "refund_money": "0", "retain_1d": "0"}
            for d in range(1, 4)
        ]
        zero_html = generate_html([_app_row()], [], zeros, "2026-03-03")
        self.assertNotIn("趋势数据加载中", zero_html)
        self.assertNotIn("inf", zero_html.lower())
        self.assertNotIn("nan", zero_html.lower())
        self.assertIn("03-01", zero_html)
        self.assertIn("03-03", zero_html)


if __name__ == "__main__":
    unittest.main()
