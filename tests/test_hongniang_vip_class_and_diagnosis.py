# -*- coding: utf-8 -*-
"""Regression coverage for hongniang VIP/allot class rollups and diagnosis gates."""
import math
import unittest

from generate_hongniang_full_report import (
    MGMT_GAP_RULES,
    agg_hongniang,
    generate_html,
)


def _finite(value):
    return math.isfinite(float(value))


class HongniangVipAllotClassTests(unittest.TestCase):
    def test_agg_hongniang_rolls_up_vip_and_allot_classes(self):
        """Multi-row vip_class0-4 / allot_class0-4 must sum independently per bucket."""
        rows = [
            {
                "pay_1d_amt": "1000",
                "staff_new": "1",
                "vip_class0": "1",
                "vip_class1": "2",
                "vip_class2": "3",
                "vip_class3": "4",
                "vip_class4": "5",
                "allot_class0": "10",
                "allot_class1": "20",
                "allot_class2": "30",
                "allot_class3": "40",
                "allot_class4": "50",
            },
            {
                "pay_1d_amt": "2000",
                "staff_new": "1",
                "vip_class0": "9",
                "vip_class1": "8",
                "vip_class2": "7",
                "vip_class3": "6",
                "vip_class4": "5",
                "allot_class0": "1",
                "allot_class1": "2",
                "allot_class2": "3",
                "allot_class3": "4",
                "allot_class4": "5",
            },
            {
                # Missing class fields must contribute zeros, not crash.
                "pay_1d_amt": "0",
                "staff_new": "0",
            },
        ]

        result = agg_hongniang(rows)

        self.assertEqual(result["vip_class"], {0: 10, 1: 10, 2: 10, 3: 10, 4: 10})
        self.assertEqual(result["allot_class"], {0: 11, 1: 22, 2: 33, 3: 44, 4: 55})
        self.assertEqual(result["total_rev"], 3000.0)
        self.assertEqual(result["staff_new"], 2)

    def test_agg_hongniang_zero_denominators_stay_finite(self):
        """Empty staff / revenue / talk volume must not yield NaN or Inf rates."""
        result = agg_hongniang([
            {
                "jm_n": "5",
                "deep_count": "3",
                "zhenai_back": "100",
                "zhenaigd_back": "50",
            }
        ])

        self.assertEqual(result["staff_new"], 0)
        self.assertEqual(result["total_rev"], 0)
        self.assertEqual(result["link_time_count"], 0)
        # staff_new or 1 → jm_rate = 5 / 1
        self.assertEqual(result["jm_rate"], 5.0)
        self.assertEqual(result["per_rev"], 0)
        # Aggregate refund_rate uses total_rev > 0 guard (unlike dept or-1 fallback).
        self.assertEqual(result["refund_rate"], 0)
        self.assertEqual(result["deep_rate"], 0)
        self.assertEqual(result["vip_class"], {0: 0, 1: 0, 2: 0, 3: 0, 4: 0})
        self.assertEqual(result["allot_class"], {0: 0, 1: 0, 2: 0, 3: 0, 4: 0})
        for key in ("jm_rate", "per_rev", "refund_rate", "deep_rate"):
            self.assertTrue(_finite(result[key]), msg=key)


class HongniangDiagnosisAndImprovementTests(unittest.TestCase):
    def _weak_rows(self):
        """Departments that trigger low-jm mgmt-gap + aggregate P0 jm/refund cards."""
        return [
            {
                "dept_name": "深圳红娘一部 白班",
                "staff_new": "5",
                "call_worker": "4",
                "on_vip": "40",
                "jm_n": "2",
                "jm_all": "3",
                "pay_1d_amt": "8000",
                "pay_1m_amt": "80000",
                "link_time_count": "40",
                "deep_count": "4",
                "love_cnt_m": "1",
                "tousu_n": "0",
                "pay_1d_num": "1",
                "zhenai_back": "600",
                "zhenaigd_back": "200",
                "vip_class0": "5",
                "allot_class0": "3",
            },
            {
                "dept_name": "厦门红娘一区一部 晚班",
                "staff_new": "4",
                "call_worker": "3",
                "on_vip": "30",
                "jm_n": "1",
                "jm_all": "2",
                "pay_1d_amt": "4000",
                "pay_1m_amt": "40000",
                "link_time_count": "20",
                "deep_count": "2",
                "love_cnt_m": "0",
                "tousu_n": "1",
                "pay_1d_num": "0",
                "zhenai_back": "400",
                "zhenai_md_back": "100",
                "vip_class1": "2",
                "allot_class1": "1",
            },
        ]

    def test_html_emits_mgmt_gap_owner_and_timed_p0_improvements(self):
        rows = self._weak_rows()
        html = generate_html(rows, rows, [], "2026-02-27")

        # Department diagnosis must name manager + management-gap inference text.
        self.assertIn("深圳红娘一部", html)
        self.assertIn("曹世迪", html)
        self.assertIn(MGMT_GAP_RULES["low_jm_rate"], html)
        self.assertIn("管理视角缺失推断", html)

        # Aggregate jm_rate = 3/9 ≈ 0.33 < 1.0 → P0 meet-rate fix.
        self.assertIn("见面安排率修复至1.0", html)
        # Aggregate refund = 1300 / 12000 ≈ 10.83% > 5 → P0 refund control.
        self.assertIn("退费率管控至4.5%", html)
        self.assertIn("【P0】", html)

        # Time-dimension deploy date = report day + 1.
        self.assertIn("部署日期: 2026-02-28", html)
        self.assertIn("坚持:", html)

    def test_healthy_metrics_skip_p0_jm_and_refund_cards(self):
        rows = [
            {
                "dept_name": "深圳红娘一部",
                "staff_new": "5",
                "call_worker": "5",
                "on_vip": "50",
                "jm_n": "8",
                "jm_all": "10",
                "pay_1d_amt": "100000",
                "pay_1m_amt": "500000",
                "link_time_count": "80",
                "deep_count": "30",
                "love_cnt_m": "3",
                "tousu_n": "0",
                "pay_1d_num": "4",
                "zhenai_back": "500",
                "vip_class2": "10",
                "allot_class2": "8",
            }
        ]
        html = generate_html(rows, [], [], "2026-03-01")

        # jm_rate = 8/5 = 1.6 ≥ 1.0 and refund_rate = 0.5% ≤ 5 → no those P0 cards.
        self.assertNotIn("见面安排率修复至1.0", html)
        self.assertNotIn("退费率管控至4.5%", html)
        # Always-on P1 items still carry tomorrow deploy date.
        self.assertIn("部署日期: 2026-03-02", html)
        self.assertIn("社会认同话术植入", html)


if __name__ == "__main__":
    unittest.main()
