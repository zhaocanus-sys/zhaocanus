# -*- coding: utf-8 -*-
"""Regression coverage for shop lead freshness, revenue fallback, and diagnosis gates."""
import math
import unittest

from generate_shop_full_report import (
    MGMT_GAP_RULES,
    agg_shop,
    build_shop_data,
    generate_html,
)


def _finite(value):
    return math.isfinite(float(value))


class ShopLeadAndSaleRevTests(unittest.TestCase):
    def test_agg_shop_lead_speed_and_sale_rev_fallback(self):
        """Lead allotment rates and sale_rev fallback must stay finite and correct."""
        with_sale = agg_shop([
            {
                "total_realpay": "10000",
                "sale_realpay": "7000",
                "deptsale_realpay": "9999",
                "leads_xyzout_3day": "10",
                "leads_3day_allot_0day": "8",
                "leads_xyzout_1day": "5",
                "leads_1day_allot_0day": "4",
                "sg_num": "10",
                "deptsale_shop_num": "3",
                "link_num": "20",
                "zaigang_rs": "2",
                "total_pay_num": "3",
            }
        ])
        self.assertEqual(with_sale["sale_rev"], 7000.0)
        self.assertAlmostEqual(with_sale["lead_speed_3d"], 80.0)
        self.assertAlmostEqual(with_sale["lead_speed_1d"], 80.0)
        self.assertTrue(_finite(with_sale["lead_speed_1d"]))

        fallback = agg_shop([
            {
                "total_realpay": "5000",
                "deptsale_realpay": "3200",
                "leads_xyzout_3day": "0",
                "leads_3day_allot_0day": "9",
                "leads_xyzout_1day": "0",
                "leads_1day_allot_0day": "4",
            }
        ])
        self.assertEqual(fallback["sale_rev"], 3200.0)
        self.assertEqual(fallback["lead_speed_3d"], 0)
        self.assertEqual(fallback["lead_speed_1d"], 0)
        self.assertTrue(_finite(fallback["lead_speed_1d"]))

    def test_build_shop_data_does_not_double_count_money_fields(self):
        rows = [
            {
                "dept_name": "深圳门店A",
                "level2": "深圳",
                "dept_worker_name": "店长A",
                "area_worker_name": "区长A",
                "total_realpay": "1000.50",
                "deptsale_realpay": "700.25",
                "invite_realpay": "100.00",
                "hn_realpay": "200.25",
                "total_pay_num": "2",
                "deptsale_shop_num": "1",
                "sg_num": "4",
                "link_num": "8",
                "call_times": "20",
                "zaigang_rs": "2",
                "refund_money_d": "50.00",
                "total_realpay_m": "3000.75",
                "deptsale_realpay_m": "2000.50",
            },
            {
                "dept_name": "深圳门店A",
                "total_realpay": "2000.25",
                "deptsale_realpay": "1500.75",
                "invite_realpay": "200.00",
                "hn_realpay": "300.25",
                "total_pay_num": "3",
                "deptsale_shop_num": "2",
                "sg_num": "6",
                "link_num": "12",
                "call_times": "30",
                "zaigang_rs": "3",
                "refundmoney_7d": "25.00",
                "total_realpay_m": "4000.25",
                "deptsale_realpay_m": "2500.50",
            },
        ]
        shop = build_shop_data(rows)[0]
        self.assertAlmostEqual(shop["total_realpay"], 3000.75)
        self.assertAlmostEqual(shop["hn_realpay"], 500.50)
        self.assertAlmostEqual(shop["refund_money_d"], 75.00)
        self.assertEqual(shop["total_pay_num"], 5)
        self.assertAlmostEqual(shop["sign_rate"], 30.0)
        self.assertAlmostEqual(shop["refund_rate"], 75.0 / 3000.75 * 100)


