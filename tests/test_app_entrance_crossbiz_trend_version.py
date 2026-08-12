# -*- coding: utf-8 -*-
"""Regression coverage for APP entrance / cross-biz / trend bars / version HTML."""
import math
import unittest

from app_report_html import (
    cross_biz_html,
    entrance_analysis_html,
    trend_bars_html,
    version_html,
)


def _orders(**overrides):
    base = {
        "total_amt": 100000,
        "by_entrance1": [
            ("直播", {"cnt": 200, "pay": 100, "amt": 60000}),
            ("消息", {"cnt": 100, "pay": 40, "amt": 30000}),
            ("空入口", {"cnt": 0, "pay": 0, "amt": 0}),
        ],
        "by_entrance2": [
            (f"二级入口{i}", {"cnt": 10 + i, "pay": 5, "amt": 1000 * (20 - i)})
            for i in range(15)
        ],
        "by_prodname": [
            ("珍心会员-¥98", {"cnt": 80, "pay": 60, "amt": 5880}),
            ("超级会员-¥198", {"cnt": 20, "pay": 15, "amt": 2970}),
        ],
        "by_version": [
            ("8.2.1", {"cnt": 120, "pay": 80, "amt": 70000}),
            ("8.1.0", {"cnt": 50, "pay": 30, "amt": 20000}),
            ("7.9.0", {"cnt": 30, "pay": 10, "amt": 10000}),
        ],
    }
    base.update(overrides)
    return base


def _cross_kpi(**overrides):
    base = {
        "leads_online": 200,
        "leads_offline": 100,
        "allot": 150,
        "laoqu": 40,
        "link_1d": 1200,
        "callout_1d": 800,
    }
    base.update(overrides)
    return base


class EntranceAnalysisHtmlTests(unittest.TestCase):
    def test_entrance_conversion_share_and_pricing_insight(self):
        html = entrance_analysis_html(_orders())

        # 直播 100/200 = 50%; 消息 40/100 = 40%; 营收占比 60%/30%
        self.assertIn("直播", html)
        self.assertIn("50.0%", html)
        self.assertIn("消息", html)
        self.assertIn("40.0%", html)
        self.assertIn("60.0%", html)
        self.assertIn("30.0%", html)

        # 零订单入口保持有限零成功率
        self.assertIn("空入口", html)
        self.assertIn("0.0%", html)

        # 价格档位洞见：最畅销档位
        self.assertIn("定价洞见", html)
        self.assertIn("珍心会员-¥98", html)
        self.assertIn("价格锚点效应", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())

    def test_entrance2_top12_truncation_and_zero_total_amt_safe(self):
        html = entrance_analysis_html(_orders())

        self.assertIn("二级入口 TOP12", html)
        # amt 降序：二级入口0 最大，二级入口14 最小；仅 TOP12
        self.assertIn("二级入口0", html)
        self.assertIn("二级入口11", html)
        self.assertNotIn("二级入口12", html)
        self.assertNotIn("二级入口14", html)

        zero_amt = entrance_analysis_html(
            _orders(
                total_amt=0,
                by_entrance1=[("未知", {"cnt": 0, "pay": 0, "amt": 0})],
                by_entrance2=[],
                by_prodname=[],
            )
        )
        self.assertIn("入口场景转化分析", zero_amt)
        self.assertIn("0.0%", zero_amt)
        self.assertNotIn("定价洞见", zero_amt)
        self.assertNotIn("inf", zero_amt.lower())
        self.assertNotIn("nan", zero_amt.lower())


