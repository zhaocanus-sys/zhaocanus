"""Regression coverage for quality-supervision compliance and email delivery gates.

quality_supervision is the only compliance verifier on main. A missing
MUST_SAY keyword (价格/退费/冷静期) or a leaked FORBIDDEN phrase
(保证找到/先付款再看) would silently pass a transcript that should fail
质检 — high legal/brand blast radius. kefu uses a shorter MUST_SAY set
than hongniang; an unknown line must not inherit hongniang keywords.

transcript_api_client.is_api_configured is the gate before any live
transcript pull. A blank/missing base_url must stay False so report
jobs do not pretend the API is wired. fetch_transcripts is still a
stub on main (returns []) — locked as the current contract.

email_sender.send_email is the shared SMTP path for all five report
generators. Missing from_email/auth_code must return False without
opening a socket. send_report_email recipient fallbacks (赵总 TO,
田小英 CC, blank CC omitted) sit on every daily send.

Does not import generate_telesale_full_report (illegal f-string on main).
Does not lock DataExpert.send_email SMTP path (open PR #74).
Does not lock persistence global cr_below_count (PR #48), APP sparkline
rate-field mapping, shop double-count, or parallel_fetch([]).

Deterministic stdlib unittest only — no live SMTP/API.
"""

import tempfile
import unittest
from email import message_from_string
from pathlib import Path
from unittest.mock import MagicMock, patch

from quality_supervision.transcript_api_client import (
    fetch_transcripts,
    is_api_configured,
)
from quality_supervision.verification_engine import FORBIDDEN, MUST_SAY, verify_transcript


_HONGNIANG_OK = "本次沟通说明了价格、收费、退费规则、合同条款、服务期和冷静期。"
_KEFU_OK = "客服已告知价格、退费流程和投诉渠道。"


class QualitySupervisionComplianceTests(unittest.TestCase):
    def test_hongniang_complete_transcript_passes(self):
        result = verify_transcript(_HONGNIANG_OK, line="hongniang")
        self.assertTrue(result["pass"])
        self.assertEqual([], result["issues"])

    def test_hongniang_missing_cooling_off_fails(self):
        text = "本次沟通说明了价格、收费、退费、合同和服务期。"
        result = verify_transcript(text, line="hongniang")
        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：冷静期", result["issues"])
        self.assertEqual(1, len(result["issues"]))

    def test_forbidden_guarantee_phrase_fails_even_when_must_say_complete(self):
        result = verify_transcript(_HONGNIANG_OK + "我们保证找到对象。", line="hongniang")
        self.assertFalse(result["pass"])
        self.assertIn("禁止用语：保证找到", result["issues"])

    def test_kefu_requires_complaint_channel_not_contract(self):
        missing_channel = "客服已告知价格和退费。"
        result = verify_transcript(missing_channel, line="kefu")
        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：投诉渠道", result["issues"])
        self.assertNotIn("必说缺失：合同", result["issues"])

        ok = verify_transcript(_KEFU_OK, line="kefu")
        self.assertTrue(ok["pass"])
        self.assertEqual([], ok["issues"])

    def test_unknown_line_skips_must_say_and_still_flags_forbidden(self):
        self.assertNotIn("other", MUST_SAY)
        clean = verify_transcript("随便闲聊，没有必说词。", line="other")
        self.assertTrue(clean["pass"])
        self.assertEqual([], clean["issues"])

        banned = verify_transcript("可以先付款再看效果。", line="other")
        self.assertFalse(banned["pass"])
        self.assertIn("禁止用语：先付款再看", banned["issues"])
        self.assertTrue(any("必说缺失" not in issue for issue in banned["issues"]))
        self.assertTrue(all(w in FORBIDDEN for w in ("保证找到", "一定能", "包成功", "先付款再看")))

    def test_is_api_configured_requires_nonblank_base_url(self):
        with patch(
            "quality_supervision.transcript_api_client.facts",
            return_value={},
        ):
            self.assertFalse(is_api_configured())
        with patch(
            "quality_supervision.transcript_api_client.facts",
            return_value={"transcript_api": {"base_url": "   "}},
        ):
            self.assertFalse(is_api_configured())
        with patch(
            "quality_supervision.transcript_api_client.facts",
            return_value={"transcript_api": {"base_url": "http://transcript.local"}},
        ):
            self.assertTrue(is_api_configured())

    def test_fetch_transcripts_stub_returns_empty_list(self):
        self.assertEqual([], fetch_transcripts())
        self.assertEqual([], fetch_transcripts(date="20260831", line="hongniang"))


class EmailSenderGateTests(unittest.TestCase):
    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_missing_credentials_skip_smtp(self, smtp_cfg, smtp_ssl):
        from agent_system.actions.email_sender import send_email

        smtp_cfg.return_value = {
            "host": "smtp.example.com",
            "port": 465,
            "from_email": "",
            "auth_code": "unused",
        }
        self.assertFalse(send_email("subj", ["to@example.com"]))
        smtp_ssl.assert_not_called()

        smtp_cfg.return_value = {
            "from_email": "from@example.com",
            "auth_code": "",
        }
        self.assertFalse(send_email("subj", ["to@example.com"]))
        smtp_ssl.assert_not_called()

    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_html_template_path_becomes_body(self, smtp_cfg, smtp_ssl):
        from agent_system.actions.email_sender import send_email

        smtp_cfg.return_value = {
            "host": "smtp.example.com",
            "port": 465,
            "from_email": "from@example.com",
            "auth_code": "token",
            "from_name": "智慧助理",
        }
        session = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = session

        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "body.html"
            template.write_text("<p>模板正文</p>", encoding="utf-8")
            ok = send_email(
                "日报",
                ["to@example.com"],
                cc=["cc@example.com"],
                html_template_path=str(template),
            )
        self.assertTrue(ok)
        session.login.assert_called_once_with("from@example.com", "token")
        _from, recipients, raw = session.sendmail.call_args[0]
        self.assertEqual("from@example.com", _from)
        self.assertEqual({"to@example.com", "cc@example.com"}, set(recipients))
        html_bodies = [
            part.get_payload(decode=True).decode("utf-8")
            for part in message_from_string(raw).walk()
            if part.get_content_type() == "text/html"
        ]
        self.assertEqual(["<p>模板正文</p>"], html_bodies)

    @patch("agent_system.actions.email_sender.send_email")
    @patch("agent_system.actions.email_sender.contacts")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_report_email_defaults_and_skips_blank_cc(self, smtp_cfg, contacts_fn, send):
        from agent_system.actions.email_sender import send_report_email

        smtp_cfg.return_value = {
            "from_email": "from@example.com",
            "auth_code": "token",
        }
        contacts_fn.return_value = {
            "zhao_coo": {"email": "zhao@example.com"},
            "tian_xiaoying": {"email": ""},
        }
        send.return_value = True

        ok = send_report_email("【门店体检】08月31日", "<p>html</p>")
        self.assertTrue(ok)
        args, kwargs = send.call_args
        self.assertEqual("【门店体检】08月31日", args[0])
        self.assertEqual(["zhao@example.com"], args[1])
        self.assertEqual([], args[2])
        self.assertEqual("<p>html</p>", kwargs["body_html"])
        self.assertEqual("Data Expert", kwargs["from_name"])


if __name__ == "__main__":
    unittest.main()
