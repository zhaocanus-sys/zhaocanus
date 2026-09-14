"""Regression coverage for leftover H1 decline alloc/pc and H2 AI 15.1.

PR #125 locked |Δcr|==+1.5 + alloc==50 / pc==200 unnamed on a
*rising* day, and +1.5 + alloc==50 + conv just-over names only
转化率变化.

PR #128 locked falling |Δcr|==-1.5 + conv 1.049 unnamed / 1.051
named, plus -1.6 first 支持.

The decline × alloc/pc leftover was never the primary lock:

- 44.5→43 (`-1.5`) + alloc==50 stays unnamed
- same CR + alloc==51 names only 分配量变化
- `-1.5` + pc==200 stays unnamed; pc==201 names only 人均产值变化

PR #122 locked AI gap ==15 and dials ==1.3x as reject, plus mixed
1-1 部分推翻. The first just-over AI tick (15.1) was never locked:

- gap 15.1 + equal dials → 部分推翻 with 能力差距显著
- gap 15.1 + dials 131/100 → first both-just-over 支持

Does not retest PR #125 rising alloc==50 or PR #122 ==15 reject
as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def _trend_pair(cr_prev, cr_last, **last_overrides):
    prev = {
        "total_revenue": 100000,
        "cr": cr_prev,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last = {
        "total_revenue": 90000,
        "cr": cr_last,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last.update(last_overrides)
    return [prev, last]


def make_person(**overrides):
    person = {
        "name": "员工A",
        "revenue": 3000,
        "ai_score": 70,
        "dial_count": 100,
    }
    person.update(overrides)
    return person


def _ten_persons(top_ai, bot_ai, top_dials, bot_dials):
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


class H1DeclineAllocAndPcExactDriverTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, trends):
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses({}, [], trends, [])
        h1 = [h for h in self.engine.hypotheses if h["id"] == "H1"]
        self.assertEqual(1, len(h1))
        return h1[0]

    def test_cr_minus_1_5_plus_alloc_50_unnamed_on_decline(self):
        # Mirror of PR #125's +1.5 + alloc==50, on the falling-CR
        # leftover after PR #128's conv-named decline.
        h1 = self._h1(_trend_pair(44.5, 43.0, allocated=1050))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("下降", h1["hypothesis"])
        self.assertTrue(any("幅度不大" in e for e in h1["reject_evidence"]))
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])

    def test_cr_minus_1_5_plus_alloc_51_names_only_allocation_on_decline(self):
        # 1051-1000 == 51 > 50 is the first named-alloc tick on a
        # 下降 day. Flipping `> 50` to `>=` would keep PR #125's ==50
        # rising suite green only if that file stays; this locks the
        # first real 分配量变化 label after a 1.5pp 接通 wobble.
        h1 = self._h1(_trend_pair(44.5, 43.0, allocated=1051))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("下降", h1["hypothesis"])
        self.assertIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertTrue(any("分配量变动" in e for e in h1["reject_evidence"]))

    def test_cr_minus_1_5_plus_pc_200_unnamed_on_decline(self):
        h1 = self._h1(_trend_pair(44.5, 43.0, pc=3200))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("下降", h1["hypothesis"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertEqual("营收变动主因可能是:", h1["alternative"])

    def test_cr_minus_1_5_plus_pc_201_names_only_per_capita_on_decline(self):
        # 3201-3000 == 201 > 200. First named-pc tick on a 下降 day
        # after PR #125's rising ==200 silence and PR #128's conv name.
        h1 = self._h1(_trend_pair(44.5, 43.0, pc=3201))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("人均产值变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])


class H2AiGap151FirstSupportTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h2(self, persons, t20=60):
        self.engine.findings = []
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses(
            {"t20": t20, "pc": 3000},
            [{"dept_name": "电销六部", "refund_rate": 5,
              "signed_deals": 10, "avg_ai_score": 70}],
            [],
            persons,
        )
        return [h for h in self.engine.hypotheses if h["id"] == "H2"][0]

    def test_ai_gap_15_1_plus_equal_dials_is_partial_reject(self):
        # 80.1-65 == 15.1 > 15 is first AI-support after PR #122's
        # ==15 reject. Equal dials stay reject → 1==1 部分推翻, and
        # the empty-alternative branch names 挖需求 not 勤奋度.
        h2 = self._h2(_ten_persons(80.1, 65, 100, 100))
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertEqual(1, len(h2["support_evidence"]))
        self.assertEqual(1, len(h2["reject_evidence"]))
        self.assertTrue(any("能力差距显著" in e for e in h2["support_evidence"]))
        self.assertTrue(any("15.1分" in e for e in h2["support_evidence"]))
        self.assertTrue(any("拨打量接近" in e for e in h2["reject_evidence"]))
        self.assertIn("挖需求", h2["alternative"])
        self.assertNotIn("勤奋度", h2["alternative"])

    def test_ai_gap_15_1_plus_dials_just_over_is_first_support(self):
        # Both leftover just-over ticks together: 15.1 AI *and*
        # 131 > 100*1.3. 2>1 reject → 支持. Distinct from PR #80's
        # far both-support and PR #122's mixed 部分推翻.
        h2 = self._h2(_ten_persons(80.1, 65, 131, 100))
        self.assertEqual("支持", h2["verdict"])
        self.assertEqual(2, len(h2["support_evidence"]))
        self.assertEqual(0, len(h2["reject_evidence"]))
        self.assertIn("勤奋度", h2["alternative"])
        self.assertNotIn("挖需求", h2["alternative"])
        cards = [f for f in self.engine.findings if f.tag.startswith("假设验证")]
        self.assertEqual(1, len(cards))
        self.assertEqual("假设验证: 支持", cards[0].tag)


if __name__ == "__main__":
    unittest.main()
