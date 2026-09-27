# -*- coding: utf-8 -*-
"""建信报表着色门槛贴线。

既有用例锁了差异倍数的文案（4.0x / 200.0x）和渠道 P1 命名，
没有锁颜色开关。颜色是管理者扫表时的动作信号：

- TOP/BOTTOM 差异倍数：原始比值 > 2 才变红；等于 2 以及四舍五入后
  仍显示 2.0x 但原始值 ≤ 2 必须保持琥珀色。
- 部门回复率：< 5% 红色，≥ 5% 绿色。零发信回退为 0%，仍走红色。
- 渠道付费人数：pay_n == 0 人数红、金额加粗红；pay_n == 1 人数绿、
  金额不加粗。
"""
import re
import unittest

from generate_jianxin_full_report import generate_html


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


def _worker(**overrides):
    row = {
        "worker_id": "w-default",
        "name": "默认员工",
        "dept_name": "建信二部",
        "channel_name": "自然流量",
        "transfer_1d_num": 5,
        "pay_1d_amt": 10000,
        "pay_1d_num": 1,
        "wechat_add_1d_num": 10,
        "reply_1d_num": 10,
        "send_msg_1d_num": 100,
        "assign_1d_num": 8,
        "pay_1m_amt": 20000,
        "worker_nums": 1,
    }
    row.update(overrides)
    return row


def _roster(top_pay, bot_pay, top_transfer=5, bot_transfer=5):
    rows = []
    for i in range(5):
        rows.append(_worker(
            worker_id=f"top-{i}",
            name=f"标杆{i}",
            pay_1d_amt=top_pay,
            transfer_1d_num=top_transfer,
        ))
    for i in range(5):
        rows.append(_worker(
            worker_id=f"bot-{i}",
            name=f"尾部{i}",
            dept_name="建信六部",
            pay_1d_amt=bot_pay,
            transfer_1d_num=bot_transfer,
        ))
    return rows


def _dept(**overrides):
    row = {
        "dept_name": "建信二部",
        "worker_nums": 4,
        "assign_1d_num": 20,
        "send_msg_1d_num": 100,
        "reply_1d_num": 5,
        "wechat_add_1d_num": 12,
        "transfer_1d_num": 3,
        "pay_1d_amt": 8000,
        "pay_1d_num": 1,
        "pay_1m_amt": 20000,
        "worker_id": "dept-only",
        "name": "部门样本",
    }
    row.update(overrides)
    return row


def _channel(**overrides):
    row = {
        "channel_name": "渠道A",
        "dept_name": "建信二部",
        "worker_id": "ch-worker",
        "name": "渠道样本",
        "trigger_1d_num": 40,
        "assign_1d_num": 10,
        "add_1d_num": 8,
        "wechat_add_1d_num": 8,
        "transfer_1d_num": 2,
        "pay_1d_num": 1,
        "pay_1d_amt": 15000,
        "pay_1m_amt": 30000,
        "send_msg_1d_num": 40,
        "reply_1d_num": 4,
        "worker_nums": 2,
    }
    row.update(overrides)
    return row


def _html(rows):
    return generate_html(rows, [], "2026-02-27")


class JianxinRatioColorTests(unittest.TestCase):
    def test_pay_ratio_exactly_2_stays_amber_while_transfer_3_is_red(self):
        # 切面 20000/10000 = 2.0，阈值是 >2，贴线保持琥珀色。
        # 调配 6/2 = 3.0，同一张表里另一行必须变红，证明按行计算。
        html = _html(_roster(20000, 10000, top_transfer=6, bot_transfer=2))
        self.assertEqual(1, html.count('color:#d97706;">2.0x'))
        self.assertEqual(0, html.count('color:#dc2626;">2.0x'))
        self.assertEqual(1, html.count('color:#dc2626;">3.0x'))
        self.assertEqual(0, html.count('color:#d97706;">3.0x'))
        self.assertIn("¥2.0万", html)
        self.assertIn("¥1.0万", html)
        self.assertIn("6人", html)
        self.assertIn("2人", html)
        self.assertIsNone(_INF_NAN.search(html))
        self.assertNotIn("躺平", html)

    def test_label_2_0x_stays_amber_when_raw_ratio_rounds_up_from_below(self):
        # 19600/10000 = 1.96，展示成 2.0x，但原始值未过线，仍是琥珀色。
        html = _html(_roster(19600, 10000))
        self.assertIn("¥2.0万", html)
        self.assertEqual(1, html.count('color:#d97706;">2.0x'))
        self.assertEqual(0, html.count('color:#dc2626;">2.0x'))

    def test_label_2_0x_turns_red_when_raw_ratio_is_just_over_2(self):
        # 20400/10000 = 2.04，展示仍是 2.0x，颜色看原始比值，必须变红。
        html = _html(_roster(20400, 10000))
        self.assertIn("¥2.0万", html)
        self.assertEqual(1, html.count('color:#dc2626;">2.0x'))
        self.assertEqual(0, html.count('color:#d97706;">2.0x'))


class JianxinDeptReplyColorTests(unittest.TestCase):
    def test_reply_rate_color_flips_at_5_percent_and_zero_send_stays_red(self):
        html = _html([
            _dept(
                dept_name="建信二部",
                worker_id="line-ok",
                name="贴线达标",
                send_msg_1d_num=100,
                reply_1d_num=5,  # 5.0%
            ),
            _dept(
                dept_name="建信六部",
                worker_id="line-low",
                name="贴线偏低",
                send_msg_1d_num=1000,
                reply_1d_num=49,  # 4.9%
            ),
            _dept(
                dept_name="建信一部",
                worker_id="line-zero",
                name="零发信",
                send_msg_1d_num=0,
                reply_1d_num=0,  # 分母为 0 → 0%
            ),
        ])
        self.assertIn('color:#16a34a">5(5.0%)', html)
        self.assertNotIn('color:#dc2626">5(5.0%)', html)
        self.assertIn('color:#dc2626">49(4.9%)', html)
        self.assertNotIn('color:#16a34a">49(4.9%)', html)
        self.assertIn('color:#dc2626">0(0.0%)', html)
        self.assertNotIn('color:#16a34a">0(0.0%)', html)
        self.assertIsNone(_INF_NAN.search(html))


class JianxinChannelPayColorTests(unittest.TestCase):
    def test_zero_pay_count_is_red_and_amount_bold_while_one_pay_is_green(self):
        html = _html([
            _channel(
                channel_name="零付费残留",
                worker_id="pay-zero",
                name="零付费",
                pay_1d_num=0,
                pay_1d_amt=5000,
            ),
            _channel(
                channel_name="单笔成交",
                worker_id="pay-one",
                name="单笔",
                dept_name="建信六部",
                pay_1d_num=1,
                pay_1d_amt=15000,
            ),
        ])
        self.assertIn('color:#dc2626">0</td>', html)
        self.assertIn('font-size:12px;color:#dc2626;font-weight:600">¥0.5万', html)
        self.assertIn('color:#16a34a">1</td>', html)
        self.assertIn('font-size:12px;">¥1.5万', html)
        self.assertNotIn('font-weight:600">¥1.5万', html)
        self.assertIsNone(_INF_NAN.search(html))


if __name__ == "__main__":
    unittest.main()
