# -*- coding: utf-8 -*-
"""Regression coverage for generate_app_full_report (rewritten on main, previously untested)."""
import unittest

from generate_app_full_report import (
    agg_app,
    build_trend_data,
    color_kpi,
    generate_html,
    parse_rows,
    prev_date,
)


def _row(**overrides):
    base = {
        "amt": 1_000_000,
        "pay_num": 4_000,
        "active_members": 100_000,
        "refund_money": 30_000,
        "pay_num_new": 100,
        "retain_1d": 300,
        "retain_7d": 120,
        "order_cnt": 200,
        "order_pay": 150,
        "reg_num_m": 10,
        "pay_num_m": 80,
        "pay_amt_m": 9_000_000,
        "mems": 1_000,
        "zhenxin_member": 810_000,
        "pay_amt": 1_000_000,
        "super_member_full": 160_000,
        "live_guard": 60_000,
        "super_member_plus": 40_000,
        "zhenai_coin": 35_000,
        "super_remind": 35_000,
        "star_privilege": 20_000,
        "super_recommend": 5_000,
        "other": 0,
    }
    base.update(overrides)
    return base


class AggAndTrendTests(unittest.TestCase):
    def test_parse_rows_rejects_non_dict(self):
        self.assertEqual(parse_rows(None), [])
        self.assertEqual(parse_rows(["rows"]), [])
        self.assertEqual(parse_rows({"rows": [1]}), [1])

    def test_agg_uses_first_row_only_and_zero_denominators_stay_finite(self):
        first = _row(amt="12,345.6", pay_num=0, active_members=0, mems=0,
                     order_cnt=0, refund_money=0, zhenxin_member=0)
        second = _row(amt=9_999_999)
        agg = agg_app([first, second])
        self.assertEqual(agg["total_rev"], 12345.6)
        self.assertEqual(agg["pay_num"], 0)
        self.assertEqual(agg["arpu"], 0)
        self.assertEqual(agg["pay_rate"], 0)
        self.assertEqual(agg["refund_rate"], 0)
        self.assertEqual(agg["zhenxin_pct"], 0)
        self.assertEqual(agg["retain_rate_1d"], 0)
        self.assertEqual(agg["retain_rate_7d"], 0)
        self.assertEqual(agg["order_conv"], 0)
        self.assertEqual(agg_app([]), {})

    def test_rates_from_first_row(self):
        agg = agg_app([_row()])
        self.assertAlmostEqual(agg["pay_rate"], 4.0)
        self.assertAlmostEqual(agg["arpu"], 250.0)
        self.assertAlmostEqual(agg["refund_rate"], 3.0)
        self.assertAlmostEqual(agg["zhenxin_pct"], 81.0)
        self.assertAlmostEqual(agg["retain_rate_1d"], 30.0)
        self.assertAlmostEqual(agg["order_conv"], 75.0)

    def test_trend_groups_sorts_and_guards_zero_divisors(self):
        rows = [
            {"ftime": "202602271530", "amt": 100, "pay_num": 0, "active_members": 0,
             "refund_money": 1, "retain_1d": 2},
            {"ftime": "20260227", "amt": "50", "pay_num": 0, "active_members": 10,
             "refund_money": 0, "retain_1d": 0},
            {"ftime": "20260226", "amt": 80, "pay_num": 4, "active_members": 0,
             "refund_money": 0, "retain_1d": 1},
            {"ftime": "", "amt": 7, "pay_num": 1, "active_members": 2,
             "refund_money": 0, "retain_1d": 0},
        ]
        trend = build_trend_data(rows)
        self.assertEqual([t["dt"] for t in trend], ["--", "2026-02-26", "2026-02-27"])
        day = trend[-1]
        self.assertEqual(day["amt"], 150)
        self.assertEqual(day["arpu"], 0)
        self.assertEqual(day["pay_rate"], 0)
        self.assertEqual(trend[1]["arpu"], 20)
        self.assertEqual(trend[1]["pay_rate"], 0)

    def test_prev_date_crosses_month_and_year(self):
        self.assertEqual(prev_date("20260301"), "20260228")
        self.assertEqual(prev_date("20260101"), "20251231")


