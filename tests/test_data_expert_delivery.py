import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent_system.agents.data_expert import DataExpert


def make_report(*, departments=None, total_revenue=120_000, rev_dod=3.5):
    return SimpleNamespace(
        date="2026-07-20",
        summary={
            "total_revenue": total_revenue,
            "rev_dod": rev_dod,
            "pc": 4_800,
            "cr": 21.5,
        },
        departments=departments or [
            {"dept_name": "电销一部", "total_revenue": total_revenue}
        ],
        data_collision_summary={"total_collisions": 6},
        logic_collision_summary={"total_hypotheses": 4, "causal_chains": 2},
        cross_domain_summary={"total_collisions": 3, "domains_count": 2},
        improvements=[],
        get_all_findings_sorted=Mock(return_value=[]),
    )


class DataExpertDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.expert = object.__new__(DataExpert)
        self.expert.total_books = 108
        self.expert.domains = 8
        self.expert.render_html = Mock(return_value="<html>report</html>")

    @patch("agent_system.agents.data_expert.send_report_email", return_value=True)
    def test_send_email_delegates_content_and_recipients_to_shared_transport(
        self, send_report_email
    ):
        report = make_report()

        result = self.expert.send_email(
            report, to="owner@example.com", cc="assistant@example.com"
        )

        self.assertTrue(result)
        subject, html = send_report_email.call_args.args
        self.assertIn("【电销体检】07月20日", subject)
        self.assertIn("¥12.0万(↑3.5%)", subject)
        self.assertIn("[数据对撞6组+逻辑对撞4组]", subject)
        self.assertEqual("<html>report</html>", html)
        self.assertEqual(
            {"to": "owner@example.com", "cc": "assistant@example.com"},
            send_report_email.call_args.kwargs,
        )

    @patch("agent_system.agents.data_expert.send_report_email", return_value=False)
    def test_send_email_propagates_transport_failure(self, send_report_email):
        self.assertFalse(self.expert.send_email(make_report()))
        send_report_email.assert_called_once()

    def test_pipeline_rejects_non_telesale_data_before_export_or_email(self):
        report = make_report(
            departments=[{"dept_name": "门店一部", "total_revenue": 120_000}]
        )
        self.expert.analyze = Mock(return_value=report)
        self.expert.export = Mock()
        self.expert.send_email = Mock()

        with self.assertRaisesRegex(AssertionError, "非电销部门数据泄漏"):
            self.expert.run_full_pipeline(
                report.date, send_mail=True, open_browser=False
            )

        self.expert.export.assert_not_called()
        self.expert.send_email.assert_not_called()

    def test_pipeline_rejects_revenue_mismatch_before_export_or_email(self):
        report = make_report(
            departments=[{"dept_name": "电销一部", "total_revenue": 119_000}]
        )
        self.expert.analyze = Mock(return_value=report)
        self.expert.export = Mock()
        self.expert.send_email = Mock()

        with self.assertRaisesRegex(AssertionError, "营收校验失败"):
            self.expert.run_full_pipeline(
                report.date, send_mail=True, open_browser=False
            )

        self.expert.export.assert_not_called()
        self.expert.send_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()
