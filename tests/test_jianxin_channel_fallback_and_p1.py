# -*- coding: utf-8 -*-
"""Regression coverage for Jianxin channel key fallbacks and P1 naming.

Open PR #70 covers channel grouping / pay ranking via assign/wechat keys.
Open PR #93 covers the global 「渠道浪费」 diagnosis banner.
This file locks the remaining production contract:
- trigger_1d_num / add_1d_num win over assign / wechat fallbacks
- missing channel_name → 未知渠道
- P1 improvement card names the zero-pay waste channel, or
  generic 「低效渠道」 when every channel has pay_n>0
"""
import unittest

from generate_jianxin_full_report import (
    MANAGER,
    build_channel_data,
    generate_html,
)


def _ch(**overrides):
    row = {
        "channel_name": "渠道A",
        "trigger_1d_num": 100,
        "assign_1d_num": 5,
        "add_1d_num": 40,
        "wechat_add_1d_num": 3,
        "transfer_1d_num": 8,
        "pay_1d_num": 1,
        "pay_1d_amt": 20000,
        "pay_1m_amt": 50000,
        "send_msg_1d_num": 80,
        "reply_1d_num": 8,
        "worker_nums": 4,
    }
    row.update(overrides)
    return row


def _html(rows, date_display="2026-02-27"):
    return generate_html(rows, [], date_display)


class JianxinChannelFallbackTests(unittest.TestCase):
    def test_trigger_and_add_primary_keys_win_over_fallbacks(self):
        channels = build_channel_data([
            _ch(trigger_1d_num=100, assign_1d_num=5, add_1d_num=40, wechat_add_1d_num=3),
        ])
        self.assertEqual(1, len(channels))
        self.assertEqual(100, channels[0]["trigger"])
        self.assertEqual(40, channels[0]["add"])

    def test_missing_trigger_and_add_fall_back_to_assign_and_wechat(self):
        row = _ch()
        del row["trigger_1d_num"]
        del row["add_1d_num"]
        row["assign_1d_num"] = 25
        row["wechat_add_1d_num"] = 17
        channels = build_channel_data([row])
        self.assertEqual(25, channels[0]["trigger"])
        self.assertEqual(17, channels[0]["add"])

    def test_mixed_keys_merge_and_missing_name_defaults(self):
        primary = _ch(
            channel_name="混渠",
            trigger_1d_num=100,
            assign_1d_num=5,
            add_1d_num=40,
            wechat_add_1d_num=3,
            pay_1d_amt=10,
        )
        fallback = _ch(
            channel_name="混渠",
            assign_1d_num=20,
            wechat_add_1d_num=7,
            pay_1d_amt=5,
        )
        del fallback["trigger_1d_num"]
        del fallback["add_1d_num"]
        unnamed = _ch()
        del unnamed["channel_name"]
        unnamed["pay_1d_amt"] = 1

        channels = build_channel_data([primary, fallback, unnamed])
        by_name = {c["channel_name"]: c for c in channels}
        self.assertEqual(120, by_name["混渠"]["trigger"])
        self.assertEqual(47, by_name["混渠"]["add"])
        self.assertIn("未知渠道", by_name)


class JianxinChannelP1NamingTests(unittest.TestCase):
    def test_zero_pay_channel_is_named_on_p1_and_waste_banner(self):
        html = _html([
            _ch(channel_name="高效投放", pay_1d_num=2, pay_1d_amt=80000, trigger_1d_num=30),
            _ch(channel_name="低付费残留", pay_1d_num=0, pay_1d_amt=10, trigger_1d_num=40),
            _ch(channel_name="试岗资源", pay_1d_num=0, pay_1d_amt=0, trigger_1d_num=90),
        ])
        # reversed zero-pay scan picks the lowest pay_amt channel
        self.assertIn("渠道浪费：试岗资源（触发90人，零付费）", html)
        self.assertIn("试岗资源触发量大但付费率极低", html)
        self.assertIn(f"【P1】{MANAGER}：优化或暂停低效渠道资源分配", html)
        self.assertNotIn("低付费残留触发量大但付费率极低", html)

    def test_all_paying_channels_use_generic_p1_name_and_skip_waste_banner(self):
        html = _html([
            _ch(channel_name="高效投放", pay_1d_num=3, pay_1d_amt=90000, trigger_1d_num=40),
            _ch(channel_name="试岗资源", pay_1d_num=1, pay_1d_amt=5000, trigger_1d_num=80),
        ])
        self.assertNotIn("渠道浪费：", html)
        self.assertIn("低效渠道触发量大但付费率极低", html)
        self.assertNotIn("试岗资源触发量大但付费率极低", html)
        self.assertIn("资源重分后", html)


if __name__ == "__main__":
    unittest.main()
