# -*- coding: utf-8 -*-
"""Regression coverage for quality-supervision transcript gates.

MUST_SAY / FORBIDDEN directly gate合规话术. The transcript API is still a
stub on main; these tests lock the local verifier and the stub contract
so a later wiring change cannot silently drop required disclosures.
"""
import unittest

from quality_supervision.transcript_api_client import fetch_transcripts, is_api_configured
from quality_supervision.verification_engine import FORBIDDEN, MUST_SAY, verify_transcript


def _ok_hongniang():
    return "沟通价格、收费、退费、合同、服务期和冷静期，不承诺结果"


def _ok_kefu():
    return "说明价格、退费和投诉渠道，按合同执行"


class TranscriptVerifierTests(unittest.TestCase):
    def test_hongniang_missing_required_phrase_fails(self):
        text = "沟通价格、收费、退费、合同、服务期"  # 缺冷静期
        result = verify_transcript(text, "hongniang")
        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：冷静期", result["issues"])
        self.assertEqual(1, len(result["issues"]))

    def test_hongniang_forbidden_phrase_fails_even_when_required_present(self):
        result = verify_transcript(_ok_hongniang() + "，保证找到对象", "hongniang")
        self.assertFalse(result["pass"])
        self.assertIn("禁止用语：保证找到", result["issues"])

    def test_kefu_line_uses_its_own_must_say_set(self):
        result = verify_transcript("只谈价格和退费", "kefu")
        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：投诉渠道", result["issues"])
        self.assertNotIn("必说缺失：冷静期", result["issues"])
        self.assertNotIn("必说缺失：合同", result["issues"])

    def test_complete_script_passes_and_unknown_line_still_blocks_forbidden(self):
        self.assertTrue(verify_transcript(_ok_hongniang(), "hongniang")["pass"])
        self.assertTrue(verify_transcript(_ok_kefu(), "kefu")["pass"])
        unknown = verify_transcript("包成功签约", "unknown-line")
        self.assertFalse(unknown["pass"])
        self.assertIn("禁止用语：包成功", unknown["issues"])
        self.assertEqual(MUST_SAY["hongniang"], ["价格", "收费", "退费", "合同", "服务期", "冷静期"])
        self.assertIn("一定能", FORBIDDEN)


class TranscriptApiStubTests(unittest.TestCase):
    def test_stub_is_unconfigured_and_returns_empty(self):
        self.assertFalse(is_api_configured())
        self.assertEqual([], fetch_transcripts(date="2026-02-27", line="hongniang"))


if __name__ == "__main__":
    unittest.main()
