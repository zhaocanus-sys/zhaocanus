"""Regression coverage for leftover CrossDomain 社会认同 / 锚定 exact gates.

PR #81 locked fire-vs-healthy-baseline for SPIN / 锚定 / 社会认同 / 信任.
PR #111 interpolated `{t20}` / `{avg_deal:,}` only on already-fired cards.
PR #115 locked 271 at `t20==50` (that tag), not 社会认同 as primary.
PR #117 locked SPIN / 信任 exact silence.

Still open:
- 影响力社会认同×从众效应: t20 > 50. Silent at exactly 50;
  just-over (50.1) must fire and interpolate. Two depts keep 271 off.
- 挑战式销售×锚定效应: avg_deal < 5500. Silent at exactly 5500;
  5499 must fire and render ¥5,499 via `{avg_deal:,}`.

A flipped comparison would either spam mid-band concentration / ASP
as a false 中腰部社会认同 or 客单价锚定 diagnosis, or hide a real one.

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


SOCIAL = "影响力社会认同×从众效应"
ANCHOR = "挑战式销售×锚定效应"
RULE_271 = "271法则×自然代谢替代裁员"


class CrossDomainSocialAnchorSilenceTests(unittest.TestCase):
    def _run(self, depts=None, **summary_overrides):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(**summary_overrides), depts or _depts(2000, 2100), [], [])
        return engine

    def test_social_proof_silent_at_t20_equals_50(self):
        engine = self._run(t20=50)
        self.assertNotIn(SOCIAL, _tags(engine))
        self.assertNotIn(RULE_271, _tags(engine))

    def test_social_proof_fires_just_over_50_and_interpolates(self):
        engine = self._run(t20=50.1)
        self.assertIn(SOCIAL, _tags(engine))
        self.assertNotIn(RULE_271, _tags(engine))
        card = next(f for f in engine.findings if f.tag == SOCIAL)
        self.assertEqual("P1", card.priority)
        self.assertIn("TOP20%占50.1%业绩", card.description)
        self.assertIn("中腰部转化率+5pp", card.evidence)
        self.assertIn("S04:影响力-社会认同", card.knowledge_refs)

    def test_anchor_silent_at_avg_deal_equals_5500(self):
        engine = self._run(avg_deal=5500)
        self.assertNotIn(ANCHOR, _tags(engine))

    def test_anchor_fires_just_below_5500_and_interpolates(self):
        engine = self._run(avg_deal=5499)
        self.assertIn(ANCHOR, _tags(engine))
        card = next(f for f in engine.findings if f.tag == ANCHOR)
        self.assertEqual("P2", card.priority)
        self.assertIn("客单价¥5,499偏低", card.description)
        self.assertIn("客单价+8%", card.evidence)
        self.assertIn("S02:挑战式销售-教学裁剪掌控", card.knowledge_refs)


if __name__ == "__main__":
    unittest.main()
