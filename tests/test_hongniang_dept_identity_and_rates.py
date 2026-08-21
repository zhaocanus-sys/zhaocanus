# -*- coding: utf-8 -*-
"""Regression coverage for Hongniang department identity and rate sentinels.

Open PR #90 covers VIP/allot class rollups and jm/refund P0 cards.
Open PR #91 covers empty-dept gap rendering and SOP-copy gates.
Open PR #75 covers hourly worker aggregation.
This file locks department-name truncation, fuzzy manager attribution,
zero-denominator rates, same-prefix merge, and pay ranking.
"""
import math
import unittest

from generate_hongniang_full_report import DEPT_MANAGERS, build_dept_data


def _dept(**overrides):
    row = {
        "dept_name": "厦门红娘一区一部",
        "staff_new": 10,
        "call_worker": 8,
        "on_vip": 50,
        "jm_n": 8,
        "jm_all": 12,
        "pay_1d_amt": 20000,
        "pay_1m_amt": 80000,
        "link_time_count": 40,
        "deep_count": 10,
        "love_cnt_m": 2,
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


class HongniangDeptIdentityTests(unittest.TestCase):
    def test_space_truncated_name_maps_known_manager(self):
        depts = build_dept_data([
            _dept(dept_name="厦门红娘一区一部 早班"),
        ])
        self.assertEqual(1, len(depts))
        self.assertEqual("厦门红娘一区一部", depts[0]["dept_name"])
        self.assertEqual("厦门红娘一区一部 早班", depts[0]["full_name"])
        self.assertEqual("温方方（代）", depts[0]["manager"])

    def test_fuzzy_full_name_recovers_manager_when_prefix_is_generic(self):
        depts = build_dept_data([
            _dept(dept_name="一组 厦门红娘一区一部"),
        ])
        self.assertEqual("一组", depts[0]["dept_name"])
        self.assertEqual(DEPT_MANAGERS["厦门红娘一区一部"], depts[0]["manager"])

    def test_prefix_match_without_space_still_maps_manager(self):
        depts = build_dept_data([
            _dept(dept_name="深圳红娘一部东区"),
        ])
        self.assertEqual("曹世迪", depts[0]["manager"])

    def test_unknown_dept_falls_back_to_pending(self):
        depts = build_dept_data([_dept(dept_name="杭州新店")])
        self.assertEqual("（待确认）", depts[0]["manager"])

    def test_same_truncated_prefix_merges_rows(self):
        depts = build_dept_data([
            _dept(dept_name="厦门红娘一区一部 早班", jm_n=3, pay_1d_amt=8000, staff_new=4),
            _dept(dept_name="厦门红娘一区一部 晚班", jm_n=5, pay_1d_amt=12000, staff_new=6),
        ])
        self.assertEqual(1, len(depts))
        self.assertEqual(8, depts[0]["jm_n"])
        self.assertEqual(20000.0, depts[0]["pay_1d_amt"])
        self.assertEqual(10, depts[0]["staff_new"])
        self.assertAlmostEqual(0.8, depts[0]["jm_rate"])


class HongniangDeptRateSentinelTests(unittest.TestCase):
    def test_zero_staff_uses_or_1_for_jm_and_per_rev(self):
        depts = build_dept_data([
            _dept(staff_new=0, jm_n=3, pay_1d_amt=9000),
        ])
        self.assertAlmostEqual(3.0, depts[0]["jm_rate"])
        self.assertAlmostEqual(9000.0, depts[0]["per_rev"])
        self.assertTrue(math.isfinite(depts[0]["jm_rate"]))
        self.assertTrue(math.isfinite(depts[0]["per_rev"]))

    def test_zero_talks_uses_or_1_for_deep_rate(self):
        depts = build_dept_data([
            _dept(link_time_count=0, deep_count=5),
        ])
        self.assertAlmostEqual(500.0, depts[0]["deep_rate"])
        self.assertTrue(math.isfinite(depts[0]["deep_rate"]))

    def test_zero_revenue_uses_or_1_for_refund_rate(self):
        depts = build_dept_data([
            _dept(pay_1d_amt=0, zhenai_back=200, zhenaigd_back=0),
        ])
        self.assertAlmostEqual(20000.0, depts[0]["refund_rate"])
        self.assertTrue(math.isfinite(depts[0]["refund_rate"]))

    def test_sorted_by_pay_desc(self):
        depts = build_dept_data([
            _dept(dept_name="厦门红娘一区一部", pay_1d_amt=20000),
            _dept(dept_name="深圳红娘一部", pay_1d_amt=50000),
            _dept(dept_name="厦门红娘二区二部", pay_1d_amt=30000),
        ])
        self.assertEqual(
            ["深圳红娘一部", "厦门红娘二区二部", "厦门红娘一区一部"],
            [d["dept_name"] for d in depts],
        )
        self.assertEqual(["曹世迪", "刘文琴", "温方方（代）"], [d["manager"] for d in depts])


if __name__ == "__main__":
    unittest.main()
