# -*- coding: utf-8 -*-
"""Regression coverage for Jianxin DoD crash flags and Hongniang refund invert.

Open PRs #90/#93 cover diagnosis/improvement gates, not these KPI-card contracts:
- Jianxin nested dod raises 🚨 only when a metric falls by 10% or more.
- Hongniang dod('refund_rate', False) treats a refund-rate drop as improvement.
"""
import unittest

from generate_hongniang_full_report import (
    color_kpi as hn_color_kpi,
    generate_html as hn_generate_html,
)
from generate_jianxin_full_report import (
    color_kpi as jx_color_kpi,
    generate_html as jx_generate_html,
    parse_rows,
    prev_date,
)


def _jx_row(**overrides):
    row = {
        "dept_name": "建信二部",
        "channel_name": "主站",
        "name": "张三",
        "worker_id": "w1",
        "assign_1d_num": "100",
        "send_msg_1d_num": "80",
        "reply_1d_num": "8",
        "wechat_add_1d_num": "40",
        "transfer_1d_num": "10",
        "pay_1d_num": "2",
        "pay_1d_amt": "100000",
        "pay_1m_amt": "1000000",
        "worker_nums": "10",
        "new_worker_num": "1",
    }
    row.update(overrides)
    return row


def _hn_row(**overrides):
    row = {
        "dept_name": "深圳红娘一部",
        "staff_new": "10",
        "call_worker": "8",
        "on_vip": "100",
        "jm_n": "12",
        "jm_all": "15",
        "pay_1d_amt": "100000",
        "pay_1m_amt": "1000000",
        "link_time_count": "200",
        "deep_count": "80",
        "love_cnt_m": "5",
        "tousu_n": "0",
        "pay_1d_num": "3",
        "allot_yes": "20",
        "zhenai_back": "4000",
        "zhenaigd_back": "0",
        "zhenai_hz_back": "0",
        "zhenai_xfh_back": "0",
        "zhenai_md_back": "0",
    }
    row.update(overrides)
    return row


class JianxinHelperTests(unittest.TestCase):
    def test_prev_date_crosses_month_and_year(self):
        self.assertEqual(prev_date("20260227"), "20260226")
        self.assertEqual(prev_date("20260301"), "20260228")
        self.assertEqual(prev_date("20260101"), "20251231")

    def test_parse_rows_rejects_non_dict_and_missing_rows(self):
        self.assertEqual(parse_rows({"rows": [{"pay_1d_amt": 1}]}), [{"pay_1d_amt": 1}])
        self.assertEqual(parse_rows({}), [])
        self.assertEqual(parse_rows([{"pay_1d_amt": 1}]), [])
        self.assertEqual(parse_rows(None), [])
        self.assertEqual(parse_rows("error"), [])

    def test_color_kpi_higher_is_better_bands(self):
        self.assertEqual(jx_color_kpi(5000, 5000, 3000), "#16a34a")
        self.assertEqual(jx_color_kpi(3000, 5000, 3000), "#d97706")
        self.assertEqual(jx_color_kpi(2999, 5000, 3000), "#dc2626")


