"""Regression coverage for leftover H2 mixed evidence + reverse-trace equality.

PR #80 locked H2 支持 (AI gap>15 AND dials>1.3x).
PR #108 locked H2 部分推翻 when both gaps are small, and reverse-trace
fire (深沟 / AI-only / t20-only) plus pc>=4000 skip.

Remaining operators were never the primary lock:

- AI gap == 15 is reject evidence (need > 15)
- dials == 1.3x is reject evidence (need >)
- mixed 1-support + 1-reject → 部分推翻 (reject >= support)
- empty / 3-person roster + t20>50 still emits 部分推翻
- reverse-trace cr==43 / dr==18 / ai==70 / t20==55 with pc<4000
  produces no 因果链追溯 (all four need strict inequality)

A flipped verdict `>=` to `>` would promote mixed evidence to 支持
and push a false 底部能力不足 card. Empty-roster H2 would diagnose
a department with no staff. Flipping reverse `<`/`>` to inclusive
would emit 因果链追溯 the day every KPI sits on its redline.

Does not retest PR #80 both-support or PR #108 both-small / fire
wording as primary.
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


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "refund_rate": 5,
        "signed_deals": 10,
        "avg_ai_score": 70,
        "per_capita_revenue": 3000,
    }
    dept.update(overrides)
    return dept


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


def _healthy_forward_summary(**overrides):
    # allocated > on_duty*12 so 资源输入 is normal; other forward
    # nodes sit on-or-above their redlines so no bottleneck.
    summary = {
        "allocated": 1300,
        "on_duty": 100,
        "alloc_rate": 0.9,
        "cr": 43,
        "dial_count": 8000,
        "dr": 18,
        "ai": 70,
        "conv": 1.0,
        "signed_deals": 20,
        "total_revenue": 399900,
        "pc": 3999,
        "ref_rate": 5,
        "complaint_count": 1,
        "t20": 55,
    }
    summary.update(overrides)
    return summary


class H2MixedAndEmptyRosterTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h2(self, persons, t20=60):
        self.engine._build_and_test_hypotheses(
            {"t20": t20, "pc": 3000},
            [make_dept()],
            [],
            persons,
        )
        return [f for f in self.engine.findings if f.tag.startswith("假设验证")]

    def test_ai_gap_exactly_15_is_reject_evidence(self):
        findings = self._h2(_ten_persons(top_ai=80, bot_ai=65, top_dials=100, bot_dials=100))
        self.assertEqual(1, len(findings))
        blob = " ".join(findings[0].evidence)
        self.assertIn("差距仅15.0分", blob)
        self.assertNotIn("能力差距显著", blob)

    def test_dials_exactly_1_3x_is_reject_evidence(self):
        findings = self._h2(_ten_persons(top_ai=70, bot_ai=70, top_dials=130, bot_dials=100))
        self.assertEqual(1, len(findings))
        blob = " ".join(findings[0].evidence)
        self.assertIn("拨打量接近", blob)
        self.assertNotIn("活动量差距明显", blob)

    def test_mixed_ai_support_and_dials_reject_is_partial_reject(self):
        # AI 16 > 15 support; dials 130 == 1.3x reject. 1>=1 → 部分推翻.
        findings = self._h2(_ten_persons(top_ai=81, bot_ai=65, top_dials=130, bot_dials=100))
        self.assertEqual(1, len(findings))
        self.assertEqual("假设验证: 部分推翻", findings[0].tag)
        self.assertIn("挖需求", findings[0].description)
        self.assertNotIn("勤奋度", findings[0].description)
        h2 = [h for h in self.engine.hypotheses if h["id"] == "H2"][0]
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertEqual(1, len(h2["support_evidence"]))
        self.assertEqual(1, len(h2["reject_evidence"]))

    def test_mixed_dials_support_and_ai_reject_keeps_effort_alternative(self):
        # AI gap 10 reject; dials 131 > 130 support. Still 部分推翻,
        # but alternative stays on the dials-support branch.
        findings = self._h2(_ten_persons(top_ai=75, bot_ai=65, top_dials=131, bot_dials=100))
        self.assertEqual(1, len(findings))
        self.assertEqual("假设验证: 部分推翻", findings[0].tag)
        self.assertIn("勤奋度", findings[0].description)
        self.assertNotIn("挖需求", findings[0].description)

    def test_empty_roster_with_high_t20_still_emits_partial_reject(self):
        findings = self._h2([], t20=60)
        self.assertEqual(1, len(findings))
        self.assertEqual("假设验证: 部分推翻", findings[0].tag)
        blob = " ".join(findings[0].evidence)
        self.assertIn("差距仅0.0分", blob)
        self.assertIn("拨打量接近", blob)
        self.assertEqual(0, findings[0].revenue_impact)

    def test_three_person_roster_has_empty_top_and_bottom_slices(self):
        # int(3*0.3)=0 and int(3*0.2)=0 → same empty-slice path.
        persons = [
            make_person(name="A", revenue=9000, ai_score=90, dial_count=200),
            make_person(name="B", revenue=4000, ai_score=70, dial_count=100),
            make_person(name="C", revenue=1000, ai_score=40, dial_count=50),
        ]
        findings = self._h2(persons, t20=60)
        self.assertEqual(1, len(findings))
        self.assertEqual("假设验证: 部分推翻", findings[0].tag)
        blob = " ".join(findings[0].evidence)
        self.assertIn("差距仅0.0分", blob)


class ReverseTraceExactRedlineSilenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_all_four_reverse_causes_exactly_on_redline_are_silent(self):
        # pc=3999 still enters the reverse block; all four cause
        # gates sit exactly on the redline and stay off.
        self.engine._build_causal_chains(
            _healthy_forward_summary(),
            [make_dept()],
            [],
        )
        self.assertEqual([], [f for f in self.engine.findings if f.tag == "因果链追溯"])
        self.assertEqual(1, len(self.engine.causal_chains))
        self.assertEqual("营收因果链", self.engine.causal_chains[0]["name"])
        self.assertNotIn("bottleneck", self.engine.causal_chains[0])
        self.assertEqual(1, len(self.engine.causal_chains))


if __name__ == "__main__":
    unittest.main()
