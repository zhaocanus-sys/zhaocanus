# -*- coding: utf-8 -*-
"""Regression coverage for Jianxin worker ranking / BOTTOM5 / 四维倍数.

Open PR #70 covers agg/dept/channel rollups and worker merge+rank.
Open PR #93 covers department diagnosis gates and improvement time fields.
Open PR #101 covers nested DoD 🚨 and parse/color helpers.
This file locks the remaining worker-ranking HTML contracts that decide
who is copied as a benchmark and who gets same-day 1v1 coaching.
"""
import re
import unittest

from generate_jianxin_full_report import build_worker_data, generate_html


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


def _flat(html: str) -> str:
    return re.sub(r"\s+", "", html)
_ZERO_TRANSFER_ISSUE = "调配量极低，企微添加不足，说明首发信缺乏吸引力且缺乏主动触达意识，需重点话术辅导"
_REPLY_RATE_ISSUE = "回复率低于团队均值，跟进节奏不稳定，需加强话术和跟进频率辅导"
_TOP1_WHY = "调配量高且切面业绩突出，企微添加率优于均值，自主触达能力强，首发信话术具备钩子效应"
_OTHER_WHY = "调配和切面业绩均衡，回复率高于团队均值，跟进节奏稳定"


def _worker_row(**overrides):
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


def _star(**overrides):
    defaults = dict(
        transfer_1d_num=20,
        pay_1d_amt=50000,
        pay_1d_num=4,
        wechat_add_1d_num=30,
        reply_1d_num=20,
        send_msg_1d_num=100,
        assign_1d_num=15,
        pay_1m_amt=80000,
    )
    defaults.update(overrides)
    return _worker_row(**defaults)


def _bot(**overrides):
    defaults = dict(
        transfer_1d_num=0,
        pay_1d_amt=0,
        pay_1d_num=0,
        wechat_add_1d_num=2,
        reply_1d_num=1,
        send_msg_1d_num=20,
        assign_1d_num=10,
        pay_1m_amt=1000,
    )
    defaults.update(overrides)
    return _worker_row(**defaults)


def _ten(stars=None, bots=None):
    stars = stars or [_star(worker_id=f"top-{i}", name=f"标杆{i}") for i in range(5)]
    bots = bots or [_bot(worker_id=f"bot-{i}", name=f"尾部{i}") for i in range(5)]
    return stars + bots


def _html(rows, prev_rows=None, date_display="2026-02-27"):
    return generate_html(rows, prev_rows or [], date_display)


class JianxinWorkerScoreTests(unittest.TestCase):
    def test_score_weights_pay_transfer_wechat_reply(self):
        workers = build_worker_data([
            _worker_row(
                worker_id="scored",
                name="加权员工",
                pay_1d_amt=10000,       # 40
                transfer_1d_num=10,     # 3
                wechat_add_1d_num=20,   # 2
                reply_1d_num=50,
                send_msg_1d_num=100,    # reply_rate 50 → 10
            ),
        ])
        self.assertEqual(1, len(workers))
        self.assertAlmostEqual(55.0, workers[0]["score"])

    def test_identity_falls_back_to_uid_then_name_and_skips_empty(self):
        workers = build_worker_data([
            {
                "uid": "u-9",
                "name": "UID员工",
                "dept_name": "建信六部",
                "pay_1d_amt": 20000,
                "transfer_1d_num": 4,
                "wechat_add_1d_num": 8,
                "reply_1d_num": 2,
                "send_msg_1d_num": 10,
                "assign_1d_num": 3,
            },
            {
                "name": "仅姓名",
                "pay_1d_amt": 1000,
                "send_msg_1d_num": 5,
                "reply_1d_num": 1,
            },
            {"pay_1d_amt": 99_999, "transfer_1d_num": 99},
        ])
        names = [w["name"] for w in workers]
        self.assertEqual(["UID员工", "仅姓名"], names)
        self.assertEqual("建信六部", workers[0]["dept"])

    def test_zero_send_msg_uses_or1_for_reply_rate(self):
        workers = build_worker_data([
            _worker_row(
                worker_id="no-send",
                name="零发信",
                send_msg_1d_num=0,
                reply_1d_num=3,
                wechat_add_1d_num=0,
                transfer_1d_num=2,
            ),
        ])
        self.assertAlmostEqual(300.0, workers[0]["reply_rate"])
        self.assertAlmostEqual(200.0, workers[0]["transfer_rate"])


