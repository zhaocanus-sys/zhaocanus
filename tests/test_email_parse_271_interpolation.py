"""Regression coverage for leftover email HTML-only, parse edges, 271 interpolation.

Email leftover (PR #115 template / PR #116 body_text + SMTP exception /
PR #117 From/To+Cc): body_html without body_text must attach only
text/html, and SMTP_SSL must keep timeout=15. Dropping the html part
or hanging on a blocked SMTP handshake would drop every daily report.

safe_float leftover (PR #113 locked comma/percent/whitespace and
None/""/"abc"/"—"): currency ¥ is not stripped (current contract →
default); combined "1,234.56%" and signed "-12.5%" must still parse.
safe_int leftover: "1,234.9" truncates after the same cleanup.
These helpers feed all five report aggregators.

CrossDomain leftover (PR #115 locked 271 fire/silence; PR #111 locked
社会认同 `{t20}` with 2 depts so 271 stayed off): when 271 fires,
`{t20}` must interpolate. A missing format key would raise and, if
uncaught, abort the remaining always-on cards.

ReportMemory leftover (PR #113 locked +10000 → 1.0万): negative
万-unit formatting. extract leftover (PR #112 locked today_val=None
does not append): today_val=0 is not None and must still append.

Does not retest 社会认同 trigger, 271 on/off, or positive 万 as primary.
Does not lock persistence global cr_below_count (PR #48), APP sparkline
mapping, shop double-count, parallel_fetch([]), or CrossDomain
missing-key format() crash.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest
from email import message_from_string
from unittest.mock import MagicMock, patch

from agent_system.actions.api_client import safe_float, safe_int
from agent_system.actions.memory_manager import ReportMemory
from agent_system.actions.report_sparkline import extract_trend_values
from agent_system.engines.collision_engine import CrossDomainCollisionEngine


def _full_summary(**overrides):
    summary = {
        "dr": 10.0,
        "conv": 2.0,
        "avg_deal": 6000,
        "t20": 40,
        "fc_rate": 5.0,
        "ai": 80,
        "ref_rate": 2.0,
    }
    summary.update(overrides)
    return summary


def _depts(*pcs):
    return [
        {"dept_name": f"电销{i}部", "per_capita_revenue": pc}
        for i, pc in enumerate(pcs, 1)
    ]


class EmailHtmlOnlyAndTimeoutTests(unittest.TestCase):
    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_html_only_attaches_html_and_uses_ssl_timeout(self, smtp_cfg, smtp_ssl):
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

        ok = send_email(
            "日报",
            ["to@example.com"],
            body_html="<p>仅HTML</p>",
        )
        self.assertTrue(ok)
        smtp_ssl.assert_called_once_with("smtp.example.com", 465, timeout=15)
        _from, recipients, raw = session.sendmail.call_args[0]
        self.assertEqual("from@example.com", _from)
        self.assertEqual(["to@example.com"], recipients)
        msg = message_from_string(raw)
        types = [part.get_content_type() for part in msg.walk() if part.get_content_maintype() != "multipart"]
        self.assertEqual(["text/html"], types)
        html_bodies = [
            part.get_payload(decode=True).decode("utf-8")
            for part in msg.walk()
            if part.get_content_type() == "text/html"
        ]
        self.assertEqual(["<p>仅HTML</p>"], html_bodies)


class SafeParseLeftoverTests(unittest.TestCase):
    def test_currency_symbol_falls_back_to_default(self):
        self.assertEqual(0.0, safe_float("¥1,234"))
        self.assertEqual(-1.0, safe_float("¥99", -1.0))

    def test_combined_comma_percent_and_signed_percent(self):
        self.assertEqual(1234.56, safe_float("1,234.56%"))
        self.assertEqual(-12.5, safe_float("-12.5%"))
        self.assertEqual(1234, safe_int("1,234.9"))


class CrossDomain271InterpolationTests(unittest.TestCase):
    def test_271_interpolates_t20_when_it_fires(self):
        engine = CrossDomainCollisionEngine()
        engine.execute(_full_summary(t20=60.5), _depts(3000, 3000, 3000, 3000), [], [])
        hits = [f for f in engine.findings if f.tag == "271法则×自然代谢替代裁员"]
        self.assertEqual(1, len(hits))
        self.assertIn("TOP20%占60.5%业绩", hits[0].description)
        self.assertEqual("P1", hits[0].priority)


class ReportMemoryFmtAndExtractLeftoverTests(unittest.TestCase):
    def test_fmt_negative_wan_unit(self):
        self.assertEqual("-1.0万", ReportMemory._fmt(-10000.0))
        self.assertEqual("-1.5万", ReportMemory._fmt(-15000.0))

    def test_extract_appends_today_val_zero(self):
        history = [{"date": "20260904", "metrics": {"cr": 40}}]
        self.assertEqual([40.0, 0.0], extract_trend_values(history, "cr", today_val=0))
        self.assertEqual([40.0], extract_trend_values(history, "cr", today_val=None))


if __name__ == "__main__":
    unittest.main()
