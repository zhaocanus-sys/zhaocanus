"""Regression coverage for remaining LogicCollisionEngine edges.

Locks causal-chain bottleneck priority (beyond 触达效率), reverse-trace
cause selection / 正反向偏差, H2 部分推翻, and multi-perspective evidence
edges (t20 / complaints / CV) that do not themselves emit a finding.

Does not retest PR #79 触达效率+反向一致, or PR #80 H2-支持 / H3 /
ROI×退费 / 负荷×低ROI conflict verdicts as primary assertions.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def make_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "connect_rate": 45,
        "avg_connect_dur": 120,
        "deep_talk_rate": 18,
        "avg_ai_score": 72,
        "deep_talk": 40,
        "link_1d_num": 200,
        "allocated": 500,
        "avg_deal_amount": 5000,
        "conversion_rate": 2.0,
        "jx_conv_rate": 1.8,
        "jx_transfer_in": 10,
        "signed_deals": 10,
        "refund_rate": 3,
        "refund_amount": 5000,
        "total_revenue": 50000,
        "on_duty": 20,
        "dial_count": 800,
        "per_capita_revenue": 2500,
        "peak_hour_revenue": 7000,
        "offpeak_hour_revenue": 3000,
    }
    dept.update(overrides)
    return dept


def make_person(**overrides):
    person = {
        "name": "员工A",
        "tenure_months": 12,
        "ai_score": 75,
        "revenue": 3000,
        "dial_count": 80,
    }
    person.update(overrides)
    return person


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


def _evidence_blob(finding):
    return " | ".join(finding.evidence)


class MultiPerspectiveEvidenceTests(unittest.TestCase):
    """Evidence edges populate the finding only when a real conflict exists."""

    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _roi_refund_conflict(self, **summary_overrides):
        """Vehicle: ROI 健康 × 高退费 (already locked in PR #80)."""
        defaults = dict(
            roi=250,
            ref_rate=7,
            dial_count=10000,
            on_duty=100,
            t20=40,
            complaint_count=1,
        )
        defaults.update(summary_overrides)
        return make_summary(**defaults)

    def test_t20_above_55_attaches_mid_tier_evidence_on_conflict(self):
        depts = [
            make_dept(dept_name="电销一部", per_capita_revenue=3000),
            make_dept(dept_name="电销六部", per_capita_revenue=3000),
        ]
        self.engine._multi_perspective_collision(
            self._roi_refund_conflict(t20=56), depts
        )
        self.assertEqual(1, len(self.engine.findings))
        blob = _evidence_blob(self.engine.findings[0])
        self.assertIn("TOP20%占56%", blob)
        self.assertIn("中腰部", blob)

    def test_t20_at_55_does_not_attach_mid_tier_evidence(self):
        depts = [
            make_dept(dept_name="电销一部", per_capita_revenue=3000),
            make_dept(dept_name="电销六部", per_capita_revenue=3000),
        ]
        self.engine._multi_perspective_collision(
            self._roi_refund_conflict(t20=55), depts
        )
        self.assertEqual(1, len(self.engine.findings))
        blob = _evidence_blob(self.engine.findings[0])
        self.assertNotIn("中腰部", blob)
        self.assertNotIn("TOP20%", blob)

    def test_complaints_above_duty_share_attach_overpromise_evidence(self):
        depts = [
            make_dept(dept_name="电销一部", per_capita_revenue=3000),
            make_dept(dept_name="电销六部", per_capita_revenue=3000),
        ]
        # on_duty=100 → threshold 10; 11 fires
        self.engine._multi_perspective_collision(
            self._roi_refund_conflict(complaint_count=11), depts
        )
        self.assertEqual(1, len(self.engine.findings))
        blob = _evidence_blob(self.engine.findings[0])
        self.assertIn("投诉11件", blob)
        self.assertIn("话术过度承诺", blob)

    def test_complaints_at_duty_share_do_not_attach_overpromise_evidence(self):
        depts = [
            make_dept(dept_name="电销一部", per_capita_revenue=3000),
            make_dept(dept_name="电销六部", per_capita_revenue=3000),
        ]
        # 10 == on_duty*0.1 → not strictly greater
        self.engine._multi_perspective_collision(
            self._roi_refund_conflict(complaint_count=10), depts
        )
        self.assertEqual(1, len(self.engine.findings))
        blob = _evidence_blob(self.engine.findings[0])
        self.assertNotIn("投诉10件", blob)
        self.assertNotIn("话术过度承诺", blob)

    def test_high_per_capita_cv_attaches_dispersion_evidence(self):
        depts = [
            make_dept(dept_name="电销一部", per_capita_revenue=1000),
            make_dept(dept_name="电销六部", per_capita_revenue=2000),
        ]
        # mean=1500, sample stdev≈707, cv≈0.47 > 0.3
        self.engine._multi_perspective_collision(
            self._roi_refund_conflict(), depts
        )
        self.assertEqual(1, len(self.engine.findings))
        blob = _evidence_blob(self.engine.findings[0])
        self.assertIn("离散度高", blob)
        self.assertRegex(blob, r"CV=0\.[4-9]")

    def test_single_dept_or_low_cv_omits_dispersion_evidence(self):
        self.engine._multi_perspective_collision(
            self._roi_refund_conflict(),
            [make_dept(per_capita_revenue=3000)],
        )
        self.assertEqual(1, len(self.engine.findings))
        self.assertNotIn("离散度高", _evidence_blob(self.engine.findings[0]))

        self.engine.findings = []
        self.engine._multi_perspective_collision(
            self._roi_refund_conflict(),
            [
                make_dept(dept_name="电销一部", per_capita_revenue=3000),
                make_dept(dept_name="电销六部", per_capita_revenue=3100),
            ],
        )
        self.assertEqual(1, len(self.engine.findings))
        self.assertNotIn("离散度高", _evidence_blob(self.engine.findings[0]))

    def test_isolated_evidence_without_conflict_emits_no_finding(self):
        # t20 / complaints / CV all fire, but no ROI×退费 or 负荷×低ROI conflict
        summary = make_summary(
            roi=150,
            ref_rate=3,
            dial_count=10000,
            on_duty=100,
            t20=60,
            complaint_count=20,
        )
        depts = [
            make_dept(dept_name="电销一部", per_capita_revenue=1000),
            make_dept(dept_name="电销六部", per_capita_revenue=2000),
        ]
        self.engine._multi_perspective_collision(summary, depts)
        self.assertEqual([], self.engine.findings)


class CausalBottleneckPriorityTests(unittest.TestCase):
    """First warning node wins; later stages stay silent until upstream is healthy."""

    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _forward(self, **overrides):
        self.engine._build_causal_chains(make_summary(**overrides), [], [])
        return self.engine.causal_chains[0]

    def test_resource_input_wins_when_allocated_equals_duty_times_12(self):
        # allocated == on_duty*12 is not strictly greater → warning
        forward = self._forward(allocated=1200, on_duty=100, cr=45)
        self.assertEqual("资源输入", forward["bottleneck"])
        self.assertIn("资源输入", forward["diagnosis"])

    def test_session_depth_wins_when_upstream_is_healthy(self):
        forward = self._forward(dr=17)
        self.assertEqual("会话深度", forward["bottleneck"])
        self.assertIn("会话深度", forward["diagnosis"])

    def test_conversion_wins_when_upstream_is_healthy(self):
        forward = self._forward(conv=0.9)
        self.assertEqual("转化产出", forward["bottleneck"])
        self.assertIn("转化产出", forward["diagnosis"])

    def test_quality_wins_when_only_refund_is_warning(self):
        forward = self._forward(ref_rate=6)
        self.assertEqual("质量保障", forward["bottleneck"])
        self.assertIn("质量保障", forward["diagnosis"])

    def test_healthy_forward_chain_has_no_bottleneck(self):
        forward = self._forward()
        self.assertNotIn("bottleneck", forward)
        self.assertNotIn("diagnosis", forward)
        self.assertTrue(all(n["status"] == "normal" for n in forward["nodes"]))


class ReverseTraceCauseTests(unittest.TestCase):
    """pc<4000 reverse-trace cause order and 正反向一致性."""

    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _reverse(self):
        return next(
            c for c in self.engine.causal_chains if c.get("direction") == "反向"
        )

    def test_deep_talk_is_primary_reverse_cause_when_connect_is_healthy(self):
        self.engine._build_causal_chains(
            make_summary(pc=3200, cr=45, dr=15, ai=75, t20=40), [], []
        )
        reverse = self._reverse()
        self.assertTrue(reverse["possible_causes"][0].startswith("深沟率"))
        self.assertEqual("正反向因果链一致", reverse["consistency_check"])
        finding = next(f for f in self.engine.findings if f.tag == "因果链追溯")
        self.assertEqual("P1", finding.priority)
        self.assertIn("深沟率", finding.description)

    def test_ai_only_reverse_cause_marks_forward_reverse_inconsistency(self):
        self.engine._build_causal_chains(
            make_summary(pc=3200, ai=65, t20=40), [], []
        )
        reverse = self._reverse()
        self.assertEqual(1, len(reverse["possible_causes"]))
        self.assertTrue(reverse["possible_causes"][0].startswith("AI均分"))
        self.assertIn("偏差", reverse["consistency_check"])
        finding = next(f for f in self.engine.findings if f.tag == "因果链追溯")
        self.assertIn("偏差", finding.description)
        self.assertIn("AI均分", finding.description)

    def test_t20_only_reverse_cause_marks_inconsistency(self):
        self.engine._build_causal_chains(
            make_summary(pc=3200, t20=56), [], []
        )
        reverse = self._reverse()
        self.assertTrue(any("TOP20%" in c for c in reverse["possible_causes"]))
        self.assertTrue(reverse["possible_causes"][0].startswith("TOP20%"))
        self.assertIn("偏差", reverse["consistency_check"])

    def test_healthy_per_capita_skips_reverse_chain_and_finding(self):
        self.engine._build_causal_chains(
            make_summary(pc=4000, cr=30, dr=10, ai=60, t20=60), [], []
        )
        self.assertFalse(
            any(c.get("direction") == "反向" for c in self.engine.causal_chains)
        )
        self.assertFalse(any(f.tag == "因果链追溯" for f in self.engine.findings))


class H2PartialRejectTests(unittest.TestCase):
    """t20 集中但能力/活动量差距不大 → 部分推翻，归因到转化环节。"""

    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_h2_partially_rejects_when_ai_and_dials_gaps_are_small(self):
        persons = [
            make_person(name="T1", revenue=10000, ai_score=75, dial_count=80),
            make_person(name="T2", revenue=9000, ai_score=74, dial_count=82),
            make_person(name="M1", revenue=5000, ai_score=73, dial_count=80),
            make_person(name="M2", revenue=4500, ai_score=72, dial_count=79),
            make_person(name="M3", revenue=4000, ai_score=71, dial_count=78),
            make_person(name="M4", revenue=3500, ai_score=71, dial_count=78),
            make_person(name="M5", revenue=3000, ai_score=70, dial_count=77),
            make_person(name="B1", revenue=1000, ai_score=70, dial_count=78),
            make_person(name="B2", revenue=900, ai_score=69, dial_count=76),
            make_person(name="B3", revenue=800, ai_score=68, dial_count=75),
        ]
        self.engine._build_and_test_hypotheses(
            make_summary(t20=60, pc=4000), [], [], persons
        )
        h2 = next(h for h in self.engine.hypotheses if h["id"] == "H2")
        self.assertEqual("部分推翻", h2["verdict"])
        self.assertTrue(h2["reject_evidence"])
        self.assertIn("挖需求", h2["alternative"])
        finding = next(f for f in self.engine.findings if "假设验证" in f.tag)
        self.assertEqual("P1", finding.priority)
        self.assertIn("部分推翻", finding.description)
        self.assertIn("挖需求", finding.description)

    def test_h2_is_skipped_when_t20_is_not_above_50(self):
        persons = [
            make_person(name=f"P{i}", revenue=1000 * (10 - i), ai_score=90, dial_count=120)
            for i in range(10)
        ]
        self.engine._build_and_test_hypotheses(
            make_summary(t20=50), [], [], persons
        )
        self.assertFalse(any(h["id"] == "H2" for h in self.engine.hypotheses))
        self.assertFalse(any("假设验证" in f.tag for f in self.engine.findings))


if __name__ == "__main__":
    unittest.main()
