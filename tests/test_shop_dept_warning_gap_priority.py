# -*- coding: utf-8 -*-
"""Regression coverage for shop department-warning MGMT_GAP priority.

Open PR #103 covers BOTTOM5 issue bands + BOTTOM5 MGMT_GAP
(low_sign / high_refund / low_invite / low_per_rev).
Open PR #105 covers remaining improvement-card thresholds.
This file locks the *department预警* chain on main, which is different:

    sign_rate < 25 → low_sign_rate
    else refund_rate > 8 → high_refund
    else low_invite_conv   # no low_per_rev fallback

plus worst-3 by sign_rate and computed 「达均值」 uplift.
"""
import re
import unittest

from generate_shop_full_report import MGMT_GAP_RULES, generate_html


def _shop(**overrides):
    row = {
        "dept_name": "深圳南山店",
        "level2": "华南",
        "dept_worker_name": "店长甲",
        "area_worker_name": "区经甲",
        "total_realpay": 40000,
        "sale_realpay": 30000,
        "deptsale_realpay": 30000,
        "invite_realpay": 5000,
        "hn_realpay": 5000,
        "total_pay_num": 10,
        "sale_pay_num_all": 8,
        "invite_pay_num": 2,
        "deptsale_shop_num": 8,
        "worker_num_call": 6,
        "call_times": 80,
        "link_num": 20,
        "sg_num": 20,
        "zaigang_rs": 6,
        "refund_money_d": 0,
        "complain_400_num_day": 0,
        "refund_money_m": 0,
        "total_realpay_m": 120000,
        "leads_xyzout_3day": 10,
        "leads_3day_allot_0day": 10,
        "leads_xyzout_1day": 6,
        "leads_1day_allot_0day": 6,
        "allot_worker_num": 6,
    }
    row.update(overrides)
    return row


def _html(rows, date_display="2026-02-27"):
    return generate_html(rows, [], date_display)


def _dept_diag(html):
    start = html.find("部门级诊断")
    end = html.find("数据→人的转向")
    if start < 0 or end <= start:
        raise AssertionError("department diagnosis section missing")
    return html[start:end]


def _warning_headers(html):
    return re.findall(r"部门预警</span>\s*<span[^>]*>([^<]+)", _dept_diag(html))


class ShopDeptWarningGapPriorityTests(unittest.TestCase):
    def test_worst3_priority_chain_and_computed_uplift(self):
        # 4 shops so BOTTOM5 stays empty (len<5); isolation from PR #103 cards.
        html = _html([
            _shop(dept_name="低签店", area_worker_name="区经低签",
                  deptsale_shop_num=4, sg_num=20, refund_money_d=0),   # 20%
            _shop(dept_name="高退店", area_worker_name="区经高退",
                  deptsale_shop_num=6, sg_num=20, refund_money_d=8000), # 30%, refund 10% after double-count
            _shop(dept_name="健康签店", area_worker_name="区经健康",
                  deptsale_shop_num=8, sg_num=20, refund_money_d=0),   # 40%
            _shop(dept_name="高签店", area_worker_name="区经高签",
                  deptsale_shop_num=16, sg_num=20, refund_money_d=0),  # 80% excluded
        ])
        headers = _warning_headers(html)
        self.assertEqual(3, len(headers))
        self.assertTrue(any("低签店（区经低签）— 签单率 20.0%" in h for h in headers))
        self.assertTrue(any("高退店（区经高退）— 签单率 30.0%" in h for h in headers))
        self.assertTrue(any("健康签店（区经健康）— 签单率 40.0%" in h for h in headers))
        self.assertFalse(any("高签店" in h for h in headers))

        diag = _dept_diag(html)
        self.assertIn(MGMT_GAP_RULES["low_sign_rate"], diag)
        self.assertIn(MGMT_GAP_RULES["high_refund"], diag)
        self.assertIn(MGMT_GAP_RULES["low_invite_conv"], diag)
        self.assertNotIn(MGMT_GAP_RULES["low_per_rev"], diag)
        # avg_deal = 160000/40 = 4000; 低签: 4000*(20*0.35-4)=12000
        self.assertIn("达均值可+¥12,000/日", diag)

    def test_sign_at_25_and_refund_above_8_uses_high_refund(self):
        html = _html([
            _shop(dept_name="边界退店", area_worker_name="区经边界",
                  deptsale_shop_num=5, sg_num=20, refund_money_d=8000),  # 25%, refund 10%
            _shop(dept_name="对照甲", deptsale_shop_num=10, sg_num=20),
            _shop(dept_name="对照乙", deptsale_shop_num=12, sg_num=20),
        ])
        diag = _dept_diag(html)
        self.assertIn("边界退店（区经边界）— 签单率 25.0%", diag)
        self.assertIn(MGMT_GAP_RULES["high_refund"], diag)
        self.assertNotIn(MGMT_GAP_RULES["low_sign_rate"], diag)

    def test_sign_at_25_and_refund_at_8_falls_to_invite_gap(self):
        # refund_rate = refund_d / (total_realpay * 2) * 100; 6400/80000 = 8.0
        html = _html([
            _shop(dept_name="边界邀约店", area_worker_name="区经邀约",
                  deptsale_shop_num=5, sg_num=20, refund_money_d=6400),
            _shop(dept_name="对照甲", deptsale_shop_num=10, sg_num=20),
            _shop(dept_name="对照乙", deptsale_shop_num=12, sg_num=20),
        ])
        diag = _dept_diag(html)
        self.assertIn("边界邀约店（区经邀约）— 签单率 25.0%", diag)
        self.assertIn(MGMT_GAP_RULES["low_invite_conv"], diag)
        self.assertNotIn(MGMT_GAP_RULES["low_sign_rate"], diag)
        self.assertNotIn(MGMT_GAP_RULES["high_refund"], diag)
        self.assertNotIn(MGMT_GAP_RULES["low_per_rev"], diag)


if __name__ == "__main__":
    unittest.main()
