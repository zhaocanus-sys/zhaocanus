import unittest

from generate_app_full_report import build_trend_data, fetch_app_trend_rows


class AppTrendReportTests(unittest.TestCase):
    def test_build_trend_data_groups_rows_by_day_and_computes_rates(self):
        rows = [
            {
                "ftime": "20260228",
                "amt": "1,000",
                "pay_num": "10",
                "active_members": "200",
                "refund_money": "10",
                "retain_1d": "20",
            },
            {
                "ftime": "20260227 10:00:00",
                "amt": "500",
                "pay_num": "5",
                "active_members": "50",
                "refund_money": "0",
                "retain_1d": "5",
            },
            {
                "ftime": "20260228",
                "amt": "250",
                "pay_num": "5",
                "active_members": "50",
                "refund_money": "5",
                "retain_1d": "10",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([item["dt"] for item in trends], ["2026-02-27", "2026-02-28"])
        self.assertEqual(trends[0]["amt"], 500.0)
        self.assertEqual(trends[0]["pay_rate"], 10.0)
        self.assertEqual(trends[1]["amt"], 1250.0)
        self.assertEqual(trends[1]["pay_num"], 15.0)
        self.assertEqual(trends[1]["active_members"], 250.0)
        self.assertEqual(trends[1]["refund_money"], 15.0)
        self.assertEqual(trends[1]["retain_1d"], 30.0)
        self.assertEqual(trends[1]["arpu"], 1250.0 / 15.0)
        self.assertEqual(trends[1]["pay_rate"], 6.0)

    def test_build_trend_data_handles_zero_denominators(self):
        trends = build_trend_data([
            {"ftime": "20260228", "amt": "99", "pay_num": "0", "active_members": "0"}
        ])

        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)

    def test_fetch_app_trend_rows_fetches_exact_10_day_window_and_tags_rows(self):
        calls = []

        def fake_daily(team, date):
            calls.append((team, date))
            if date in {"20260220", "20260228"}:
                return {"rows": [{"amt": "100"}]}
            return {"rows": []}

        rows = fetch_app_trend_rows("20260228", fetch_daily=fake_daily)

        self.assertEqual(
            calls,
            [
                ("app", "20260219"),
                ("app", "20260220"),
                ("app", "20260221"),
                ("app", "20260222"),
                ("app", "20260223"),
                ("app", "20260224"),
                ("app", "20260225"),
                ("app", "20260226"),
                ("app", "20260227"),
                ("app", "20260228"),
            ],
        )
        self.assertEqual([row["ftime"] for row in rows], ["20260220", "20260228"])


if __name__ == "__main__":
    unittest.main()
