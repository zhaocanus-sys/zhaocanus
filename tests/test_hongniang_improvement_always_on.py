# -*- coding: utf-8 -*-
"""Regression coverage for Hongniang always-on improvement cards.

Open PR #90 covers P0 见面安排率 / 退费率 gates. Open PR #91 covers
标杆复制 P1 when jm_rate gap > 0.3. This file locks the leftover
always-on cards, computed 预估增幅, TOP1 name interpolation, year-end
deploy, and sort-by-rev_est — the paths that still decide same-day
action priority when P0 cards are silent.
"""
import unittest

from generate_hongniang_full_report import generate_html


def _dept(**overrides):
    row = {
        "dept_name": "深圳红娘一部",
        "staff_new": 10,
        "call_worker": 8,
        "on_vip": 40,
        "jm_n": 10,
        "jm_all": 12,
        "pay_1d_amt": 100000,
        "pay_1m_amt": 300000,
        "link_time_count": 80,
        "deep_count": 20,
        "love_cnt_m": 2,
        "tousu_n": 0,
        "pay_1d_num": 4,
        "zhenai_back": 0,
        "zhenaigd_back": 0,
        "zhenai_hz_back": 0,
        "zhenai_xfh_back": 0,
        "zhenai_md_back": 0,
    }
    row.update(overrides)
    return row


def _hourly(**overrides):
    row = {
        "worker_name": "标杆红娘甲",
        "dept_name": "深圳红娘一部",
        "jm_n": 3,
        "jm_all": 3,
        "on_vip": 8,
        "off_vip": 0,
        "link_time_count": 20,
        "jianmian_cs": 3,
        "jianmian_rs": 3,
        "jianmiangd_cs": 2,
        "jianmiangd_rs": 2,
        "love_cnt_m": 1,
        "tousu_n": 0,
        "online_pay_m": 8000,
        "xml_pay_m": 0,
        "offline_pay_m": 2000,
        "zhenai_back": 0,
        "zhenaigd_back": 0,
    }
    row.update(overrides)
    return row


def _html(rows, hourly=None, date_display="2026-02-27"):
    return generate_html(rows, [], hourly if hourly is not None else [], date_display)


def _card_chunk(html, title, width=700):
    idx = html.find(title)
    if idx < 0:
        return ""
    return html[idx:idx + width]


class HongniangAlwaysOnImprovementTests(unittest.TestCase):
    def test_always_emits_social_top5_and_vip_cards_with_computed_uplift(self):
        # jm_rate=10/10=1.0 and refund=0 → skip #90 P0s; no SOP-copy pair.
        # social = 10 * 0.2 * (100000 / 10) = 20,000
        # top5  = 100000 * 0.08 = 8,000
        # vip   = 100000 * 0.05 = 5,000
        html = _html([_dept()])
        self.assertNotIn("见面安排率修复至1.0", html)
        self.assertNotIn("退费率管控至4.5%", html)
        self.assertNotIn("标杆复制：", html)

        social = _card_chunk(html, "社会认同话术植入（见面率+0.2）")
        top5 = _card_chunk(html, "TOP5标杆员工晨会分享机制")
        vip = _card_chunk(html, "VIP存量盘活（NPS+留存）")
        self.assertIn("预估增幅: +¥20,000/日", social)
        self.assertIn("📚《Influence》Cialdini", social)
        self.assertIn("预估增幅: +¥8,000/日", top5)
        self.assertIn("预估增幅: +¥5,000/日", vip)
        self.assertIn("在线VIP40个", vip)
        self.assertIn("部署日期: 2026-02-28", social)
        self.assertIn("坚持: 7天", social)

    def test_top1_worker_name_interpolated_else_pending(self):
        named = _html([_dept()], hourly=[_hourly(worker_name="标杆红娘甲")])
        self.assertIn("综合评分TOP1员工(标杆红娘甲)", named)

        pending = _html([_dept()], hourly=[])
        self.assertIn("综合评分TOP1员工(待定)", pending)

    def test_year_end_deploy_date_rolls_to_next_year(self):
        html = _html([_dept()], date_display="2026-12-31")
        self.assertIn("部署日期: 2027-01-01", html)
        self.assertNotIn("部署日期: 2026-12-32", html)

    def test_cards_sorted_by_rev_est_so_p2_can_outrank_a_p1(self):
        # jm_n=100 keeps social small: 10*0.2*(100000/100)=2,000
        # TOP5 P1 = 8,000; VIP P2 = 5,000 → P2 outranks the social P1.
        html = _html([_dept(jm_n=100)])
        top5 = html.find("TOP5标杆员工晨会分享机制")
        vip = html.find("VIP存量盘活（NPS+留存）")
        social = html.find("社会认同话术植入（见面率+0.2）")
        self.assertTrue(top5 != -1 and vip != -1 and social != -1)
        self.assertLess(top5, vip)
        self.assertLess(vip, social)

    def test_zero_revenue_keeps_always_on_estimates_finite(self):
        html = _html([_dept(pay_1d_amt=0, jm_n=0, staff_new=8, on_vip=12)])
        social = _card_chunk(html, "社会认同话术植入（见面率+0.2）")
        top5 = _card_chunk(html, "TOP5标杆员工晨会分享机制")
        vip = _card_chunk(html, "VIP存量盘活（NPS+留存）")
        self.assertIn("预估增幅: +¥0/日", social)
        self.assertIn("预估增幅: +¥0/日", top5)
        self.assertIn("预估增幅: +¥0/日", vip)
        self.assertIn("在线VIP12个", vip)
        self.assertNotRegex(social + top5 + vip, r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


if __name__ == "__main__":
    unittest.main()
