"""Regression coverage for leftover validate_feasibility keyword gates.

PR #64 locked self-contained → high, 技术部 → cross_dept/medium,
增加拨打量 → low, and 门店扩张+高客单价+快速转化 → low. PR #111
re-locked 增加拨打量 on a generated connect card.

Neither locked the budget_required path. The PR #64 case that
mentions "budget" actually used 「系统升级」(a cross_dept keyword),
not 「升级系统」(a budget keyword). Precedence when both fire,
and remaining overload/compliance tokens, were also unlocked.

Does not retest PR #64 self-contained / 技术部 / 增加拨打量 /
门店扩张+高客单价 as the primary assertion.

Deterministic stdlib unittest only — no network/DB.
"""

import unittest

from agent_system.engines.collision_engine import validate_feasibility


class FeasibilityBudgetKeywordTests(unittest.TestCase):
    def test_upgrade_system_budget_keyword_is_not_cross_dept(self):
        # 「升级系统」 is budget; 「系统升级」 is cross_dept (PR #64).
        result = validate_feasibility({"act": "升级系统以提升接通率"})

        self.assertEqual("budget_required", result["dependency"])
        self.assertEqual("medium", result["feasibility"])
        self.assertIn("边际ROI", result["risk_notes"])
        self.assertIn("现金流", result["risk_notes"])
        self.assertNotIn("跨部门", result["risk_notes"])

    def test_remaining_budget_keywords_mark_medium_budget_required(self):
        for kw in ("大额投入", "采购", "招聘", "外部顾问"):
            with self.subTest(kw=kw):
                result = validate_feasibility({"title": kw})
                self.assertEqual("budget_required", result["dependency"], kw)
                self.assertEqual("medium", result["feasibility"], kw)
                self.assertIn("边际ROI", result["risk_notes"])

    def test_cross_dept_plus_budget_keeps_cross_dept_and_both_notes(self):
        result = validate_feasibility(
            {"detail": "需要技术部配合", "act": "采购外呼线路"}
        )

        self.assertEqual("cross_dept", result["dependency"])
        self.assertEqual("medium", result["feasibility"])
        self.assertIn("跨部门协调成本较高", result["risk_notes"])
        self.assertIn("边际ROI", result["risk_notes"])

    def test_budget_plus_overload_downgrades_to_low_keeps_budget_dep(self):
        result = validate_feasibility(
            {"act": "招聘并加班提高拨打量"}
        )

        self.assertEqual("budget_required", result["dependency"])
        self.assertEqual("low", result["feasibility"])
        self.assertIn("边际ROI", result["risk_notes"])
        self.assertIn("组织疲劳度", result["risk_notes"])


class FeasibilityRemainingTokenTests(unittest.TestCase):
    def test_remaining_overload_keywords_mark_low(self):
        for kw in ("加班", "延长工时", "人均拨打提至"):
            with self.subTest(kw=kw):
                result = validate_feasibility({"daily_action": kw})
                self.assertEqual("low", result["feasibility"], kw)
                self.assertIn("组织疲劳度", result["risk_notes"])

    def test_remaining_compliance_keywords_mark_low(self):
        for kw in ("逼签", "压单", "强制成交"):
            with self.subTest(kw=kw):
                result = validate_feasibility({"act": kw})
                self.assertEqual("low", result["feasibility"], kw)
                self.assertIn("合规敏感操作", result["risk_notes"])
                self.assertIn("SaaS隔离", result["risk_notes"])

    def test_overload_plus_compliance_keeps_both_notes(self):
        result = validate_feasibility({"act": "加班逼签"})

        self.assertEqual("low", result["feasibility"])
        self.assertIn("组织疲劳度", result["risk_notes"])
        self.assertIn("合规敏感操作", result["risk_notes"])

    def test_first_cross_dept_keyword_wins_and_stops(self):
        # 技术部 is first in the list; 行政 must not replace the note.
        result = validate_feasibility({"title": "技术部与行政联席推进"})

        self.assertEqual("cross_dept", result["dependency"])
        self.assertEqual("medium", result["feasibility"])
        self.assertIn("需技术部配合", result["risk_notes"])
        self.assertNotIn("需行政配合", result["risk_notes"])


if __name__ == "__main__":
    unittest.main()
