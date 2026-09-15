"""Regression coverage for leftover H1 decline alloc==50 × conv 1.051.

PR #125 locked |Δcr|==+1.5 + alloc==50 / pc==200 unnamed on a
*rising* day, and +1.5 + alloc==50 + conv just-over names only
转化率变化.
PR #128 locked falling |Δcr|==-1.5 + conv 1.049 unnamed / 1.051
named (alloc held flat).
PR #129 locked falling -1.5 + alloc==50 / pc==200 unnamed, and
alloc==51 / pc==201 named (conv held flat).

The combined leftover was never the primary lock:

- 44.5→43 (`-1.5`) + alloc==50 + conv==1.051 names only 转化率变化
- same CR + alloc==51 + conv==1.051 names both 分配量变化 and 转化率变化
- `-1.5` + alloc==50 + conv==1.051 + pc==201 names 转化率变化 and
  人均产值变化, still not 分配量变化

Does not retest PR #129 alloc-only / pc-only or PR #128 conv-only
as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import LogicCollisionEngine


def _trend_pair(cr_prev, cr_last, **last_overrides):
    prev = {
        "total_revenue": 100000,
        "cr": cr_prev,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last = {
        "total_revenue": 90000,
        "cr": cr_last,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last.update(last_overrides)
    return [prev, last]


class H1DeclineAlloc50PlusConv1051Tests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, trends):
        self.engine.hypotheses = []
        self.engine._build_and_test_hypotheses({}, [], trends, [])
        h1 = [h for h in self.engine.hypotheses if h["id"] == "H1"]
        self.assertEqual(1, len(h1))
        return h1[0]

    def test_cr_minus_1_5_alloc_50_plus_conv_1_051_names_only_conversion(self):
        # Combined leftover after PR #129's alloc==50 unnamed and
        # PR #128's conv 1.051 named: the 50-条 jitter stays unnamed
        # while 转化率变化 is the only driver label.
        h1 = self._h1(_trend_pair(44.5, 43.0, allocated=1050, conv=1.051))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("下降", h1["hypothesis"])
        self.assertTrue(any("幅度不大" in e for e in h1["reject_evidence"]))
        self.assertFalse(any("分配量变动" in e for e in h1["reject_evidence"]))
        self.assertIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_cr_minus_1_5_alloc_51_plus_conv_1_051_names_both_drivers(self):
        # 1051-1000 == 51 > 50 AND conv 1.051. Both leftover named
        # ticks together. Flipping alloc `>` to `>=` would keep the
        # conv-only suite green while blaming a 50-条 wobble.
        h1 = self._h1(_trend_pair(44.5, 43.0, allocated=1051, conv=1.051))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("分配量变化", h1["alternative"])
        self.assertIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])
        self.assertTrue(any("分配量变动" in e for e in h1["reject_evidence"]))
        self.assertEqual(2, len(h1["reject_evidence"]))

    def test_cr_minus_1_5_alloc_50_conv_1_051_pc_201_omits_allocation(self):
        # Three leftover ticks: alloc stays unnamed, conv + pc name.
        # Locks the AND of the two named drivers without dragging a
        # 50-条 jitter into the 主因 sentence.
        h1 = self._h1(_trend_pair(
            44.5, 43.0, allocated=1050, conv=1.051, pc=3201,
        ))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("转化率变化", h1["alternative"])
        self.assertIn("人均产值变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertFalse(any("分配量变动" in e for e in h1["reject_evidence"]))


if __name__ == "__main__":
    unittest.main()
