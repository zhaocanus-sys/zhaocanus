# -*- coding: utf-8 -*-
"""Regression coverage for remaining shop improvement gates and 四维插值.

Open PR #89 covers sign_rate<30 P0, lead_speed_1d<80 P1, and the money
double-count fix. Open PR #102/#103 cover DoD / why_shop_good / BOTTOM5.
This file locks the leftover improvement-card thresholds and the
four-dimension interpolated KPIs that still drive same-day ops actions.
"""
import re
import unittest

from generate_shop_full_report import generate_html


_INF_NAN = re.compile(r"(?i)(?<![A-Za-z])(inf|nan)(?![A-Za-z])")


def _flat(html: str) -> str:
    return re.sub(r"\s+", "", html)


def _shop(**overrides):
    row = {
        "dept_name": "深圳南山店",
        "level2": "华南",
        "dept_worker_name": "店长甲",
        "area_worker_name": "区经甲",
        "total_realpay": 80000,
        "sale_realpay": 60000,
        "deptsale_realpay": 60000,
        "invite_realpay": 10000,
        "hn_realpay": 10000,
        "total_pay_num": 20,
        "sale_pay_num_all": 15,
        "invite_pay_num": 5,
        "deptsale_shop_num": 16,
        "worker_num_call": 8,
        "call_times": 200,
        "link_num": 80,
        "sg_num": 40,
        "zaigang_rs": 8,
        "refund_money_d": 0,
        "complain_400_num_day": 0,
        "refund_money_m": 0,
        "total_realpay_m": 200000,
        "leads_xyzout_3day": 20,
        "leads_3day_allot_0day": 18,
        "leads_xyzout_1day": 10,
        "leads_1day_allot_0day": 10,
        "allot_worker_num": 8,
    }
    row.update(overrides)
    return row


def _html(rows, prev_rows=None, date_display="2026-02-27"):
    return generate_html(rows, prev_rows or [], date_display)


class ShopInviteConvImprovementTests(unittest.TestCase):
    def test_invite_conv_below_30_emits_p0_with_computed_uplift(self):
        # sign 8/20=40% (skip #89 P0); invite 20/100=20%; avg_deal=80000/20=4000
        html = _html([
            _shop(
                sg_num=20,
                deptsale_shop_num=8,
                link_num=100,
                total_realpay=80000,
                total_pay_num=20,
            ),
        ])
        self.assertIn("接通→到店转化提至30%（当前20.0%）", html)
        self.assertIn("部署: 2026-02-28", html)
        # extra_arr=100*(30-20)/100=10; est=10*0.40*4000=16000
        self.assertIn("预估增幅: +¥16,000/日", html)

    def test_invite_conv_at_30_skips_p0(self):
        html = _html([
            _shop(sg_num=30, deptsale_shop_num=12, link_num=100),
        ])
        self.assertNotIn("接通→到店转化提至30%", html)

    def test_year_end_deploy_date_rolls_to_next_year(self):
        html = _html([
            _shop(sg_num=20, deptsale_shop_num=8, link_num=100),
        ], date_display="2026-12-31")
        self.assertIn("接通→到店转化提至30%", html)
        self.assertIn("部署: 2027-01-01", html)


class ShopRefundImprovementTests(unittest.TestCase):
    def test_refund_above_5_emits_p1_save_to_4pct(self):
        # refund 16000/200000=8%; save=200000*(8-4)/100=8000
        html = _html([
            _shop(total_realpay=200000, refund_money_d=16000, total_pay_num=40),
        ])
        self.assertIn("退费率管控至4%（当前8.0%）", html)
        self.assertIn("预估增幅: +¥8,000/日", html)

    def test_refund_at_5_skips_p1(self):
        html = _html([
            _shop(total_realpay=200000, refund_money_d=10000),
        ])
        self.assertNotIn("退费率管控至4%", html)


