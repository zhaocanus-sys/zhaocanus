# -*- coding: utf-8 -*-
"""Regression coverage for APP diagnosis gates and timed improvements."""
import unittest

from generate_app_full_report import MANAGER, generate_html


def _app_row(**overrides):
    """Minimal daily-row fixture with string-like API values."""
    row = {
        "amt": "100000",
        "pay_num": "200",
        "active_members": "10000",
        "refund_money": "5000",
        "pay_num_new": "50",
        "retain_1d": "300",
        "retain_7d": "200",
        "order_cnt": "100",
        "order_pay": "70",
        "reg_num_m": "1000",
        "pay_num_m": "500",
        "pay_amt_m": "500000",
        "mems": "1000",
        "zhenxin_member": "90000",
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


class AppDiagnosisGateTests(unittest.TestCase):
    def test_critical_metrics_fire_p0_p1_with_deploy_tomorrow(self):
        """Zhenxin/retain/pay/refund thresholds emit timed improvement cards."""
        # zhenxin 90% > 80 → P0; retain 30% < 40 → P0;
        # pay_rate 2% < 5 → P1; refund_rate 5% > 2 → P1.
        rows = [_app_row()]
        html = generate_html(rows, rows, [], "2026-02-27")

        self.assertIn("全局诊断 · 环比分析", html)
        self.assertIn("珍心会员占比 90.0%", html)
        self.assertIn("⚠ 超80%红线", html)
        self.assertIn("次日留存率 30.0%", html)
        self.assertIn("严重偏低", html)
        self.assertIn("退款率 5.0%", html)
        self.assertIn("超4%", html)

        self.assertIn("【P0】珍心占比治理", html)
        self.assertIn("【P0】次日留存率提升至40%", html)
        self.assertIn("【P1】付费率从2.0%提升至5%", html)
        self.assertIn("【P1】退款率控制至<2%", html)

        # Time-dimension execution fields (report day + 1).
        self.assertIn(f"负责人: {MANAGER}", html)
        self.assertIn("部署: 2026-02-28", html)
        self.assertIn("周期: 30天", html)
        self.assertIn("周期: 14天", html)

    def test_healthy_metrics_skip_threshold_cards_but_keep_baseline(self):
        """Healthy rates skip P0/P1 threshold cards; always-on ARPU/traffic remain."""
        rows = [
            _app_row(
                zhenxin_member="50000",  # 50%
                retain_1d="500",  # 50%
                pay_num="800",  # 8% of 10k DAU
                refund_money="500",  # 0.5%
            )
        ]
        html = generate_html(rows, [], [], "2026-03-01")

        self.assertIn("产品结构健康", html)
        self.assertIn("留存良好", html)
        self.assertIn("退款控制良好", html)

        self.assertNotIn("珍心占比治理", html)
        self.assertNotIn("次日留存率提升至40%", html)
        self.assertNotIn("付费率从", html)
        self.assertNotIn("退款率控制至<2%", html)
        # Product-table warning badge is threshold-gated (static KB copy may still mention 80%).
        self.assertNotIn("⚠ 超80%红线", html)

        # Always-on baseline cards still carry deploy_date = tomorrow.
        self.assertIn("ARPU提升策略", html)
        self.assertIn("流量质量优化", html)
        self.assertIn(f"负责人: {MANAGER}", html)
        self.assertIn("部署: 2026-03-02", html)

    def test_empty_rows_render_empty_state_without_crash(self):
        """Empty API payload must short-circuit to a safe empty-state page."""
        html = generate_html([], [], [], "2026-03-02")
        self.assertIn("暂无数据", html)
        self.assertNotIn("全局诊断", html)
        self.assertNotIn("珍心占比治理", html)


if __name__ == "__main__":
    unittest.main()
