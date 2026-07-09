import unittest

from agent_system.actions.api_client import parallel_fetch, safe_float, safe_int
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from agent_system.engines.collision_engine import CollisionFinding, validate_feasibility


class ApiClientUtilityTests(unittest.TestCase):
    def test_safe_number_parsing_handles_common_report_formats(self):
        self.assertEqual(safe_float("1,234.50%"), 1234.5)
        self.assertEqual(safe_float(None, d=7.5), 7.5)
        self.assertEqual(safe_float("not-a-number", d=3.25), 3.25)
        self.assertEqual(safe_int("2,001.9"), 2001)

    def test_parallel_fetch_handles_empty_call_list(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_isolates_failures(self):
        def first():
            return {"name": "first"}

        def failing():
            raise RuntimeError("boom")

        def third():
            return {"name": "third"}

        result = parallel_fetch([first, failing, third])

        self.assertEqual(result[0], {"name": "first"})
        self.assertEqual(result[2], {"name": "third"})
        self.assertIn("boom", result[1]["error"])
        self.assertEqual(result[1]["rows"], [])
        self.assertEqual(result[1]["row_count"], 0)
        self.assertEqual(result[1]["columns"], [])


class ReportSparklineTests(unittest.TestCase):
    def test_sparkline_returns_empty_string_when_less_than_two_points(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 5, None]), "")

    def test_sparkline_handles_flat_series_without_dividing_by_zero(self):
        svg = sparkline_svg([8, 8, 8], width=30, height=12, fill=False)

        self.assertIn("<svg", svg)
        self.assertIn("<polyline", svg)
        self.assertIn("<circle", svg)
        self.assertIn('fill="#16a34a"', svg)

    def test_extract_trend_values_returns_chronological_history_then_today(self):
        history = [
            {"date": "2026-03-03", "metrics": {"revenue": 300}},
            {"date": "2026-03-02", "metrics": {"revenue": None}},
            {"date": "2026-03-01", "metrics": {"revenue": 100}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=400),
            [100.0, 0.0, 300.0, 400.0],
        )

    def test_extract_trend_values_uses_previous_value_as_baseline(self):
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=120, prev_val=80),
            [80.0, 120.0],
        )


class CollisionEngineRuleTests(unittest.TestCase):
    def test_collision_finding_serializes_scope_and_manager_gap_metadata(self):
        finding = CollisionFinding(
            collision_type="metric_x_entity",
            tag="low_connect",
            description="电销六部接通率低于红线",
            revenue_impact=5200,
            priority="P1",
            evidence=["接通率 38%"],
            recommendations=["优化外呼时段"],
            scope="dept",
            dept_name="电销六部",
            manager_name="游云清",
            management_gap="缺乏号码健康度和外呼时段精细化管理意识",
        )

        data = finding.to_dict()

        self.assertEqual(data["scope"], "dept")
        self.assertEqual(data["dept_name"], "电销六部")
        self.assertEqual(data["manager_name"], "游云清")
        self.assertIn("号码健康度", data["management_gap"])

    def test_validate_feasibility_marks_self_contained_actions_high_feasibility(self):
        result = validate_feasibility(
            {
                "title": "话术训练",
                "daily_action": "晨会播放1条标杆录音，午间完成话术通关",
            }
        )

        self.assertEqual(result["feasibility"], "high")
        self.assertEqual(result["dependency"], "self_contained")
        self.assertIn("业务团队可自行推动", result["risk_notes"])

    def test_validate_feasibility_flags_cross_department_budget_and_overload_risks(self):
        cross_dept = validate_feasibility({"detail": "需要技术部配合系统升级"})
        overload = validate_feasibility({"act": "要求一线增加拨打量"})
        compliance = validate_feasibility({"act": "门店扩张并推动高客单价快速转化"})

        self.assertEqual(cross_dept["dependency"], "cross_dept")
        self.assertEqual(cross_dept["feasibility"], "medium")
        self.assertIn("跨部门协调成本较高", cross_dept["risk_notes"])

        self.assertEqual(overload["feasibility"], "low")
        self.assertIn("组织疲劳度", overload["risk_notes"])

        self.assertEqual(compliance["feasibility"], "low")
        self.assertIn("合规敏感操作", compliance["risk_notes"])


if __name__ == "__main__":
    unittest.main()
