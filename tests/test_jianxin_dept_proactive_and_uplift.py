# -*- coding: utf-8 -*-
"""Regression coverage for Jianxin dept proactive clamp and leftover uplifts.

Open PR #70 covers agg_jianxin. Open PR #104 covers worker score / BOTTOM5
bands. Open PR #106 covers channel-key fallback and P1 waste naming.
This file locks department merge/manager/proactive clamp, reply-rate
color, TOP1 interpolation, empty-payload copy, and the pay_n==0 调配 SOP
fallback that still drive same-day resource decisions.
"""
import unittest

from generate_jianxin_full_report import build_dept_data, generate_html


def _row(**overrides):
    row = {
        "dept_name": "建信二部",
        "channel_name": "主站",
        "worker_id": "w1",
        "name": "标杆建信甲",
        "worker_nums": 5,
        "assign_1d_num": 40,
        "send_msg_1d_num": 40,
        "reply_1d_num": 8,
        "wechat_add_1d_num": 20,
        "transfer_1d_num": 6,
        "pay_1d_num": 2,
        "pay_1d_amt": 20000,
        "pay_1m_amt": 80000,
    }
    row.update(overrides)
    return row


class JianxinDeptProactiveTests(unittest.TestCase):
    def test_clamps_proactive_to_zero_when_assign_exceeds_wechat(self):
        depts = build_dept_data([
            _row(wechat_add_1d_num=10, assign_1d_num=30, worker_nums=5),
        ])
        self.assertEqual(len(depts), 1)
        self.assertEqual(depts[0]["proactive"], 0)
        self.assertEqual(depts[0]["per_proactive"], 0.0)
        self.assertEqual(depts[0]["manager"], "刘源")

    def test_merges_same_dept_and_maps_unknown_to_pending(self):
        depts = build_dept_data([
            _row(
                dept_name="建信二部",
                pay_1d_amt=10000,
                worker_nums=3,
                wechat_add_1d_num=20,
                assign_1d_num=10,
            ),
            _row(
                dept_name="建信二部",
                pay_1d_amt=5000,
                worker_nums=2,
                wechat_add_1d_num=8,
                assign_1d_num=4,
            ),
            _row(
                dept_name="幽灵实验组",
                pay_1d_amt=1000,
                worker_nums=1,
                wechat_add_1d_num=4,
                assign_1d_num=1,
            ),
        ])
        self.assertEqual([d["dept_name"] for d in depts], ["建信二部", "幽灵实验组"])
        self.assertEqual(depts[0]["workers"], 5)
        self.assertEqual(depts[0]["pay_amt"], 15000)
        self.assertEqual(depts[0]["proactive"], 14)  # (20+8) - (10+4)
        self.assertEqual(depts[0]["manager"], "刘源")
        self.assertEqual(depts[1]["manager"], "（待确认）")
        self.assertEqual(depts[1]["proactive"], 3)


class JianxinImprovementAndRenderTests(unittest.TestCase):
    def test_dept_gap_names_managers_and_reply_rate_colors(self):
        html = generate_html([
            _row(
                dept_name="建信二部",
                send_msg_1d_num=100,
                reply_1d_num=10,  # 10% → green
                pay_1d_amt=30000,
            ),
            _row(
                dept_name="建信六部",
                send_msg_1d_num=100,
                reply_1d_num=2,   # 2% → red
                pay_1d_amt=8000,
                worker_id="w2",
                name="尾部员工",
            ),
        ], [], "2026-02-27")
        self.assertIn("建信二部（刘源）切面¥3.0万", html)
        self.assertIn("建信六部（罗林）切面¥0.8万", html)
        self.assertIn("#16a34a\">10(10.0%)", html.replace(" ", ""))
        self.assertIn("#dc2626\">2(2.0%)", html.replace(" ", ""))

    def test_top1_name_interpolated_in_p1_card(self):
        html = generate_html([
            _row(name="标杆建信甲", transfer_1d_num=9, pay_1d_amt=45000),
        ], [], "2026-02-27")
        self.assertIn("标杆建信甲当日调配9人切面¥4.5万，为全团最高", html)

    def test_zero_pay_transfer_sop_falls_back_to_28_wan(self):
        html = generate_html([
            _row(pay_1d_num=0, pay_1d_amt=0, transfer_1d_num=20),
        ], [], "2026-02-27")
        self.assertIn("月增切面约¥28万", html)
        self.assertIn("建立调配交接SOP", html)

    def test_empty_payload_uses_safe_fallbacks(self):
        html = generate_html([], [], "2026-02-27")
        self.assertIn("部门差距待分析", html)
        self.assertIn("暂无部门数据", html)
        self.assertIn("暂无员工数据", html)
        self.assertIn("暂无渠道数据", html)
        self.assertIn("标杆员工当日调配0人切面¥0.0万", html)
        self.assertIn("人均¥0", html)  # J01 transfer==0
        self.assertNotRegex(html, r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


if __name__ == "__main__":
    unittest.main()
