# -*- coding: utf-8 -*-
"""Regression coverage for telesale diagnosis gates and improvement actions."""
import unittest

from generate_telesale_full_report import DEPT_MANAGERS, generate_html


class TelesaleDiagnosisGateTests(unittest.TestCase):
    def _weak_and_strong_rows(self):
        """One critical dept (六部) + one healthy dept (一部) for scope-separated gates."""
        return [
            {
                "dept_name": "电销一部",
                "worker_nums": "10",
                "pay_1d_amt": "30000",
                "callout_1d_num": "1000",
                "link_1d_num": "220",
                "linkmems_deeptalk_10_1d_num": "90",
                "pay_1d_num": "8",
                "ai_score": "80",
                "new_worker_num": "1",
                "pay_1m_amt": "400000",
            },
            {
                "dept_name": "电销六部",
                "worker_nums": "10",
                "pay_1d_amt": "8000",
                "callout_1d_num": "1000",
                "link_1d_num": "80",
                "linkmems_deeptalk_10_1d_num": "16",
                "pay_1d_num": "1",
                "ai_score": "55",
                "new_worker_num": "3",
                "pay_1m_amt": "90000",
            },
        ]

    def test_dept_diagnosis_names_manager_and_mgmt_gap_text(self):
        rows = self._weak_and_strong_rows()
        html = generate_html(rows, rows, "2026-02-27")

        # Department-scoped findings must include mapped managers.
        self.assertIn("电销六部", html)
        self.assertIn(DEPT_MANAGERS["电销六部"], html)
        self.assertIn("电销一部", html)
        self.assertIn(DEPT_MANAGERS["电销一部"], html)
        self.assertIn("管理视角缺失推断", html)

        # 六部: connect 8% < 18, deep 20% < 30, per_capita 800 < 2000
        self.assertIn("缺乏号码健康度和外呼时段精细化管理意识", html)
        self.assertIn("忽视话术结构化训练，团队在浅层沟通而非深度卖货", html)
        self.assertIn("缺乏中腰部差异化辅导策略", html)

        # Global connect_rate = 300/2000 = 15% → warning band (12–18), not critical redline copy.
        self.assertIn("低于18%基准，建议排查号码健康度和外呼时段", html)
        self.assertNotIn("严重偏低，低于12%红线", html)

        # Global deep_rate = 106/300 ≈ 35.3% ≥ 35 → healthy deep-talk copy.
        self.assertIn("深沟率达标，保持稳定", html)

        # Improvement table carries owner + daily action + duration (time-dimension contract).
        self.assertIn("每日08:30前提交号码健康度自查报告", html)
        self.assertIn("14天", html)
        self.assertIn("吴胜悍", html)

    def test_healthy_dept_skips_low_connect_mgmt_gap(self):
        rows = [
            {
                "dept_name": "电销一部",
                "worker_nums": "8",
                "pay_1d_amt": "24000",
                "callout_1d_num": "800",
                "link_1d_num": "200",
                "linkmems_deeptalk_10_1d_num": "80",
                "pay_1d_num": "6",
                "ai_score": "82",
                "new_worker_num": "1",
                "pay_1m_amt": "300000",
            }
        ]
        html = generate_html(rows, [], "2026-03-01")

        # connect 25% ≥ 18 and deep 40% ≥ 30 and per_capita 3000 ≥ 2000 → no gap phrases.
        self.assertIn("电销一部 · 罗阳", html)
        self.assertNotIn("缺乏号码健康度和外呼时段精细化管理意识", html)
        self.assertNotIn("忽视话术结构化训练，团队在浅层沟通而非深度卖货", html)
        self.assertNotIn("缺乏中腰部差异化辅导策略", html)

        # Global healthy bands.
        self.assertIn("接通率达标", html)
        self.assertIn("深沟率达标，保持稳定", html)
        self.assertIn("人均产值优秀", html)

    def test_empty_rows_render_without_crash(self):
        """Empty API payload must not ZeroDivide or fail f-string parse."""
        html = generate_html([], [], "2026-03-02")
        self.assertIn("电销团队业务体检报告", html)
        self.assertIn("0/0 (0%)", html)
        self.assertIn("正常，建议保持新人辅导节奏", html)
        self.assertIn("35岁客户", html)
        self.assertNotIn("{{}age{}", html)


if __name__ == "__main__":
    unittest.main()
