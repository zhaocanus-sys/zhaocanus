"""Regression coverage for leftover APP 全局诊断 mid-band copy.

PR #95 locked the improvement-card gates (珍心>80 P0 / 留存<40 P0 /
付费<5 P1 / 退款>2 P1), the empty payload short-circuit, and the
extreme 全局诊断 strings (30%→严重偏低, 5%→超4%, healthy→良好).

It did not lock the *middle* diagnosis bands that change the banner
without necessarily emitting those threshold cards:

- 次日留存 35% ≤ x < 45% → ⚠ 偏低 (not 严重 / not 良好)
- 退款率 2% < x ≤ 4% → ⚠ 超2%红线 (not 超4%)
- ARPU < 30 → 有提升空间；ARPU ≥ 30 → 良好
- 四维产品结构：>80 超过红线；否则 接近红线

A regression that collapses 40% retain into「留存良好」or 3% refund
into「控制良好」would hide the cash-cow warning while P0 cards stay
silent (retain==40 skips the <40 improvement card).

Does not retest PR #95 P0/P1 card titles, empty-state, or 超80%产品表
badge as the primary assertion. Does not lock APP sparkline rate-field
mapping (open PRs #52–#55/#68).

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from generate_app_full_report import generate_html


def _app_row(**overrides):
    row = {
        "amt": "100000",
        "pay_num": "800",
        "active_members": "10000",
        "refund_money": "500",
        "pay_num_new": "50",
        "retain_1d": "500",
        "retain_7d": "200",
        "order_cnt": "100",
        "order_pay": "70",
        "reg_num_m": "1000",
        "pay_num_m": "500",
        "pay_amt_m": "500000",
        "mems": "1000",
        "zhenxin_member": "50000",
        "pay_amt": "100000",
        "super_member_full": "5000",
        "live_guard": "2000",
        "super_member_plus": "1000",
        "zhenai_coin": "500",
        "super_remind": "300",
        "star_privilege": "100",
        "super_recommend": "100",
        "other": "0",
    }
    row.update(overrides)
    return row


class AppDiagnosisMidbandTests(unittest.TestCase):
    def test_retain_at_40_is_watch_band_not_severe_or_healthy(self):
        # retain_1d/mems = 400/1000 = 40%. Improvement card needs <40, so
        # the only visible signal is the ⚠ 偏低 banner.
        html = generate_html([_app_row(retain_1d="400")], [], [], "2026-08-30")
        self.assertIn("次日留存率 40.0%", html)
        self.assertIn("偏低，需优化首日Hook机制", html)
        self.assertNotIn("严重偏低", html)
        self.assertNotIn("留存良好", html)
        self.assertNotIn("次日留存率提升至40%", html)

    def test_refund_at_4_is_redline_watch_not_crisis(self):
        # 4000/100000 = 4%. `>4` crisis is off; `>2` watch is on.
        html = generate_html([_app_row(refund_money="4000")], [], [], "2026-08-30")
        self.assertIn("退款率 4.0%", html)
        self.assertIn("超2%红线，需分产品追因", html)
        self.assertNotIn("超4%，退款规模大", html)
        self.assertNotIn("退款控制良好", html)

    def test_arpu_below_and_at_30_switch_copy(self):
        # amt 100000 / pay_num 4000 = ARPU 25; / 3333 ≈ 30.00 ≥ 30
        low = generate_html(
            [_app_row(pay_num="4000")], [], [], "2026-08-30"
        )
        self.assertIn("ARPU ¥25.0", low)
        self.assertIn("ARPU有提升空间（目标¥30）", low)
        self.assertNotIn("ARPU良好，聚焦付费率提升", low)

        ok = generate_html(
            [_app_row(pay_num="3333")], [], [], "2026-08-30"
        )
        self.assertIn("ARPU良好，聚焦付费率提升", ok)
        self.assertNotIn("ARPU有提升空间（目标¥30）", ok)

    def test_four_dim_structure_copy_splits_on_80(self):
        over = generate_html(
            [_app_row(zhenxin_member="90000")], [], [], "2026-08-30"
        )
        self.assertIn("超过80%红线，产品结构高风险，需立即推进多元化", over)
        self.assertNotIn("接近红线，提前布局产品多元化", over)

        under = generate_html(
            [_app_row(zhenxin_member="50000")], [], [], "2026-08-30"
        )
        self.assertIn("接近红线，提前布局产品多元化，培育第二增长曲线", under)
        self.assertNotIn("超过80%红线，产品结构高风险", under)


if __name__ == "__main__":
    unittest.main()
