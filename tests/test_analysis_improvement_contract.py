import unittest

from agent_system.engines.analysis_pipeline import AnalysisPipeline
from agent_system.engines.collision_engine import CollisionFinding


class AnalysisImprovementContractTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = AnalysisPipeline(":memory:")

    @staticmethod
    def summary(**overrides):
        values = {
            "date": "2026-12-31",
            "avg_deal": 5_000,
            "cr": 43,
            "allocated": 1_000,
            "conv": 2,
            "t20": 50,
            "on_duty": 20,
            "dr": 20,
            "link_1d_num": 400,
            "ai": 75,
            "ref_rate": 5,
            "total_revenue": 100_000,
            "jx_cr": 18,
            "jx_transfer_in": 100,
            "p_cr": 12,
            "pool_retrieval": 100,
        }
        values.update(overrides)
        return values

    @staticmethod
    def departments():
        return [
            {
                "dept_name": "电销一部",
                "per_capita_revenue": 8_000,
                "deep_talk_rate": 25,
            },
            {
                "dept_name": "电销二部",
                "per_capita_revenue": 4_000,
                "deep_talk_rate": 20,
            },
        ]

    def test_all_generated_improvements_include_execution_contract(self):
        finding = CollisionFinding(
            collision_type="metric_x_entity",
            tag="部门转化异常",
            description="电销二部转化率显著低于基准",
            revenue_impact=2_500,
            priority="P0",
            recommendations=["每日复盘三通未成交录音"],
            scope="dept",
            dept_name="电销二部",
            manager_name="赵梅",
        )
        summary = self.summary(
            cr=40,
            t20=60,
            dr=15,
            ai=65,
            ref_rate=6,
            jx_cr=15,
            p_cr=10,
        )

        improvements, total_uplift = self.pipeline._calc_improvements(
            summary, self.departments(), [finding]
        )

        self.assertEqual(
            {
                "接通率修复至43%",
                "中腰部标杆复制",
                "深沟率向标杆看齐",
                "AI Score提升至75",
                "退费率管控至4.5%",
                "建信调配转化率→18%",
                "公海捞取转化→12%",
                "[对撞] 部门转化异常",
            },
            {item["title"] for item in improvements},
        )
        self.assertEqual(sum(item["rev"] for item in improvements), total_uplift)

        required_text_fields = (
            "target_entity",
            "daily_action",
            "milestone",
            "risk_notes",
        )
        for item in improvements:
            with self.subTest(title=item["title"]):
                self.assertEqual("2027-01-01", item["deploy_date"])
                self.assertTrue(
                    all(
                        isinstance(item[field], str) and item[field].strip()
                        for field in required_text_fields
                    )
                )
                self.assertIsInstance(item["duration_days"], int)
                self.assertGreater(item["duration_days"], 0)
                self.assertIn(item["feasibility"], {"high", "medium", "low"})
                self.assertIn(
                    item["dependency"],
                    {"self_contained", "cross_dept", "budget_required"},
                )

        collision_item = next(
            item for item in improvements if item["title"] == "[对撞] 部门转化异常"
        )
        self.assertEqual("电销二部(管理者:赵梅)", collision_item["target_entity"])
        self.assertEqual(
            "每日复盘三通未成交录音", collision_item["daily_action"]
        )

    def test_threshold_boundaries_do_not_create_false_positive_actions(self):
        excluded_findings = [
            CollisionFinding(
                collision_type="metric_x_metric",
                tag="低优先级",
                description="不应进入执行建议",
                revenue_impact=1_000,
                priority="P2",
            ),
            CollisionFinding(
                collision_type="metric_x_metric",
                tag="无收益影响",
                description="不应进入执行建议",
                revenue_impact=0,
                priority="P1",
            ),
        ]

        improvements, total_uplift = self.pipeline._calc_improvements(
            self.summary(), self.departments(), excluded_findings
        )

        self.assertEqual([], improvements)
        self.assertEqual(0, total_uplift)


if __name__ == "__main__":
    unittest.main()
