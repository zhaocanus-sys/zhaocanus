# -*- coding: utf-8 -*-
"""Contract tests for report-generator Skill references added in the latest packaging merge."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".cursor" / "skills" / "report-generator"
REF_DIR = SKILL_DIR / "references"


class SkillReferenceContractTests(unittest.TestCase):
    def test_api_reference_documents_five_teams_and_auth_contract(self):
        text = (REF_DIR / "api-reference.md").read_text(encoding="utf-8")

        for team in ("jianxin", "telesale", "hongniang", "shop", "app"):
            with self.subTest(team=team):
                self.assertIn(f"`{team}`", text)

        self.assertIn("X-API-Key", text)
        self.assertIn("agent_system/actions/api_client.py", text)
        self.assertIn("YYYYMMDD", text)
        self.assertIn("parallel_fetch", text)
        self.assertIn("safe_float", text)

        # Core endpoints used by all personal reports must remain documented.
        self.assertIn("/api/v1/team/{team}/daily", text)
        self.assertIn("/api/v1/team/{team}/query", text)
        self.assertRegex(text, r"table_role.*hourly|hourly.*table_role")

    def test_scoring_rules_lock_process_result_weights_and_shop_special_case(self):
        text = (REF_DIR / "scoring-and-fraud.md").read_text(encoding="utf-8")

        self.assertIn("过程30分", text)
        self.assertIn("结果70分", text)
        self.assertIn("100%关联业绩", text)
        self.assertIn("无成交率和业绩 = 0分", text)
        self.assertIn("珍心", text)
        self.assertIn("80%", text)
        self.assertIn("退款", text)
        self.assertIn("2%", text)

        # Telemarketing redlines used by collision/improvement engines.
        self.assertRegex(text, r"接通率.*18%|18%.*接通")
        self.assertIn("深沟率", text)

    def test_rules_all_teams_locks_ten_day_trend_and_seven_day_escalation(self):
        text = (REF_DIR / "rules-all-teams.md").read_text(encoding="utf-8")

        self.assertIn("10天趋势", text)
        self.assertRegex(text, r"连续7天|7天.*P0|P0")
        self.assertIn("全局 vs 部门诊断必须分栏", text)
        self.assertIn("管理者姓名必须体现", text)
        self.assertIn("时间维度", text)
        self.assertIn("弱依赖强闭环", text)

        # Skill.md must keep links to these three reference files resolvable.
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for name in ("api-reference.md", "scoring-and-fraud.md", "rules-all-teams.md"):
            with self.subTest(reference=name):
                self.assertTrue(
                    any(name in link for link in re.findall(r"\(([^)]+)\)", skill)),
                    f"SKILL.md 未链接 {name}",
                )
                self.assertTrue((REF_DIR / name).is_file())


if __name__ == "__main__":
    unittest.main()
