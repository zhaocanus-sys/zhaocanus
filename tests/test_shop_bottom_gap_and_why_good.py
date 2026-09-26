# -*- coding: utf-8 -*-
"""门店 TOP 原因与 BOTTOM 管理视角的贴线合同。

全局签单 25/30/35、邀约 20/30、线索 80 已有覆盖。
这里锁的是员工/门店卡上的另一套比较符：为什么好、BOTTOM 问题清单，
以及「签单 < 25 → 退费 > 8 → 邀约 < 20 → 人均」的视角优先级。
"""
import unittest

from generate_shop_full_report import generate_html


def _shop(**overrides):
    row = {
        "dept_name": "深圳门店A",
        "level2": "深圳",
        "dept_worker_name": "店长甲",
        "area_worker_name": "",
        "total_realpay": "10000",
        "sale_realpay": "0",
        "deptsale_realpay": "0",
        "invite_realpay": "0",
        "hn_realpay": "0",
        "total_pay_num": "4",
        "sale_pay_num_all": "0",
        "invite_pay_num": "0",
        "deptsale_shop_num": "1",
        "sg_num": "4",
        "link_num": "20",
        "call_times": "50",
        "zaigang_rs": "1",
        "refund_money_d": "0",
        "complain_400_num_day": "0",
        "leads_xyzout_3day": "0",
        "leads_3day_allot_0day": "0",
        "leads_xyzout_1day": "0",
        "leads_1day_allot_0day": "0",
        "total_realpay_m": "0",
        "deptsale_realpay_m": "0",
        "worker_num_call": "1",
    }
    row.update(overrides)
    return row


def _between(html, start, end):
    return html.split(start, 1)[1].split(end, 1)[0]


def _why(html):
    return _between(html, "TOP5门店深度分析", "TOP5 vs BOTTOM5")


def _bottom(html):
    return _between(html, "BOTTOM5门店专项诊断", "部门级诊断")


def _dept(html):
    return _between(html, "部门级诊断（管理者视角 + 管理视角缺失推断）", "数据→人的转向")


class ShopWhyGoodTests(unittest.TestCase):
    def test_reasons_include_exact_lines_and_zero_complaint_blocks_fallback(self):
        # 7/20 = 35%；20/66 ≈ 30.3%；营收字段按当前聚合进入人均 15000。
        star = generate_html(
            [_shop(
                deptsale_shop_num="7",
                sg_num="20",
                link_num="66",
                total_realpay="7500",
                zaigang_rs="1",
                complain_400_num_day="0",
            )],
            [],
            "2026-02-27",
        )
        reasons = _why(star)
        self.assertIn(
            "签单率35%达优秀线；接通→到店转化效率高；人均产值突出；零投诉高口碑",
            reasons,
        )
        self.assertNotIn("综合表现稳健", reasons)

        quiet = generate_html(
            [_shop(
                deptsale_shop_num="34",
                sg_num="100",
                link_num="400",
                total_realpay="7499",
                zaigang_rs="1",
                complain_400_num_day="0",
            )],
            [],
            "2026-02-27",
        )
        quiet_why = _why(quiet)
        # 签单 34、邀约 25、人均低于 15000，但投诉为 0 仍写出零投诉，不走兜底。
        self.assertIn("零投诉高口碑", quiet_why)
        self.assertNotIn("综合表现稳健", quiet_why)
        self.assertNotIn("达优秀线", quiet_why)
        self.assertNotIn("接通→到店转化效率高", quiet_why)
        self.assertNotIn("人均产值突出", quiet_why)

        noisy = generate_html(
            [_shop(
                deptsale_shop_num="34",
                sg_num="100",
                link_num="400",
                total_realpay="7499",
                zaigang_rs="1",
                complain_400_num_day="1",
            )],
            [],
            "2026-02-27",
        )
        noisy_why = _why(noisy)
        self.assertIn("综合表现稳健", noisy_why)
        self.assertNotIn("零投诉高口碑", noisy_why)
        self.assertNotIn("达优秀线", noisy_why)
        self.assertNotIn("接通→到店转化效率高", noisy_why)
        self.assertNotIn("人均产值突出", noisy_why)


