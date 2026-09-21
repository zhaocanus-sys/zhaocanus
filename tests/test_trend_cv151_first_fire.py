"""Regression coverage for leftover trend CV==0.151 first 营收波动.

PR #80 locked far-volatility fire.
PR #121 locked exact silence at CV==0.15.
PR #126 locked leftover first fire at CV==0.16 (840/1000/1160).

The leftover 3-decimal tick was never the primary lock:

- 849/1000/1151 → sample stdev=151, CV=0.151 is the first
  `rev_cv > 0.15` tick
- 850/1000/1150 → CV==0.150 stays silent

Does not retest PR #126 far 0.16 as primary.
Does not import generate_telesale_full_report.

Deterministic stdlib unittest only — no live SMTP/API.
"""

import unittest

from agent_system.engines.collision_engine import DataCollisionEngine


def _days(*revs):
    dates = ["2026-09-18", "2026-09-19", "2026-09-20"]
    return [{"dt": dt, "total_revenue": rev} for dt, rev in zip(dates, revs)]


class TrendCv151FirstFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = DataCollisionEngine()

    def test_cv_151_is_first_volatility_tick(self):
        # mean=1000, sample stdev=151, CV=0.151. Distinct from
        # PR #126's 840/1000/1160 (CV=0.16).
        # Impact = round(151 * 0.5) = 76.
        self.engine._collide_trend_x_volatility(_days(849, 1000, 1151))
        cards = [f for f in self.engine.findings if f.tag == "营收波动过大"]
        self.assertEqual(1, len(cards))
        self.assertEqual("P2", cards[0].priority)
        self.assertEqual("global", cards[0].scope)
        self.assertEqual(76, cards[0].revenue_impact)
        self.assertIn("7日营收CV=0.151(>0.15)", cards[0].description)
        self.assertTrue(any("营收CV=0.151" in e for e in cards[0].evidence))
        self.assertIn("系统脆弱性高", cards[0].description)
        self.assertIn("DA03:信号与噪声-预测思维", cards[0].knowledge_refs)

    def test_cv_exactly_150_stays_silent(self):
        # 850/1000/1150 → stdev=150, CV=0.15 is not `> 0.15`.
        # Flipping to `>=` would keep PR #126's 0.16 suite green
        # while tagging a 贴线 15% 波动日 as 系统脆弱.
        self.engine._collide_trend_x_volatility(_days(850, 1000, 1150))
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "营收波动过大"],
        )

    def test_two_day_window_stays_silent_even_with_leftover_swing(self):
        # len < 3 early-returns. Leftover 0.151 still needs 3 days.
        self.engine._collide_trend_x_volatility(
            [
                {"dt": "2026-09-19", "total_revenue": 849},
                {"dt": "2026-09-20", "total_revenue": 1151},
            ]
        )
        self.assertEqual(
            [],
            [f for f in self.engine.findings if f.tag == "营收波动过大"],
        )


if __name__ == "__main__":
    unittest.main()