class ShopSopCopyImprovementTests(unittest.TestCase):
    def test_sign_rate_gap_over_10_emits_benchmark_copy(self):
        html = _html([
            _shop(
                dept_name="标杆南山",
                sg_num=20,
                deptsale_shop_num=10,
                link_num=40,
                total_realpay=100000,
            ),
            _shop(
                dept_name="尾部宝安",
                sg_num=20,
                deptsale_shop_num=6,
                link_num=40,
                total_realpay=50000,
            ),
        ])
        self.assertIn("标杆复制：标杆南山签单SOP推广", html)
        self.assertIn("尾部宝安今日组织1h话术通关培训", html)

    def test_sign_rate_gap_at_10_skips_benchmark_copy(self):
        html = _html([
            _shop(
                dept_name="标杆南山",
                sg_num=20,
                deptsale_shop_num=8,
                link_num=40,
                total_realpay=100000,
            ),
            _shop(
                dept_name="尾部宝安",
                sg_num=20,
                deptsale_shop_num=6,
                link_num=40,
                total_realpay=50000,
            ),
        ])
        self.assertNotIn("标杆复制：", html)


class ShopImprovementOrderingTests(unittest.TestCase):
    def test_cards_sorted_by_rev_est_not_priority(self):
        # P2 always-on estimate (total_pay*1000) outranks the P0/P1 cards.
        html = _html([
            _shop(
                sg_num=40,
                deptsale_shop_num=10,   # sign 25% → P0 est=2*1250=2500
                link_num=200,           # invite 20% → P0 est=20*0.25*1250=6250
                total_realpay=100000,
                total_pay_num=80,       # P2 est=80000
                refund_money_d=6000,    # refund 6% → P1 est=2000
                leads_xyzout_1day=10,
                leads_1day_allot_0day=10,
            ),
        ])
        p2 = html.find("高客单价产品比例提升")
        invite = html.find("接通→到店转化提至30%")
        sign = html.find("签单率修复至30%")
        refund = html.find("退费率管控至4%")
        self.assertTrue(p2 != -1 and invite != -1 and sign != -1 and refund != -1)
        self.assertLess(p2, invite)
        self.assertLess(invite, sign)
        self.assertLess(sign, refund)

    def test_always_emits_p2_high_ticket_card(self):
        html = _html([_shop()])
        self.assertIn("高客单价产品比例提升（情感护航/超豪VIP）", html)
        self.assertIn("📚《Influence》Cialdini", html)


class ShopFourDimensionTests(unittest.TestCase):
    def test_interpolates_max_min_sign_rate_and_exec_kpis(self):
        html = _html([
            _shop(
                dept_name="标杆南山",
                sg_num=20,
                deptsale_shop_num=10,  # 50%
                link_num=40,
                total_realpay=100000,
                leads_xyzout_1day=10,
                leads_1day_allot_0day=9,
            ),
            _shop(
                dept_name="尾部宝安",
                sg_num=20,
                deptsale_shop_num=6,   # 30%
                link_num=40,
                total_realpay=50000,
                leads_xyzout_1day=0,
                leads_1day_allot_0day=0,
            ),
        ])
        # build_shop_data sign_rate is not double-counted
        self.assertIn("TOP门店签单率50% vs 最低30%", html)
        # agg: lead 9/10=90%; invite 40/80=50%; sign 16/40=40%
        self.assertIn("线索即日分配率（当前90%，目标≥80%）", html)
        self.assertIn("到店邀约成功率（50%，目标≥30%）", html)
        self.assertIn("签单率（40%，目标≥30%）", html)

    def test_empty_payload_four_dimension_is_finite_and_safe(self):
        html = _html([])
        self.assertIn("TOP门店签单率0% vs 最低0%", html)
        self.assertIn("线索即日分配率（当前0%，目标≥80%）", html)
        self.assertNotRegex(_flat(html), _INF_NAN)
        self.assertNotIn("躺平", html)
        self.assertIn("高客单价产品比例提升", html)


if __name__ == "__main__":
    unittest.main()
