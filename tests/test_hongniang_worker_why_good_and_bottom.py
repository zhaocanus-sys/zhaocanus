# -*- coding: utf-8 -*-
"""Regression coverage for Hongniang worker why_good / BOTTOM5 / compare gates.

Open PR #75 covers hourly aggregation + main routing.
Open PR #90/#91 cover VIP/allot classes, P0 jm/refund cards, and empty-dept gaps.
Open PR #102 covers shop why_shop_good and Hongniang refund-channel concentration.
This file locks the remaining worker-ranking HTML contracts that drive
benchmark copy and same-day 1v1 coaching.
"""
import re
import unittest

from generate_hongniang_full_report import generate_html


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


def _dept_row(**overrides):
    row = {
        "dept_name": "深圳红娘一部",
        "staff_new": "2",
        "call_worker": "2",
        "on_vip": "20",
        "jm_n": "2",
        "pay_1d_amt": "10000",
        "pay_1m_amt": "40000",
        "link_time_count": "20",
        "deep_count": "8",
        "love_cnt_m": "1",
        "tousu_n": "0",
        "pay_1d_num": "1",
    }
    row.update(overrides)
    return row


def _worker_row(**overrides):
    row = {
        "worker_name": "甲红娘",
        "dept_name": "深圳红娘一部",
        "jm_n": "1",
        "on_vip": "10",
        "off_vip": "0",
        "link_time_count": "8",
        "jianmian_cs": "2",
        "jianmian_rs": "1",
        "jianmiangd_cs": "2",
        "jianmiangd_rs": "1",
        "love_cnt_m": "0",
        "tousu_n": "0",
        "online_pay_m": "1000",
        "xml_pay_m": "0",
        "offline_pay_m": "0",
        "zhenai_back": "0",
        "zhenaigd_back": "0",
    }
    row.update(overrides)
    return row


def _html(workers, date_display="2026-02-27"):
    return generate_html([_dept_row()], [], workers, date_display)


class HongniangWhyGoodTests(unittest.TestCase):
    def test_why_good_emits_all_excellent_bands(self):
        html = _html([
            _worker_row(
                worker_name="标杆红娘",
                jm_n="4",
                jianmian_cs="10",
                jianmian_rs="9",   # 90% >= 85
                jianmiangd_cs="10",
                jianmiangd_rs="8",  # 80% >= 70
                love_cnt_m="2",
            ),
        ])
        self.assertIn("见面安排频次高", html)
        self.assertIn("见面确认率强", html)
        self.assertIn("复见面推进积极", html)
        self.assertIn("恋爱达成有突破", html)
        self.assertNotIn("资源盘点系统化", html)
        self.assertIsNone(_INF_NAN.search(html))

    def test_why_good_falls_back_when_no_band_hits(self):
        html = _html([
            _worker_row(
                worker_name="稳健红娘",
                jm_n="2",
                jianmian_cs="10",
                jianmian_rs="8",    # 80% < 85
                jianmiangd_cs="10",
                jianmiangd_rs="6",  # 60% < 70
                love_cnt_m="0",
            ),
        ])
        self.assertIn("资源盘点系统化", html)
        self.assertNotIn("见面安排频次高", html)
        self.assertNotIn("见面确认率强", html)
        self.assertNotIn("复见面推进积极", html)
        self.assertNotIn("恋爱达成有突破", html)


class HongniangBottom5Tests(unittest.TestCase):
    def test_bottom5_zero_meeting_flags_unserved_vip(self):
        html = _html([_worker_row(worker_name="零见面", jm_n="0")])
        self.assertIn("⚠ 零见面 · 深圳红娘一部", html)
        self.assertIn("今日零见面安排，VIP资源完全未服务", html)

    def test_bottom5_low_confirm_rate_flags_invite_script(self):
        html = _html([
            _worker_row(
                worker_name="低确认",
                jm_n="2",
                jianmian_cs="10",
                jianmian_rs="4",  # 40% < 50
            ),
        ])
        self.assertIn("见面确认率仅40%，邀约话术需优化", html)
        self.assertNotIn("今日零见面安排，VIP资源完全未服务", html)

    def test_bottom5_high_refund_flags_promise_compliance(self):
        html = _html([
            _worker_row(
                worker_name="高退费",
                jm_n="2",
                jianmian_cs="10",
                jianmian_rs="6",  # 60% >= 50，避免确认率分支
                zhenai_back="4000",
                zhenaigd_back="1500",  # 5500 > 5000
            ),
        ])
        self.assertIn("退费金额¥5,500，需排查服务承诺合规性", html)

    def test_bottom5_falls_back_when_no_issue_band_hits(self):
        html = _html([
            _worker_row(
                worker_name="综合偏低",
                jm_n="1",
                jianmian_cs="10",
                jianmian_rs="6",  # 60%
                zhenai_back="100",
            ),
        ])
        self.assertIn("综合评分偏低，需排查具体薄弱环节", html)
        self.assertNotIn("今日零见面安排，VIP资源完全未服务", html)
        self.assertNotIn("邀约话术需优化", html)
        self.assertNotIn("需排查服务承诺合规性", html)


class HongniangCompareSentinelTests(unittest.TestCase):
    def test_compare_uses_99x_when_bottom_meetings_are_zero(self):
        stars = [
            _worker_row(
                worker_name=f"TOP{i}",
                jm_n="5",
                jianmian_cs="10",
                jianmian_rs="9",
                jianmiangd_cs="10",
                jianmiangd_rs="8",
                love_cnt_m="1",
                online_pay_m="8000",
            )
            for i in range(5)
        ]
        bottoms = [
            _worker_row(
                worker_name=f"BOT{i}",
                jm_n="0",
                jianmian_cs="0",
                jianmian_rs="0",
                jianmiangd_cs="0",
                jianmiangd_rs="0",
                love_cnt_m="0",
                online_pay_m="100",
            )
            for i in range(5)
        ]
        html = _html(stars + bottoms)
        self.assertIn("99.0x", html)
        self.assertIn("差距显著，可通过SOP复制TOP工作模式", html)
        self.assertIsNone(_INF_NAN.search(html))

    def test_refund_compare_inverts_to_green_when_top_refunds_less(self):
        stars = [
            _worker_row(
                worker_name=f"低退费{i}",
                jm_n="5",
                jianmian_cs="10",
                jianmian_rs="9",
                jianmiangd_cs="10",
                jianmiangd_rs="8",
                love_cnt_m="1",
                zhenai_back="1000",
            )
            for i in range(5)
        ]
        bottoms = [
            _worker_row(
                worker_name=f"高退费{i}",
                jm_n="0",
                zhenai_back="10000",
            )
            for i in range(5)
        ]
        html = _html(stars + bottoms)
        # 1000/10000 = 0.1x；低优维度 ratio<=0.7 → 绿色
        self.assertIn('color:#16a34a">0.1x</td>', html)
        self.assertIn("退费总额", html)


if __name__ == "__main__":
    unittest.main()
