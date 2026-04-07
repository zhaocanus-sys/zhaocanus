import os
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


from diagnostics import CheckResult, render_report


class DiagnosticsRenderTests(unittest.TestCase):
    def test_render_report_contains_actionable_guidance(self):
        report = render_report(
            [
                CheckResult(
                    name="依赖 pymysql",
                    status="error",
                    summary="数据库访问（CynosDB） 未安装。",
                    action="执行 pip install pymysql 安装缺失依赖。",
                )
            ],
            title="安装环境检查",
        )
        self.assertIn("安装环境检查", report)
        self.assertIn("依赖 pymysql", report)
        self.assertIn("pip install pymysql", report)


class CliIntegrationTests(unittest.TestCase):
    def test_doctor_command_is_exposed_in_help(self):
        result = subprocess.run(
            [sys.executable, "scripts/handler.py", "-h"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("doctor", result.stdout)

    def test_data_command_is_exposed_in_help(self):
        result = subprocess.run(
            [sys.executable, "scripts/handler.py", "-h"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("data", result.stdout)


class InstallerGuidanceTests(unittest.TestCase):
    def test_install_script_covers_pymysql(self):
        content = Path(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "install.sh"))
        ).read_text(encoding="utf-8")
        self.assertIn("pymysql", content)

    def test_install_script_runs_setup_diagnostics(self):
        content = Path(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "install.sh"))
        ).read_text(encoding="utf-8")
        self.assertIn("doctor --setup-only", content)


class ProjectStructureTests(unittest.TestCase):
    def test_readme_exists(self):
        base = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        readme = base / "README.md"
        self.assertTrue(readme.exists(), "missing README.md")
        content = readme.read_text(encoding="utf-8")
        self.assertIn("install.sh", content)
        self.assertIn("doctor", content)


if __name__ == "__main__":
    unittest.main()
