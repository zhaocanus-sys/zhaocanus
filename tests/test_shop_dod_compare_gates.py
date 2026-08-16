# -*- coding: utf-8 -*-
"""Regression coverage for shop KPI DoD, compare sentinels, and diagnosis bands.

Open PR #89 covers lead-speed / sale_rev fallback and improvement cards.
This file locks the remaining high-risk shop HTML contracts:
- nested dod omits arrows when prev is missing or the previous value is 0
- higher-is-better DoD paints rises green and drops red (no 🚨 crash flag)
- why_shop_good bands vs fallback copy
- TOP vs BOTTOM 99x zero-denominator + refund invert
- global diagnosis / bottleneck selectors that drive daily management action
"""
import re
import unittest

from generate_shop_full_report import (
    color_kpi,
    generate_html,
    parse_rows,
    prev_date,
)


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


def _shop_row(**overrides):
    row = {
        "dept_name": "深圳门店A",
        "level2": "深圳",
        "dept_worker_name": "店长A",
        "area_worker_name": "区长A",
        "total_realpay": "20000",
        "sale_realpay": "15000",
        "deptsale_realpay": "15000",
        "invite_realpay": "3000",
        "hn_realpay": "2000",
        "total_pay_num": "4",
        "sale_pay_num_all": "3",
        "invite_pay_num": "1",
        "deptsale_shop_num": "4",
        "sg_num": "10",
        "link_num": "20",
        "call_times": "50",
        "zaigang_rs": "2",
        "refund_money_d": "200",
        "complain_400_num_day": "0",
        "leads_xyzout_3day": "10",
        "leads_3day_allot_0day": "9",
        "leads_xyzout_1day": "5",
        "leads_1day_allot_0day": "5",
        "total_realpay_m": "80000",
        "deptsale_realpay_m": "60000",
        "worker_num_call": "2",
    }
    row.update(overrides)
    return row


class ShopHelperTests(unittest.TestCase):
    def test_prev_date_crosses_month_and_year(self):
        self.assertEqual(prev_date("20260227"), "20260226")
        self.assertEqual(prev_date("20260301"), "20260228")
        self.assertEqual(prev_date("20260101"), "20251231")

    def test_parse_rows_rejects_non_dict_and_missing_rows(self):
        self.assertEqual(parse_rows({"rows": [{"sg_num": 1}]}), [{"sg_num": 1}])
        self.assertEqual(parse_rows({}), [])
        self.assertEqual(parse_rows([{"sg_num": 1}]), [])
        self.assertEqual(parse_rows(None), [])
        self.assertEqual(parse_rows("error"), [])

    def test_color_kpi_higher_and_lower_bands_include_thresholds(self):
        self.assertEqual(color_kpi(35, 35, 30), "#16a34a")
        self.assertEqual(color_kpi(30, 35, 30), "#d97706")
        self.assertEqual(color_kpi(29.9, 35, 30), "#dc2626")
        self.assertEqual(color_kpi(4, 4, 7, False), "#16a34a")
        self.assertEqual(color_kpi(7, 4, 7, False), "#d97706")
        self.assertEqual(color_kpi(7.1, 4, 7, False), "#dc2626")


class ShopDodTests(unittest.TestCase):
    def test_missing_prev_rows_omit_dod_arrows(self):
        html = generate_html([_shop_row()], [], "2026-02-27")
        self.assertIn("门店销售全量业务体检报告", html)
        self.assertNotIn("▲", html)
        self.assertNotIn("▼", html)
        self.assertIsNone(_INF_NAN.search(html))

    def test_zero_previous_revenue_skips_revenue_dod(self):
        html = generate_html(
            [_shop_row(total_realpay="20000", sg_num="10", deptsale_shop_num="4")],
            [_shop_row(total_realpay="0", sg_num="10", deptsale_shop_num="4")],
            "2026-02-27",
        )
        # prv total_rev==0 → nested dod returns blank (no fake ▲/▼ on 日营收).
        self.assertIn("月累¥8万 </div>", html)
        self.assertNotIn("▲", html)
        # 持平指标走 chg>0 为假 → ▼0.0%（红色），不是 ▲0.0%。
        self.assertIn('color:#dc2626">▼0.0%</span>', html)
        self.assertIsNone(_INF_NAN.search(html))

    def test_flat_dod_is_red_down_arrow(self):
        html = generate_html([_shop_row()], [_shop_row()], "2026-02-27")
        self.assertIn('color:#dc2626">▼0.0%</span>', html)
        self.assertNotIn("▲", html)

    def test_sign_rate_rise_is_green(self):
        # 8/20=40% vs 4/20=20% → ▲100.0%；营收同步上升避免持平 ▼0.0% 干扰。
        html = generate_html(
            [_shop_row(
                sg_num="20", deptsale_shop_num="8", link_num="40",
                total_realpay="30000",
            )],
            [_shop_row(
                sg_num="20", deptsale_shop_num="4", link_num="80",
                total_realpay="20000",
            )],
            "2026-02-27",
        )
        self.assertIn('color:#16a34a">▲100.0%</span>', html)
        self.assertIn('color:#16a34a">▲50.0%</span>', html)  # 营收 3万 vs 2万
        self.assertNotIn('color:#dc2626">▲', html)

    def test_sign_rate_drop_is_red(self):
        # 4/20=20% vs 8/20=40% → ▼50.0%
        html = generate_html(
            [_shop_row(
                sg_num="20", deptsale_shop_num="4", link_num="80",
                total_realpay="20000",
            )],
            [_shop_row(
                sg_num="20", deptsale_shop_num="8", link_num="40",
                total_realpay="30000",
            )],
            "2026-02-27",
        )
        self.assertIn('color:#dc2626">▼50.0%</span>', html)
        self.assertNotIn('color:#16a34a">▼50.0%</span>', html)
        # 门店 nested dod 本身不带 🚨；诊断区的 🚨 来自签单率色带，不在此断言。


