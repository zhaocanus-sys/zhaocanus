# -*- coding: utf-8 -*-
"""Regression coverage for Hongniang refund-channel concentration gates.

Open PR #101 covers nested dod('refund_rate', False) invert.
This file locks the channel breakdown that decides which refund source
gets 🔴治理 / ⚠中等 / ✅正常 — a high-blast-radius compliance path.
"""
import re
import unittest

from generate_hongniang_full_report import generate_html


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


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
        "zhenai_back": "1000",
        "zhenaigd_back": "1000",
        "zhenai_hz_back": "1000",
        "zhenai_xfh_back": "1000",
        "zhenai_md_back": "1000",
    }
    row.update(overrides)
    return row


def _channel_row(html, name):
    for block in html.split("<tr>"):
        if name in block:
            return block
    raise AssertionError(f"channel row not found: {name}")


class HongniangRefundChannelGateTests(unittest.TestCase):
    def test_channel_over_forty_percent_is_priority_governance(self):
        # 8000 / 12000 = 66.7% → 🔴；其余各 1000 / 12000 ≈ 8.3% → ✅
        html = generate_html(
            [_hn_row(
                zhenai_back="8000",
                zhenaigd_back="1000",
                zhenai_hz_back="1000",
                zhenai_xfh_back="1000",
                zhenai_md_back="1000",
            )],
            [],
            [],
            "2026-02-27",
        )
        main = _channel_row(html, "珍爱主站")
        self.assertIn("66.7%", main)
        self.assertIn("🔴 重点治理渠道", main)
        self.assertIn("#dc2626", main)
        self.assertIn("✅ 正常", _channel_row(html, "珍爱广东"))
        self.assertNotIn("🔴 重点治理渠道", _channel_row(html, "珍爱广东"))
        self.assertIsNone(_INF_NAN.search(html))

    def test_channel_between_twenty_and_forty_is_medium_risk(self):
        # 3000 / 11000 ≈ 27.3% → ⚠；2000 / 11000 ≈ 18.2% → ✅
        html = generate_html(
            [_hn_row(
                zhenai_back="3000",
                zhenaigd_back="2000",
                zhenai_hz_back="2000",
                zhenai_xfh_back="2000",
                zhenai_md_back="2000",
            )],
            [],
            [],
            "2026-02-27",
        )
        main = _channel_row(html, "珍爱主站")
        self.assertIn("27.3%", main)
        self.assertIn("⚠ 中等风险", main)
        self.assertIn("#d97706", main)
        self.assertNotIn("🔴 重点治理渠道", main)
        self.assertIn("✅ 正常", _channel_row(html, "珍爱广东"))

    def test_even_split_and_zero_refund_stay_normal_and_finite(self):
        even = generate_html([_hn_row()], [], [], "2026-02-27")
        # 1000/5000 = 20.0%，阈值是 >20 / >40，等于 20 仍走正常。
        self.assertIn("20.0%", _channel_row(even, "珍爱主站"))
        self.assertIn("✅ 正常", _channel_row(even, "珍爱主站"))
        self.assertNotIn("🔴 重点治理渠道", even)
        self.assertNotIn("⚠ 中等风险", even)

        zero = generate_html(
            [_hn_row(
                zhenai_back="0",
                zhenaigd_back="0",
                zhenai_hz_back="0",
                zhenai_xfh_back="0",
                zhenai_md_back="0",
            )],
            [],
            [],
            "2026-02-27",
        )
        # total_refund==0 → 分母回退 1，pct=0，不得出现 inf/nan。
        self.assertIn("✅ 正常", _channel_row(zero, "珍爱主站"))
        self.assertIn("0.0%", _channel_row(zero, "珍爱主站"))
        self.assertIsNone(_INF_NAN.search(zero))


if __name__ == "__main__":
    unittest.main()
