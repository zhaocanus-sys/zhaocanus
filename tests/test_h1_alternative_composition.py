"""Regression coverage for LogicCollision H1 alternative-string composition.

PR #79 locked H1 推翻(分配驱动) and 支持(接通率大幅波动) as primary
verdicts. It did not lock how the alternative sentence is composed from
分配量 / 转化率 / 人均产值, the <2-trend skip, decline wording, or the
equal-evidence → 支持 tie.

Does not retest PR #79 allocation-reject / large-cr-support as the
primary assertion, or PR #80/#108 H2/H3/causal paths.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_summary(**overrides):
    summary = {
        "allocated": 2000,
        "dial_count": 10000,
        "link_1d_num": 3000,
        "deep_talk": 600,
        "signed_deals": 40,
        "on_duty": 100,
        "cr": 45,
        "dr": 20,
        "ai": 75,
        "conv": 1.2,
        "pc": 5000,
        "total_revenue": 500000,
        "ref_rate": 3,
        "complaint_count": 2,
        "alloc_rate": 0.9,
        "t20": 40,
        "roi": 180,
    }
    summary.update(overrides)
    return summary


def make_trend(**overrides):
    trend = {
        "total_revenue": 100000,
        "cr": 45.0,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    trend.update(overrides)
    return trend


def _h1(engine):
    return next(h for h in engine.hypotheses if h["id"] == "H1")


class H1SkipAndWordingTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_fewer_than_two_trends_skips_h1(self):
        self.engine._build_and_test_hypotheses(make_summary(), [], [], [])
        self.assertEqual([], [h for h in self.engine.hypotheses if h["id"] == "H1"])

        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            make_summary(), [], [make_trend()], []
        )
        self.assertEqual([], [h for h in self.engine.hypotheses if h["id"] == "H1"])

    def test_revenue_decline_wording_uses_下降(self):
        trends = [
            make_trend(total_revenue=120000, cr=45.0),
            make_trend(total_revenue=90000, cr=44.8, allocated=1010),
        ]
        self.engine._build_and_test_hypotheses(make_summary(), [], trends, [])
        self.assertIn("营收下降的主驱动力是接通率变化", _h1(self.engine)["hypothesis"])

    def test_revenue_growth_wording_uses_增长(self):
        trends = [
            make_trend(total_revenue=90000, cr=45.0),
            make_trend(total_revenue=110000, cr=44.8, allocated=1010),
        ]
        self.engine._build_and_test_hypotheses(make_summary(), [], trends, [])
        self.assertIn("营收增长的主驱动力是接通率变化", _h1(self.engine)["hypothesis"])


class H1AlternativeCompositionTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _reject_h1(self, **last_overrides):
        """Small cr swing so H1 is 推翻; last-day overrides pick drivers."""
        last = dict(
            total_revenue=110000,
            cr=45.4,  # |Δcr|=0.4 <= 1.5 → reject 接通率
            conv=1.02,  # |Δconv|=0.02 <= 0.05
            pc=3100,  # |Δpc|=100 <= 200
            allocated=1020,  # |Δalloc|=20 <= 50
        )
        last.update(last_overrides)
        trends = [make_trend(), make_trend(**last)]
        self.engine._build_and_test_hypotheses(make_summary(), [], trends, [])
        h1 = _h1(self.engine)
        self.assertEqual("推翻", h1["verdict"])
        return h1

    def test_no_other_driver_leaves_empty_alternative_prefix(self):
        h1 = self._reject_h1()
        self.assertEqual("营收变动主因可能是:", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_equal_thresholds_do_not_name_a_driver(self):
        # abs(change) must be strictly greater than the gate.
        # conv uses 1.04 (Δ=0.04) rather than 1.05: 1.05-1.0 is
        # 0.050000000000000044 in IEEE float and would trip > 0.05.
        h1 = self._reject_h1(allocated=1050, conv=1.04, pc=3200)
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_conversion_only_names_转化率变化(self):
        h1 = self._reject_h1(conv=1.06)
        self.assertIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_per_capita_only_names_人均产值变化(self):
        h1 = self._reject_h1(pc=3201)
        self.assertIn("人均产值变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])

    def test_allocation_just_over_threshold_names_分配量变化(self):
        h1 = self._reject_h1(allocated=1051)
        self.assertIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_all_three_drivers_compose_in_order(self):
        h1 = self._reject_h1(allocated=1100, conv=1.2, pc=3400)
        alt = h1["alternative"]
        self.assertIn("分配量变化", alt)
        self.assertIn("转化率变化", alt)
        self.assertIn("人均产值变化", alt)
        self.assertLess(alt.index("分配量变化"), alt.index("转化率变化"))
        self.assertLess(alt.index("转化率变化"), alt.index("人均产值变化"))

    def test_equal_support_and_reject_counts_as_支持(self):
        # |Δcr|=2.0 > 1.5 → support; |Δalloc|=80 > 50 → reject; 1 == 1 → 支持
        trends = [
            make_trend(cr=40.0, allocated=1000, conv=1.0, pc=3000),
            make_trend(cr=42.0, allocated=1080, conv=1.02, pc=3050),
        ]
        self.engine._build_and_test_hypotheses(make_summary(), [], trends, [])
        h1 = _h1(self.engine)
        self.assertEqual(1, len(h1["support_evidence"]))
        self.assertEqual(1, len(h1["reject_evidence"]))
        self.assertEqual("支持", h1["verdict"])
        self.assertEqual("", h1["alternative"])


if __name__ == "__main__":
    unittest.main()