class ShopBottomGapTests(unittest.TestCase):
    def test_sign_below_25_owns_the_gap_even_when_refund_and_invite_are_also_bad(self):
        html = generate_html(
            [_shop(
                deptsale_shop_num="6",
                sg_num="25",
                link_num="200",
                total_realpay="10000",
                total_pay_num="4",
                refund_money_d="5000",
                area_worker_name="",
                dept_worker_name="店长甲",
            )],
            [],
            "2026-02-27",
        )
        bot = _bottom(html)
        # 6/25 = 24%。问题清单可以并列，管理视角只取签单。
        self.assertIn("负责人: 店长甲", bot)
        self.assertIn("签单率仅24.0%，严重低于30%合格线，到店资源大量流失", bot)
        self.assertIn("接通→到店转化12.5%，邀约话术或邀约时机有问题", bot)
        self.assertIn("退费率25.0%，签单话术可能存在过度承诺", bot)
        self.assertIn(
            "管理视角缺失：</strong>邀约质量管控不足，或现场接待SOP缺失，到店客户流失严重",
            bot,
        )
        self.assertNotIn("签单话术存在过度承诺风险，或服务兑现能力与承诺不匹配", bot)
        self.assertNotIn("邀约话术吸引力不足，电话-到店转化效率低于基准30%", bot)
        self.assertNotIn("差异化辅导策略缺失", bot)

        diag = _dept(html)
        self.assertIn("深圳门店A（店长甲）— 签单率 24.0%", diag)
        self.assertIn(
            "管理视角缺失推断：</strong>邀约质量管控不足，或现场接待SOP缺失，到店客户流失严重",
            diag,
        )
        # 全局客单 10000/4 = 2500；达 35% 签单的增量是 25*0.35-6。
        self.assertIn("达均值可+¥6,875/日", diag)

    def test_sign_25_with_refund_over_8_switches_gap_and_invite_20_reaches_per_capita(self):
        refund = generate_html(
            [_shop(
                deptsale_shop_num="1",
                sg_num="4",
                link_num="40",
                total_realpay="10000",
                total_pay_num="4",
                # 诊断使用的营收是该字段的整数与浮点之和，1620/20000 = 8.1%。
                refund_money_d="1620",
            )],
            [],
            "2026-02-27",
        )
        refund_bot = _bottom(refund)
        self.assertIn("退费率8.1%，签单话术可能存在过度承诺", refund_bot)
        self.assertIn("接通→到店转化10.0%，邀约话术或邀约时机有问题", refund_bot)
        self.assertNotIn("签单率仅", refund_bot)
        self.assertIn(
            "管理视角缺失：</strong>签单话术存在过度承诺风险，或服务兑现能力与承诺不匹配",
            refund_bot,
        )
        self.assertNotIn("邀约质量管控不足", refund_bot)
        self.assertNotIn("邀约话术吸引力不足", refund_bot)
        refund_diag = _dept(refund)
        self.assertIn("签单率 25.0%", refund_diag)
        self.assertIn(
            "管理视角缺失推断：</strong>签单话术存在过度承诺风险，或服务兑现能力与承诺不匹配",
            refund_diag,
        )
        self.assertNotIn("邀约质量管控不足", refund_diag)
        # 2500 * (4*0.35 - 1) = 1000。
        self.assertIn("达均值可+¥1,000/日", refund_diag)

        invite = generate_html(
            [_shop(
                deptsale_shop_num="1",
                sg_num="4",
                link_num="21",
                total_realpay="10000",
                refund_money_d="1600",
            )],
            [],
            "2026-02-27",
        )
        invite_bot = _bottom(invite)
        # 1600/20000 = 8.0% 不触发退费；4/21 ≈ 19.0% 仍低于 20。
        self.assertIn("接通→到店转化19.0%，邀约话术或邀约时机有问题", invite_bot)
        self.assertNotIn("签单率仅", invite_bot)
        self.assertNotIn("退费率", invite_bot)
        self.assertIn(
            "管理视角缺失：</strong>邀约话术吸引力不足，电话-到店转化效率低于基准30%",
            invite_bot,
        )
        self.assertNotIn("签单话术存在过度承诺风险", invite_bot)
        self.assertNotIn("差异化辅导策略缺失", invite_bot)

        settled = generate_html(
            [_shop(
                deptsale_shop_num="1",
                sg_num="4",
                link_num="20",
                total_realpay="10000",
                refund_money_d="1600",
                complain_400_num_day="0",
            )],
            [],
            "2026-02-27",
        )
        settled_bot = _bottom(settled)
        # 签单 25、退费 8.0、邀约 20：三条问题都不写，视角落到人均。
        self.assertIn("综合指标偏弱，需全面诊断门店运营机制", settled_bot)
        self.assertNotIn("签单率仅", settled_bot)
        self.assertNotIn("接通→到店转化", settled_bot)
        self.assertNotIn("退费率", settled_bot)
        self.assertNotIn("当日投诉", settled_bot)
        self.assertIn(
            "管理视角缺失：</strong>差异化辅导策略缺失，TOP销售SOP未标准化推广",
            settled_bot,
        )

        complained = generate_html(
            [_shop(
                deptsale_shop_num="1",
                sg_num="4",
                link_num="20",
                total_realpay="10000",
                refund_money_d="1600",
                complain_400_num_day="1",
            )],
            [],
            "2026-02-27",
        )
        complained_bot = _bottom(complained)
        self.assertIn("当日投诉1单，客户体验存在系统性问题", complained_bot)
        self.assertNotIn("综合指标偏弱", complained_bot)
        # 投诉写入问题清单，但不改签单→退费→邀约→人均的视角链。
        self.assertIn(
            "管理视角缺失：</strong>差异化辅导策略缺失，TOP销售SOP未标准化推广",
            complained_bot,
        )

    def test_best_sign_rate_shop_is_left_out_of_worst3(self):
        html = generate_html(
            [
                _shop(dept_name="旗舰店", area_worker_name="区长优",
                      deptsale_shop_num="5", sg_num="10", link_num="20",
                      total_realpay="80000"),
                _shop(dept_name="弱店甲", area_worker_name="店长甲",
                      deptsale_shop_num="6", sg_num="25", link_num="100",
                      total_realpay="10000"),
                _shop(dept_name="弱店乙", area_worker_name="店长乙",
                      deptsale_shop_num="1", sg_num="4", link_num="20",
                      total_realpay="10000"),
                _shop(dept_name="弱店丙", area_worker_name="店长丙",
                      deptsale_shop_num="3", sg_num="10", link_num="20",
                      total_realpay="10000"),
            ],
            [],
            "2026-02-27",
        )
        diag = _dept(html)
        self.assertIn("弱店甲（店长甲）", diag)
        self.assertIn("弱店乙（店长乙）", diag)
        self.assertIn("弱店丙（店长丙）", diag)
        self.assertNotIn("旗舰店", diag)
        self.assertNotIn("区长优", diag)
        self.assertEqual(diag.count("部门预警"), 3)
