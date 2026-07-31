"""Regression coverage for DataExpert HTML render boundaries.

Covers:
- Inline KPI spark: empty / single-point / flat series stay finite
- Day-over-day arrow markers for up / down / flat deltas
- Improvement cards emit time-dimension execution instructions
- Missing deploy/daily fields suppress the execution block

Deterministic stdlib unittest; no network or live database required.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from agent_system.agents.data_expert import DataExpert
from agent_system.engines.analysis_pipeline import AnalysisReport


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
        "rev_dod": 3.5,
        "pc_dod": -1.2,
        "cr_dod": 0.0,
    }
    summary.update(overrides)
    return summary


def make_trend(dt, **overrides):
    row = {
        "dt": dt,
        "total_revenue": 100000,
        "pc": 5500,
        "cr": 42.0,
        "conv": 2.5,
        "dr": 19.0,
        "rr": 3.0,
        "dials_pp": 36.0,
    }
    row.update(overrides)
    return row


def make_report(trends=None, improvements=None, summary_overrides=None) -> AnalysisReport:
    return AnalysisReport(
        date="2026-02-27",
        summary=make_summary(**(summary_overrides or {})),
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
        trends=trends if trends is not None else [
            make_trend("2026-02-26", total_revenue=90000, cr=41.0, conv=2.2),
            make_trend("2026-02-27"),
        ],
        persons=[],
        top_performers=[],
        bottom_performers=[],
        new_hire_stats=[],
        tenure_analysis={},
        data_collision_findings=[],
        data_collision_summary={
            "total_collisions": 0,
            "collision_types": [],
        },
        logic_collision_findings=[],
        logic_collision_summary={
            "total_hypotheses": 0,
            "hypotheses_supported": 0,
            "hypotheses_rejected": 0,
            "causal_chains": 0,
        },
        cross_domain_findings=[],
        cross_domain_summary={
            "total_collisions": 0,
            "domains_count": 0,
            "domains_used": [],
        },
        hypotheses=[],
        causal_chains=[],
        improvements=improvements if improvements is not None else [],
        total_uplift=0,
        funnel=[("分配→拨打", 3.0, 3.0, "拨打倍率")],
        pc_cv=0.2,
    )


def _polyline_points(html: str) -> list[str]:
    return re.findall(r'<polyline points="([^"]*)"', html)


def _assert_finite_points(testcase: unittest.TestCase, points: str):
    testcase.assertTrue(points.strip())
    for token in points.split():
        x_str, y_str = token.split(",")
        x = float(x_str)
        y = float(y_str)
        testcase.assertTrue(x == x and y == y, f"non-finite point: {token}")
        testcase.assertNotIn("nan", token.lower())
        testcase.assertNotIn("inf", token.lower())


class DataExpertRenderBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = str(Path(self._tmpdir.name) / "unused.db")
        Path(db_path).touch()
        self.expert = DataExpert(
            db_path,
            dept_managers={"电销六部": "游云清"},
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_empty_trends_omit_kpi_sparklines_without_crash(self):
        html = self.expert.render_html(make_report(trends=[]))
        self.assertIn("数据专家诊断报告", html)
        # Nested spark returns "" when vals is empty — no polyline under KPI.
        self.assertEqual(_polyline_points(html), [])

    def test_single_point_trend_renders_finite_sparkline(self):
        html = self.expert.render_html(
            make_report(trends=[make_trend("2026-02-27", total_revenue=88000, cr=40.0)])
        )
        points = _polyline_points(html)
        self.assertGreaterEqual(len(points), 1)
        for pts in points:
            _assert_finite_points(self, pts)

    def test_flat_trend_series_avoids_zero_range_division(self):
        flat = [
            make_trend("2026-02-25"),
            make_trend("2026-02-26"),
            make_trend("2026-02-27"),
        ]
        html = self.expert.render_html(make_report(trends=flat))
        points = _polyline_points(html)
        self.assertGreaterEqual(len(points), 1)
        for pts in points:
            _assert_finite_points(self, pts)
            ys = [float(token.split(",")[1]) for token in pts.split()]
            # Flat series maps every point to the same padded y.
            self.assertEqual(len(set(ys)), 1)

    def test_dod_arrows_render_up_down_and_flat(self):
        # Only revenue / per-capita KPI cards render DoD arrows.
        html = self.expert.render_html(
            make_report(summary_overrides={"rev_dod": 3.5, "pc_dod": 0.0})
        )
        self.assertIn("▲+3.5%", html)
        self.assertIn("—", html)
        self.assertNotIn("▼", html)

        html_down = self.expert.render_html(
            make_report(summary_overrides={"rev_dod": -2.0, "pc_dod": 1.5})
        )
        self.assertIn("▼-2.0%", html_down)
        self.assertIn("▲+1.5%", html_down)

    def test_improvement_time_instructions_rendered_when_complete(self):
        improvements = [
            {
                "p": "P0",
                "title": "接通率修复至43%",
                "cur": "42%",
                "tgt": "43%",
                "act": "排查号码标记",
                "detail": "细节",
                "rev": 5200,
                "deploy_date": "2026-02-28",
                "target_entity": "电销六部全员",
                "daily_action": "晨会播放1条标杆录音+午间话术通关测试",
                "duration_days": 14,
                "milestone": "第7天中期检查，第14天验收",
                "feasibility": "high",
                "dependency": "self_contained",
                "risk_notes": "业务自闭环",
            }
        ]
        html = self.expert.render_html(make_report(improvements=improvements))
        self.assertIn("执行指令", html)
        self.assertIn("部署日期: 2026-02-28", html)
        self.assertIn("对象: 电销六部全员", html)
        self.assertIn("每日执行: 晨会播放1条标杆录音+午间话术通关测试", html)
        self.assertIn("坚持周期: 14天", html)
        self.assertIn("里程碑: 第7天中期检查，第14天验收", html)
        self.assertIn("可行性: 高可行", html)
        self.assertIn("自闭环", html)

    def test_improvement_time_block_omitted_without_deploy_or_daily(self):
        improvements = [
            {
                "p": "P1",
                "title": "缺少执行字段的建议",
                "cur": "1%",
                "tgt": "2%",
                "act": "动作",
                "detail": "细节",
                "rev": 1000,
                "deploy_date": "2026-02-28",
                # daily_action intentionally absent
                "duration_days": 7,
                "milestone": "第7天",
                "feasibility": "medium",
                "dependency": "cross_dept",
                "risk_notes": "跨部门协调成本高",
            }
        ]
        html = self.expert.render_html(make_report(improvements=improvements))
        self.assertNotIn("执行指令", html)
        self.assertNotIn("部署日期:", html)
        self.assertIn("可行性: 中可行", html)
        self.assertIn("跨部门依赖", html)


if __name__ == "__main__":
    unittest.main()
