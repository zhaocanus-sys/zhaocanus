# -*- coding: utf-8 -*-
"""建信渠道字段优先级与零付费渠道点名。

现有聚合测试只在 trigger/add 字段缺失时，把 assign / wechat 当成触发和添加。
一旦日报同时带上专属字段，或专属字段显式为 0，错误的回退会把渠道浪费算到别的池子上。
浪费横幅从营收低到高扫描，必须点名付费人数为 0 里金额最低的渠道，
不能因为旁边有一个更低营收但已经有付费的渠道就改口。
"""
import unittest

import generate_jianxin_full_report as report


def _channel(**overrides):
    row = {
        "channel_name": "未命名",
        "dept_name": "建信一部",
        "worker_nums": 1,
        "assign_1d_num": 1,
        "send_msg_1d_num": 1,
        "reply_1d_num": 1,
        "wechat_add_1d_num": 1,
        "transfer_1d_num": 1,
        "pay_1d_num": 1,
        "pay_1d_amt": 100,
        "pay_1m_amt": 0,
    }
    row.update(overrides)
    return row


class JianxinChannelFieldPrecedenceTests(unittest.TestCase):
    def test_dedicated_trigger_and_add_override_fallback_including_explicit_zero(self):
        channels = {
            c["channel_name"]: c
            for c in report.build_channel_data([
                _channel(
                    channel_name="专属字段",
                    trigger_1d_num="7",
                    assign_1d_num="100",
                    add_1d_num="4",
                    wechat_add_1d_num="90",
                    pay_1d_amt=1000,
                ),
                _channel(
                    channel_name="显式零",
                    trigger_1d_num=0,
                    assign_1d_num=80,
                    add_1d_num="0",
                    wechat_add_1d_num=40,
                    pay_1d_num=0,
                    pay_1d_amt=0,
                ),
                _channel(
                    channel_name="空字符串",
                    trigger_1d_num="",
                    assign_1d_num=9,
                    add_1d_num="",
                    wechat_add_1d_num=6,
                    pay_1d_amt=20,
                ),
                _channel(
                    channel_name="缺字段回退",
                    assign_1d_num=11,
                    wechat_add_1d_num=13,
                    pay_1d_amt=50,
                ),
                _channel(
                    channel_name="同行相加",
                    trigger_1d_num=3,
                    assign_1d_num=100,
                    add_1d_num=2,
                    wechat_add_1d_num=100,
                    pay_1d_amt=10,
                    pay_1d_num=0,
                ),
                _channel(
                    channel_name="同行相加",
                    assign_1d_num=2,
                    wechat_add_1d_num=5,
                    pay_1d_amt=10,
                    pay_1d_num=0,
                ),
            ])
        }

        self.assertEqual(channels["专属字段"]["trigger"], 7)
        self.assertEqual(channels["专属字段"]["add"], 4)
        self.assertEqual(channels["显式零"]["trigger"], 0)
        self.assertEqual(channels["显式零"]["add"], 0)
        self.assertEqual(channels["空字符串"]["trigger"], 0)
        self.assertEqual(channels["空字符串"]["add"], 0)
        self.assertEqual(channels["缺字段回退"]["trigger"], 11)
        self.assertEqual(channels["缺字段回退"]["add"], 13)
        self.assertEqual(channels["同行相加"]["trigger"], 5)
        self.assertEqual(channels["同行相加"]["add"], 7)
        self.assertEqual(channels["同行相加"]["pay_amt"], 20)

    def test_waste_banner_names_lowest_zero_pay_channel(self):
        html = report.generate_html([
            _channel(channel_name="高额零付费", pay_1d_amt=80000, pay_1d_num=0,
                     trigger_1d_num=20, assign_1d_num=999),
            _channel(channel_name="低额有付费", pay_1d_amt=1000, pay_1d_num=1,
                     trigger_1d_num=5),
            _channel(channel_name="垫底零付费", pay_1d_amt=500, pay_1d_num=0,
                     trigger_1d_num=9, assign_1d_num=999),
        ], [], "2026-02-27")

        self.assertIn("渠道浪费：垫底零付费（触发9人，零付费）", html)
        self.assertNotIn("渠道浪费：高额零付费", html)
        self.assertNotIn("渠道浪费：低额有付费", html)
        self.assertIn("垫底零付费触发量大但付费率极低", html)

    def test_waste_banner_skips_lower_revenue_channel_that_already_paid(self):
        html = report.generate_html([
            _channel(channel_name="高额零付费", pay_1d_amt=50000, pay_1d_num=0,
                     trigger_1d_num=30, assign_1d_num=1),
            _channel(channel_name="垫底有付费", pay_1d_amt=100, pay_1d_num=2,
                     trigger_1d_num=4),
        ], [], "2026-02-27")

        self.assertIn("渠道浪费：高额零付费（触发30人，零付费）", html)
        self.assertNotIn("渠道浪费：垫底有付费", html)
        self.assertIn("高额零付费触发量大但付费率极低", html)
        # 重分目的地按付费金额最高的渠道，而不是营收垫底但已有付费的渠道。
        self.assertIn("资源重分到高额零付费", html)


if __name__ == "__main__":
    unittest.main()
