"""Regression coverage for leftover feasibility cross-dept / compliance tokens.

PR #112 locked 加班 / 逼签 / 升级系统 / 大额投入 / 采购 / 招聘 / 外部顾问
and 技术部+行政 first-match. PR #117 locked 快速转化 / 加量 / APP端.
PR #118 locked 购买 / 新增人员 / 扩招 / 行政 / HR / 提高拨打量 / 增加拨打量.

Still unlocked tokens that decide whether a daily improvement card is
flagged as cross_dept or 风险回流总部 instead of self_contained / high:

- cross_dept: 人力 / IT部 / 平台改造 / 产品部 / 研发
- compliance: 门店扩张 / 高客单价 as standalone tokens
  (PR #64 only locked the combined 门店扩张+高客单价+快速转化 phrase;
  PR #112 left them untested as primary assertions)

A dropped token would let a redline suggestion render as
self_contained / high and enter the report without a warning.

Does not retest 系统升级 (PR #64) or 技术部+行政 first-match.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import validate_feasibility


class FeasibilityLeftoverCrossDeptTests(unittest.TestCase):
    def test_remaining_cross_dept_tokens_are_medium(self):
        for kw in ("人力", "IT部", "平台改造", "产品部", "研发"):
            with self.subTest(kw=kw):
                result = validate_feasibility({
                    "title": "协同",
                    "act": f"请{kw}配合补齐流程",
                    "detail": "",
                    "daily_action": "",
                })
                self.assertEqual("medium", result["feasibility"], kw)
                self.assertEqual("cross_dept", result["dependency"], kw)
                self.assertIn(kw, result["risk_notes"], kw)
                self.assertIn("跨部门", result["risk_notes"], kw)


class FeasibilityLeftoverComplianceTests(unittest.TestCase):
    def test_store_expansion_is_compliance_low(self):
        result = validate_feasibility({
            "title": "渠道",
            "act": "推进门店扩张覆盖空白城市",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("low", result["feasibility"])
        self.assertIn("风险回流总部", result["risk_notes"])
        self.assertIn("SaaS隔离", result["risk_notes"])

    def test_high_ticket_is_compliance_low(self):
        result = validate_feasibility({
            "title": "客单",
            "act": "主推高客单价套餐提升均单",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("low", result["feasibility"])
        self.assertEqual("self_contained", result["dependency"])
        self.assertIn("风险回流总部", result["risk_notes"])
        self.assertIn("SaaS隔离", result["risk_notes"])


if __name__ == "__main__":
    unittest.main()
