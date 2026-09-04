"""Regression coverage for leftover improvement just-over gates and 质检禁语.

PR #72 locked far-from-threshold fire (cr=40 / t20=60 / ref=6 / jx=15 /
p_cr=10). PR #110 locked AI ==75 silence + 74.9 fire, and deep-talk
`best_dr - 2` silence. Exact just-over/just-under fire for the other
five generated cards was never the primary assertion.

A flipped comparison (`<` → `<=` or the reverse) would hide a real
接通/中腰部/退费/建信/公海 card the day a KPI crosses the redline.

quality_supervision leftover FORBIDDEN (PR #115 locked 保证找到 /
先付款再看 only): 一定能 / 包成功 must still fail a complete MUST_SAY
transcript. Dropping either phrase would let a 质检 recording pass.

Does not retest AI ==75 / deep-talk 23 vs 25 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline
from quality_supervision.verification_engine import verify_transcript


def healthy_summary(**overrides):
    values = {
        "date": "2026-09-04",
        "avg_deal": 5_000,
        "cr": 43,
        "allocated": 10_000,
        "conv": 2,
        "t20": 50,
        "on_duty": 20,
        "dr": 25,
        "link_1d_num": 400,
        "ai": 75,
        "ref_rate": 5,
        "total_revenue": 100_000,
        "jx_cr": 18,
        "jx_transfer_in": 200,
        "p_cr": 12,
        "pool_retrieval": 100,
    }
    values.update(overrides)
    return values


def two_depts():
    return [
        {
            "dept_name": "电销一部",
            "per_capita_revenue": 8_000,
            "deep_talk_rate": 25,
        },
        {
            "dept_name": "电销二部",
            "per_capita_revenue": 4_000,
            "deep_talk_rate": 20,
        },
    ]


def _by_title(items):
    return {item["title"]: item for item in items}


_HONGNIANG_OK = "本次沟通说明了价格、收费、退费规则、合同条款、服务期和冷静期。"


class ImprovementJustOverGateTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    def test_connect_just_below_43_fires_p0(self):
        # gap=0.1, extra=int(10000*0.1/100)=10, rev=round(10*2/100*5000)=1000
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(cr=42.9), two_depts(), []
        )
        card = _by_title(items)["接通率修复至43%"]
        self.assertEqual("P0", card["p"])
        self.assertEqual("42.9%", card["cur"])
        self.assertEqual("43%", card["tgt"])
        self.assertEqual(1_000, card["rev"])

    def test_top20_just_over_50_fires_midband_copy(self):
        # bot_n=10, gap_pc=4000, rev=round(10*4000*0.2)=8000
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(t20=50.1), two_depts(), []
        )
        card = _by_title(items)["中腰部标杆复制"]
        self.assertEqual("P1", card["p"])
        self.assertEqual("TOP20%占50.1%", card["cur"])
        self.assertEqual("<=50%", card["tgt"])
        self.assertEqual(8_000, card["rev"])
        self.assertIn("电销二部", card["target_entity"])

    def test_refund_just_over_5_fires_control_card(self):
        # save=round(100000*(5.1-4.5)/100)=600
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(ref_rate=5.1), two_depts(), []
        )
        card = _by_title(items)["退费率管控至4.5%"]
        self.assertEqual("P1", card["p"])
        self.assertEqual("5.1%", card["cur"])
        self.assertEqual("4.5%", card["tgt"])
        self.assertEqual(600, card["rev"])

    def test_jianxin_just_below_18_fires_even_when_extra_truncates(self):
        # extra=int(200*(18-17.9)/100)=int(0.2)=0, rev=0 — card still emits
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(jx_cr=17.9), two_depts(), []
        )
        card = _by_title(items)["建信调配转化率→18%"]
        self.assertEqual("P2", card["p"])
        self.assertEqual("17.9%", card["cur"])
        self.assertEqual("18%", card["tgt"])
        self.assertEqual(0, card["rev"])

    def test_pool_just_below_12_fires_with_floor_one(self):
        # extra=max(1, int(100*(12-11.9)/100))=max(1,0)=1, rev=5000
        items, _ = self.pipeline._calc_improvements(
            healthy_summary(p_cr=11.9), two_depts(), []
        )
        card = _by_title(items)["公海捞取转化→12%"]
        self.assertEqual("P2", card["p"])
        self.assertEqual("11.9%", card["cur"])
        self.assertEqual("12%", card["tgt"])
        self.assertEqual(5_000, card["rev"])


class QualityForbiddenLeftoverTests(unittest.TestCase):
    def test_certainty_phrase_fails_even_when_must_say_complete(self):
        result = verify_transcript(_HONGNIANG_OK + "我们一定能帮您脱单。")
        self.assertFalse(result["pass"])
        self.assertIn("禁止用语：一定能", result["issues"])

    def test_guaranteed_success_phrase_fails_even_when_must_say_complete(self):
        result = verify_transcript(_HONGNIANG_OK + "这套方案包成功。")
        self.assertFalse(result["pass"])
        self.assertIn("禁止用语：包成功", result["issues"])


if __name__ == "__main__":
    unittest.main()
