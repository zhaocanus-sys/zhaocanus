"""Regression coverage for DataExpert consumption of sorted findings.

Covers:
- get_findings_json preserves P0→P1→P2 / revenue ordering and scope metadata
- get_executive_summary lists only P0 findings, in sorted order
- render_html separates global vs dept findings and surfaces manager names

Deterministic stdlib unittest; no network or live database required.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_system.agents.data_expert import DataExpert
from agent_system.engines.analysis_pipeline import AnalysisReport
from agent_system.engines.collision_engine import CollisionFinding


def make_finding(
    priority: str,
    revenue_impact: float,
    tag: str,
    *,
    scope: str = "global",
    dept_name: str = "",
    manager_name: str = "",
    management_gap: str = "",
    collision_type: str = "metric_x_metric",
) -> CollisionFinding:
    return CollisionFinding(
        collision_type=collision_type,
        tag=tag,
        description=f"{tag} detail for {priority}",
        revenue_impact=revenue_impact,
        priority=priority,
        evidence=["e1"],
        recommendations=["r1", "r2"],
        knowledge_refs=["kb1"],
        scope=scope,
        dept_name=dept_name,
        manager_name=manager_name,
        management_gap=management_gap,
    )


def make_summary(**overrides):
    summary = {
        "date": "2026-02-27",
        "head_count": 20,
        "on_duty": 18,
        "allocated": 200,
        "alloc_rate": 0.9,
        "dial_count": 600,
        "link_1d_num": 84,
        "deep_talk": 18,
        "total_revenue": 100000,
        "signed_deals": 10,
        "avg_deal": 10000,
        "refund_count": 1,
        "refund_amount": 3000,
        "complaint_count": 0,
        "jx_transfer_in": 5,
        "jx_signed": 1,
        "jx_cr": 20.0,
        "pool_retrieval": 10,
        "pool_signed": 2,
        "p_cr": 20.0,
        "peak_pct": 55.0,
        "t20": 48.0,
        "pc": 5500,
        "cr": 42.0,
        "dr": 21.4,
        "ai": 78.0,
        "conv": 2.5,
        "ref_rate": 3.0,
        "rev_dod": -2.0,
        "pc_dod": 1.0,
        "cr_dod": 0.0,
    }
    summary.update(overrides)
    return summary


def make_report(
    findings_data=None,
    findings_logic=None,
    findings_cross=None,
) -> AnalysisReport:
    data = findings_data if findings_data is not None else []
    logic = findings_logic if findings_logic is not None else []
    cross = findings_cross if findings_cross is not None else []
    return AnalysisReport(
        date="2026-02-27",
        summary=make_summary(),
        departments=[
            {
                "dept_name": "电销六部",
                "total_revenue": 50000,
                "per_capita_revenue": 5000,
                "connect_rate": 38.0,
                "deep_talk_rate": 18.0,
                "avg_ai_score": 72,
                "conversion_rate": 2.0,
                "signed_deals": 4,
                "top20_pct": 60,
                "refund_rate": 5.0,
                "team_roi": 40,
            }
        ],
        trends=[
            {
                "dt": "2026-02-26",
                "total_revenue": 90000,
                "pc": 5000,
                "cr": 41.0,
                "conv": 2.2,
                "dr": 18.0,
                "rr": 2.5,
                "dials_pp": 35.0,
            },
            {
                "dt": "2026-02-27",
                "total_revenue": 100000,
                "pc": 5500,
                "cr": 42.0,
                "conv": 2.5,
                "dr": 19.0,
                "rr": 3.0,
                "dials_pp": 36.0,
            },
        ],
        persons=[],
        top_performers=[],
        bottom_performers=[],
        new_hire_stats=[],
        tenure_analysis={},
        data_collision_findings=data,
        data_collision_summary={
            "total_collisions": len(data),
            "collision_types": ["metric_x_metric"],
        },
        logic_collision_findings=logic,
        logic_collision_summary={
            "total_hypotheses": 1,
            "hypotheses_supported": 1,
            "hypotheses_rejected": 0,
            "causal_chains": 0,
        },
        cross_domain_findings=cross,
        cross_domain_summary={
            "total_collisions": len(cross),
            "domains_count": 1,
            "domains_used": ["销售精通"],
        },
        hypotheses=[],
        causal_chains=[],
        improvements=[
            {
                "p": "P0",
                "title": "提升接通率",
                "cur": "42%",
                "tgt": "45%",
                "rev": 5200,
                "act": "晨会通关",
                "detail": "细节",
                "deploy_date": "2026-02-28",
                "target_entity": "电销六部全员",
                "daily_action": "晨会播放1条标杆录音",
                "duration_days": 14,
                "milestone": "第7天中期检查",
                "feasibility": "high",
                "dependency": "self_contained",
                "risk_notes": "业务自闭环",
            }
        ],
        total_uplift=5200,
        funnel=[("分配→拨打", 3.0, 3.0, "拨打倍率")],
        pc_cv=0.2,
    )


class DataExpertFindingsConsumptionTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = str(Path(self._tmpdir.name) / "unused.db")
        Path(db_path).touch()
        self.expert = DataExpert(
            db_path,
            dept_managers={
                "电销六部": "游云清",
                "电销四部": "宋晓鹏",
            },
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_get_findings_json_preserves_sort_and_scope_metadata(self):
        report = make_report(
            findings_data=[
                make_finding("P1", 100, "data-p1", scope="global"),
                make_finding(
                    "P0",
                    50,
                    "data-p0-dept",
                    scope="dept",
                    dept_name="电销六部",
                    manager_name="游云清",
                    management_gap="缺乏号码健康度管理意识",
                ),
            ],
            findings_logic=[
                make_finding("P2", 999, "logic-p2"),
                make_finding("P0", 200, "logic-p0-high"),
            ],
            findings_cross=[
                make_finding(
                    "P1",
                    500,
                    "xd-p1",
                    collision_type="cross_domain_sales_psych",
                ),
            ],
        )

        payload = self.expert.get_findings_json(report)
        tags = [item["tag"] for item in payload]

        self.assertEqual(
            ["logic-p0-high", "data-p0-dept", "xd-p1", "data-p1", "logic-p2"],
            tags,
        )
        dept_item = next(item for item in payload if item["tag"] == "data-p0-dept")
        self.assertEqual("dept", dept_item["scope"])
        self.assertEqual("电销六部", dept_item["dept_name"])
        self.assertEqual("游云清", dept_item["manager_name"])
        self.assertEqual("缺乏号码健康度管理意识", dept_item["management_gap"])

        global_item = next(item for item in payload if item["tag"] == "logic-p0-high")
        self.assertEqual("global", global_item["scope"])
        self.assertNotIn("manager_name", global_item)

    def test_executive_summary_lists_only_sorted_p0_findings(self):
        report = make_report(
            findings_data=[
                make_finding("P1", 800, "skip-p1"),
                make_finding("P0", 100, "p0-low"),
            ],
            findings_logic=[
                make_finding("P0", 300, "p0-high"),
                make_finding("P2", 9000, "skip-p2"),
            ],
        )

        text = self.expert.get_executive_summary(report)

        self.assertIn("总发现: 4项 (P0:2项)", text)
        p0_section = text.split(">> P0级紧急问题")[1].split(">> TOP3改善建议")[0]
        self.assertIn("* p0-high:", p0_section)
        self.assertIn("* p0-low:", p0_section)
        self.assertNotIn("skip-p1", p0_section)
        self.assertNotIn("skip-p2", p0_section)
        self.assertLess(p0_section.index("p0-high"), p0_section.index("p0-low"))
        self.assertIn("提升接通率", text)
        self.assertIn("日增Y5,200", text)

    def test_render_html_separates_global_and_dept_findings_with_managers(self):
        report = make_report(
            findings_data=[
                make_finding(
                    "P0",
                    400,
                    "global-funnel",
                    scope="global",
                    collision_type="funnel_x_benchmark",
                ),
                make_finding(
                    "P0",
                    300,
                    "dept-六部接通",
                    scope="dept",
                    dept_name="电销六部",
                    manager_name="游云清",
                    management_gap="缺乏号码健康度和外呼时段精细化管理意识",
                ),
                make_finding(
                    "P1",
                    200,
                    "dept-四部退费",
                    scope="dept",
                    dept_name="电销四部",
                    manager_name="宋晓鹏",
                    management_gap="对签单话术合规性监管不足",
                    collision_type="metric_x_metric",
                ),
            ],
        )

        html = self.expert.render_html(report)

        self.assertIn("全局诊断 · 1项发现", html)
        self.assertIn("部门级诊断 · 2项发现", html)
        self.assertIn("global-funnel", html)
        self.assertIn("dept-六部接通", html)
        self.assertIn("dept-四部退费", html)

        # Global and dept columns must remain separate headings (management rule 1).
        global_idx = html.index("全局诊断")
        dept_idx = html.index("部门级诊断")
        self.assertLess(global_idx, dept_idx)
        self.assertLess(html.index("global-funnel"), dept_idx)
        self.assertGreater(html.index("dept-六部接通"), dept_idx)

        # Dept sections show manager labels from DataExpert.managers mapping.
        self.assertIn("电销六部 · 负责人: 游云清", html)
        self.assertIn("电销四部 · 负责人: 宋晓鹏", html)
        self.assertIn("管理视角评估 [游云清]", html)
        self.assertIn("缺乏号码健康度和外呼时段精细化管理意识", html)
        self.assertIn("管理视角评估 [宋晓鹏]", html)

        # Departments are rendered in sorted(name) order (Unicode: 六 before 四).
        self.assertLess(html.index("电销六部 · 负责人"), html.index("电销四部 · 负责人"))
        self.assertEqual(["电销六部", "电销四部"], sorted(["电销四部", "电销六部"]))


if __name__ == "__main__":
    unittest.main()