class ColorAndHtmlGateTests(unittest.TestCase):
    def test_color_kpi_inclusive_edges(self):
        self.assertEqual(color_kpi(200_000, 200_000, 150_000), "#16a34a")
        self.assertEqual(color_kpi(150_000, 200_000, 150_000), "#d97706")
        self.assertEqual(color_kpi(149_999, 200_000, 150_000), "#dc2626")
        self.assertEqual(color_kpi(2, 2, 4, False), "#16a34a")
        self.assertEqual(color_kpi(4, 2, 4, False), "#d97706")
        self.assertEqual(color_kpi(4.1, 2, 4, False), "#dc2626")
        self.assertEqual(color_kpi(79, 79, 80, False), "#16a34a")
        self.assertEqual(color_kpi(80, 79, 80, False), "#d97706")
        self.assertEqual(color_kpi(80.1, 79, 80, False), "#dc2626")

    def test_empty_payload_does_not_crash(self):
        html = generate_html([], [], [], "2026-02-27")
        self.assertIn("暂无数据", html)
        self.assertNotIn("珍心占比治理", html)

    def test_triggered_gates_estimates_order_and_deploy_date(self):
        html = generate_html([_row()], [_row(amt=0)], [], "2026-02-27")
        self.assertIn("⚠ 超80%红线", html)
        self.assertIn("P0", html)
        self.assertIn("🚨 超80%红线", html)
        self.assertIn("珍心占比治理（从81.0%→<80%）", html)
        self.assertIn("部署: 2026-02-28", html)
        self.assertIn("周期: 30天", html)
        self.assertIn("+¥50,000", html)
        self.assertIn("次日留存率提升至40%（当前30.0%）", html)
        self.assertIn("+¥30,000", html)
        self.assertIn("🚨 严重偏低", html)
        self.assertIn("付费率从4.0%提升至5%", html)
        self.assertIn("+¥250,000", html)
        self.assertIn("退款率控制至<2%（当前3.0%）", html)
        self.assertIn("+¥300", html)
        self.assertIn("⚠ 超2%红线", html)
        self.assertIn("ARPU提升策略", html)
        self.assertIn("+¥8,000", html)
        self.assertIn("流量质量优化", html)
        self.assertIn("+¥500,000", html)
        self.assertLess(html.index("流量质量优化"), html.index("付费率从4.0%"))
        self.assertLess(html.index("付费率从4.0%"), html.index("珍心占比治理"))
        self.assertLess(html.index("珍心占比治理"), html.index("次日留存率提升至40%"))
        self.assertLess(html.index("次日留存率提升至40%"), html.index("ARPU提升策略"))
        self.assertLess(html.index("ARPU提升策略"), html.index("退款率控制至"))
        self.assertIn("最大瓶颈：次日留存率", html)
        self.assertIn("日增营收¥50000元", html)
        self.assertIn("核心收入引擎", html)
        self.assertIn("占比健康，用户主动购买意愿强", html)
        self.assertIn("绝对金额可观，值得专项运营", html)
        self.assertIn("具备增长潜力", html)
        self.assertIn("有一定基础，但增长潜力未释放", html)
        self.assertIn("占比偏低，激活场景单一", html)
        self.assertIn("占比极低，付费路径可能存在障碍", html)
        self.assertIn("差距显著，珍心会员设计值得珍爱币借鉴", html)
        self.assertIn("适度差距，关注产品价值传递是否清晰", html)
        self.assertIn("超过80%红线，产品结构高风险", html)

    def test_exact_thresholds_stay_silent_and_healthy_copy(self):
        healthy = _row(
            amt=1_000_000,
            zhenxin_member=800_000,
            active_members=10_000,
            pay_num=500,
            mems=1_000,
            retain_1d=450,
            retain_7d=200,
            refund_money=20_000,
            super_member_full=50_000,
            live_guard=40_000,
            super_member_plus=0,
            zhenai_coin=0,
            super_remind=0,
            star_privilege=0,
            super_recommend=0,
            other=0,
        )
        html = generate_html([healthy], [], [], "2026-02-28")
        self.assertNotIn("⚠ 超80%红线", html)
        self.assertNotIn("🚨 超80%红线", html)
        self.assertIn("产品结构健康，珍心占比合理", html)
        self.assertIn("接近红线，提前布局产品多元化", html)
        self.assertNotIn("珍心占比治理", html)
        self.assertNotIn("次日留存率提升至40%", html)
        self.assertIn("留存良好", html)
        self.assertNotIn("付费率从", html)
        self.assertNotIn("退款率控制至", html)
        self.assertIn("退款控制良好", html)
        self.assertIn("ARPU良好", html)
        self.assertIn("部署: 2026-03-01", html)
        self.assertIn("最大瓶颈：付费率", html)
        self.assertIn("日增¥200000", html)
        self.assertIn("99.0x", html)
        self.assertIn("差距显著，珍心会员设计值得珍爱币借鉴", html)

    def test_diagnosis_band_edges(self):
        severe = generate_html([_row(retain_1d=349, mems=1_000, refund_money=41_000,
                                     zhenxin_member=801_000)], [], [], "2026-02-27")
        self.assertIn("严重偏低", severe)
        self.assertIn("超4%，退款规模大", severe)

        mid = generate_html([_row(retain_1d=350, mems=1_000, refund_money=40_000,
                                  zhenxin_member=800_000, amt=1_000_000)], [], [], "2026-02-27")
        self.assertIn("偏低，需优化首日Hook", mid)
        self.assertNotIn("严重偏低", mid)
        self.assertIn("超2%红线，需分产品追因", mid)
        self.assertNotIn("超4%", mid)

        good_retain = generate_html(
            [_row(retain_1d=450, mems=1_000, pay_num=400, active_members=10_000,
                  amt=8_000, zhenxin_member=1_000)],
            [], [], "2026-02-27")
        self.assertIn("留存良好", good_retain)
        self.assertIn("ARPU有提升空间", good_retain)
        self.assertNotIn("ARPU良好", good_retain)

    def test_dod_direction_flat_and_zero_baseline(self):
        up = generate_html([_row(amt=110)], [_row(amt=100)], [], "2026-02-27")
        self.assertIn("▲10.0%", up)
        self.assertIn("#16a34a", up)

        flat = generate_html([_row()], [_row()], [], "2026-02-27")
        self.assertIn("▼0.0%", flat)

        zero_base = generate_html(
            [_row(active_members=100, pay_num=4)],
            [_row(active_members=0)], [], "2026-02-27")
        dau_slice = zero_base.split("DAU", 1)[1].split("次日留存", 1)[0]
        self.assertNotIn("▲", dau_slice)
        self.assertNotIn("▼", dau_slice)
        self.assertIn("日环比", dau_slice)

    def test_trend_window_highlights_report_day_only(self):
        trend_rows = []
        for day in range(1, 13):
            trend_rows.append({
                "ftime": f"202602{day:02d}",
                "amt": day * 1000,
                "pay_num": 10,
                "active_members": 100,
                "refund_money": 0,
                "retain_1d": 1,
            })
        html = generate_html([_row()], [], trend_rows, "2026-02-12")
        self.assertNotIn(">02-01<", html)
        self.assertNotIn(">02-02<", html)
        self.assertIn(">02-03<", html)
        self.assertIn(">02-12<", html)
        self.assertEqual(html.count("background:#0f172a"), 1)
        self.assertEqual(html.count("background:#3b82f6"), 9)


if __name__ == "__main__":
    unittest.main()
