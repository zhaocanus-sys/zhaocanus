import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".cursor" / "skills" / "report-generator"


class ReportSkillPackagingTests(unittest.TestCase):
    def test_skill_references_and_report_scripts_resolve(self):
        skill_path = SKILL_DIR / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")

        self.assertRegex(content, r"(?m)^name:\s*report-generator$")
        self.assertRegex(content, r"(?m)^description:\s*\S+")
        self.assertRegex(content, r"(?m)^compatibility:\s*\S+")

        markdown_links = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", content)
        self.assertTrue(markdown_links)
        for relative_path in markdown_links:
            with self.subTest(reference=relative_path):
                self.assertTrue(
                    (SKILL_DIR / relative_path).resolve().is_file(),
                    f"Skill 引用不存在: {relative_path}",
                )

        report_scripts = set(re.findall(r"`(generate_[a-z_]+\.py)`", content))
        self.assertEqual(
            report_scripts,
            {
                "generate_app_full_report.py",
                "generate_hongniang_full_report.py",
                "generate_jianxin_full_report.py",
                "generate_shop_full_report.py",
                "generate_telesale_full_report.py",
            },
        )
        for script in report_scripts:
            with self.subTest(script=script):
                self.assertTrue((ROOT / script).is_file())

    def test_facts_template_matches_runtime_configuration_contract(self):
        template_path = ROOT / "agent_system" / "config" / "facts.json.template"
        template = json.loads(template_path.read_text(encoding="utf-8"))

        self.assertTrue(
            {"smtp", "contacts", "dept_managers", "api", "default_recipients"}
            <= template.keys()
        )
        self.assertTrue(
            {"host", "port", "ssl", "from_email", "auth_code", "from_name"}
            <= template["smtp"].keys()
        )
        self.assertTrue(
            {"base_url", "api_key", "auth_header", "query_script", "knowledge_file"}
            <= template["api"].keys()
        )
        self.assertEqual(template["api"]["auth_header"], "X-API-Key")

        for key in ("query_script", "knowledge_file"):
            with self.subTest(config_key=key):
                self.assertTrue(
                    (ROOT / template["api"][key]).is_file(),
                    f"配置模板引用不存在: {template['api'][key]}",
                )


if __name__ == "__main__":
    unittest.main()
