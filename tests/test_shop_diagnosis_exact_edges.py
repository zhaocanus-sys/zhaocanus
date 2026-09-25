# -*- coding: utf-8 -*-
"""Exact inclusive/exclusive edges for shop global diagnosis and funnel switch.

Interior bands (20% / 28% / 40% sign, 12.5% / 25% / 50% invite, 30% / 90% lead)
are already locked. These cases pin the thresholds managers act on:
sign 25 / 30 / 35, invite 20 / 30, and same-day lead allotment 80.
"""
import unittest

from generate_shop_full_report import generate_html


def _shop_row(**overrides):
    row = {
        "dept_name": "深圳门店A",
        "level2": "深圳",
        "dept_worker_name": "店长A",
        "area_worker_name": "区长A",
        "total_realpay": "20000",
        "sale_realpay": "15000",
        "deptsale_realpay": "15000",
        "invite_realpay": "3000",
        "hn_realpay": "2000",
        "total_pay_num": "4",
        "sale_pay_num_all": "3",
        "invite_pay_num": "1",
        "deptsale_shop_num": "4",
        "sg_num": "10",
        "link_num": "20",
        "call_times": "50",
        "zaigang_rs": "2",
        "refund_money_d": "200",
        "complain_400_num_day": "0",
        "leads_xyzout_3day": "10",
        "leads_3day_allot_0day": "9",
        "leads_xyzout_1day": "10",
        "leads_1day_allot_0day": "8",
        "total_realpay_m": "80000",
        "deptsale_realpay_m": "60000",
        "worker_num_call": "2",
    }
    row.update(overrides)
    return row


def _html(**overrides):
    return generate_html([_shop_row(**overrides)], [], "2026-02-27")


def _sign_block(html):
    return html.split("全局诊断", 1)[1].split("接通→到店转化", 1)[0]


def _invite_block(html):
    return html.split("接通→到店转化", 1)[1].split("退费率", 1)[0]


class ShopSignRateExactEdges(unittest.TestCase):
    def test_sign_rate_24_is_crisis_and_25_stays_qualified_warning(self):
        crisis = _html(deptsale_shop_num="6", sg_num="25", link_num="50")
        # 6/25 = 24.0% < 25 → 现场接待失效，签单漏斗芯片为红。
        self.assertIn("🚨 低于25%，现场接待严重失效", crisis)
        self.assertIn("border-left:3px solid #dc2626", _sign_block(crisis))
        self.assertIn("签单6(24%)", crisis)

        line = _html(deptsale_shop_num="1", sg_num="4", link_num="10")
        # 1/4 = 25.0%。比较符是 <25，贴线仍是合格线预警，不是失效。
        block = _sign_block(line)
        self.assertIn("到店签单率 25.0%", line)
        self.assertIn("⚠ 低于30%合格线，需强化现场签单能力", block)
        self.assertNotIn("🚨 低于25%", block)
        self.assertIn("border-left:3px solid #d97706", block)
        self.assertNotIn("border-left:3px solid #dc2626", block)
        self.assertIn("签单率修复至30%（当前25.0%）", line)
        self.assertIn("签单1(25%)", line)

    def test_sign_rate_30_is_met_and_35_is_excellent(self):
        met = _html(deptsale_shop_num="3", sg_num="10", link_num="20")
        # 3/10 = 30.0%。<30 才预警；贴线改为达标，且不再出签单修复卡。
        block = _sign_block(met)
        self.assertIn("到店签单率 30.0%", met)
        self.assertIn("✅ 签单率达标", block)
        self.assertNotIn("⚠ 低于30%合格线", block)
        self.assertNotIn("⭐ 签单率优秀", block)
        self.assertIn("border-left:3px solid #16a34a", block)
        self.assertNotIn("签单率修复至30%", met)

        star = _html(deptsale_shop_num="7", sg_num="20", link_num="40")
        # 7/20 = 35.0% 含等号进入优秀档。
        star_block = _sign_block(star)
        self.assertIn("到店签单率 35.0%", star)
        self.assertIn("⭐ 签单率优秀≥35%", star_block)
        self.assertNotIn("✅ 签单率达标", star_block)
        self.assertNotIn("签单率修复至30%", star)


