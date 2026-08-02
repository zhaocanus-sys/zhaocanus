# -*- coding: utf-8 -*-
"""Regression tests for SETUP.md packaging contract from the latest packaging merge."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SetupPackagingTests(unittest.TestCase):
    def test_setup_documents_existing_report_scripts_and_config_paths(self):
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")

        report_scripts = [
            "generate_jianxin_full_report.py",
            "generate_telesale_full_report.py",
            "generate_hongniang_full_report.py",
            "generate_shop_full_report.py",
            "generate_app_full_report.py",
        ]
        for script in report_scripts:
            with self.subTest(script=script):
                self.assertIn(script, setup)
                self.assertTrue((ROOT / script).is_file(), f"缺失脚本: {script}")

        self.assertIn("app_report_data.py", setup)
        self.assertIn("app_report_html.py", setup)
        self.assertTrue((ROOT / "app_report_data.py").is_file())
        self.assertTrue((ROOT / "app_report_html.py").is_file())

        self.assertIn(
            "cp agent_system/config/facts.json.template agent_system/config/facts.json",
            setup,
        )
        self.assertTrue(
            (ROOT / "agent_system" / "config" / "facts.json.template").is_file()
        )

        self.assertIn(".cursor/skills/report-generator/", setup)
        self.assertTrue(
            (ROOT / ".cursor" / "skills" / "report-generator" / "SKILL.md").is_file()
        )

        self.assertIn("report_sparkline.py", setup)
        self.assertTrue(
            (ROOT / "agent_system" / "actions" / "report_sparkline.py").is_file()
        )

    def test_setup_manual_commands_use_date_and_optional_no_email(self):
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        command_lines = [
            line.strip()
            for line in setup.splitlines()
            if line.strip().startswith("python3 generate_")
        ]
        self.assertGreaterEqual(len(command_lines), 5)
        for line in command_lines:
            with self.subTest(command=line):
                self.assertRegex(line, r"--date\s+\d{4}-\d{2}-\d{2}")
                self.assertTrue(
                    line.endswith("--no-email") or "telesale" in line,
                    "非电销脚本应默认演示 --no-email；电销可演示发信路径",
                )

    def test_gitignore_excludes_facts_credentials(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        patterns = {
            line.strip()
            for line in gitignore.splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        self.assertIn("agent_system/config/facts.json", patterns)

        # SETUP must not instruct committing the live credentials file.
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(r"git\s+add\s+.*facts\.json(?!\.template)", setup),
            "SETUP 不应引导提交真实凭据 facts.json",
        )


if __name__ == "__main__":
    unittest.main()
