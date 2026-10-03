# -*- coding: utf-8 -*-
"""APP 全量报告产品「为什么好」与尾部品类诊断的贴线。

现有用例用 20%、4%、2%、0.4% 这类远离门槛的占比，证明文案分支存在。
这里锁的是比较符本身：占比 >15 才叫健康，金额 >50000 才叫可观，
尾部 <1 才叫极低、<3 才叫偏低。展示保留 1 位小数后，15.0001% 与 15.0%、
2.999% 与 3.0%、0.999% 与 1.0% 会印成同一个数字，诊断不能跟着舍入升级。
珍心会员即使又小又不到 5 万，仍然先走核心引擎，不掉进金额或占比兜底。
"""
import unittest

from generate_app_full_report import generate_html


def _row(**overrides):
    row = {
        "amt": "1000000",
        "pay_num": "200",
        "active_members": "10000",
        "refund_money": "1000",
        "pay_num_new": "10",
        "retain_1d": "500",
        "retain_7d": "200",
        "order_cnt": "100",
        "order_pay": "80",
        "mems": "1000",
        "zhenxin_member": "0",
        "super_member_full": "0",
        "live_guard": "0",
        "super_member_plus": "0",
        "zhenai_coin": "0",
        "super_remind": "0",
        "star_privilege": "0",
        "super_recommend": "0",
        "other": "0",
    }
    row.update(overrides)
    return row


def _html(**overrides):
    return generate_html([_row(**overrides)], [], [], "2026-02-27")


def _top_row(html, name):
    """TOP 表里该产品名称所在行（金额、占比、为什么好）。"""
    return html.split(f">{name}</td>", 1)[1].split("</tr>", 1)[0]


def _bottom_card(html, name):
    return html.split(f"⚠ {name} ·", 1)[1].split("即日行动", 1)[0]


class ProductWhyGoodExactEdgesTests(unittest.TestCase):
    def test_share_and_amount_lines_do_not_follow_rounded_labels(self):
        html = _html(
            amt="1000000",
            zhenxin_member="400000",
            super_member_full="150001",
            live_guard="150000",
            super_member_plus="50001",
            zhenai_coin="50000",
            super_remind="1000",
            star_privilege="500",
            super_recommend="100",
            other="50",
        )

        # 150001/1000000 = 15.0001%，印成 15.0%，仍高于 15，优先于金额档。
        just_over = _top_row(html, "超级会员全")
        self.assertIn("15.0%", just_over)
        self.assertIn("占比健康，用户主动购买意愿强", just_over)
        self.assertNotIn("绝对金额可观", just_over)
        self.assertNotIn("具备增长潜力", just_over)

        # 150000/1000000 = 15.0%，同样印成 15.0%，但 >15 不成立，落到金额档。
        at_share = _top_row(html, "直播守护")
        self.assertIn("15.0%", at_share)
        self.assertIn("¥15.0万", at_share)
        self.assertIn("绝对金额可观，值得专项运营", at_share)
        self.assertNotIn("占比健康", at_share)
        self.assertNotIn("具备增长潜力", at_share)

        # 50001 印成 ¥5.0万且占比 5.0%，金额刚过 50000，不要求占比过 15。
        just_over_amt = _top_row(html, "超级会员+")
        self.assertIn("¥5.0万", just_over_amt)
        self.assertIn("5.0%", just_over_amt)
        self.assertIn("绝对金额可观，值得专项运营", just_over_amt)
        self.assertNotIn("占比健康", just_over_amt)
        self.assertNotIn("具备增长潜力", just_over_amt)

        # 50000 印成同一个 ¥5.0万 / 5.0%，等于 50000 不再叫可观。
        at_amt = _top_row(html, "珍爱币")
        self.assertIn("¥5.0万", at_amt)
        self.assertIn("5.0%", at_amt)
        self.assertIn("具备增长潜力", at_amt)
        self.assertNotIn("绝对金额可观", at_amt)
        self.assertNotIn("占比健康", at_amt)

    def test_zhenxin_stays_core_engine_below_share_and_amount_lines(self):
        html = _html(
            amt="1000000",
            zhenxin_member="40000",
            super_member_full="30000",
            live_guard="20000",
            super_member_plus="10000",
            zhenai_coin="5000",
        )
        reason = _top_row(html, "珍心会员")
        self.assertIn("4.0%", reason)
        self.assertIn("¥4.0万", reason)
        self.assertIn("核心收入引擎，用户首选付费路径", reason)
        self.assertNotIn("占比健康", reason)
        self.assertNotIn("绝对金额可观", reason)
        self.assertNotIn("具备增长潜力", reason)


class ProductBottomShareExactEdgesTests(unittest.TestCase):
    def test_one_and_three_percent_lines_do_not_follow_rounded_labels(self):
        html = _html(
            amt="100000",
            zhenxin_member="40000",
            super_member_full="20000",
            live_guard="10000",
            super_member_plus="8000",
            zhenai_coin="3000",
            super_remind="2999",
            star_privilege="1000",
            super_recommend="999",
            other="100",
        )

        # 3000/100000 = 3.0%。比较符是 <3，贴线进入「有一定基础」。
        at_three = _bottom_card(html, "珍爱币")
        self.assertIn("占比3.0%", at_three)
        self.assertIn("有一定基础，但增长潜力未释放", at_three)
        self.assertNotIn("占比偏低", at_three)
        self.assertNotIn("占比极低", at_three)

        # 2999/100000 = 2.999%，印成 3.0%，仍低于 3。
        just_under_three = _bottom_card(html, "超级提醒")
        self.assertIn("占比3.0%", just_under_three)
        self.assertIn("占比偏低，激活场景单一", just_under_three)
        self.assertNotIn("有一定基础", just_under_three)
        self.assertNotIn("占比极低", just_under_three)

        # 1000/100000 = 1.0%。比较符是 <1，贴线仍是偏低，不是极低。
        at_one = _bottom_card(html, "星光特权")
        self.assertIn("占比1.0%", at_one)
        self.assertIn("占比偏低，激活场景单一", at_one)
        self.assertNotIn("占比极低", at_one)
        self.assertNotIn("有一定基础", at_one)

        # 999/100000 = 0.999%，印成 1.0%，才进入极低。
        just_under_one = _bottom_card(html, "超级推荐")
        self.assertIn("占比1.0%", just_under_one)
        self.assertIn("占比极低，付费路径可能存在障碍或用户感知价值不足", just_under_one)
        self.assertNotIn("占比偏低", just_under_one)
        self.assertNotIn("有一定基础", just_under_one)


if __name__ == "__main__":
    unittest.main()
