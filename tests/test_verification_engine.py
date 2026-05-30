import unittest

from quality_supervision.verification_engine import verify_transcript


class VerifyTranscriptTest(unittest.TestCase):
    def test_hongniang_passes_when_all_required_terms_are_present(self):
        result = verify_transcript(
            "本次会说明价格、收费方式、退费规则、合同条款、服务期和冷静期。"
        )

        self.assertTrue(result["pass"])
        self.assertEqual([], result["issues"])

    def test_hongniang_reports_missing_required_terms(self):
        result = verify_transcript("已说明收费、退费、合同、服务期和冷静期。")

        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：价格", result["issues"])

    def test_forbidden_phrase_fails_even_when_required_terms_present(self):
        result = verify_transcript(
            "价格、收费、退费、合同、服务期、冷静期都已说明，我们包成功。"
        )

        self.assertFalse(result["pass"])
        self.assertIn("禁止用语：包成功", result["issues"])

    def test_kefu_line_uses_kefu_required_terms(self):
        result = verify_transcript("客服已说明价格、退费和投诉渠道。", line="kefu")

        self.assertTrue(result["pass"])
        self.assertEqual([], result["issues"])

    def test_unknown_line_only_checks_forbidden_terms(self):
        result = verify_transcript("内部抽检文本包含普通服务说明。", line="unknown")

        self.assertTrue(result["pass"])
        self.assertEqual([], result["issues"])

    def test_reports_multiple_issue_types_together(self):
        result = verify_transcript("只说明收费，但承诺一定能达成。")

        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：价格", result["issues"])
        self.assertIn("禁止用语：一定能", result["issues"])
        self.assertGreaterEqual(len(result["issues"]), 2)


if __name__ == "__main__":
    unittest.main()