class JianxinDodAlertTests(unittest.TestCase):
    def test_missing_prev_rows_omit_dod_arrows_and_flags(self):
        html = jx_generate_html([_jx_row()], [], "2026-02-27")
        self.assertIn("建信团队体检", html)
        self.assertNotIn("▲", html)
        self.assertNotIn("▼", html)
        self.assertNotIn("🚨", html)

    def test_zero_previous_pay_skips_revenue_dod(self):
        html = jx_generate_html(
            [_jx_row(pay_1d_amt="100000")],
            [_jx_row(pay_1d_amt="0")],
            "2026-02-27",
        )
        # Other KPIs still have a previous baseline → ▲0.0%, but pay_amt prv==0 is blank.
        self.assertIn("▲0.0%", html)
        self.assertNotIn("▼", html)
        self.assertNotIn("🚨", html)
        self.assertNotRegex(html, r"(?i)(?<![A-Za-z])inf(?![A-Za-z])")
        self.assertNotRegex(html, r"(?i)(?<![A-Za-z])nan(?![A-Za-z])")

    def test_rise_is_green_without_alert(self):
        html = jx_generate_html(
            [_jx_row(pay_1d_amt="200000")],
            [_jx_row(pay_1d_amt="100000")],
            "2026-02-27",
        )
        self.assertIn("▲100.0%", html)
        self.assertIn("#16a34a", html)
        self.assertNotIn("▼", html)
        self.assertNotIn("🚨", html)

    def test_drop_just_above_threshold_has_no_alert(self):
        html = jx_generate_html(
            [_jx_row(pay_1d_amt="90100")],
            [_jx_row(pay_1d_amt="100000")],
            "2026-02-27",
        )
        self.assertIn("▼9.9%", html)
        self.assertIn("#dc2626", html)
        self.assertNotIn("🚨", html)

    def test_drop_of_exactly_ten_percent_raises_alert(self):
        html = jx_generate_html(
            [_jx_row(pay_1d_amt="90000")],
            [_jx_row(pay_1d_amt="100000")],
            "2026-02-27",
        )
        self.assertIn("▼10.0% 🚨", html)
        # Header 环比 + KPI 卡片各渲染一次 pay_amt DoD。
        self.assertEqual(html.count("🚨"), 2)

    def test_steeper_drop_keeps_pay_amt_alerts_only(self):
        html = jx_generate_html(
            [_jx_row(pay_1d_amt="80000")],
            [_jx_row(pay_1d_amt="100000")],
            "2026-02-27",
        )
        self.assertIn("▼20.0% 🚨", html)
        self.assertEqual(html.count("🚨"), 2)
        self.assertNotIn("▼20.0%</span>", html.replace("▼20.0% 🚨", ""))


class HongniangRefundInvertTests(unittest.TestCase):
    def test_color_kpi_lower_is_better_refund_bands(self):
        self.assertEqual(hn_color_kpi(5.0, 5, 10, False), "#16a34a")
        self.assertEqual(hn_color_kpi(10.0, 5, 10, False), "#d97706")
        self.assertEqual(hn_color_kpi(10.1, 5, 10, False), "#dc2626")

    def test_refund_rate_drop_is_green_improvement(self):
        # 4% vs 8% → ▼50.0% and invert paints it green (lower refund is better).
        html = hn_generate_html(
            [_hn_row(zhenai_back="4000")],
            [_hn_row(zhenai_back="8000")],
            [],
            "2026-02-27",
        )
        self.assertIn("▼50.0%", html)
        self.assertIn('color:#16a34a">▼50.0%</span>', html)
        self.assertNotIn('color:#dc2626">▼50.0%</span>', html)
        self.assertNotIn("🚨", html)

    def test_refund_rate_rise_is_red_regression(self):
        html = hn_generate_html(
            [_hn_row(zhenai_back="8000")],
            [_hn_row(zhenai_back="4000")],
            [],
            "2026-02-27",
        )
        self.assertIn("▲100.0%", html)
        self.assertIn('color:#dc2626">▲100.0%</span>', html)
        self.assertNotIn('color:#16a34a">▲100.0%</span>', html)
        self.assertNotIn("🚨", html)

    def test_zero_previous_refund_rate_skips_refund_dod(self):
        html = hn_generate_html(
            [_hn_row(zhenai_back="4000")],
            [_hn_row(zhenai_back="0")],
            [],
            "2026-02-27",
        )
        # prv refund_rate == 0 → nested dod returns blank (no fake ▲/▼ on 退费).
        self.assertIn("退费¥0.4万 </div>", html)
        self.assertNotRegex(html, r"(?i)(?<![A-Za-z])inf(?![A-Za-z])")
        self.assertNotRegex(html, r"(?i)(?<![A-Za-z])nan(?![A-Za-z])")


if __name__ == "__main__":
    unittest.main()
