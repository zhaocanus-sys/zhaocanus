# -*- coding: utf-8 -*-
"""Exclusive 40% edge for Hongniang refund-channel governance.

Interior points (66.7% 重点治理, 27.3% 中等风险, 20.0% 正常) are already locked.
治理动作在 >40 才升级；等于 40 必须留在中等风险。
"""
import unittest

from generate_hongniang_full_report import generate_html


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
        if name in block and "万" in block:
            return block
    raise AssertionError(f"channel row not found: {name}")


class HongniangRefundChannelFortyEdgeTests(unittest.TestCase):
    def test_exactly_forty_percent_stays_medium_risk(self):
        # 4000 / 10000 = 40.0%。阈值是 >40，贴线仍是中等风险。
        html = generate_html(
            [_hn_row(
                zhenai_back="4000",
                zhenaigd_back="1500",
                zhenai_hz_back="1500",
                zhenai_xfh_back="1500",
                zhenai_md_back="1500",
            )],
            [],
            [],
            "2026-02-27",
        )
        main = _channel_row(html, "珍爱主站")
        self.assertIn("40.0%", main)
        self.assertIn("⚠ 中等风险", main)
        self.assertIn('color:#d97706">40.0%', main)
        self.assertNotIn("🔴 重点治理渠道", main)
        self.assertNotIn('color:#dc2626">40.0%', main)
        other = _channel_row(html, "珍爱广东")
        self.assertIn("15.0%", other)
        self.assertIn("✅ 正常", other)

    def test_just_over_forty_percent_is_priority_governance(self):
        # 401 / 1000 = 40.1%，首次进入重点治理。
        html = generate_html(
            [_hn_row(
                zhenai_back="401",
                zhenaigd_back="150",
                zhenai_hz_back="150",
                zhenai_xfh_back="150",
                zhenai_md_back="149",
            )],
            [],
            [],
            "2026-02-27",
        )
        main = _channel_row(html, "珍爱主站")
        self.assertIn("40.1%", main)
        self.assertIn("🔴 重点治理渠道", main)
        self.assertIn('color:#dc2626">40.1%', main)
        self.assertNotIn("⚠ 中等风险", main)
        self.assertIn("✅ 正常", _channel_row(html, "珍爱门店"))
        self.assertNotIn("🔴 重点治理渠道", _channel_row(html, "珍爱门店"))


if __name__ == "__main__":
    unittest.main()
