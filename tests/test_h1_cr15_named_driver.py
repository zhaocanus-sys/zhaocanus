"""Regression coverage for leftover H1 |Δcr|==1.5 + named drivers.

PR #79 locked H1 支持 on a large connect swing and 推翻 on a large
allocation swing.
PR #109 locked alternative composition with a *small* |Δcr|=0.4 reject,
plus equal-gate silence and support==reject → 支持.
PR #123 locked |Δcr|==1.5 / -1.5 as reject with an *empty* alternative.

Remaining operators were never the primary lock:

- |Δcr|==1.5 is still reject, but a named secondary driver
  (alloc / conv / pc) must appear in the 推翻 alternative
- |Δcr|==-1.5 + alloc just-over likewise names 分配量变化
- all three drivers keep 分配量→转化率→人均产值 order even when
  the connect gate is sitting exactly on the 1.5 reject line

A flipped `>` to `>=` on the H1 connect gate would turn
|Δcr|==1.5 + alloc>50 into support==reject → 支持 and drop the
resource-side alternative. The daily 营收主因 card would then
blame a 1.5pp wiggle and hide the real allocation swing.

Does not retest PR #123 empty-driver 1.5 wording or PR #109
|Δcr|=0.4 composition as primary.
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
        "total_revenue": 110000,
        "cr": cr_last,
        "conv": 1.0,
        "pc": 3000,
        "allocated": 1000,
    }
    last.update(last_overrides)
    return [prev, last]


class H1Connect15NamedDriverTests(unittest.TestCase):
    def setUp(self):
        self.engine = LogicCollisionEngine()

    def _h1(self, trends):
        self.engine._build_and_test_hypotheses({}, [], trends, [])
        h1 = [h for h in self.engine.hypotheses if h["id"] == "H1"]
        self.assertEqual(1, len(h1))
        return h1[0]

    def test_cr_change_exactly_1_5_plus_alloc_names_分配量变化(self):
        # |Δcr|==1.5 → reject; |Δalloc|==51 > 50 → second reject.
        # Must stay 推翻 (2>0) and name the resource driver.
        h1 = self._h1(_trend_pair(43, 44.5, allocated=1051))
        self.assertEqual(0, len(h1["support_evidence"]))
        self.assertEqual(2, len(h1["reject_evidence"]))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_cr_change_exactly_1_5_plus_conv_names_转化率变化(self):
        h1 = self._h1(_trend_pair(43, 44.5, conv=1.06))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("转化率变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("人均产值变化", h1["alternative"])

    def test_cr_change_exactly_1_5_plus_pc_names_人均产值变化(self):
        h1 = self._h1(_trend_pair(43, 44.5, pc=3201))
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("人均产值变化", h1["alternative"])
        self.assertNotIn("分配量变化", h1["alternative"])
        self.assertNotIn("转化率变化", h1["alternative"])

    def test_cr_change_exactly_1_5_all_three_drivers_keep_order(self):
        h1 = self._h1(_trend_pair(43, 44.5, allocated=1100, conv=1.2, pc=3400))
        self.assertEqual("推翻", h1["verdict"])
        alt = h1["alternative"]
        self.assertIn("分配量变化", alt)
        self.assertIn("转化率变化", alt)
        self.assertIn("人均产值变化", alt)
        self.assertLess(alt.index("分配量变化"), alt.index("转化率变化"))
        self.assertLess(alt.index("转化率变化"), alt.index("人均产值变化"))

    def test_cr_change_exactly_minus_1_5_plus_alloc_still_names_driver(self):
        h1 = self._h1(_trend_pair(44.5, 43, allocated=1051))
        self.assertEqual(0, len(h1["support_evidence"]))
        self.assertIn("幅度不大", h1["reject_evidence"][0])
        self.assertEqual("推翻", h1["verdict"])
        self.assertIn("分配量变化", h1["alternative"])


if __name__ == "__main__":
    unittest.main()
