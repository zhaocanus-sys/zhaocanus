"""Regression coverage for leftover CrossDomain 话术标准化 / AI质检 gates.

PR #115 locked Simpson / 271 / flywheel / brand-repair thresholds and
the trigger-exception swallow. PR #111 interpolated `{ai}` when the
质检AI化 rule already fired (ai=70), but did not lock the 75-point
silence or the 话术标准化×优势管理 fire path.

话术标准化 is the only telesale×management rule that keys off
department per-capita spread. A silent miss (or a fire at exactly
1.5× mean) would hide or invent a mid-band SOP gap for operators.

Always-on cards (狼性PK / 指标陷阱 / Hook / 杠铃 / 用户分层 / 战时CEO /
AARRR) are background only.

Does not import generate_telesale_full_report.
Does not lock persistence global count (PR #48), APP sparkline mapping,
shop double-count, or CrossDomain missing-key format() crash.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import CrossDomainCollisionEngine


SCRIPT_TAG = "话术标准化×优势管理"
AI_TAG = "质检AI化×复盘四步法"


def _full_summary(**overrides):
    """Complete format keys so leftover rules do not KeyError on .format."""
    summary = {
        "dr": 10.0,
        "conv": 2.0,
        "avg_deal": 6000,
        "t20": 40,
        "fc_rate": 5.0,
        "ai": 80,
        "ref_rate": 2.0,
    }
    summary.update(overrides)
    return summary


def _depts(*pcs):
    return [{"dept_name": f"电销{i}部", "per_capita_revenue": pc} for i, pc in enumerate(pcs, 1)]


def _by_tag(engine, tag):
    return [f for f in engine.findings if f.tag == tag]


class ScriptStandardizationTriggerTests(unittest.TestCase):
    def test_fires_when_one_dept_exceeds_1_5x_mean(self):
        # 2000 + 6001 → mean 4000.5; 1.5×mean = 6000.75. Both ≥1200 so 飞轮 stays off.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(2000, 6001), [], [])

        hits = _by_tag(engine, SCRIPT_TAG)
        self.assertEqual(1, len(hits))
        finding = hits[0]
        self.assertEqual("P1", finding.priority)
        self.assertEqual("cross_domain:telesale_x_management", finding.collision_type)
        self.assertIn("话术三层架构", " ".join(finding.recommendations))
        self.assertTrue(any("T06" in ref for ref in finding.knowledge_refs))
        self.assertTrue(any("L03" in ref for ref in finding.knowledge_refs))
        self.assertEqual(["中腰部产值+15%"], finding.evidence)
        self.assertIn("电销×团队管理", engine.get_summary()["domains_used"])

    def test_silent_at_exactly_1_5x_mean(self):
        # 2000 + 6000 → mean 4000; 1.5×mean = 6000. Trigger is strict `>`.
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(2000, 6000), [], [])
        self.assertEqual([], _by_tag(engine, SCRIPT_TAG))

    def test_silent_for_single_or_empty_depts(self):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), _depts(99999), [], [])
        self.assertEqual([], _by_tag(engine, SCRIPT_TAG))

        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(), [], [], [])
        self.assertEqual([], _by_tag(engine, SCRIPT_TAG))


class AiQualityThresholdTests(unittest.TestCase):
    def test_ai_quality_silent_at_75_fires_just_below(self):
        # Equal depts keep 话术标准化 off; 飞轮/271/辛普森 stay off.
        even = _depts(2000, 2000)

        silent = CrossDomainCollisionEngine()
        silent.execute(_full_summary(ai=75), even, [], [])
        self.assertEqual([], _by_tag(silent, AI_TAG))

        firing = CrossDomainCollisionEngine()
        firing.execute(_full_summary(ai=74.9), even, [], [])
        hits = _by_tag(firing, AI_TAG)
        self.assertEqual(1, len(hits))
        self.assertEqual("P1", hits[0].priority)
        self.assertIn("74.9", hits[0].description)
        self.assertIn("标杆75", hits[0].description)


if __name__ == "__main__":
    unittest.main()
