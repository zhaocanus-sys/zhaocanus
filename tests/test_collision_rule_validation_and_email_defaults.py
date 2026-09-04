"""Regression coverage for collision rule-validation and email defaults.

DataCollisionEngine._validate_rules / LogicCollisionEngine._validate_rules
were never locked. If the P2 对撞数量不足 / 对撞类型覆盖不足 / 假设数量不足
cards disappear, a thin data day would ship as a complete three-engine
analysis. AnalysisReport.get_all_findings_sorted is the merge used by
DataExpert 高管摘要 — a flipped key would bury P0 under P2.

Email leftover (PR #115/#117/#118 locked creds / From / To+Cc / override):
- smtp missing host/port must fall back to smtp.exmail.qq.com:465
- send_report_email with empty contacts and blank `to` must use from_email

Does not lock persistence global cr_below_count (PR #48), APP sparkline
mapping, shop double-count, parallel_fetch([]), or CrossDomain KeyError.
Does not import generate_telesale_full_report.
Does not read or assert secret values from facts.json.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest
from email import message_from_string
from email.header import decode_header
from unittest.mock import MagicMock, patch

from agent_system.actions.email_sender import send_email, send_report_email
from agent_system.engines.analysis_pipeline import AnalysisReport
from agent_system.engines.collision_engine import (
    CollisionFinding,
    DataCollisionEngine,
    LogicCollisionEngine,
)


def _finding(priority, impact, tag):
    return CollisionFinding(
        collision_type="test",
        tag=tag,
        description="d",
        revenue_impact=impact,
        priority=priority,
    )


class DataCollisionRuleValidationTests(unittest.TestCase):
    def test_empty_engine_emits_both_validation_cards(self):
        engine = DataCollisionEngine()
        engine._validate_rules()
        tags = [f.tag for f in engine.findings]
        self.assertEqual(["对撞数量不足", "对撞类型覆盖不足"], tags)
        self.assertTrue(all(f.priority == "P2" for f in engine.findings))
        self.assertIn("当前仅完成0组对撞", engine.findings[0].description)
        # first card itself registers type `rule_validation`
        self.assertIn("仅覆盖1种对撞类型", engine.findings[1].description)
        self.assertIn("rule_validation", engine.findings[1].description)
        summary = engine.get_summary()
        self.assertFalse(summary["rules_satisfied"])
        self.assertEqual(2, summary["findings_by_priority"]["P2"])

    def test_five_collisions_but_two_types_emits_coverage_card_only(self):
        engine = DataCollisionEngine()
        engine.collision_count = 5
        engine.collision_types_used = {"metric_x_time", "funnel_x_benchmark"}
        engine._validate_rules()
        tags = [f.tag for f in engine.findings]
        self.assertEqual(["对撞类型覆盖不足"], tags)
        self.assertIn("metric_x_time", engine.findings[0].description)
        self.assertIn("funnel_x_benchmark", engine.findings[0].description)

    def test_five_collisions_and_three_types_is_silent(self):
        engine = DataCollisionEngine()
        engine.collision_count = 5
        engine.collision_types_used = {
            "metric_x_time",
            "funnel_x_benchmark",
            "metric_x_entity",
        }
        engine._validate_rules()
        self.assertEqual([], engine.findings)
        self.assertTrue(engine.get_summary()["rules_satisfied"])


class LogicCollisionRuleValidationTests(unittest.TestCase):
    def test_thin_payload_emits_hypothesis_shortage(self):
        engine = LogicCollisionEngine()
        summary = {
            "allocated": 100,
            "alloc_rate": 0.5,
            "on_duty": 10,
            "cr": 50,
            "dial_count": 200,
            "dr": 20,
            "ai": 80,
            "conv": 2.0,
            "signed_deals": 10,
            "total_revenue": 50_000,
            "pc": 5_000,
            "ref_rate": 2,
            "complaint_count": 0,
            "t20": 40,
            "roi": 250,
        }
        depts = [{
            "dept_name": "电销一部",
            "per_capita_revenue": 5_000,
            "refund_rate": 3,
            "connect_rate": 50,
            "total_revenue": 50_000,
            "signed_deals": 10,
            "avg_ai_score": 80,
        }]
        findings, hypotheses, _chains = engine.execute(summary, depts, [], [], [])
        self.assertEqual([], hypotheses)
        tags = [f.tag for f in findings]
        self.assertEqual(["假设数量不足"], tags)
        self.assertEqual("P2", findings[0].priority)
        self.assertIn("当前仅建立0个假设", findings[0].description)
        logic_summary = engine.get_summary()
        self.assertEqual(0, logic_summary["total_hypotheses"])
        self.assertFalse(logic_summary["rules_satisfied"])


class FindingsSortContractTests(unittest.TestCase):
    def test_merged_findings_sort_by_priority_then_impact(self):
        report = AnalysisReport(
            date="2026-09-04",
            summary={},
            departments=[],
            trends=[],
            persons=[],
            top_performers=[],
            bottom_performers=[],
            new_hire_stats=[],
            tenure_analysis={},
            data_collision_findings=[
                _finding("P2", 9_000, "d2"),
                _finding("P0", 100, "d0-low"),
            ],
            data_collision_summary={},
            logic_collision_findings=[
                _finding("P1", 50, "l1"),
                _finding("PX", 1, "unknown"),
            ],
            logic_collision_summary={},
            cross_domain_findings=[_finding("P0", 500, "c0-high")],
        )
        self.assertEqual(
            ["c0-high", "d0-low", "l1", "d2", "unknown"],
            [f.tag for f in report.get_all_findings_sorted()],
        )


class EmailDefaultDeliveryTests(unittest.TestCase):
    @patch("agent_system.actions.email_sender.smtplib.SMTP_SSL")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_missing_host_port_use_exmail_defaults(self, smtp_cfg, smtp_ssl):
        smtp_cfg.return_value = {
            "from_email": "from@example.com",
            "auth_code": "token",
        }
        session = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = session

        self.assertTrue(send_email("日报", ["to@example.com"], body_html="<p>x</p>"))
        smtp_ssl.assert_called_once_with("smtp.exmail.qq.com", 465, timeout=15)
        session.login.assert_called_once_with("from@example.com", "token")
        _from, _recipients, raw = session.sendmail.call_args[0]
        msg = message_from_string(raw)
        decoded = "".join(
            part.decode(enc or "utf-8") if isinstance(part, bytes) else part
            for part, enc in decode_header(msg["From"])
        )
        self.assertEqual("智慧助理 <from@example.com>", decoded)

    @patch("agent_system.actions.email_sender.send_email")
    @patch("agent_system.actions.email_sender.contacts")
    @patch("agent_system.actions.email_sender.smtp_config")
    def test_report_email_falls_back_to_from_email_when_contacts_empty(
        self, smtp_cfg, contacts_fn, send
    ):
        smtp_cfg.return_value = {
            "from_email": "from@example.com",
            "auth_code": "token",
        }
        contacts_fn.return_value = {}
        send.return_value = True

        self.assertTrue(send_report_email("日报", "<p>x</p>"))
        args, kwargs = send.call_args
        self.assertEqual("日报", args[0])
        self.assertEqual(["from@example.com"], args[1])
        self.assertEqual([], args[2])
        self.assertEqual("<p>x</p>", kwargs["body_html"])
        self.assertEqual("Data Expert", kwargs["from_name"])


if __name__ == "__main__":
    unittest.main()
