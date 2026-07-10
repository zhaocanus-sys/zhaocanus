import unittest
from unittest.mock import patch

from agent_system.actions import email_sender


class EmailSenderTests(unittest.TestCase):
    def test_send_email_returns_false_without_credentials_and_skips_smtp(self):
        with patch.object(email_sender, "smtp_config", return_value={"from_email": "", "auth_code": ""}), \
             patch.object(email_sender.smtplib, "SMTP_SSL") as smtp_ssl:
            ok = email_sender.send_email("日报", ["boss@example.com"], body_html="<p>ok</p>")

        self.assertFalse(ok)
        smtp_ssl.assert_not_called()

    def test_send_email_sends_html_to_deduped_to_and_cc_recipients(self):
        smtp_config = {
            "host": "smtp.example.com",
            "port": 465,
            "from_email": "reports@example.com",
            "auth_code": "secret",
            "from_name": "Reports",
        }
        with patch.object(email_sender, "smtp_config", return_value=smtp_config), \
             patch.object(email_sender.smtplib, "SMTP_SSL") as smtp_ssl:
            smtp = smtp_ssl.return_value.__enter__.return_value

            ok = email_sender.send_email(
                "日报",
                ["boss@example.com"],
                cc=["assistant@example.com", "boss@example.com"],
                body_html="<h1>ok</h1>",
                from_name="Data Expert",
            )

        self.assertTrue(ok)
        smtp_ssl.assert_called_once_with("smtp.example.com", 465, timeout=15)
        smtp.login.assert_called_once_with("reports@example.com", "secret")
        from_addr, recipients, message = smtp.sendmail.call_args.args
        self.assertEqual(from_addr, "reports@example.com")
        self.assertEqual(set(recipients), {"boss@example.com", "assistant@example.com"})
        self.assertIn("Data Expert <reports@example.com>", message)
        self.assertIn("Content-Type: text/html", message)
        self.assertIn("<h1>ok</h1>", message)

    def test_send_report_email_defaults_to_ceo_and_assistant_contacts(self):
        contacts = {
            "zhao_coo": {"email": "ceo@example.com"},
            "tian_xiaoying": {"email": "assistant@example.com"},
        }
        with patch.object(email_sender, "smtp_config", return_value={"from_email": "fallback@example.com"}), \
             patch.object(email_sender, "contacts", return_value=contacts), \
             patch.object(email_sender, "send_email", return_value=True) as send_email:
            ok = email_sender.send_report_email("门店报告", "<html>report</html>")

        self.assertTrue(ok)
        send_email.assert_called_once_with(
            "门店报告",
            ["ceo@example.com"],
            ["assistant@example.com"],
            body_html="<html>report</html>",
            from_name="Data Expert",
        )


if __name__ == "__main__":
    unittest.main()
