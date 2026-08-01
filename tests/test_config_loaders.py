"""Regression coverage for shared config loading accessors.

Covers:
- missing facts/preferences files return empty dicts (no crash)
- JSON cache hit until reload()
- smtp_config / contacts / dept_managers / api_config projections
- preferences() independent cache key from facts()

Uses a temporary config directory so real credentials are never read or asserted.
Deterministic stdlib unittest; no network required.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import agent_system.config as config


class ConfigLoaderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmp.name)
        self._orig_D = config._D
        config._D = self._tmp_path
        config.reload()

    def tearDown(self):
        config._D = self._orig_D
        config.reload()
        self._tmp.cleanup()

    def _write_facts(self, payload: dict):
        (self._tmp_path / "facts.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def _write_prefs(self, payload: dict):
        (self._tmp_path / "preferences.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def test_missing_files_return_empty_and_accessors_default(self):
        self.assertEqual(config.facts(), {})
        self.assertEqual(config.preferences(), {})
        self.assertEqual(config.smtp_config(), {})
        self.assertEqual(config.contacts(), {})
        self.assertEqual(config.dept_managers(), {})
        self.assertEqual(config.api_config(), {})

    def test_facts_projections_and_cache_until_reload(self):
        self._write_facts({
            "smtp": {"host": "smtp.example.test", "port": 465, "from_email": "bot@example.test"},
            "contacts": {"zhao_coo": {"name": "赵总", "email": "zhao@example.test"}},
            "dept_managers": {"电销一部": "何丹丹", "电销六部": "游云清"},
            "api": {"base_url": "http://example.test", "api_key": "test-key-not-real"},
        })
        config.reload()

        self.assertEqual(config.smtp_config()["host"], "smtp.example.test")
        self.assertEqual(config.contacts()["zhao_coo"]["email"], "zhao@example.test")
        self.assertEqual(config.dept_managers()["电销六部"], "游云清")
        self.assertEqual(config.api_config()["api_key"], "test-key-not-real")

        # Mutate file on disk; cache should still serve the old snapshot
        self._write_facts({
            "smtp": {"host": "smtp.changed.test"},
            "dept_managers": {"电销一部": "新经理"},
        })
        self.assertEqual(config.smtp_config()["host"], "smtp.example.test")
        self.assertEqual(config.dept_managers()["电销六部"], "游云清")

        config.reload()
        self.assertEqual(config.smtp_config()["host"], "smtp.changed.test")
        self.assertEqual(config.dept_managers(), {"电销一部": "新经理"})
        self.assertEqual(config.api_config(), {})

    def test_preferences_uses_independent_cache_key(self):
        self._write_facts({"smtp": {"host": "smtp.example.test"}})
        self._write_prefs({
            "report_standards": {
                "redline_words": ["示例红线词A", "示例红线词B"],
                "modules": 14,
            }
        })
        config.reload()

        prefs = config.preferences()
        facts = config.facts()
        self.assertEqual(prefs["report_standards"]["modules"], 14)
        self.assertEqual(
            prefs["report_standards"]["redline_words"],
            ["示例红线词A", "示例红线词B"],
        )
        self.assertIn("smtp", facts)
        self.assertNotIn("report_standards", facts)

        # Changing preferences should not flush facts cache until reload
        self._write_prefs({"report_standards": {"modules": 99}})
        self.assertEqual(config.preferences()["report_standards"]["modules"], 14)
        self.assertEqual(config.facts()["smtp"]["host"], "smtp.example.test")

        config.reload()
        self.assertEqual(config.preferences()["report_standards"]["modules"], 99)
        self.assertEqual(config.facts()["smtp"]["host"], "smtp.example.test")


if __name__ == "__main__":
    unittest.main()
