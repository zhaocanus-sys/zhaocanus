"""Regression coverage for leftover always-on CrossDomain P1 cards.

PR #81 locked always-on 狼性PK / 指标陷阱 / Hook / 杠铃 (and healthy
trigger silence). It did not lock the other always-on cards that appear
on every DataExpert report:

- 用户分层运营×孤独经济消费 (P1, 30+/25- talk-track)
- 战时CEO×20英里行军 (P1, no-big-bang cadence)
- AARRR漏斗×进化心理学择偶差异 (P2, male/female activation)

A silent drop of these cards would strip the standing management
playbook from every daily collision report.

Does not retest PR #81 named always-on tags, interpolation (PR #110/#111),
or trigger on/off as the primary assertion.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.collision_engine import CrossDomainCollisionEngine


def _complete_summary(**overrides):
    # Keep interpolating rules that need keys from KeyError-ing mid-execute.
    # Healthy values so gated rules stay off; only always-on cards fire.
    summary = {
        "dr": 10,
        "conv": 2.0,
        "avg_deal": 6_000,
        "t20": 40,
        "fc_rate": 5,
        "ai": 80,
        "ref_rate": 3,
    }
    summary.update(overrides)
    return summary


def _depts(n=2, per_capita=3_000):
    return [
        {"dept_name": f"电销{i}部", "per_capita_revenue": per_capita}
        for i in range(1, n + 1)
    ]


def _by_tag(findings):
    return {f.tag: f for f in findings}


class CrossDomainAlwaysOnP1Tests(unittest.TestCase):
    def setUp(self):
        self.engine = CrossDomainCollisionEngine()

    def test_age_segment_talk_track_is_always_on_p1(self):
        findings = self.engine.execute(_complete_summary(), _depts(), [], [])
        card = _by_tag(findings)["用户分层运营×孤独经济消费"]
        self.assertEqual("P1", card.priority)
        self.assertIn("30+", card.description)
        self.assertIn("25-", card.description)
        recs = " ".join(card.recommendations)
        self.assertIn("差异化话术", recs)
        self.assertIn("高付费潜力客户", recs)
        self.assertIn("A09:用户增长方法论-分层", card.knowledge_refs)

    def test_wartime_ceo_cadence_is_always_on_p1(self):
        findings = self.engine.execute(_complete_summary(), _depts(), [], [])
        card = _by_tag(findings)["战时CEO×20英里行军"]
        self.assertEqual("P1", card.priority)
        self.assertIn("20英里行军", card.description)
        recs = " ".join(card.recommendations)
        self.assertIn("每周改善目标不超过当前值的5%", recs)
        self.assertIn("红黄绿灯", recs)
        self.assertIn("R17:创业维艰-战时CEO", card.knowledge_refs)

    def test_aarrr_gender_activation_is_always_on_p2(self):
        findings = self.engine.execute(_complete_summary(), _depts(), [], [])
        card = _by_tag(findings)["AARRR漏斗×进化心理学择偶差异"]
        self.assertEqual("P2", card.priority)
        recs = " ".join(card.recommendations)
        self.assertIn("男性客户", recs)
        self.assertIn("女性客户", recs)
        self.assertIn("A01:增长黑客-AARRR", card.knowledge_refs)

    def test_get_summary_counts_always_on_domains(self):
        self.engine.execute(_complete_summary(), _depts(), [], [])
        summary = self.engine.get_summary()
        self.assertIn("APP增长×交友行业", summary["domains_used"])
        self.assertIn("困境重建×经营现实", summary["domains_used"])
        self.assertGreaterEqual(summary["findings_by_priority"]["P1"], 2)
        self.assertGreaterEqual(summary["total_collisions"], 3)
        self.assertTrue(summary["matrices_loaded"])


if __name__ == "__main__":
    unittest.main()
