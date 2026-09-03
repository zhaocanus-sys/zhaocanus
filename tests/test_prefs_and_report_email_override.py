"""Regression coverage for leftover preferences fallback and report-mail override.

PR #117 locked missing facts.json → empty smtp/api/contacts, and facts
reload(). preferences.json was never locked: report language / module
count / style tokens all read this file. A missing or relocated prefs
file must yield {} rather than raise.

PR #115 locked send_report_email default TO + blank CC omitted.
PR #117 locked send_email To/Cc join when Cc is present. Leftover:
- explicit to/cc must win over contacts() defaults
- send_email with no cc must omit the Cc header (not send Cc: None)

Does not lock DataExpert.send_email (open PR #74, hardcoded SMTP).
Does not read or assert secret values from facts.json / preferences.json.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest
from email import message_from_string
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_system import config as cfg
from agent_system.actions.email_sender import send_email, send_report_email


class PreferencesMissingFileTests(unittest.TestCase):
    def tearDown(self):
        cfg.reload()

    def test_missing_preferences_file_returns_empty_mapping(self):
        cfg.reload()
        with patch.object(Path, "exists", return_value=False):
            self.assertEqual({}, cfg.preferences())


class ReportEmailOverrideAndBareCcTests(unittest.TestCase):
    def _cfg(self):
        return {
            "host": "smtp.example.com",
            "port": 465,
            "from_email": "from@example.com",
            "auth_code": "token",
            "from_name": "智慧助理",
        }

    @patch("agent_system.actions.email_sender.send_email")
    @patch("agent_system.actions.email_sender.contacts")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_send_report_email_explicit_to_cc_override(self, smtp_cfg, contacts, send):
        smtp_cfg.return_value = self._cfg()
        contacts.return_value = {
            "zhao_coo": {"email": "default-to@example.com"},
            "tian_xiaoying": {"email": "default-cc@example.com"},
        }
        send.return_value = True

        self.assertTrue(send_report_email(
            "日报",
            "<p>x</p>",
            to="override-to@example.com",
            cc="override-cc@example.com",
        ))
        args, kwargs = send.call_args
        self.assertEqual("日报", args[0])
        self.assertEqual(["override-to@example.com"], args[1])
        self.assertEqual(["override-cc@example.com"], args[2])
        self.assertEqual("<p>x</p>", kwargs["body_html"])
        self.assertEqual("Data Expert", kwargs["from_name"])

    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_send_email_omits_cc_header_when_cc_absent(self, smtp_cfg, smtp_ssl):
        smtp_cfg.return_value = self._cfg()
        session = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = session

        self.assertTrue(send_email(
            "日报",
            ["to@example.com"],
            body_html="<p>x</p>",
        ))
        _from, recipients, raw = session.sendmail.call_args[0]
        self.assertEqual("from@example.com", _from)
        self.assertEqual(["to@example.com"], recipients)
        msg = message_from_string(raw)
        self.assertEqual("to@example.com", msg["To"])
        self.assertIsNone(msg["Cc"])


if __name__ == "__main__":
    unittest.main()
