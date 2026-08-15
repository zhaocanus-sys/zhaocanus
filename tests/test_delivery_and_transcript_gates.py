# -*- coding: utf-8 -*-
"""Regression coverage for report delivery gates and transcript API stubs.

These paths are not covered by open PRs #73/#74 (exporter / DataExpert SMTP):
- email_sender refuses to open SMTP when credentials are missing.
- send_report_email falls back to contacts() when to/cc are omitted.
- transcript_api_client.is_api_configured treats blank URLs as unconfigured
  and fetch_transcripts stays a local stub (no network).
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_system.actions.email_sender import send_email, send_report_email
from quality_supervision.transcript_api_client import (
    fetch_transcripts,
    is_api_configured,
)


class _FakeSMTP:
    def __init__(self, *args, **kwargs):
        self.login_args = None
        self.sent = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def login(self, user, password):
        self.login_args = (user, password)

    def sendmail(self, frm, recipients, payload):
        self.sent = (frm, set(recipients), payload)


class EmailDeliveryGateTests(unittest.TestCase):
    def test_send_email_skips_smtp_without_credentials(self):
        cases = [
            {"from_email": "", "auth_code": "token"},
            {"from_email": "sender@example.com", "auth_code": ""},
        ]
        for cfg in cases:
            with self.subTest(cfg=cfg):
                with patch(
                    "agent_system.actions.email_sender.smtp_config",
                    return_value=cfg,
                ), patch(
                    "agent_system.actions.email_sender.smtplib.SMTP_SSL",
                ) as smtp:
                    ok = send_email("subj", ["to@example.com"], body_html="<p>x</p>")
                    self.assertFalse(ok)
                    smtp.assert_not_called()

    def test_send_email_uses_template_and_returns_true(self):
        fake = _FakeSMTP()
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "report.html"
            template.write_text("<h1>模板正文</h1>", encoding="utf-8")
            with patch(
                "agent_system.actions.email_sender.smtp_config",
                return_value={
                    "host": "smtp.example.com",
                    "port": 465,
                    "from_email": "sender@example.com",
                    "auth_code": "test-auth",
                    "from_name": "智慧助理",
                },
            ), patch(
                "agent_system.actions.email_sender.smtplib.SMTP_SSL",
                return_value=fake,
            ):
                ok = send_email(
                    "日报",
                    ["to@example.com"],
                    cc=["cc@example.com"],
                    body_html="<p>会被模板覆盖</p>",
                    html_template_path=str(template),
                )
        self.assertTrue(ok)
        self.assertEqual(fake.login_args, ("sender@example.com", "test-auth"))
        self.assertEqual(fake.sent[0], "sender@example.com")
        self.assertEqual(fake.sent[1], {"to@example.com", "cc@example.com"})
        self.assertIn("模板正文", fake.sent[2])
        self.assertNotIn("会被模板覆盖", fake.sent[2])

    def test_send_email_returns_false_when_smtp_raises(self):
        with patch(
            "agent_system.actions.email_sender.smtp_config",
            return_value={
                "from_email": "sender@example.com",
                "auth_code": "test-auth",
            },
        ), patch(
            "agent_system.actions.email_sender.smtplib.SMTP_SSL",
            side_effect=OSError("smtp down"),
        ):
            self.assertFalse(send_email("subj", ["to@example.com"], body_text="hi"))

    def test_send_report_email_uses_contact_defaults(self):
        with patch(
            "agent_system.actions.email_sender.smtp_config",
            return_value={"from_email": "sender@example.com", "auth_code": "x"},
        ), patch(
            "agent_system.actions.email_sender.contacts",
            return_value={
                "zhao_coo": {"email": "coo@example.com"},
                "tian_xiaoying": {"email": "assistant@example.com"},
            },
        ), patch(
            "agent_system.actions.email_sender.send_email",
            return_value=True,
        ) as send:
            ok = send_report_email("subj", "<p>hi</p>")
        self.assertTrue(ok)
        args, kwargs = send.call_args
        self.assertEqual(args[0], "subj")
        self.assertEqual(args[1], ["coo@example.com"])
        self.assertEqual(args[2], ["assistant@example.com"])
        self.assertEqual(kwargs["body_html"], "<p>hi</p>")
        self.assertEqual(kwargs["from_name"], "Data Expert")

    def test_send_report_email_omits_blank_default_cc(self):
        with patch(
            "agent_system.actions.email_sender.smtp_config",
            return_value={"from_email": "sender@example.com", "auth_code": "x"},
        ), patch(
            "agent_system.actions.email_sender.contacts",
            return_value={
                "zhao_coo": {"email": "coo@example.com"},
                "tian_xiaoying": {"email": ""},
            },
        ), patch(
            "agent_system.actions.email_sender.send_email",
            return_value=True,
        ) as send:
            send_report_email("subj", "<p>hi</p>")
        self.assertEqual(send.call_args[0][2], [])


class TranscriptApiGateTests(unittest.TestCase):
    def test_is_api_configured_requires_nonblank_base_url(self):
        cases = [
            ({}, False),
            ({"transcript_api": {}}, False),
            ({"transcript_api": {"base_url": ""}}, False),
            ({"transcript_api": {"base_url": "   "}}, False),
            ({"transcript_api": {"base_url": "http://transcript.local"}}, True),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                with patch(
                    "quality_supervision.transcript_api_client.facts",
                    return_value=payload,
                ):
                    self.assertEqual(is_api_configured(), expected)

    def test_fetch_transcripts_stays_local_stub(self):
        self.assertEqual(fetch_transcripts(), [])
        self.assertEqual(fetch_transcripts("2026-02-27", "hongniang"), [])


if __name__ == "__main__":
    unittest.main()
