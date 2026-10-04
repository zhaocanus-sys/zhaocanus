# -*- coding: utf-8 -*-
"""APP HTML 产品诊断与 iOS/Android 差距的贴线。

品类表此前用 90%/50%、81、12、5 这类远离门槛的样本证明文案分支存在。
全量报告里的 15%/5万/3%/1% 是另一套比较符。这里锁的是 HTML 模块自己的
严格大于：珍心占比 >80、其他产品 >10、>3、金额 >1000。展示保留 1 位小数后，
80.0001% 与 80.0%、10.0001% 与 10.0%、3.0001% 与 3.0%、1.001% 与 1.0%
会印成同一个数字，诊断不能跟着舍入升级。

平台对比此前用 30% 对 70%、65% 对 70%。警告句用整数百分比，
54.9% 与 55.0% 都会印成 55%，但只有低于 Android 15 个百分点才报警。
"""
import unittest

from app_report_html import platform_compare_html, product_mix_html


def _kpi(prod_vals, total_rev=1_000_000, pay_num=100):
    return {
        "prod_vals": prod_vals,
        "total_rev": total_rev,
        "pay_num": pay_num,
    }


def _vals(**overrides):
    base = {
        "zhenxin_member": 0,
        "super_member_full": 0,
        "live_guard": 0,
        "super_member_plus": 0,
        "zhenai_coin": 0,
        "super_remind": 0,
        "star_privilege": 0,
        "super_recommend": 0,
        "other": 0,
    }
    base.update(overrides)
    return base


def _product_row(html, name):
    marker = f"<strong>{name}</strong>"
    return html.split(marker, 1)[1].split("</tr>", 1)[0]


class ProductDiagExactEdgesTests(unittest.TestCase):
    def test_zhenxin_eighty_line_does_not_follow_rounded_label(self):
        at_line = product_mix_html(_kpi(_vals(zhenxin_member=800_000)))
        just_over = product_mix_html(_kpi(_vals(zhenxin_member=800_001)))

        at_row = _product_row(at_line, "珍心会员")
        over_row = _product_row(just_over, "珍心会员")

        self.assertIn("¥80.0万", at_row)
        self.assertIn("80.0%", at_row)
        self.assertIn("核心产品，占比健康", at_row)
        self.assertNotIn("超80%红线", at_row)
        self.assertNotIn("占比过高", at_row)
        self.assertIn("珍心会员占比80.0%，结构相对健康", at_line)
        self.assertNotIn("产品结构高风险", at_line)

        self.assertIn("¥80.0万", over_row)
        self.assertIn("80.0%", over_row)
        self.assertIn("⚠ 超80%红线", over_row)
        self.assertIn("核心产品，但占比过高有结构风险", over_row)
        self.assertNotIn("占比健康", over_row)
        self.assertIn("珍心会员占比80.0%超80%红线，产品结构高风险", just_over)

    def test_share_and_amount_lines_do_not_follow_rounded_labels(self):
        html = product_mix_html(
            _kpi(
                _vals(
                    super_member_full=100_001,
                    live_guard=100_000,
                    super_member_plus=30_001,
                    zhenai_coin=30_000,
                )
            )
        )

        # 100001/1000000 = 10.0001%，印成 10.0% / ¥10.0万，仍高于 10。
        just_over_ten = _product_row(html, "超级会员全")
        self.assertIn("¥10.0万", just_over_ten)
        self.assertIn("10.0%", just_over_ten)
        self.assertIn("第二梯队，具有独立增长潜力", just_over_ten)
        self.assertNotIn("有一定基础", just_over_ten)

        # 100000/1000000 = 10.0%，同样印成 10.0%，>10 不成立。
        at_ten = _product_row(html, "直播守护")
        self.assertIn("¥10.0万", at_ten)
        self.assertIn("10.0%", at_ten)
        self.assertIn("有一定基础，提升曝光可加速增长", at_ten)
        self.assertNotIn("第二梯队", at_ten)
        self.assertNotIn("占比偏低", at_ten)

        # 30001/1000000 印成 3.0% / ¥3.0万，刚过 3。
        just_over_three = _product_row(html, "超级会员+")
        self.assertIn("¥3.0万", just_over_three)
        self.assertIn("3.0%", just_over_three)
        self.assertIn("有一定基础，提升曝光可加速增长", just_over_three)
        self.assertNotIn("占比偏低", just_over_three)
        self.assertNotIn("待激活", just_over_three)

        # 30000/1000000 印成同一个 3.0%，金额远高于 1000，落到偏低档。
        at_three = _product_row(html, "珍爱币")
        self.assertIn("¥3.0万", at_three)
        self.assertIn("3.0%", at_three)
        self.assertIn("占比偏低，需优化入口和价值感知", at_three)
        self.assertNotIn("有一定基础", at_three)
        self.assertNotIn("待激活", at_three)

        # 金额门槛用 10 万总营收，让 1000 与 1001 都印成 1.0% / ¥0.1万。
        amount_html = product_mix_html(
            _kpi(
                _vals(super_remind=1_001, star_privilege=1_000),
                total_rev=100_000,
            )
        )
        # 1001/100000 = 1.001%，金额刚过 1000。
        just_over_amt = _product_row(amount_html, "超级提醒")
        self.assertIn("¥0.1万", just_over_amt)
        self.assertIn("1.0%", just_over_amt)
        self.assertIn("占比偏低，需优化入口和价值感知", just_over_amt)
        self.assertNotIn("待激活", just_over_amt)

        # 1000/100000 印成同一个 1.0% / ¥0.1万，等于 1000 不再叫偏低。
        at_amt = _product_row(amount_html, "星光特权")
        self.assertIn("¥0.1万", at_amt)
        self.assertIn("1.0%", at_amt)
        self.assertIn("待激活，考虑捆绑推荐或场景教育", at_amt)
        self.assertNotIn("占比偏低", at_amt)


class IosAndroidGapExactEdgesTests(unittest.TestCase):
    def test_fifteen_point_gap_does_not_follow_rounded_percent(self):
        def orders(ios_pay):
            return {
                "total_amt": 10_000,
                "by_platform": [
                    ("iOS", {"cnt": 1000, "pay": ios_pay, "amt": 5000, "pay_num": 40}),
                    ("Android", {"cnt": 1000, "pay": 700, "amt": 5000, "pay_num": 40}),
                ],
            }

        # 550/1000 = 55.0%，与 Android 70% 正好差 15 个百分点，不报警。
        at_gap = platform_compare_html(orders(550))
        self.assertIn("iOS(55%) vs Android(70%)，差距正常范围", at_gap)
        self.assertNotIn("显著低于", at_gap)
        self.assertIn("55.0%", at_gap)

        # 549/1000 = 54.9%，警告句四舍五入后同样印成 55%，但仍低于 15 个百分点门槛。
        just_under = platform_compare_html(orders(549))
        self.assertIn("54.9%", just_under)
        self.assertIn("iOS成功率(55%)显著低于Android(70%)", just_under)
        self.assertIn("排查IAP/Apple Pay回调", just_under)
        self.assertNotIn("差距正常范围", just_under)


if __name__ == "__main__":
    unittest.main()
