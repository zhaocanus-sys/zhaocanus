"""Regression coverage for leftover H1 +1.51 支持 and H2 dials 130.1.

PR #123/#124/#125/#127 locked |Δcr|==1.5 as *reject* (幅度不大)
and named/unnamed alternatives.
PR #128 locked the first *falling* support at -1.6 (45.0→43.4).

The first *rising* support tick was never the primary lock:

- |Δcr|==+1.51 is the first 支持 (`> 1.5`)
- |Δcr|==+1.5 stays 推翻 + 幅度不大

PR #122 locked exact ==15 / ==1.3x reject.
PR #129 locked AI 15.1 + dials 131 behind a far t20.
PR #132 locked t20==50.1 + AI 15.1 + dials 131.

The leftover 1.3x tick on the leftover inclusion gate:

- t20==50.1 + AI 15.1 + dials 130.1 vs 100 is the first 支持
  (`130.1 > 100*1.3`)
- 130 vs 100 stays 部分推翻 (`130 > 130` is false)
- t20==50 + 130.1 still skips H2

Does not retest PR #128 falling -1.6 or PR #132 dials 131 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_person(**overrides):
    person = {
        "name": "员工A",
        "revenue": 3000,
        "ai_score": 70,
        "dial_count": 100,
    }
    person.update(overrides)
    return person


def _ten_persons(top_ai=72, bot_ai=70, top_dials=100, bot_dials=100):
    """10 people → TOP20%=2, BOTTOM30%=3."""
    persons = []
    for i in range(2):
        persons.append(make_person(
            name=f"TOP{i}", revenue=9000 - i, ai_score=top_ai, dial_count=top_dials,
        ))
    for i in range(5):
        persons.append(make_person(
            name=f"MID{i}", revenue=4000 - i, ai_score=70, dial_count=100,
        ))
    for i in range(3):
        persons.append(make_person(
            name=f"BOT{i}", revenue=1000 - i, ai_score=bot_ai, dial_count=bot_dials,
        ))
    return persons


def _midband_dept():
    return {
        "dept_name": "电销六部",
        "refund_rate": 5,
        "signed_deals": 10,
        "avg_ai_score": 70,
    }


class H1Rising151FirstSupportTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, cr_prev, cr_last):
        self.engine.hypotheses = []
        self.engine.findings = []
        self.engine._build_and_test_hypotheses(
            {"t20": 40, "pc": 3000},
            [_midband_dept()],
            [
                {
                    "total_revenue": 100000,
                    "cr": cr_prev,
                    "conv": 2.0,
                    "pc": 3000,
                    "allocated": 1000,
                },
                {
                    "total_revenue": 101000,
                    "cr": cr_last,
                    "conv": 2.0,
                    "pc": 3000,
                    "allocated": 1000,
                },
            ],
            [],
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H1"]

    def test_cr_plus_1_51_is_first_rising_support(self):
        # 44.51 - 43.0 == 1.51 > 1.5 is the first rising support.
        # Distinct from PR #128's falling -1.6 and PR #124's 1.5 reject
        # with a named 分配/转化/人均 driver.
        h1s = self._h1(43.0, 44.51)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("支持", h1["verdict"])
        self.assertEqual(1, len(h1["support_evidence"]))
        self.assertEqual(0, len(h1["reject_evidence"]))
        self.assertTrue(any("接通率变动" in e and "幅度显著" in e
                            for e in h1["support_evidence"]))
        self.assertIn("增长", h1["hypothesis"])
        self.assertEqual("", h1["alternative"])

    def test_cr_plus_exactly_1_5_stays_rejected(self):
        # 44.5 - 43.0 == 1.5 is not `> 1.5`. Same growth / no other
        # drivers → 推翻 + 幅度不大. Flipping to `>=` would keep the
        # -1.6 / named-1.5 suites green while promoting a 贴线 day
        # to 接通率主因.
        h1s = self._h1(43.0, 44.5)
        self.assertEqual(1, len(h1s))
        h1 = h1s[0]
        self.assertEqual("推翻", h1["verdict"])
        self.assertEqual(0, len(h1["support_evidence"]))
        self.assertEqual(1, len(h1["reject_evidence"]))
        self.assertTrue(any("幅度不大" in e for e in h1["reject_evidence"]))
        self.assertIn("营收变动主因可能是:", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])


class H2T501PlusAi151PlusDials1301Tests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h2(self, t20, top_ai=85.1, bot_ai=70, top_dials=130.1, bot_dials=100):
        self.engine.findings = []
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            {"t20": t20, "pc": 3000},
            [_midband_dept()],
            [],
            _ten_persons(
                top_ai=top_ai, bot_ai=bot_ai,
                top_dials=top_dials, bot_dials=bot_dials,
            ),
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H2"]

    def test_t20_50_1_plus_ai_15_1_plus_dials_130_1_is_first_support(self):
        # 130.1 > 100*1.3 is the first 1.3x tick. PR #132 locked 131
        # (farther). Together with leftover 50.1 / 15.1 this is the
        # first 支持 at the inclusion gate.
        h2s = self._h2(50.1)
        self.assertEqual(1, len(h2s))
        h2 = h2s[0]
        self.assertEqual("支持", h2["verdict"])
        self.assertEqual(2, len(h2["support_evidence"]))
        self.assertEqual(0, len(h2["reject_evidence"]))
        self.assertIn("勤奋度", h2["alternative"])
        self.assertNotIn("挖需求", h2["alternative"])
        cards = [f for f in self.engine.findings if f.tag.startswith("假设验证")]
        self.assertEqual(1, len(cards))
        self.assertEqual("假设验证: 支持", cards[0].tag)

    def test_t20_50_1_plus_ai_15_1_dials_130_stays_partial(self):
        # 130 > 130 is false. AI support cannot outvote the 1.3x
        # reject (`>=` on reject). Stays 部分推翻 + 挖需求.
        h2s = self._h2(50.1, top_dials=130, bot_dials=100)
        self.assertEqual(1, len(h2s))
        h2 = h2s[0]
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertEqual(1, len(h2["support_evidence"]))
        self.assertEqual(1, len(h2["reject_evidence"]))
        self.assertIn("挖需求", h2["alternative"])
        self.assertNotIn("勤奋度", h2["alternative"])

    def test_t20_exactly_50_plus_dials_130_1_skips_h2(self):
        # ==50 is not `> 50`. The leftover 1.3x tick must not emit
        # H2 (or a 假设验证 card) on a 贴线集中度 day.
        self.assertEqual([], self._h2(50))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag.startswith("假设验证")],
        )


if __name__ == "__main__":
    unittest.main()