class JianxinWhyGoodAndBottomTests(unittest.TestCase):
    def test_top1_why_good_differs_from_other_top_copy(self):
        html = _html(_ten())
        self.assertIn(_TOP1_WHY, html)
        self.assertEqual(1, html.count(_TOP1_WHY))
        self.assertGreaterEqual(html.count(_OTHER_WHY), 4)
        self.assertIn("标杆0", html)

    def test_bottom5_zero_transfer_flags_script_and_proactive_gap(self):
        html = _html(_ten())
        self.assertIn(_ZERO_TRANSFER_ISSUE, html)
        self.assertEqual(5, html.count(_ZERO_TRANSFER_ISSUE))
        self.assertNotIn(_REPLY_RATE_ISSUE, html)
        self.assertIn("尾部0", html)
        self.assertIn("即日行动：安排与TOP员工1对1话术共建", html)

    def test_bottom5_nonzero_transfer_uses_reply_rate_copy(self):
        bots = [
            _bot(
                worker_id=f"bot-{i}",
                name=f"有调配{i}",
                transfer_1d_num=1,
                reply_1d_num=18,
                send_msg_1d_num=20,  # 90% 回复率，生产仍走回复率分支
            )
            for i in range(5)
        ]
        html = _html(_ten(bots=bots))
        self.assertIn(_REPLY_RATE_ISSUE, html)
        self.assertEqual(5, html.count(_REPLY_RATE_ISSUE))
        self.assertNotIn(_ZERO_TRANSFER_ISSUE, html)
        self.assertIn("有调配0", html)


class JianxinCompareAndFourDimTests(unittest.TestCase):
    def test_compare_zero_bottom_pay_uses_max1_not_inf(self):
        html = _html(_ten())
        # BOTTOM 切面均值为 0，分母回退 max(..., 1) → 50000.0x
        self.assertIn("50000.0x", html)
        self.assertIn("业绩差距说明中腰部提升空间巨大", html)
        self.assertIn("调配量差距=意向判断能力差距", html)
        self.assertIsNone(_INF_NAN.search(html))

    def test_compare_zero_bottom_reply_rate_uses_point_one_sentinel(self):
        bots = [
            _bot(
                worker_id=f"bot-{i}",
                name=f"零回复{i}",
                reply_1d_num=0,
                send_msg_1d_num=20,
            )
            for i in range(5)
        ]
        html = _html(_ten(bots=bots))
        # TOP 回复率 20.0 / max(0.0, 0.1) = 200.0x
        self.assertIn("200.0x", html)
        self.assertIn("首发信话术是核心分水岭", html)
        self.assertIsNone(_INF_NAN.search(html))

    def test_four_dimension_emits_reply_and_proactive_multiples(self):
        html = _html(_ten())
        # TOP 回复率 20.0 / BOTTOM 5.0 = 4.0 倍
        self.assertIn("TOP员工回复率是BOTTOM的4.0倍", html)
        # 心态倍数在模板里跨行；压空白后锁定 15 / max(0, 1) = 15.0
        self.assertIn("TOP员工是BOTTOM的15.0倍", _flat(html))
        self.assertNotIn("TOP员工回复率是BOTTOM的N/A倍", html)
        self.assertIn("技能维度（话术与信任构建能力）", html)
        self.assertIn("心态维度（主动性与韧性）", html)

    def test_four_dimension_send_rate_from_assign(self):
        stars = [
            _star(
                worker_id=f"top-{i}",
                name=f"标杆{i}",
                assign_1d_num=100,
                send_msg_1d_num=80,
            )
            for i in range(5)
        ]
        bots = [
            _bot(
                worker_id=f"bot-{i}",
                name=f"尾部{i}",
                assign_1d_num=100,
                send_msg_1d_num=40,
            )
            for i in range(5)
        ]
        html = _html(stars + bots)
        # 合计发信 600 / 分配 1000 = 60.0%，未发信 40.0%
        self.assertIn("当前分配后发信率60.0%", html)
        self.assertIn("说明有40.0%分配未及时发信", html)

    def test_fewer_than_five_workers_suppresses_bottom5_and_ratios(self):
        rows = [_star(worker_id=f"only-{i}", name=f"独苗{i}") for i in range(4)]
        html = _html(rows)
        self.assertIn("独苗0", html)
        self.assertIn("暂无数据", html)
        self.assertNotIn(_ZERO_TRANSFER_ISSUE, html)
        self.assertNotIn(_REPLY_RATE_ISSUE, html)
        self.assertIn("TOP员工回复率是BOTTOM的N/A倍", html)
        self.assertIn("TOP员工是BOTTOM的N/A倍", _flat(html))
        self.assertIsNone(_INF_NAN.search(html))

    def test_empty_workers_safe_render(self):
        html = _html([])
        self.assertIn("暂无员工数据", html)
        self.assertIn("暂无数据", html)
        self.assertIn("四维人员分析（技能·心态·资源管理·执行力）", html)
        self.assertIn("TOP员工回复率是BOTTOM的N/A倍", html)
        self.assertNotIn("躺平", html)
        self.assertIsNone(_INF_NAN.search(html))


if __name__ == "__main__":
    unittest.main()
