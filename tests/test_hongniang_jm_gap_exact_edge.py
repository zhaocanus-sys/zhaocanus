# -*- coding: utf-8 -*-
"""红娘部门见面率差距贴在 0.30x 时，标杆复制卡是否该开。

PR #91 锁了差距 1.60 开卡、0.20 静默，没有锁「展示同为 0.30x」的严格大于。
比较式是 best - worst > 0.3，不是四舍五入后的文案。
"""
import unittest

from generate_hongniang_full_report import generate_html


def _dept(name, jm_n, pay):
    return {
        "dept_name": name,
        "staff_new": 10,
        "call_worker": 8,
        "on_vip": 20,
        "jm_n": jm_n,
        "jm_all": jm_n,
        "pay_1d_amt": pay,
        "pay_1m_amt": pay,
        "link_time_count": 40,
        "deep_count": 10,
        "love_cnt_m": 0,
        "tousu_n": 0,
        "pay_1d_num": 1,
        "zhenai_back": 0,
    }


def _html(best_jm, worst_jm):
    rows = [
        _dept("深圳红娘一部", best_jm, 20000),
        _dept("厦门红娘一区二部", worst_jm, 10000),
    ]
    return generate_html(rows, [], [], "2026-02-27")


def _card(html):
    idx = html.find("标杆复制：")
    if idx < 0:
        return ""
    return html[idx:idx + 900]


class HongniangJmGapExactEdgeTests(unittest.TestCase):
    def test_exact_point_three_stays_silent_while_summary_prints_0_30(self):
        # 3/10 - 0/10 == 0.3，比较式用 >，卡必须关掉。
        # 汇总仍打印「差距0.30x」，不能把展示文案当成已经开卡。
        html = _html(3, 0)
        self.assertIn("见面安排率 0.30 vs 最低 0.00 — 差距0.30x", html)
        self.assertNotIn("标杆复制：", html)

    def test_float_residue_opens_card_when_summary_still_prints_0_30(self):
        # 13/10 - 10/10 == 0.30000000000000004，展示仍是 1.30 vs 1.00、差距0.30x。
        # 严格大于会开卡。增幅 (2000-1000)*10*0.3 == 3000，执行人是末位经理周美。
        html = _html(13, 10)
        self.assertIn("见面安排率 1.30 vs 最低 1.00 — 差距0.30x", html)
        card = _card(html)
        self.assertIn("标杆复制：深圳红娘一部SOP推广", card)
        self.assertIn("【P1】", card)
        self.assertIn("负责人: 张心蕊+周美", card)
        self.assertIn("厦门红娘一区二部(周美)", card)
        self.assertIn("当前: 差距1.30x vs 1.00x → 目标: 缩小至0.2x", card)
        self.assertIn("坚持: 14天", card)
        self.assertIn("部署日期: 2026-02-28", card)
        self.assertIn("预估增幅: +¥3,000/日", card)
        self.assertIn("《Atomic Habits》", card)
        self.assertNotIn("曹世迪", card)

    def test_rates_that_look_0_30_apart_still_follow_strict_compare(self):
        # 4/10 - 1/10 也是 0.30000000000000004。汇总差距打印 0.30x，但率是 0.40 vs 0.10。
        # 与精确 0.30 vs 0.00 的静默成对，防止先四舍五入再比较。
        html = _html(4, 1)
        self.assertIn("见面安排率 0.40 vs 最低 0.10 — 差距0.30x", html)
        card = _card(html)
        self.assertIn("标杆复制：深圳红娘一部SOP推广", card)
        self.assertIn("当前: 差距0.40x vs 0.10x → 目标: 缩小至0.2x", card)
        self.assertIn("预估增幅: +¥3,000/日", card)
        self.assertIn("厦门红娘一区二部(周美)", card)


if __name__ == "__main__":
    unittest.main()
