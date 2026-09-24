# -*- coding: utf-8 -*-
"""红娘全局诊断与漏斗瓶颈的贴线合同。

见面安排率 0.8 / 1.0 / 1.2、退费率 5 / 10、深沟率 20
决定预警文案、退费专项和「最大瓶颈」杠杆公式。
这些比较此前没有被锁住。
"""
import unittest

from generate_hongniang_full_report import generate_html


def _row(**overrides):
    row = {
        "dept_name": "深圳红娘一部",
        "staff_new": "10",
        "call_worker": "10",
        "on_vip": "100",
        "jm_n": "10",
        "pay_1d_amt": "100000",
        "pay_1m_amt": "400000",
        "link_time_count": "100",
        "deep_count": "20",
        "love_cnt_m": "1",
        "tousu_n": "0",
        "pay_1d_num": "2",
        "zhenai_back": "0",
    }
    row.update(overrides)
    return row


def _html(**overrides):
    return generate_html([_row(**overrides)], [], [], "2026-02-27")


class HongniangMeetRateBandTests(unittest.TestCase):
    def test_jm_rate_exactly_0_8_is_caution_not_severe(self):
        # 8/10 == 0.80; severe copy needs < 0.8, healthy copy needs >= 1.0
        html = _html(jm_n="8")
        self.assertIn(">注意</span>\n<strong>见面安排率 0.80</strong>", html)
        self.assertIn("⚠ 未达1.0基准，需专项提升", html)
        self.assertNotIn("🚨 严重偏低，大量VIP资源未服务", html)
        self.assertNotIn("✅ 达标，继续保持", html)
        self.assertIn(
            'border:3px solid #d97706;font-size:11px;font-weight:600">见面8(率0.80)',
            html,
        )
        self.assertIn("见面安排率修复至1.0", html)

    def test_jm_rate_exactly_1_0_is_healthy_and_0_9_stays_short(self):
        healthy = _html(jm_n="10")
        self.assertIn(">良好</span>\n<strong>见面安排率 1.00</strong>", healthy)
        self.assertIn("✅ 达标，继续保持", healthy)
        self.assertNotIn("未达1.0基准", healthy)
        self.assertNotIn("见面安排率修复至1.0", healthy)

        short = _html(jm_n="9")
        self.assertIn(">注意</span>\n<strong>见面安排率 0.90</strong>", short)
        self.assertIn("⚠ 未达1.0基准，需专项提升", short)
        self.assertNotIn("✅ 达标，继续保持", short)
        self.assertIn("见面安排率修复至1.0", short)

    def test_jm_rate_0_7_is_severe_and_1_2_chip_turns_green(self):
        severe = _html(jm_n="7")
        self.assertIn(">预警</span>\n<strong>见面安排率 0.70</strong>", severe)
        self.assertIn("🚨 严重偏低，大量VIP资源未服务，立即启动专项盘点", severe)
        self.assertIn(
            'border:3px solid #dc2626;font-size:11px;font-weight:600">见面7(率0.70)',
            severe,
        )
        # gap = 0.3 is binary-exact: extra meetings = 3, uplift = 3 * 100000/7
        self.assertIn("预估增幅: +¥42,857/日", severe)

        green = _html(jm_n="12")
        self.assertIn(
            'border:3px solid #16a34a;font-size:11px;font-weight:600">见面12(率1.20)',
            green,
        )
        amber = _html(staff_new="100", jm_n="119")
        self.assertIn(
            'border:3px solid #d97706;font-size:11px;font-weight:600">见面119(率1.19)',
            amber,
        )


class HongniangRefundBandTests(unittest.TestCase):
    def test_refund_exactly_10_stays_channel_review_and_10_1_is_p0(self):
        # 10000/100000 == 10; trigger is >
        at_line = _html(zhenai_back="10000")
        self.assertIn(">P1</span>\n<strong>退费率 10.0%</strong>", at_line)
        self.assertIn("⚠ 偏高，分渠道追因，检查话术合规性", at_line)
        self.assertNotIn("🚨 超10%红线，立即启动退费专项", at_line)
        self.assertNotIn("✅ 退费控制良好", at_line)

        over = _html(zhenai_back="10100")
        self.assertIn(">P0</span>\n<strong>退费率 10.1%</strong>", over)
        self.assertIn("🚨 超10%红线，立即启动退费专项", over)
        self.assertNotIn("分渠道追因", over)
        self.assertNotIn("✅ 退费控制良好", over)

    def test_refund_exactly_5_stays_healthy_and_5_1_opens_p0_card(self):
        # diagnosis banner and the 4.5% control card both use >
        at_line = _html(zhenai_back="5000")
        self.assertIn(">正常</span>\n<strong>退费率 5.0%</strong>", at_line)
        self.assertIn("✅ 退费控制良好", at_line)
        self.assertNotIn("偏高，分渠道追因", at_line)
        self.assertNotIn("退费率管控至4.5%", at_line)

        over = _html(zhenai_back="5100")
        self.assertIn(">P1</span>\n<strong>退费率 5.1%</strong>", over)
        self.assertIn("⚠ 偏高，分渠道追因，检查话术合规性", over)
        self.assertNotIn("超10%红线", over)
        self.assertNotIn("✅ 退费控制良好", over)
        self.assertIn("退费率管控至4.5%", over)
        # save = 100000 * (5.1 - 4.5) / 100
        self.assertIn("预估增幅: +¥600/日", over)


class HongniangFunnelBottleneckTests(unittest.TestCase):
    def test_deep_rate_exactly_20_switches_bottleneck_and_leverage(self):
        # 20/100 == 20; deep-talk bottleneck needs < 20
        at_line = _html(deep_count="20", jm_n="10", staff_new="10")
        self.assertIn("最大瓶颈：见面安排率", at_line)
        self.assertNotIn("最大瓶颈：深度沟通", at_line)
        self.assertIn("见面安排率仅1.0", at_line)
        self.assertNotIn("深沟率仅", at_line)
        self.assertIn(
            'border:3px solid #d97706;font-size:11px;font-weight:600;background:#fffbeb">⚠ 深沟20(20.0%)',
            at_line,
        )
        # staff*0.1 = 1; revenue per meeting / 10000 = 1
        self.assertIn("见面安排率每+0.1，见面数+1→营收+¥1万/日", at_line)
        self.assertNotIn("深沟率每+1pp", at_line)

        below = _html(deep_count="19", jm_n="10", staff_new="10")
        self.assertIn("最大瓶颈：深度沟通", below)
        self.assertNotIn("最大瓶颈：见面安排率", below)
        self.assertIn("深沟率仅19.0%", below)
        self.assertIn(
            'border:3px solid #dc2626;font-size:11px;font-weight:600;background:#fef2f2">🔴 深沟19(19.0%)',
            below,
        )
        # link_time_count * 0.01 = 1; same ¥1万/日 unit revenue
        self.assertIn("深沟率每+1pp，见面数+1→营收+¥1万/日", below)
        self.assertNotIn("见面安排率每+0.1", below)


if __name__ == "__main__":
    unittest.main()
