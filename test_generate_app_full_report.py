import unittest

from generate_app_full_report import build_trend_data


class BuildTrendDataTests(unittest.TestCase):
    def test_groups_rows_by_day_and_sorts_ascending(self):
        trend_rows = [
            {"ftime": "20260303", "amt": 200, "pay_num": 4, "active_members": 100, "refund_money": 20, "retain_1d": 40},
            {"ftime": "20260301", "amt": 100, "pay_num": 2, "active_members": 50, "refund_money": 10, "retain_1d": 20},
            {"ftime": "20260303", "amt": 100, "pay_num": 1, "active_members": 50, "refund_money": 5, "retain_1d": 10},
        ]

        result = build_trend_data(trend_rows)

        self.assertEqual([item["dt"] for item in result], ["2026-03-01", "2026-03-03"])
        self.assertEqual(result[1]["amt"], 300.0)
        self.assertEqual(result[1]["pay_num"], 5.0)
        self.assertEqual(result[1]["active_members"], 150.0)
        self.assertEqual(result[1]["refund_money"], 25.0)
        self.assertEqual(result[1]["retain_1d"], 50.0)
        self.assertEqual(result[1]["arpu"], 60.0)
        self.assertAlmostEqual(result[1]["pay_rate"], 5 / 150 * 100)

    def test_handles_zero_denominator_for_rates(self):
        trend_rows = [
            {"ftime": "20260305", "amt": 50, "pay_num": 0, "active_members": 0},
        ]

        result = build_trend_data(trend_rows)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["arpu"], 0)
        self.assertEqual(result[0]["pay_rate"], 0)


if __name__ == "__main__":
    unittest.main()
