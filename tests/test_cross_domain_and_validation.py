"""Regression coverage for CrossDomain matrix gates and logic cross-validation.

Covers gated CrossDomainCollisionEngine matrix triggers (beyond refund
enrichment), funnel P0 super-collision enrichment, and
LogicCollisionEngine alternative-explanation paths for P0 data findings.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.collision_engine import (
    CollisionFinding,
    CrossDomainCollisionEngine,
    LogicCollisionEngine,
)


def make_summary(**overrides):
    summary = {
        "dr": 10,
        "conv": 2.0,
        "avg_deal": 6000,
        "t20": 40,
        "fc_rate": 5.0,
        "ai": 80,
        "ref_rate": 3.0,
    }
    summary.update(overrides)
    return summary


def make_dept(name="电销一部", per_capita_revenue=2500):
    return {
        "dept_name": name,
        "per_capita_revenue": per_capita_revenue,
    }


def finding(tag, priority="P0", description="原始发现描述"):
    return CollisionFinding(
        collision_type="metric_x_metric",
        tag=tag,
        description=description,
        revenue_impact=1000,
        priority=priority,
    )


class CrossDomainMatrixGateTests(unittest.TestCase):
    def setUp(self):
        self.engine = CrossDomainCollisionEngine()

    def _tags(self, findings=None):
        src = findings if findings is not None else self.engine.findings
        return {f.tag for f in src}

    def test_gated_sales_psychology_triggers_and_silence(self):
        # Healthy baseline: no gated sales×psychology rules should fire.
        healthy = make_summary()
        self.engine.execute(healthy, [make_dept()], [], [])
        healthy_tags = self._tags()
        self.assertNotIn("SPIN暗示问题×损失厌恶", healthy_tags)
        self.assertNotIn("挑战式销售×锚定效应", healthy_tags)
        self.assertNotIn("影响力社会认同×从众效应", healthy_tags)
        self.assertNotIn("信任构建×非暴力沟通共情", healthy_tags)

        # Gated sales×psychology thresholds.
        self.engine.execute(
            make_summary(dr=16, conv=1.0, avg_deal=5000, t20=55, fc_rate=2.0),
            [make_dept()],
            [],
            [],
        )
        tags = self._tags()
        self.assertIn("SPIN暗示问题×损失厌恶", tags)
        self.assertIn("挑战式销售×锚定效应", tags)
        self.assertIn("影响力社会认同×从众效应", tags)
        self.assertIn("信任构建×非暴力沟通共情", tags)

        spin = next(f for f in self.engine.findings if f.tag == "SPIN暗示问题×损失厌恶")
        self.assertEqual("P1", spin.priority)
        self.assertEqual("cross_domain:sales_x_psychology", spin.collision_type)
        self.assertIn("16%", spin.description)
        self.assertIn("1.0%", spin.description)

    def test_telesale_management_and_dept_spread_gates(self):
        # AI healthy + balanced depts → no AI质检 / 话术标准化 spread finding.
        self.engine.execute(
            make_summary(ai=80),
            [
                make_dept("电销一部", 2500),
                make_dept("电销二部", 2600),
            ],
            [],
            [],
        )
        tags = self._tags()
        self.assertNotIn("质检AI化×复盘四步法", tags)
        self.assertNotIn("话术标准化×优势管理", tags)

        # AI below 75 + extreme department spread → both fire.
        self.engine.execute(
            make_summary(ai=70),
            [
                make_dept("电销一部", 5000),
                make_dept("电销二部", 2000),
            ],
            [],
            [],
        )
        tags = self._tags()
        self.assertIn("质检AI化×复盘四步法", tags)
        self.assertIn("话术标准化×优势管理", tags)

        ai_finding = next(f for f in self.engine.findings if f.tag == "质检AI化×复盘四步法")
        self.assertEqual("P1", ai_finding.priority)
        self.assertIn("70", ai_finding.description)

    def test_ops_simpson_and_turnaround_conditional_gates(self):
        # Fewer than 4 depts → 辛普森 / 271 不触发；低退费+健康产值 → 品牌修复/飞轮静默
        self.engine.execute(
            make_summary(t20=60, ref_rate=3),
            [
                make_dept("电销一部", 2500),
                make_dept("电销二部", 2500),
                make_dept("电销三部", 2500),
            ],
            [],
            [],
        )
        tags = self._tags()
        self.assertNotIn("辛普森悖论×二八法则", tags)
        self.assertNotIn("271法则×自然代谢替代裁员", tags)
        self.assertNotIn("客户成功×品牌修复信任链", tags)
        self.assertNotIn("飞轮效应×困境六悖论", tags)

        # 4+ depts, high TOP集中度, high退费, low-productivity dept → all fire
        self.engine.execute(
            make_summary(t20=58, ref_rate=5.5),
            [
                make_dept("电销一部", 3000),
                make_dept("电销二部", 2800),
                make_dept("电销三部", 2600),
                make_dept("电销四部", 900),
            ],
            [],
            [],
        )
        tags = self._tags()
        self.assertIn("辛普森悖论×二八法则", tags)
        self.assertIn("271法则×自然代谢替代裁员", tags)
        self.assertIn("客户成功×品牌修复信任链", tags)
        self.assertIn("飞轮效应×困境六悖论", tags)

        refund_brand = next(
            f for f in self.engine.findings if f.tag == "客户成功×品牌修复信任链"
        )
        self.assertEqual("P1", refund_brand.priority)
        self.assertIn("5.5%", refund_brand.description)
        self.assertTrue(any("退费" in r or "信任" in r for r in refund_brand.recommendations))

    def test_always_on_domains_and_summary_counts(self):
        findings = self.engine.execute(make_summary(), [make_dept()], [], [])
        tags = self._tags(findings)

        # Always-true matrix rules should still fire for baseline coverage.
        self.assertIn("狼性PK×内在动机驱动力", tags)
        self.assertIn("指标陷阱×TOC约束瓶颈", tags)
        self.assertIn("Hook上瘾模型×社交天性连接需求", tags)
        self.assertIn("杠铃策略×现金流红线", tags)

        summary = self.engine.get_summary()
        self.assertEqual(len(findings), summary["findings_count"])
        self.assertEqual(self.engine.collision_count, summary["total_collisions"])
        self.assertGreaterEqual(summary["domains_count"], 3)
        self.assertTrue(summary["matrices_loaded"])
        self.assertEqual(
            summary["findings_by_priority"]["P1"]
            + summary["findings_by_priority"]["P2"]
            + summary["findings_by_priority"]["P0"],
            summary["findings_count"],
        )

    def test_trigger_exception_is_isolated(self):
        # Missing per_capita_revenue would raise inside dept-spread / flywheel triggers.
        # execute() must swallow trigger errors and continue other rules.
        broken_depts = [{"dept_name": "电销一部"}]
        findings = self.engine.execute(make_summary(ai=70), broken_depts, [], [])
        tags = {f.tag for f in findings}
        self.assertIn("质检AI化×复盘四步法", tags)
        self.assertNotIn("话术标准化×优势管理", tags)
        self.assertNotIn("飞轮效应×困境六悖论", tags)


class CrossDomainEnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = CrossDomainCollisionEngine()

    def test_funnel_p0_triggers_toc_bayes_super_collision(self):
        data_findings = [
            finding("漏斗瓶颈:接通→深沟", priority="P0", description="接通到深沟转化偏低"),
            finding("普通波动", priority="P1"),
        ]
        self.engine._enrich_from_data_findings(data_findings, make_summary())

        supers = [
            f for f in self.engine.findings
            if f.collision_type == "cross_domain:super_collision"
        ]
        self.assertEqual(1, len(supers))
        self.assertEqual("漏斗瓶颈×TOC约束×贝叶斯迭代", supers[0].tag)
        self.assertEqual("P1", supers[0].priority)
        self.assertIn("TOC", supers[0].description)
        self.assertIn("超级对撞", self.engine.domains_used)
        self.assertEqual(1, self.engine.collision_count)

    def test_non_p0_funnel_does_not_enrich(self):
        self.engine._enrich_from_data_findings(
            [finding("漏斗瓶颈", priority="P1")],
            make_summary(),
        )
        self.assertEqual([], self.engine.findings)


class LogicCrossValidationTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def test_generate_alternative_for_known_tags(self):
        self.assertIn(
            "运营商",
            self.engine._generate_alternative(finding("低接通·长通话"), {}, []),
        )
        self.assertIn(
            "7日",
            self.engine._generate_alternative(finding("漏斗瓶颈:分配→接通"), {}, []),
        )
        self.assertIn(
            "大单",
            self.engine._generate_alternative(finding("高活动高营收异常"), {}, []),
        )
        self.assertIsNone(
            self.engine._generate_alternative(finding("深沟率偏低"), {}, [])
        )

    def test_cross_validate_emits_p2_only_for_p0_with_alternative(self):
        data_findings = [
            finding("接通率持续低于红线", priority="P0", description="电销六部接通率连续偏低"),
            finding("漏斗瓶颈:接通→深沟", priority="P0", description="漏斗薄弱"),
            finding("高活动高营收异常", priority="P0", description="营收冲高"),
            finding("深沟率偏低", priority="P0", description="无替代解释标签"),
            finding("接通率波动", priority="P1", description="非P0应忽略"),
        ]

        self.engine._cross_validate_with_data_findings(
            data_findings, make_summary(), [make_dept()]
        )

        self.assertEqual(3, len(self.engine.findings))
        for f in self.engine.findings:
            self.assertEqual("cross_validation", f.collision_type)
            self.assertEqual("P2", f.priority)
            self.assertTrue(f.tag.startswith("验证:"))
            self.assertIn("替代解释", f.description)
            self.assertTrue(any("原始发现" in e for e in f.evidence))

        tags = {f.tag for f in self.engine.findings}
        self.assertIn("验证: 接通率持续低于红线", tags)
        self.assertIn("验证: 漏斗瓶颈:接通→深沟", tags)
        self.assertIn("验证: 高活动高营收异常", tags)
        self.assertNotIn("验证: 深沟率偏低", tags)
        self.assertNotIn("验证: 接通率波动", tags)

    def test_cross_validate_noop_without_p0(self):
        self.engine._cross_validate_with_data_findings(
            [finding("接通率波动", priority="P1")],
            make_summary(),
            [make_dept()],
        )
        self.assertEqual([], self.engine.findings)


if __name__ == "__main__":
    unittest.main()
