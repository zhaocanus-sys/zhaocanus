"""Regression coverage for DataExpert export paths and leftover email gates.

PR #114 locked `export_html(..., open_browser=False)` on the shared
report_exporter. DataExpert.export still had no contract: a relative
filename must resolve to the repo root (same dirname×3 as __init__),
an absolute path must stay put, and open_browser=False must not open
a browser. A wrong join would drop the HTML artifact off the machine
operators actually open.

PR #115 locked missing credentials, an *existing* html_template_path,
and send_report_email default TO / blank CC. Leftover:
- SMTP exception must return False (not look like a successful send)
- missing template path must keep the caller-supplied body_html
- body_text attaches a text/plain part

Does not lock DataExpert.send_email (open PR #74, hardcoded SMTP).
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import os
import tempfile
import unittest
from email import message_from_string
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_system.agents import data_expert as de_mod
from agent_system.agents.data_expert import DataExpert
from agent_system.engines.analysis_pipeline import AnalysisReport


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(de_mod.__file__)))


def _minimal_report(date="2026-09-01"):
    return AnalysisReport(
        date=date,
        summary={},
        departments=[],
        trends=[],
        persons=[],
        top_performers=[],
        bottom_performers=[],
        new_hire_stats=[],
        tenure_analysis={},
        data_collision_findings=[],
        data_collision_summary={},
        logic_collision_findings=[],
        logic_collision_summary={},
    )


class DataExpertPathTests(unittest.TestCase):
    def test_init_resolves_relative_db_path_to_repo_root(self):
        expert = DataExpert(db_path="zhenai_ts_v4.db")
        expected = os.path.join(_repo_root(), "zhenai_ts_v4.db")
        self.assertEqual(expected, expert.db_path)
        self.assertEqual(expected, expert.pipeline.db_path)

        abs_expert = DataExpert(db_path="/tmp/coverage-dummy.db")
        self.assertEqual("/tmp/coverage-dummy.db", abs_expert.db_path)

    def test_export_relative_resolves_to_repo_root_and_skips_browser(self):
        expert = DataExpert(db_path="/tmp/coverage-dummy.db")
        report = _minimal_report()
        name = "_coverage_data_expert_export.html"
        expected = os.path.join(_repo_root(), name)

        try:
            with patch.object(expert, "render_html", return_value="<p>导出正文</p>"):
                with patch.object(de_mod.webbrowser, "open") as opener:
                    path = expert.export(report, name, open_browser=False)
            self.assertEqual(expected, path)
            self.assertEqual("<p>导出正文</p>", Path(path).read_text(encoding="utf-8"))
            opener.assert_not_called()
        finally:
            if os.path.exists(expected):
                os.remove(expected)

    def test_export_absolute_path_unchanged_and_default_filename(self):
        expert = DataExpert(db_path="/tmp/coverage-dummy.db")
        report = _minimal_report("2026-09-01")

        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "abs.html")
            with patch.object(expert, "render_html", return_value="<html>abs</html>"):
                with patch.object(de_mod.webbrowser, "open") as opener:
                    path = expert.export(report, dest, open_browser=False)
            self.assertEqual(dest, path)
            self.assertEqual("<html>abs</html>", Path(dest).read_text(encoding="utf-8"))
            opener.assert_not_called()

        default_path = os.path.join(_repo_root(), "DataExpert_Report_2026-09-01.html")
        try:
            with patch.object(expert, "render_html", return_value="<html>default</html>"):
                with patch.object(de_mod.webbrowser, "open") as opener:
                    path = expert.export(report, open_browser=False)
            self.assertEqual(default_path, path)
            self.assertEqual("<html>default</html>", Path(path).read_text(encoding="utf-8"))
            opener.assert_not_called()
        finally:
            if os.path.exists(default_path):
                os.remove(default_path)


class EmailLeftoverGateTests(unittest.TestCase):
    def _cfg(self):
        return {
            "host": "smtp.example.com",
            "port": 465,
            "from_email": "from@example.com",
            "auth_code": "token",
            "from_name": "智慧助理",
        }

    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_smtp_exception_returns_false(self, smtp_cfg, smtp_ssl):
        from agent_system.actions.email_sender import send_email

        smtp_cfg.return_value = self._cfg()
        session = MagicMock()
        session.login.side_effect = OSError("smtp down")
        smtp_ssl.return_value.__enter__.return_value = session

        self.assertFalse(send_email("subj", ["to@example.com"], body_html="<p>x</p>"))
        session.sendmail.assert_not_called()

    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_missing_template_keeps_body_html_and_attaches_plain(self, smtp_cfg, smtp_ssl):
        from agent_system.actions.email_sender import send_email

        smtp_cfg.return_value = self._cfg()
        session = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = session

        missing = "/tmp/does-not-exist-coverage-template.html"
        ok = send_email(
            "日报",
            ["to@example.com"],
            body_text="纯文本摘要",
            body_html="<p>调用方HTML</p>",
            html_template_path=missing,
        )
        self.assertTrue(ok)
        _from, recipients, raw = session.sendmail.call_args[0]
        self.assertEqual("from@example.com", _from)
        self.assertEqual(["to@example.com"], recipients)
        msg = message_from_string(raw)
        types = [part.get_content_type() for part in msg.walk()]
        self.assertIn("text/plain", types)
        self.assertIn("text/html", types)
        plains = [
            part.get_payload(decode=True).decode("utf-8")
            for part in msg.walk()
            if part.get_content_type() == "text/plain"
        ]
        htmls = [
            part.get_payload(decode=True).decode("utf-8")
            for part in msg.walk()
            if part.get_content_type() == "text/html"
        ]
        self.assertEqual(["纯文本摘要"], plains)
        self.assertEqual(["<p>调用方HTML</p>"], htmls)


if __name__ == "__main__":
    unittest.main()
