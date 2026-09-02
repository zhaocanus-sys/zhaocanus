"""Regression coverage for leftover KB / config fallback and redline keywords.

MEMORIES leftover: DataExpert._load_knowledge_base missing book_index
must zero total_books/domains (the happy-path file is present on main,
so the else branch was never locked). A missing or relocated index
would silently advertise 0 books in every DataExpert header.

Config reload / missing-file fallback is shared by SMTP, contacts,
dept managers, and API headers. A stale cache after a failed write
would keep sending with yesterday's credentials view; a missing file
must yield {} rather than raise.

DataCollisionEngine leftover: missing data_collision_rules.json
must leave rules/benchmarks empty and _bm(...) == 0. A wrong
default would change every collision threshold.

Feasibility leftover keywords (PR #112 locked 加班/逼签/升级系统
etc., not these remaining tokens):
- 快速转化 → low + 风险回流总部 / SaaS隔离
- 加量 → low + 鞭打快牛
- APP端 → cross_dept / medium

Does not lock DataExpert.send_email (PR #74). Does not import
generate_telesale_full_report. Does not read or assert secret values
from facts.json.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_system.agents.data_expert import DataExpert
from agent_system.engines.collision_engine import (
    DataCollisionEngine,
    validate_feasibility,
)
from agent_system import config as cfg


class KnowledgeBaseFallbackTests(unittest.TestCase):
    def test_missing_book_index_zeros_books_and_domains(self):
        real_exists = os.path.exists

        def fake_exists(path):
            if str(path).endswith("book_index.json"):
                return False
            return real_exists(path)

        with patch("agent_system.agents.data_expert.os.path.exists", side_effect=fake_exists):
            expert = DataExpert(db_path="/tmp/coverage-dummy.db")

        self.assertEqual({}, expert.knowledge_base)
        self.assertEqual(0, expert.total_books)
        self.assertEqual(0, expert.domains)

    def test_present_book_index_exposes_meta_keys(self):
        expert = DataExpert(db_path="/tmp/coverage-dummy.db")
        self.assertIn("knowledge_base_meta", expert.knowledge_base)
        meta = expert.knowledge_base["knowledge_base_meta"]
        self.assertIsInstance(expert.total_books, int)
        self.assertEqual(meta.get("total_books"), expert.total_books)
        self.assertEqual(meta.get("domains"), expert.domains)
        self.assertGreaterEqual(expert.total_books, 0)


class ConfigReloadAndMissingFileTests(unittest.TestCase):
    def tearDown(self):
        cfg.reload()

    def test_missing_facts_file_returns_empty_mappings(self):
        cfg.reload()
        with patch.object(Path, "exists", return_value=False):
            self.assertEqual({}, cfg.facts())
            self.assertEqual({}, cfg.smtp_config())
            self.assertEqual({}, cfg.api_config())
            self.assertEqual({}, cfg.contacts())
            self.assertEqual({}, cfg.dept_managers())

    def test_reload_rereads_json_after_stale_cache(self):
        cfg.reload()
        cfg._cache["facts"] = {"smtp": {"host": "stale.example.test", "port": 25}}
        self.assertEqual("stale.example.test", cfg.smtp_config()["host"])

        fake = json.dumps({"smtp": {"host": "fresh.example.test", "port": 465}})
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=fake):
                cfg.reload()
                self.assertEqual("fresh.example.test", cfg.smtp_config()["host"])
                self.assertEqual(465, cfg.smtp_config()["port"])


class CollisionRulesFallbackTests(unittest.TestCase):
    def test_missing_rules_file_zeros_benchmarks(self):
        real_exists = os.path.exists

        def fake_exists(path):
            if str(path).endswith("data_collision_rules.json"):
                return False
            return real_exists(path)

        with patch(
            "agent_system.engines.collision_engine.os.path.exists",
            side_effect=fake_exists,
        ):
            engine = DataCollisionEngine()

        self.assertEqual({}, engine.rules)
        self.assertEqual({}, engine.benchmarks)
        self.assertEqual(0, engine._bm("connect_rate"))
        self.assertEqual(0, engine._bm("connect_rate", "critical"))


class FeasibilityLeftoverKeywordTests(unittest.TestCase):
    def test_fast_conversion_is_compliance_low(self):
        result = validate_feasibility({
            "title": "提升签单",
            "act": "对高意向客户快速转化",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("low", result["feasibility"])
        self.assertIn("风险回流总部", result["risk_notes"])
        self.assertIn("SaaS隔离", result["risk_notes"])

    def test_add_volume_is_overload_low(self):
        result = validate_feasibility({
            "title": "活动量",
            "act": "全员加量跟进公海",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("low", result["feasibility"])
        self.assertIn("鞭打快牛", result["risk_notes"])

    def test_app_side_is_cross_dept_medium(self):
        result = validate_feasibility({
            "title": "导流",
            "act": "协调APP端补齐入口转化",
            "detail": "",
            "daily_action": "",
        })
        self.assertEqual("medium", result["feasibility"])
        self.assertEqual("cross_dept", result["dependency"])
        self.assertIn("APP端", result["risk_notes"])


if __name__ == "__main__":
    unittest.main()
