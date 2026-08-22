# -*- coding: utf-8 -*-
"""Regression coverage for Hongniang department diagnosis gap-key priority.

Open PR #90 covers the low_jm_rate path and P0 jm/refund cards.
Open PR #91 covers empty-dept gap rendering and SOP-copy gates.
Open PR #105 covers department identity / rate sentinels.
This file locks the remaining priority chain on main:

    jm_rate < 0.8 → low_jm_rate
    else refund_rate > 8 → high_refund
    else low_per_rev

plus worst-3 selection and computed 「达均值」 uplift.
"""
import re
import unittest

from generate_hongniang_full_report import MGMT_GAP_RULES, generate_html


def _dept(**overrides):
    row = {
        "dept_name": "厦门红娘一区一部",
        "staff_new": 10,
        "call_worker": 8,
        "on_vip": 40,
        "jm_n": 8,
        "jm_all": 10,
        "pay_1d_amt": 20000,
        "pay_1m_amt": 80000,
        "link_time_count": 40,
        "deep_count": 10,
        "love_cnt_m": 1,
        "tousu_n": 0,
        "pay_1d_num": 2,
        "zhenai_back": 0,
        "zhenaigd_back": 0,
        "zhenai_hz_back": 0,
        "zhenai_xfh_back": 0,
        "zhenai_md_back": 0,
    }
    row.update(overrides)
    return row


def _html(rows, date_display="2026-02-27"):
    return generate_html(rows, [], [], date_display)


def _warning_headers(html):
    return re.findall(r"部门预警</span>\s*<span[^>]*>([^<]+)", html)


class HongniangDeptGapPriorityTests(unittest.TestCase):
    def test_jm_below_08_wins_over_high_refund(self):
        html = _html([
            _dept(dept_name="厦门红娘一区一部", jm_n=4, staff_new=10,
                  pay_1d_amt=10000, zhenai_back=2000),  # 0.40 + 20% refund
            _dept(dept_name="深圳红娘一部", jm_n=8, staff_new=10,
                  pay_1d_amt=20000, zhenai_back=2000),  # 0.80 + 10% refund
            _dept(dept_name="厦门红娘一区二部", jm_n=9, staff_new=10,
                  pay_1d_amt=30000, zhenai_back=2400),  # 0.90 + 8.0% refund
            _dept(dept_name="厦门红娘二区一部", jm_n=15, staff_new=10,
                  pay_1d_amt=40000, zhenai_back=0),     # 1.50 healthy
        ])
        headers = _warning_headers(html)
        self.assertEqual(3, len(headers))
        self.assertTrue(any("厦门红娘一区一部（温方方（代））— 见面安排率 0.40" in h for h in headers))
        self.assertTrue(any("深圳红娘一部（曹世迪）— 见面安排率 0.80" in h for h in headers))
        self.assertTrue(any("厦门红娘一区二部（周美）— 见面安排率 0.90" in h for h in headers))
        self.assertFalse(any("厦门红娘二区一部" in h for h in headers))

        self.assertIn(MGMT_GAP_RULES["low_jm_rate"], html)
        self.assertIn(MGMT_GAP_RULES["high_refund"], html)
        self.assertIn(MGMT_GAP_RULES["low_per_rev"], html)
        # team per_rev = 100000/40=2500; dept A 1000 → +¥15,000/日
        self.assertIn("达均值可+¥15,000/日", html)

    def test_jm_at_08_and_refund_above_8_uses_high_refund(self):
        html = _html([
            _dept(dept_name="深圳红娘一部", jm_n=8, staff_new=10,
                  pay_1d_amt=10000, zhenai_back=801),  # 8.01%
            _dept(dept_name="厦门红娘一区一部", jm_n=12, staff_new=10,
                  pay_1d_amt=30000, zhenai_back=0),
            _dept(dept_name="厦门红娘一区二部", jm_n=13, staff_new=10,
                  pay_1d_amt=40000, zhenai_back=0),
        ])
        self.assertIn("深圳红娘一部（曹世迪）— 见面安排率 0.80", html)
        self.assertIn(MGMT_GAP_RULES["high_refund"], html)
        self.assertNotIn(MGMT_GAP_RULES["low_jm_rate"], html)

    def test_refund_at_8_falls_through_to_low_per_rev(self):
        html = _html([
            _dept(dept_name="厦门红娘一区二部", jm_n=9, staff_new=10,
                  pay_1d_amt=10000, zhenai_back=800),  # exactly 8.0%
            _dept(dept_name="厦门红娘一区一部", jm_n=12, staff_new=10,
                  pay_1d_amt=30000, zhenai_back=0),
            _dept(dept_name="深圳红娘一部", jm_n=13, staff_new=10,
                  pay_1d_amt=40000, zhenai_back=0),
        ])
        self.assertIn("厦门红娘一区二部（周美）— 见面安排率 0.90", html)
        self.assertIn(MGMT_GAP_RULES["low_per_rev"], html)
        self.assertNotIn(MGMT_GAP_RULES["low_jm_rate"], html)
        self.assertNotIn(MGMT_GAP_RULES["high_refund"], html)


if __name__ == "__main__":
    unittest.main()
