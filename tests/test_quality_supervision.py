import unittest

from quality_supervision.verification_engine import verify_transcript


class VerifyTranscriptTests(unittest.TestCase):
    def test_hongniang_transcript_passes_when_required_terms_present(self):
        text = "本次服务会说明价格、收费、退费、合同、服务期和冷静期规则。"

        result = verify_transcript(text, line="hongniang")

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])

    def test_missing_required_terms_are_reported(self):
        result = verify_transcript("只介绍价格和合同", line="hongniang")

        self.assertFalse(result["pass"])
        self.assertIn("必说缺失：收费", result["issues"])
        self.assertIn("必说缺失：退费", result["issues"])
        self.assertIn("必说缺失：服务期", result["issues"])
        self.assertIn("必说缺失：冷静期", result["issues"])

    def test_forbidden_terms_fail_even_when_required_terms_are_present(self):
        text = "价格、收费、退费、合同、服务期、冷静期都清楚说明，但保证找到。"

        result = verify_transcript(text, line="hongniang")

        self.assertFalse(result["pass"])
        self.assertIn("禁止用语：保证找到", result["issues"])

    def test_kefu_uses_its_own_required_terms(self):
        result = verify_transcript("价格、退费、投诉渠道均已说明", line="kefu")

        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])


if __name__ == "__main__":
    unittest.main()
