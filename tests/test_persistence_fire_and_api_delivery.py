"""Regression coverage for persistence fire payload and shared delivery paths.

PR #110 locked persistence *early exits* (trends < 5; current connect >= 43)
and explicitly did not lock the fire path. Open PR #48 has an unmerged
department-scoped count fix — fixtures here set *both* global `cr` and
matching `dept_trends` below 43 so either implementation still fires.
These cases lock the P0 penalty contract (绩效挂钩 / 书面计划 / 抄送),
not how `cr_below_count` is sourced.

`parallel_fetch` / `_req` sit under every 10-day report pull. Order
scramble or a leaked exception would swap or crash KPI windows.
Empty `parallel_fetch([])` still raises on main (PR #53) — not locked.

`export_html(..., open_browser=False)` is the shared write path for all
five report generators; a wrong directory or encoding drop loses the
HTML artifact.

Does not import generate_telesale_full_report (illegal f-string on main).
Does not lock persistence global-vs-dept counting (PR #48).
Does not lock APP sparkline rate-field mapping or shop double-count.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_system.actions import report_exporter
from agent_system.actions.api_client import daily, health, parallel_fetch
from agent_system.engines.collision_engine import DataCollisionEngine


def _low_cr_dept(**overrides):
    dept = {
        "dept_name": "电销六部",
        "connect_rate": 30,
        "allocated": 500,
        "avg_deal_amount": 5_000,
    }
    dept.update(overrides)
    return dept


def _aligned_red_trends(n=7, cr=30, dept="电销六部"):
    """Global cr *and* dept_trends agree, so PR #48 would still fire."""
    return [
        {"cr": cr, "dept_trends": [{"dept_name": dept, "cr": cr}]}
        for _ in range(n)
    ]


class PersistenceFirePayloadTests(unittest.TestCase):
    def test_long_red_streak_emits_p0_salary_penalty_contract(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}
        engine._collide_persistence_detection(
            [_low_cr_dept()],
            _aligned_red_trends(),
        )
        persist = [f for f in engine.findings if f.tag == "持续不达标预警"]
        self.assertEqual(1, len(persist))
        finding = persist[0]
        self.assertEqual("P0", finding.priority)
        self.assertEqual("dept", finding.scope)
        self.assertEqual("电销六部", finding.dept_name)
        self.assertEqual("metric_x_time", finding.collision_type)
        self.assertIn("游云清", finding.description)
        self.assertIn("低于43%", finding.description)
        self.assertIn("无明显改善趋势", finding.description)
        recs = " ".join(finding.recommendations)
        self.assertIn("绩效分数扣减5分/日", recs)
        self.assertIn("书面改善计划", recs)
        self.assertIn("抄送上级领导", recs)
        self.assertEqual(75_000, finding.revenue_impact)

    def test_unmapped_manager_falls_back_to_dept_owner_wording(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {}
        engine._collide_persistence_detection(
            [_low_cr_dept()],
            _aligned_red_trends(),
        )
        finding = engine.findings[0]
        self.assertEqual("P0", finding.priority)
        self.assertIn("电销六部", finding.description)
        self.assertNotIn("(", finding.description)
        recs = " ".join(finding.recommendations)
        self.assertIn("今日发出正式预警通知给部门负责人", recs)
        self.assertNotIn("游云清", finding.description)
        self.assertNotIn("游云清", recs)


class ParallelFetchAndReqTests(unittest.TestCase):
    def test_parallel_fetch_preserves_call_order(self):
        results = parallel_fetch(
            [
                lambda: {"id": "first"},
                lambda: {"id": "second"},
                lambda: {"id": "third"},
            ]
        )
        self.assertEqual(
            [{"id": "first"}, {"id": "second"}, {"id": "third"}],
            results,
        )

    def test_parallel_fetch_isolates_one_failure(self):
        def boom():
            raise RuntimeError("upstream timeout")

        results = parallel_fetch(
            [lambda: {"ok": 1}, boom, lambda: {"ok": 3}]
        )
        self.assertEqual({"ok": 1}, results[0])
        self.assertEqual({"ok": 3}, results[2])
        self.assertEqual("upstream timeout", results[1]["error"])
        self.assertEqual([], results[1]["rows"])
        self.assertEqual(0, results[1]["row_count"])
        self.assertEqual([], results[1]["columns"])

    def test_req_exception_returns_empty_envelope(self):
        with patch(
            "agent_system.actions.api_client.requests.request",
            side_effect=RuntimeError("timeout"),
        ):
            result = daily("telesale", date="20260830")
        self.assertIn("timeout", result["error"])
        self.assertEqual([], result["rows"])
        self.assertEqual(0, result["row_count"])
        self.assertEqual([], result["columns"])

    def test_health_path_includes_team_when_provided(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()
        with patch(
            "agent_system.actions.api_client.requests.request",
            return_value=mock_resp,
        ) as req:
            bare = health()
            named = health("telesale")
        self.assertEqual({"status": "ok"}, bare)
        self.assertEqual({"status": "ok"}, named)
        paths = [call.args[1] for call in req.call_args_list]
        self.assertTrue(paths[0].endswith("/api/v1/health/"))
        self.assertTrue(paths[1].endswith("/api/v1/health/telesale"))
        self.assertEqual("GET", req.call_args_list[0].args[0])


class ReportExporterTests(unittest.TestCase):
    def test_export_html_writes_utf8_and_skips_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp) / "reports"
            with patch.object(report_exporter, "_REPORTS", reports):
                with patch.object(report_exporter, "_open") as opener:
                    path = report_exporter.export_html(
                        "<p>你好</p>",
                        "coverage.html",
                        open_browser=False,
                    )
            written = Path(path)
            self.assertEqual(reports / "coverage.html", written)
            self.assertEqual("<p>你好</p>", written.read_text(encoding="utf-8"))
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