class ShopDiagnosisAndImprovementTests(unittest.TestCase):
    def _weak_shop_rows(self):
        """Two shops: one strong, one weak — triggers P0/P1 and mgmt-gap diagnosis."""
        return [
            {
                "dept_name": "标杆门店",
                "area_worker_name": "区长强",
                "dept_worker_name": "店长强",
                "total_realpay": "50000",
                "deptsale_realpay": "40000",
                "sale_realpay": "40000",
                "invite_realpay": "5000",
                "hn_realpay": "5000",
                "total_pay_num": "10",
                "sale_pay_num_all": "8",
                "invite_pay_num": "2",
                "deptsale_shop_num": "8",
                "sg_num": "20",
                "link_num": "40",
                "call_times": "100",
                "zaigang_rs": "4",
                "refund_money_d": "500",
                "complain_400_num_day": "0",
                "leads_xyzout_3day": "20",
                "leads_3day_allot_0day": "18",
                "leads_xyzout_1day": "10",
                "leads_1day_allot_0day": "5",
                "total_realpay_m": "200000",
                "deptsale_realpay_m": "150000",
            },
            {
                "dept_name": "弱势门店",
                "area_worker_name": "区长弱",
                "dept_worker_name": "店长弱",
                "total_realpay": "8000",
                "deptsale_realpay": "6000",
                "sale_realpay": "6000",
                "invite_realpay": "1000",
                "hn_realpay": "1000",
                "total_pay_num": "2",
                "sale_pay_num_all": "1",
                "invite_pay_num": "1",
                "deptsale_shop_num": "1",
                "sg_num": "20",
                "link_num": "50",
                "call_times": "80",
                "zaigang_rs": "5",
                "refund_money_d": "1200",
                "complain_400_num_day": "1",
                "leads_xyzout_3day": "15",
                "leads_3day_allot_0day": "6",
                "leads_xyzout_1day": "8",
                "leads_1day_allot_0day": "2",
                "total_realpay_m": "40000",
                "deptsale_realpay_m": "30000",
            },
        ]

    def test_html_emits_mgmt_gap_owner_and_timed_improvements(self):
        rows = self._weak_shop_rows()
        html = generate_html(rows, rows, "2026-02-27")

        # Department-scoped diagnosis must name the manager and mgmt-gap rule text.
        self.assertIn("弱势门店", html)
        self.assertIn("区长弱", html)
        self.assertIn(MGMT_GAP_RULES["low_sign_rate"], html)

        # Time-dimension deploy date = report day + 1.
        self.assertIn("部署: 2026-02-28", html)

        # Aggregate sign_rate = 9/40 = 22.5% → P0 sign-rate fix.
        self.assertIn("签单率修复至30%", html)
        self.assertIn("【P0】", html)

        # Aggregate lead_speed_1d = 7/18 ≈ 38.9% → P1 lead allotment action.
        self.assertIn("当日线索当日分配率提至80%", html)
        self.assertIn("【P1】", html)

        # Invite conversion = 40/90 ≈ 44.4% (≥30) should NOT emit invite P0.
        self.assertNotIn("接通→到店转化提至30%", html)

    def test_healthy_lead_speed_skips_allotment_improvement(self):
        rows = [
            {
                "dept_name": "健康门店",
                "area_worker_name": "区长健",
                "total_realpay": "100000",
                "sale_realpay": "80000",
                "deptsale_realpay": "80000",
                "total_pay_num": "20",
                "deptsale_shop_num": "12",
                "sg_num": "30",
                "link_num": "60",
                "zaigang_rs": "5",
                "refund_money_d": "100",
                "leads_xyzout_1day": "10",
                "leads_1day_allot_0day": "9",
                "leads_xyzout_3day": "20",
                "leads_3day_allot_0day": "18",
                "total_realpay_m": "300000",
            }
        ]
        html = generate_html(rows, [], "2026-03-01")
        self.assertNotIn("当日线索当日分配率提至80%", html)
        # Sign rate 40% ≥ 30 → no P0 sign-rate card.
        self.assertNotIn("签单率修复至30%", html)
        self.assertIn("部署: 2026-03-02", html)


if __name__ == "__main__":
    unittest.main()
