import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from agent_system.engines.collision_engine import DataCollisionEngine, MANAGEMENT_GAP_RULES
from generate_app_full_report import build_trend_data


class SparklineRegressionTests(unittest.TestCase):
    def test_sparkline_requires_two_real_values(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 42]), "")

    def test_sparkline_scales_values_and_marks_downward_trend(self):
        svg = sparkline_svg([10, 30, 20], fill=False)

        self.assertIn('<svg width="60" height="22"', svg)
        self.assertIn('<polyline points="1.0,21.0 30.0,1.0 59.0,11.0"', svg)
        self.assertNotIn("<polygon", svg)
        self.assertIn('cx="59.0" cy="11.0"', svg)
        self.assertIn('fill="#dc2626"', svg)

    def test_sparkline_handles_flat_series_without_division_by_zero(self):
        svg = sparkline_svg([5, 5, 5])

        self.assertIn('<polygon points="1.0,21.0 30.0,21.0 59.0,21.0', svg)
        self.assertIn('fill="#16a34a"', svg)

    def test_extract_trend_values_returns_chronological_numeric_series(self):
        history_desc = [
            {"date": "20260229", "metrics": {"revenue": 300}},
            {"date": "20260228", "metrics": {"revenue": "200.5"}},
            {"date": "20260227", "metrics": {}},
        ]

        values = extract_trend_values(history_desc, "revenue", today_val=400)

        self.assertEqual(values, [0.0, 200.5, 300.0, 400.0])

    def test_extract_trend_values_uses_previous_value_when_history_is_empty(self):
        values = extract_trend_values([], "revenue", today_val=120, prev_val=100)

        self.assertEqual(values, [100.0, 120.0])


class AppTrendRegressionTests(unittest.TestCase):
    def test_build_trend_data_groups_rows_by_day_and_calculates_rates(self):
        trend_rows = [
            {
                "ftime": "20260228",
                "amt": "1,500",
                "pay_num": "3",
                "active_members": "60",
                "refund_money": "30",
                "retain_1d": "10",
            },
            {
                "ftime": "20260227",
                "amt": "1000",
                "pay_num": "2",
                "active_members": "50",
                "refund_money": None,
                "retain_1d": "8",
            },
            {
                "ftime": "20260228",
                "amt": 500,
                "pay_num": 1,
                "active_members": 40,
                "refund_money": 20,
                "retain_1d": 5,
            },
        ]

        trends = build_trend_data(trend_rows)

        self.assertEqual([row["dt"] for row in trends], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trends[0]["amt"], 1000.0)
        self.assertEqual(trends[0]["refund_money"], 0.0)
        self.assertEqual(trends[0]["arpu"], 500.0)
        self.assertEqual(trends[0]["pay_rate"], 4.0)
        self.assertEqual(trends[1]["amt"], 2000.0)
        self.assertEqual(trends[1]["pay_num"], 4.0)
        self.assertEqual(trends[1]["active_members"], 100.0)
        self.assertEqual(trends[1]["refund_money"], 50.0)
        self.assertEqual(trends[1]["retain_1d"], 15.0)
        self.assertEqual(trends[1]["arpu"], 500.0)
        self.assertEqual(trends[1]["pay_rate"], 4.0)


class CollisionFindingRegressionTests(unittest.TestCase):
    def test_department_finding_includes_scope_manager_and_management_gap(self):
        engine = DataCollisionEngine()
        engine.dept_managers = {"电销六部": "游云清"}

        engine._add_finding(
            collision_type="metric_x_metric",
            tag="低接通",
            description="电销六部接通率低于红线",
            revenue_impact=5200,
            priority="P0",
            scope="dept",
            dept_name="电销六部",
            gap_key="low_connect",
        )

        finding = engine.findings[0].to_dict()
        self.assertEqual(finding["scope"], "dept")
        self.assertEqual(finding["dept_name"], "电销六部")
        self.assertEqual(finding["manager_name"], "游云清")
        self.assertEqual(finding["management_gap"], MANAGEMENT_GAP_RULES["low_connect"])

    def test_global_finding_does_not_leak_department_fields(self):
        engine = DataCollisionEngine()

        engine._add_finding(
            collision_type="trend_x_volatility",
            tag="营收波动",
            description="全局营收波动异常",
            revenue_impact=8000,
            priority="P1",
        )

        finding = engine.findings[0].to_dict()
        self.assertEqual(finding["scope"], "global")
        self.assertEqual(finding["dept_name"], "")
        self.assertNotIn("manager_name", finding)
        self.assertNotIn("management_gap", finding)


if __name__ == "__main__":
    unittest.main()
