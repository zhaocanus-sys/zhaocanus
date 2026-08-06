# -*- coding: utf-8 -*-
"""Regression coverage for hongniang empty-dept HTML safety and gap gates."""
import unittest

from generate_hongniang_full_report import generate_html


class HongniangEmptyDeptGapTests(unittest.TestCase):
    def test_generate_html_empty_rows_does_not_crash(self):
        """Empty API payload must not ValueError on max/min over depts."""
        html = generate_html([], [], [], "2026-02-27")

        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 500)
        self.assertIn("部门差距：", html)
        self.assertIn("暂无部门数据，待分配后对比", html)
        # Empty depts → no dept-gap P1 card (only always-on P1s remain).
        self.assertNotIn("标杆复制：", html)
        self.assertIn("部署日期: 2026-02-28", html)

    def test_dept_gap_summary_and_benchmark_p1_when_gap_large(self):
        """jm_rate gap > 0.3 must show correct extremes and emit P1 标杆复制."""
        rows = [
            {
                "dept_name": "深圳红娘一部 白班",
                "staff_new": "5",
                "call_worker": "5",
                "on_vip": "50",
                "jm_n": "10",
                "jm_all": "12",
                "pay_1d_amt": "50000",
                "pay_1m_amt": "200000",
                "link_time_count": "80",
                "deep_count": "20",
                "love_cnt_m": "2",
                "tousu_n": "0",
                "pay_1d_num": "3",
                "zhenai_back": "100",
            },
            {
                "dept_name": "厦门红娘一区一部 晚班",
                "staff_new": "5",
                "call_worker": "4",
                "on_vip": "40",
                "jm_n": "2",
                "jm_all": "3",
                "pay_1d_amt": "8000",
                "pay_1m_amt": "40000",
                "link_time_count": "30",
                "deep_count": "4",
                "love_cnt_m": "0",
                "tousu_n": "1",
                "pay_1d_num": "0",
                "zhenai_back": "200",
            },
        ]
        html = generate_html(rows, [], [], "2026-03-01")

        # Global diagnosis line: best 2.00 vs worst 0.40, gap 1.60x.
        self.assertIn("最高深圳红娘一部 见面安排率 2.00", html)
        self.assertIn("最低 0.40", html)
        self.assertIn("差距1.60x", html)
        self.assertNotIn("暂无部门数据", html)

        # Improvement gate: gap > 0.3 → P1 benchmark copy with managers.
        self.assertIn("标杆复制：深圳红娘一部SOP推广", html)
        self.assertIn("【P1】", html)
        self.assertIn("温方方（代）", html)
        self.assertIn("部署日期: 2026-03-02", html)

    def test_small_dept_gap_skips_benchmark_p1(self):
        """jm_rate gap ≤ 0.3 must not emit the benchmark-copy P1 card."""
        rows = [
            {
                "dept_name": "深圳红娘一部",
                "staff_new": "5",
                "call_worker": "5",
                "on_vip": "50",
                "jm_n": "5",
                "jm_all": "6",
                "pay_1d_amt": "40000",
                "pay_1m_amt": "160000",
                "link_time_count": "60",
                "deep_count": "18",
                "love_cnt_m": "1",
                "tousu_n": "0",
                "pay_1d_num": "2",
                "zhenai_back": "50",
            },
            {
                "dept_name": "厦门红娘一区二部",
                "staff_new": "5",
                "call_worker": "5",
                "on_vip": "45",
                "jm_n": "4",
                "jm_all": "5",
                "pay_1d_amt": "32000",
                "pay_1m_amt": "120000",
                "link_time_count": "55",
                "deep_count": "16",
                "love_cnt_m": "1",
                "tousu_n": "0",
                "pay_1d_num": "1",
                "zhenai_back": "40",
            },
        ]
        html = generate_html(rows, [], [], "2026-03-05")

        # Gap = 1.0 - 0.8 = 0.2 ≤ 0.3 → summary still renders, no P1 copy card.
        self.assertIn("最高深圳红娘一部 见面安排率 1.00", html)
        self.assertIn("最低 0.80", html)
        self.assertIn("差距0.20x", html)
        self.assertNotIn("标杆复制：", html)


if __name__ == "__main__":
    unittest.main()
