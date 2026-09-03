"""Regression coverage for leftover feasibility redline tokens.

PR #112 locked 加班 / 逼签 / 升级系统 / 大额投入 / 采购 / 招聘 / 外部顾问
and 技术部+行政 first-match. PR #117 locked 快速转化 / 加量 / APP端.

Still unlocked tokens that decide whether a daily improvement card is
flagged as budget, cross-dept, or 鞭打快牛:

- budget: 购买 / 新增人员 / 扩招
- cross_dept: 行政 / HR (standalone, not paired with 技术部)
- overload: 提高拨打量 / 增加拨打量 (PR #112 left 增加拨打量 untested
  as a direct validate_feasibility call)

A dropped token would let a redline suggestion render as
self_contained / high and enter the report without a warning.

Does not retest 门店扩张+高客单价 or 系统升级. Does not import
generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import validate_feasibility


class FeasibilityRemainingKeywordTests(unittest.TestCase):
    def test_purchase_is_budget_medium(self):
        result = validate_feasibility({
            "title": "工具采购",
            "act": "购买外呼线路监测软件",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("medium", result["feasibility"])
        self.assertEqual("budget_required", result["dependency"])
        self.assertIn("边际ROI", result["risk_notes"])
        self.assertIn("现金流", result["risk_notes"])

    def test_new_headcount_is_budget_medium(self):
        result = validate_feasibility({
            "title": "编制",
            "act": "新增人员补充中腰部辅导岗",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("medium", result["feasibility"])
        self.assertEqual("budget_required", result["dependency"])
        self.assertIn("边际ROI", result["risk_notes"])

    def test_expansion_hire_is_budget_medium(self):
        result = validate_feasibility({
            "title": "编制",
            "act": "扩招电销坐席应对旺季",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("medium", result["feasibility"])
        self.assertEqual("budget_required", result["dependency"])
        self.assertIn("现金流", result["risk_notes"])

    def test_admin_dept_is_cross_dept_medium(self):
        result = validate_feasibility({
            "title": "排班",
            "act": "协调行政调整工位与班次",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("medium", result["feasibility"])
        self.assertEqual("cross_dept", result["dependency"])
        self.assertIn("行政", result["risk_notes"])
        self.assertIn("跨部门", result["risk_notes"])

    def test_hr_is_cross_dept_medium(self):
        result = validate_feasibility({
            "title": "编制审批",
            "act": "请 HR 同步绩效任期模板",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("medium", result["feasibility"])
        self.assertEqual("cross_dept", result["dependency"])
        self.assertIn("HR", result["risk_notes"])

    def test_raise_dial_volume_is_overload_low(self):
        result = validate_feasibility({
            "title": "活动量",
            "act": "提高拨打量至人均60通",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("low", result["feasibility"])
        self.assertIn("鞭打快牛", result["risk_notes"])

    def test_increase_dial_volume_is_overload_low(self):
        result = validate_feasibility({
            "title": "活动量",
            "act": "全员增加拨打量跟进公海",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("low", result["feasibility"])
        self.assertEqual("self_contained", result["dependency"])
        self.assertIn("鞭打快牛", result["risk_notes"])


if __name__ == "__main__":
    unittest.main()
