"""Regression coverage for leftover email From/To join and ad_categories path.

PR #115 locked missing credentials, an existing html_template_path, and
send_report_email default TO / blank CC. PR #116 locked SMTP exception,
missing-template keeps body_html, and body_text attaches text/plain.

Leftover:
- from_name override must win over cfg from_name; empty from_name
  falls back to cfg
- To / Cc headers join with ", "; sendmail recipients are the
  de-duplicated union
- ad_categories must hit /api/v1/advertising/categories (PR #115
  locked ad_daily / ad_report date params, not this path)

A swapped From header or a dropped To address would send the daily
report as the wrong identity or drop a manager from the envelope.
A wrong ad_categories path would empty the advertising taxonomy
used by APP/投放 windows.

Does not lock DataExpert.send_email (open PR #74, hardcoded SMTP).
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest
from email import message_from_string
from email.header import decode_header, make_header
from unittest.mock import MagicMock, patch

from agent_system.actions.api_client import ad_categories
from agent_system.actions.email_sender import send_email


def _header(value):
    """RFC 2047-decode a header so CJK From names stay readable."""
    return str(make_header(decode_header(value)))


class EmailFromNameAndRecipientTests(unittest.TestCase):
    def _cfg(self):
        return {
            "host": "smtp.example.com",
            "port": 465,
            "from_email": "from@example.com",
            "auth_code": "token",
            "from_name": "智慧助理",
        }

    def _session(self, smtp_ssl):
        session = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = session
        return session

    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_from_name_override_wins_over_cfg(self, smtp_cfg, smtp_ssl):
        smtp_cfg.return_value = self._cfg()
        session = self._session(smtp_ssl)

        self.assertTrue(send_email(
            "日报",
            ["to@example.com"],
            body_html="<p>x</p>",
            from_name="自定义发件人",
        ))
        raw = session.sendmail.call_args[0][2]
        msg = message_from_string(raw)
        self.assertEqual("自定义发件人 <from@example.com>", _header(msg["From"]))

    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_empty_from_name_uses_cfg_display_name(self, smtp_cfg, smtp_ssl):
        smtp_cfg.return_value = self._cfg()
        session = self._session(smtp_ssl)

        self.assertTrue(send_email(
            "日报",
            ["to@example.com"],
            body_html="<p>x</p>",
            from_name="",
        ))
        raw = session.sendmail.call_args[0][2]
        msg = message_from_string(raw)
        self.assertEqual("智慧助理 <from@example.com>", _header(msg["From"]))

    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_to_cc_join_and_sendmail_union_dedup(self, smtp_cfg, smtp_ssl):
        smtp_cfg.return_value = self._cfg()
        session = self._session(smtp_ssl)

        self.assertTrue(send_email(
            "日报",
            ["a@example.com", "b@example.com"],
            cc=["c@example.com", "a@example.com"],
            body_html="<p>x</p>",
        ))
        _from, recipients, raw = session.sendmail.call_args[0]
        self.assertEqual("from@example.com", _from)
        self.assertEqual(
            {"a@example.com", "b@example.com", "c@example.com"},
            set(recipients),
        )
        msg = message_from_string(raw)
        self.assertEqual("a@example.com, b@example.com", msg["To"])
        self.assertEqual("c@example.com, a@example.com", msg["Cc"])


class AdCategoriesPathTests(unittest.TestCase):
    def test_ad_categories_hits_categories_endpoint(self):
        resp = MagicMock()
        resp.json.return_value = {"rows": [], "row_count": 0}
        resp.raise_for_status = MagicMock()

        with patch(
            "agent_system.actions.api_client.requests.request",
            return_value=resp,
        ) as req:
            ad_categories()

        self.assertEqual(1, req.call_count)
        method, url = req.call_args.args[:2]
        self.assertEqual("GET", method)
        self.assertTrue(url.endswith("/api/v1/advertising/categories"))
        self.assertEqual(30, req.call_args.kwargs["timeout"])
        self.assertFalse(req.call_args.kwargs.get("params"))


if __name__ == "__main__":
    unittest.main()