class ShopInviteAndLeadExactEdges(unittest.TestCase):
    def test_invite_20_is_warning_and_chip_turns_red_only_below(self):
        below = _html(sg_num="1", link_num="6", deptsale_shop_num="1")
        # 1/6 ≈ 16.7% < 20 → 重建话术，到店芯片带红点。
        self.assertIn("🚨 严重偏低，邀约话术或邀约时机需根本性重建", below)
        self.assertIn("🔴 到店1(17%)", below)

        line = _html(sg_num="1", link_num="5", deptsale_shop_num="1")
        # 1/5 = 20.0%。<20 才升级；贴线保持基准预警，芯片去掉红点。
        block = _invite_block(line)
        self.assertIn("接通→到店转化 20.0%", line)
        self.assertIn("⚠ 低于30%基准，邀约话术需优化", block)
        self.assertNotIn("🚨 严重偏低", block)
        self.assertIn("到店1(20%)", line)
        self.assertNotIn("🔴 到店", line)
        self.assertIn("接通→到店转化提至30%（当前20.0%）", line)

    def test_invite_30_switches_bottleneck_and_leverage_formula(self):
        below = _html(
            sg_num="119",
            link_num="400",
            deptsale_shop_num="30",
            total_realpay="20000",
            total_pay_num="4",
        )
        # 119/400 = 29.75% 仍走邀约瓶颈；杠杆按到店增量估算。
        self.assertIn("最大瓶颈：邀约→到店转化", below)
        self.assertNotIn("最大瓶颈：到店→签单转化", below)
        self.assertIn("接通→到店29.8%，低于30%基准", below)
        self.assertIn("到店率每+5pp，新增到店20人→按25.0%签单率增签5单→+¥25210", below)
        self.assertIn("接通→到店转化提至30%（当前29.8%）", below)

        line = _html(
            sg_num="120",
            link_num="400",
            deptsale_shop_num="30",
            total_realpay="20000",
            total_pay_num="4",
        )
        # 120/400 = 30.0% 且签单 30/120 = 25%。贴线改判到店→签单，杠杆改为签单增量。
        self.assertIn("接通→到店转化 30.0%", line)
        self.assertIn("✅ 邀约转化达标", _invite_block(line))
        self.assertNotIn("⚠ 低于30%基准", _invite_block(line))
        self.assertIn("最大瓶颈：到店→签单转化", line)
        self.assertNotIn("最大瓶颈：邀约→到店转化", line)
        self.assertIn("签单率25.0%，低于30%合格线", line)
        self.assertIn("签单率每+5pp，新增签单6单→+¥30000", line)
        self.assertNotIn("接通→到店转化提至30%", line)
        self.assertNotIn("到店率每+5pp", line)

    def test_lead_speed_80_is_on_time_and_79_still_warns(self):
        on_time = _html(
            leads_xyzout_1day="10",
            leads_1day_allot_0day="8",
            deptsale_shop_num="3",
            sg_num="10",
            link_num="20",
        )
        # 8/10 = 80%。比较符是 >=80。
        self.assertIn("线索即日分配率 80%", on_time)
        self.assertIn("线索分配及时性良好", on_time)
        self.assertNotIn("⚠ 未达80%", on_time)
        self.assertNotIn("当日线索当日分配率提至80%", on_time)

        late = _html(
            leads_xyzout_1day="100",
            leads_1day_allot_0day="79",
            deptsale_shop_num="3",
            sg_num="10",
            link_num="20",
        )
        # 79/100 = 79% 仍出流失预警和分配改善卡。
        self.assertIn("线索即日分配率 79%", late)
        self.assertIn("⚠ 未达80%，当日线索流失，越新鲜转化率越高", late)
        self.assertNotIn("线索分配及时性良好", late)
        self.assertIn("当日线索当日分配率提至80%（当前79%）", late)
        self.assertIn("当日线索100条，已分配79条(79%)", late)


if __name__ == "__main__":
    unittest.main()
