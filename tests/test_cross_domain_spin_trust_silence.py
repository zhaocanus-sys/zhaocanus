"""Regression coverage for leftover CrossDomain SPIN / 信任 exact gates.

PR #81 locked fire-vs-healthy-baseline for SPIN / 锚定 / 社会认同 / 信任.
PR #111 locked successful interpolation on already-fired cards
({dr}/{conv} at 18/1.0, {fc_rate} at 2.5). Exact boundary silence
was still open:

- SPIN 暗示问题×损失厌恶: dr > 15 AND conv < 1.2
- 信任构建×非暴力沟通共情: fc_rate < 3

A flipped comparison would either spam mid-band teams with a false
深沟→转化 diagnosis, or hide a real first-call trust gap.

Always-on cards (狼性PK / Hook / 杠铃 / 用户分层 / 战时CEO / AARRR)
are background only. Does not lock desc.format KeyError (PR #111).
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import CrossDomainCollisionEngine


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


def _tags(engine):
    return {f.tag for f in engine.findings}


SPIN = "SPIN暗示问题×损失厌恶"
TRUST = "信任构建×非暴力沟通共情"
SOCIAL = "影响力社会认同×从众效应"


class CrossDomainSpinTrustSilenceTests(unittest.TestCase):
    def _run(self, **summary_overrides):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(**summary_overrides), _depts(2000, 2100), [], [])
        return engine

    def test_spin_silent_at_dr_equals_15(self):
        engine = self._run(dr=15, conv=1.0)
        self.assertNotIn(SPIN, _tags(engine))

    def test_spin_silent_at_conv_equals_1_2(self):
        engine = self._run(dr=20, conv=1.2)
        self.assertNotIn(SPIN, _tags(engine))

    def test_spin_fires_just_over_both_gates_and_interpolates(self):
        engine = self._run(dr=15.1, conv=1.19)
        self.assertIn(SPIN, _tags(engine))
        card = next(f for f in engine.findings if f.tag == SPIN)
        self.assertEqual("P1", card.priority)
        self.assertIn("深沟率15.1%", card.description)
        self.assertIn("转化率仅1.19%", card.description)
        self.assertIn("深沟→签单转化率+3pp", card.evidence)

    def test_trust_silent_at_fc_rate_equals_3(self):
        engine = self._run(fc_rate=3)
        self.assertNotIn(TRUST, _tags(engine))
        self.assertNotIn(SOCIAL, _tags(engine))

    def test_trust_fires_just_below_3_and_interpolates(self):
        engine = self._run(fc_rate=2.99)
        self.assertIn(TRUST, _tags(engine))
        card = next(f for f in engine.findings if f.tag == TRUST)
        self.assertEqual("P2", card.priority)
        self.assertIn("首通转化率仅2.99%", card.description)
        self.assertIn("S07:销售圣经-信任", card.knowledge_refs)


if __name__ == "__main__":
    unittest.main()