class CrossBizHtmlTests(unittest.TestCase):
    def test_cross_biz_totals_and_revenue_estimates(self):
        html = cross_biz_html(_cross_kpi())

        self.assertIn("跨业务线协同", html)
        self.assertIn("线上leads", html)
        self.assertIn("200", html)
        self.assertIn("线下leads", html)
        self.assertIn("100", html)
        # 线上+线下 = 300
        self.assertIn("300", html)
        self.assertIn("已分配150", html)

        # 线下: 100 * 0.3 * 8000 = 240,000
        self.assertIn("潜在线下营收¥240,000/日", html)
        # 线上: 200 * 0.1 * 3000 = 60,000
        self.assertIn("潜在在线营收¥60,000/日", html)
        self.assertIn("流量水库", html)
        self.assertNotIn("inf", html.lower())

    def test_cross_biz_zero_leads_keeps_finite_zero_estimates(self):
        html = cross_biz_html(
            _cross_kpi(
                leads_online=0,
                leads_offline=0,
                allot=0,
                laoqu=0,
                link_1d=0,
                callout_1d=0,
            )
        )

        self.assertIn("0", html)
        self.assertIn("潜在线下营收¥0/日", html)
        self.assertIn("潜在在线营收¥0/日", html)
        self.assertNotIn("inf", html.lower())
        self.assertNotIn("nan", html.lower())
        self.assertTrue(math.isfinite(0.0))


class TrendBarsHtmlTests(unittest.TestCase):
    def test_trend_bars_highlight_today_and_show_rates(self):
        trends = [
            {
                "dt": f"2026-08-{d:02d}",
                "amt": 10000 * d,
                "pay_rate": float(d),
                "order_conv": 50.0 + d,
            }
            for d in range(1, 11)
        ]
        html = trend_bars_html(trends, "2026-08-10")

        self.assertIn("10日营收趋势", html)
        self.assertIn("08-10", html)
        self.assertIn("¥10.0万", html)  # amt=100000
        self.assertIn("10.0%付", html)
        self.assertIn("60%成", html)
        # 今日条用深色背景标记
        self.assertIn("#0f172a", html)
        self.assertNotIn("inf", html.lower())

    def test_trend_bars_empty_and_keeps_last_10_only(self):
        self.assertEqual(trend_bars_html([], "2026-08-10"), "")
        self.assertEqual(trend_bars_html(None, "2026-08-10"), "")

        trends = [
            {
                "dt": f"2026-07-{d:02d}",
                "amt": 1000,
                "pay_rate": 1.0,
                "order_conv": 50.0,
            }
            for d in range(1, 13)
        ]
        html = trend_bars_html(trends, "2026-07-12")

        # 仅保留最后 10 天：07-03..07-12，不含 07-01/07-02
        self.assertIn("07-03", html)
        self.assertIn("07-12", html)
        self.assertNotIn("07-01", html)
        self.assertNotIn("07-02", html)

        # max_rev=0 时不除零
        zero_rev = trend_bars_html(
            [{"dt": "2026-08-01", "amt": 0, "pay_rate": 0, "order_conv": 0}],
            "2026-08-01",
        )
        self.assertIn("¥0.0万", zero_rev)
        self.assertIn("0.0%付", zero_rev)
        self.assertNotIn("inf", zero_rev.lower())


class VersionHtmlTests(unittest.TestCase):
    def test_version_top_rows_and_share(self):
        html = version_html(_orders())

        self.assertIn("APP版本分布", html)
        self.assertIn("v8.2.1", html)
        self.assertIn("v8.1.0", html)
        self.assertIn("v7.9.0", html)
        # 70000/100000 = 70%
        self.assertIn("70.0%", html)
        self.assertIn("20.0%", html)
        self.assertIn("10.0%", html)
        self.assertNotIn("inf", html.lower())

    def test_version_empty_and_top10_truncation(self):
        self.assertEqual(version_html(_orders(by_version=[])), "")

        many = [
            (f"9.0.{i}", {"cnt": i + 1, "pay": i, "amt": (20 - i) * 1000})
            for i in range(15)
        ]
        html = version_html(_orders(by_version=many, total_amt=sum(v["amt"] for _, v in many)))

        self.assertIn("v9.0.0", html)
        self.assertIn("v9.0.9", html)
        self.assertNotIn("v9.0.10", html)
        self.assertNotIn("v9.0.14", html)

        zero_total = version_html(
            _orders(
                total_amt=0,
                by_version=[("1.0.0", {"cnt": 0, "pay": 0, "amt": 0})],
            )
        )
        self.assertIn("v1.0.0", zero_total)
        self.assertIn("0.0%", zero_total)
        self.assertNotIn("inf", zero_total.lower())
        self.assertNotIn("nan", zero_total.lower())


if __name__ == "__main__":
    unittest.main()
