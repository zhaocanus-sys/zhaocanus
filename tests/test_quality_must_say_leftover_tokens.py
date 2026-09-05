"""Regression coverage for leftover quality_supervision MUST_SAY tokens.

PR #115 locked 冷静期 (hongniang) and 投诉渠道 (kefu) as the only
individual missing-token cases. PR #106 locked a generic miss/FORBIDDEN
pair. The remaining hongniang tokens (价格/收费/退费/合同/服务期) and
kefu tokens (价格/退费) were never the primary assertion.

A dropped token would let a 红娘/客服 recording pass 质检 without
disclosing 价格/收费/退费/合同/服务期 — legal and brand blast radius.
Empty text must still list every hongniang MUST_SAY in definition order.

Does not retest 冷静期 / 投诉渠道 / 保证找到 / 一定能 / 包成功 /
先付款再看 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from quality_supervision.verification_engine import MUST_SAY, verify_transcript


_HONGNIANG_COMPLETE = {
    "价格": "本次沟通说明了收费、退费规则、合同条款、服务期和冷静期。",
    "收费": "本次沟通说明了价格、退费规则、合同条款、服务期和冷静期。",
    "退费": "本次沟通说明了价格、收费、合同条款、服务期和冷静期。",
    "合同": "本次沟通说明了价格、收费、退费规则、服务期和冷静期。",
    "服务期": "本次沟通说明了价格、收费、退费规则、合同条款和冷静期。",
}

_KEFU_COMPLETE = {
    "价格": "客服已告知退费流程和投诉渠道。",
    "退费": "客服已告知价格和投诉渠道。",
}


class HongniangMustSayLeftoverTests(unittest.TestCase):
    def test_each_leftover_hongniang_token_fails_alone(self):
        leftover = ["价格", "收费", "退费", "合同", "服务期"]
        self.assertEqual(
            ["价格", "收费", "退费", "合同", "服务期", "冷静期"],
            MUST_SAY["hongniang"],
        )
        for token in leftover:
            with self.subTest(token=token):
                result = verify_transcript(_HONGNIANG_COMPLETE[token], line="hongniang")
                self.assertFalse(result["pass"])
                self.assertEqual([f"必说缺失：{token}"], result["issues"])

    def test_empty_hongniang_text_lists_every_must_say(self):
        result = verify_transcript("", line="hongniang")
        self.assertFalse(result["pass"])
        self.assertEqual(
            [f"必说缺失：{kw}" for kw in MUST_SAY["hongniang"]],
            result["issues"],
        )


class KefuMustSayLeftoverTests(unittest.TestCase):
    def test_each_leftover_kefu_token_fails_alone(self):
        leftover = ["价格", "退费"]
        self.assertEqual(["价格", "退费", "投诉渠道"], MUST_SAY["kefu"])
        for token in leftover:
            with self.subTest(token=token):
                result = verify_transcript(_KEFU_COMPLETE[token], line="kefu")
                self.assertFalse(result["pass"])
                self.assertEqual([f"必说缺失：{token}"], result["issues"])
                self.assertNotIn("必说缺失：合同", result["issues"])
                self.assertNotIn("必说缺失：投诉渠道", result["issues"])


if __name__ == "__main__":
    unittest.main()
