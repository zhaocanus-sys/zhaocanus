"""Regression coverage for leftover improvement exact-on-target silence.

PR #72 locked far-below fire. PR #110 locked AI==75 / deep-talk
best_dr-2. PR #119 locked just-over fire (cr=42.9 / t20=50.1 /
ref_rate=5.1 / jx_cr=17.9 / p_cr=11.9). Sitting exactly on the
target was never the primary lock:

- cr == 43  (need < 43)  → no 接通率修复至43%
- t20 == 50 (need > 50)  → no 中腰部标杆复制
- ref_rate == 5 (need > 5) → no 退费率管控至4.5%
- jx_cr == 18 (need < 18) → no 建信调配转化率→18%
- p_cr == 12 (need < 12)  → no 公海捞取转化→12%

A flipped comparison would push a false 改善卡 (and a 部署日期 /
每日执行指令) the day the team already sits on the KPI target.

Does not retest just-over fire, AI==75, or best_dr-2 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline


def make_summary(**overrides):
    summary = {
        "date": "2026-09-06",
        "cr": 45,
        "t20": 40,
        "dr": 20,
        "ai": 80,
        "ref_rate": 4,
        "jx_cr": 20,
        "p_cr": 15,
        "allocated": 1000,
        "conv": 2.0,
        "avg_deal": 5000,
        "on_duty": 20,
        "link_1d_num": 400,
        "jx_transfer_in": 50,
        "pool_retrieval": 40,
        "total_revenue": 100000,
    }
    summary.update(overrides)
    return summary


def make_depts():
    return [
        {
            "dept_name": "电销六部",
            "deep_talk_rate": 20,
            "per_capita_revenue": 2500,
        }
    ]


def _titles(items):
    return [item["title"] for item in items]


class ImprovementExactTargetSilenceTests(unittest.TestCase):
    def setUp(self):
        self.pipe = AnalysisPipeline("/tmp/unused-coverage.db")

    def test_connect_rate_exactly_43_emits_no_repair_card(self):
        items, _total = self.pipe._calc_improvements(
            make_summary(cr=43), make_depts(), []
        )
        self.assertNotIn("接通率修复至43%", _titles(items))

    def test_t20_exactly_50_emits_no_benchmark_card(self):
        items, _total = self.pipe._calc_improvements(
            make_summary(t20=50), make_depts(), []
        )
        self.assertNotIn("中腰部标杆复制", _titles(items))

    def test_refund_rate_exactly_5_emits_no_control_card(self):
        items, _total = self.pipe._calc_improvements(
            make_summary(ref_rate=5), make_depts(), []
        )
        self.assertNotIn("退费率管控至4.5%", _titles(items))

    def test_jx_conv_exactly_18_emits_no_transfer_card(self):
        items, _total = self.pipe._calc_improvements(
            make_summary(jx_cr=18), make_depts(), []
        )
        self.assertNotIn("建信调配转化率→18%", _titles(items))

    def test_pool_conv_exactly_12_emits_no_retrieval_card(self):
        items, _total = self.pipe._calc_improvements(
            make_summary(p_cr=12), make_depts(), []
        )
        self.assertNotIn("公海捞取转化→12%", _titles(items))


if __name__ == "__main__":
    unittest.main()
