# -*- coding: utf-8 -*-
"""Regression coverage for jianxin department diagnosis gates and timed improvements."""
import unittest

from generate_jianxin_full_report import DEPT_MANAGERS, MGMT_GAP_RULES, generate_html


class JianxinDiagnosisGateTests(unittest.TestCase):
    def _weak_and_strong_rows(self):
        """One critical dept (六部) + one healthy dept (二部) + zero-pay channel."""
        return [
            {
                "dept_name": "建信二部",
                "channel_name": "高效渠道",
                "worker_nums": "10",
                "assign_1d_num": "100",
                "send_msg_1d_num": "100",
                "reply_1d_num": "20",
                "wechat_add_1d_num": "50",
                "transfer_1d_num": "15",
                "pay_1d_num": "4",
                "pay_1d_amt": "40000",
                "pay_1m_amt": "200000",
                "worker_id": "w-strong",
                "name": "标杆员工",
                "new_worker_num": "1",
            },
            {
                "dept_name": "建信六部",
                "channel_name": "试岗资源",
                "worker_nums": "10",
                "assign_1d_num": "100",
                "send_msg_1d_num": "100",
                "reply_1d_num": "2",
                "wechat_add_1d_num": "8",
                "transfer_1d_num": "1",
                "pay_1d_num": "0",
                "pay_1d_amt": "0",
                "pay_1m_amt": "5000",
                "worker_id": "w-weak",
                "name": "弱势员工",
                "new_worker_num": "3",
            },
        ]

    def test_dept_diagnosis_names_manager_and_mgmt_gap_text(self):
        rows = self._weak_and_strong_rows()
        html = generate_html(rows, rows, "2026-02-27")

        # Department-scoped findings must include mapped managers + section.
        self.assertIn("部门级诊断（含管理者姓名 + 管理视角缺失推断）", html)
        self.assertIn("建信六部", html)
        self.assertIn(DEPT_MANAGERS["建信六部"], html)
        self.assertIn("建信二部", html)
        self.assertIn(DEPT_MANAGERS["建信二部"], html)
        self.assertIn("管理视角缺失推断", html)

        # 六部: reply_rate = 2% < 5 → low_reply_rate gap text.
        self.assertIn(MGMT_GAP_RULES["low_reply_rate"], html)

        # Global channel waste gate: zero-pay channel named.
        self.assertIn("渠道浪费", html)
        self.assertIn("试岗资源", html)

        # Improvement cards carry deploy_date = report day + 1 and duration.
        self.assertIn("部署: 2026-02-28", html)
        self.assertIn("每日执行: 晨会比对模板效果+回复率排名", html)
        self.assertIn("坚持: 14天", html)
        self.assertIn("【P0】", html)

    def test_healthy_dept_skips_mgmt_gap_phrases(self):
        rows = [
            {
                "dept_name": "建信二部",
                "channel_name": "高效渠道",
                "worker_nums": "8",
                "assign_1d_num": "80",
                "send_msg_1d_num": "80",
                "reply_1d_num": "16",
                "wechat_add_1d_num": "40",
                "transfer_1d_num": "12",
                "pay_1d_num": "4",
                "pay_1d_amt": "32000",
                "pay_1m_amt": "150000",
                "worker_id": "w-healthy",
                "name": "健康员工",
                "new_worker_num": "1",
            }
        ]
        html = generate_html(rows, [], "2026-03-01")

        # reply 20% / wechat 50% / transfer 30% / per_capita 4000 → no gap cards.
        self.assertIn("建信二部", html)
        self.assertIn(DEPT_MANAGERS["建信二部"], html)
        self.assertIn("各部门关键指标暂无触发预警门槛", html)
        self.assertNotIn(MGMT_GAP_RULES["low_reply_rate"], html)
        self.assertNotIn(MGMT_GAP_RULES["low_wechat_rate"], html)
        self.assertNotIn(MGMT_GAP_RULES["low_transfer_rate"], html)
        self.assertNotIn(MGMT_GAP_RULES["low_per_capita"], html)

        # No zero-pay channel → channel-waste warning omitted.
        self.assertNotIn("渠道浪费", html)

        # Deploy date still derived from report day + 1.
        self.assertIn("部署: 2026-03-02", html)

    def test_empty_rows_render_without_crash(self):
        """Empty API payload must render finite zeros and empty-state diagnosis."""
        html = generate_html([], [], "2026-03-02")
        self.assertIn("建信团队运营体检报告", html)
        self.assertIn("部门级诊断（含管理者姓名 + 管理视角缺失推断）", html)
        self.assertIn("各部门关键指标暂无触发预警门槛", html)
        self.assertIn("首发信回复率偏低（0.0%）", html)
        self.assertIn("部署: 2026-03-03", html)
        self.assertNotIn("渠道浪费", html)


if __name__ == "__main__":
    unittest.main()
