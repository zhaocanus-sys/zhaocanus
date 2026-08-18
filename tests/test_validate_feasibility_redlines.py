# -*- coding: utf-8 -*-
"""Regression coverage for validate_feasibility redline keyword gates.

PR #72 asserts that improvement items carry feasibility/dependency enums,
but does not lock the keyword classification that decides those values.
A silent change here would drop overload or compliance warnings from
every analysis-pipeline recommendation.
"""
import unittest

from agent_system.engines.collision_engine import validate_feasibility


class ValidateFeasibilityRedlineTests(unittest.TestCase):
    def test_self_contained_item_is_high_feasibility(self):
        result = validate_feasibility({
            "title": "接通率修复至43%",
            "act": "排查号码标记+优化外呼时段",
            "detail": "增加有效接通后按既有转化率测算",
            "daily_action": "每日复盘外呼时段数据",
        })
        self.assertEqual(result["feasibility"], "high")
        self.assertEqual(result["dependency"], "self_contained")
        self.assertIn("弱依赖·强闭环", result["risk_notes"])

    def test_cross_dept_keyword_in_title_sets_medium(self):
        result = validate_feasibility({
            "title": "请技术部配合导出质检明细",
            "act": "业务侧先整理口径",
        })
        self.assertEqual(result["feasibility"], "medium")
        self.assertEqual(result["dependency"], "cross_dept")
        self.assertIn("需技术部配合，跨部门协调成本较高", result["risk_notes"])

    def test_budget_keyword_in_act_sets_budget_required(self):
        result = validate_feasibility({
            "title": "扩容质检覆盖",
            "act": "招聘两名质检专员补齐抽检缺口",
        })
        self.assertEqual(result["feasibility"], "medium")
        self.assertEqual(result["dependency"], "budget_required")
        self.assertIn("涉及预算投入，需核算边际ROI", result["risk_notes"])

    def test_overload_keyword_drops_feasibility_to_low(self):
        result = validate_feasibility({
            "title": "冲刺接通量",
            "daily_action": "要求一线增加拨打量直到达标",
        })
        self.assertEqual(result["feasibility"], "low")
        self.assertEqual(result["dependency"], "self_contained")
        self.assertIn("要求一线大幅加量", result["risk_notes"])

    def test_compliance_keyword_drops_feasibility_to_low(self):
        result = validate_feasibility({
            "title": "提升客单",
            "detail": "对犹豫客户采用逼签话术缩短决策",
        })
        self.assertEqual(result["feasibility"], "low")
        self.assertIn("涉及合规敏感操作，违反SaaS隔离原则", result["risk_notes"])

    def test_overload_keeps_budget_dependency_but_overrides_feasibility(self):
        result = validate_feasibility({
            "title": "招聘冲刺",
            "act": "招聘补充坐席后增加拨打量",
        })
        self.assertEqual(result["feasibility"], "low")
        self.assertEqual(result["dependency"], "budget_required")
        self.assertIn("涉及预算投入", result["risk_notes"])
        self.assertIn("要求一线大幅加量", result["risk_notes"])

    def test_compliance_overrides_cross_dept_feasibility(self):
        result = validate_feasibility({
            "title": "请产品部评估高客单价套餐",
            "act": "门店扩张同步上线快速转化流程",
        })
        self.assertEqual(result["feasibility"], "low")
        self.assertEqual(result["dependency"], "cross_dept")
        self.assertIn("需产品部配合", result["risk_notes"])
        self.assertIn("涉及合规敏感操作", result["risk_notes"])


if __name__ == "__main__":
    unittest.main()