class ShopWhyGoodAndCompareTests(unittest.TestCase):
    def test_why_shop_good_emits_all_excellent_bands(self):
        html = generate_html(
            [_shop_row(
                deptsale_shop_num="8",
                sg_num="20",
                link_num="40",
                total_realpay="40000",
                zaigang_rs="2",
                complain_400_num_day="0",
            )],
            [],
            "2026-02-27",
        )
        self.assertIn("签单率40%达优秀线", html)
        self.assertIn("接通→到店转化效率高", html)
        self.assertIn("人均产值突出", html)
        self.assertIn("零投诉高口碑", html)
        self.assertNotIn("综合表现稳健", html)

    def test_why_shop_good_falls_back_when_no_band_hits(self):
        html = generate_html(
            [_shop_row(
                deptsale_shop_num="2",
                sg_num="20",
                link_num="80",
                total_realpay="2000",
                zaigang_rs="2",
                complain_400_num_day="1",
            )],
            [],
            "2026-02-27",
        )
        self.assertIn("综合表现稳健", html)
        self.assertNotIn("达优秀线", html)
        self.assertNotIn("接通→到店转化效率高", html)
        self.assertNotIn("人均产值突出", html)
        self.assertNotIn("零投诉高口碑", html)

    def test_compare_uses_99x_sentinel_and_refund_invert(self):
        strong = [
            _shop_row(
                dept_name=f"标杆{i}",
                total_realpay="50000",
                deptsale_shop_num="8",
                sg_num="20",
                link_num="40",
                zaigang_rs="4",
                refund_money_d="100",
                complain_400_num_day="0",
            )
            for i in range(5)
        ]
        weak = [
            _shop_row(
                dept_name=f"薄弱{i}",
                total_realpay="1000",
                deptsale_shop_num="0",
                sg_num="0",
                link_num="10",
                zaigang_rs="2",
                refund_money_d="800",
                complain_400_num_day="3",
            )
            for i in range(5)
        ]
        html = generate_html(strong + weak, [], "2026-02-27")
        self.assertIn("99.0x", html)
        self.assertIn("差距显著，TOP门店经验具备高复制价值", html)
        # 退费率 TOP≪BOTTOM → ratio≤0.7 走低优绿色。
        self.assertIn("退费率", html)
        refund_row = [line for line in html.split("<tr>") if "退费率" in line][0]
        self.assertIn("#16a34a", refund_row)


class ShopDiagnosisBandTests(unittest.TestCase):
    def test_sign_rate_bands_and_invite_bottleneck(self):
        # 2/10=20% → 🚨签单；10/80=12.5% → 🚨邀约 + 邀约瓶颈
        html = generate_html(
            [_shop_row(
                deptsale_shop_num="2",
                sg_num="10",
                link_num="80",
                refund_money_d="200",
            )],
            [],
            "2026-02-27",
        )
        self.assertIn("🚨 低于25%，现场接待严重失效", html)
        self.assertIn("🚨 严重偏低，邀约话术或邀约时机需根本性重建", html)
        self.assertIn("最大瓶颈：邀约→到店转化", html)
        self.assertNotIn("最大瓶颈：到店→签单转化", html)

    def test_healthy_sign_uses_sign_bottleneck_and_star_band(self):
        # 8/20=40% ⭐；invite 20/40=50% ≥30 → 文案仍走「到店→签单」分支
        html = generate_html(
            [_shop_row(
                deptsale_shop_num="8",
                sg_num="20",
                link_num="40",
                refund_money_d="200",
                leads_xyzout_1day="10",
                leads_1day_allot_0day="9",
            )],
            [],
            "2026-02-27",
        )
        self.assertIn("⭐ 签单率优秀≥35%", html)
        self.assertIn("✅ 邀约转化达标", html)
        self.assertIn("✅ 退费控制良好", html)
        self.assertIn("线索分配及时性良好", html)
        self.assertIn("最大瓶颈：到店→签单转化", html)

    def test_mid_bands_warn_without_crash_copy(self):
        # 7/25=28% ⚠；25/100=25% ⚠；1200/20000=6% ⚠；3/10=30% ⚠
        html = generate_html(
            [_shop_row(
                deptsale_shop_num="7",
                sg_num="25",
                link_num="100",
                total_realpay="20000",
                refund_money_d="1200",
                leads_xyzout_1day="10",
                leads_1day_allot_0day="3",
            )],
            [],
            "2026-02-27",
        )
        self.assertIn("⚠ 低于30%合格线，需强化现场签单能力", html)
        self.assertIn("⚠ 低于30%基准，邀约话术需优化", html)
        self.assertIn("⚠ 超4%红线，分门店追因", html)
        self.assertIn("⚠ 未达80%，当日线索流失", html)
        self.assertNotIn("🚨 低于25%", html)
        self.assertNotIn("🚨 超8%", html)

    def test_empty_payload_stays_finite(self):
        html = generate_html([], [], "2026-02-27")
        self.assertIn("门店销售全量业务体检报告", html)
        self.assertIn("0家门店", html)
        self.assertIsNone(_INF_NAN.search(html))


if __name__ == "__main__":
    unittest.main()
