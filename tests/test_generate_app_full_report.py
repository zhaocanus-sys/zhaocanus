import unittest

from generate_app_full_report import build_trend_data, generate_html


PRODUCT_VALUES = {
    "zhenxin_member": 85000,
    "super_member_full": 9000,
    "live_guard": 3000,
    "super_member_plus": 1000,
    "zhenai_coin": 700,
    "super_remind": 500,
    "star_privilege": 300,
    "super_recommend": 200,
    "other": 100,
}


def app_row(**overrides):
    row = {
        "amt": 100000,
        "pay_num": 100,
        "active_members": 1000,
        "refund_money": 1000,
        "pay_num_new": 20,
        "retain_1d": 400,
        "retain_7d": 300,
        "order_cnt": 100,
        "order_pay": 80,
        "reg_num_m": 2000,
        "pay_num_m": 500,
        "pay_amt_m": 1000000,
        "mems": 1000,
        "pay_amt": 100000,
        **PRODUCT_VALUES,
    }
    row.update(overrides)
    return row


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_groups_rows_by_day_and_sorts_chronologically(self):
        trend_rows = [
            {
                "ftime": "2026022708",
                "amt": "1,000",
                "pay_num": "10",
                "active_members": "100",
                "refund_money": "25",
                "retain_1d": "1",
            },
            {
                "ftime": "20260226",
                "amt": "500",
                "pay_num": "5",
                "active_members": "0",
                "refund_money": "0",
                "retain_1d": "2",
            },
            {
                "ftime": "2026022712",
                "amt": "500",
                "pay_num": "5",
                "active_members": "50",
                "refund_money": "5",
                "retain_1d": "2",
            },
        ]

        result = build_trend_data(trend_rows)

        self.assertEqual([row["dt"] for row in result], ["2026-02-26", "2026-02-27"])
        self.assertEqual(result[1]["amt"], 1500.0)
        self.assertEqual(result[1]["pay_num"], 15.0)
        self.assertEqual(result[1]["active_members"], 150.0)
        self.assertEqual(result[1]["refund_money"], 30.0)
        self.assertEqual(result[1]["arpu"], 100.0)
        self.assertEqual(result[1]["pay_rate"], 10.0)
        self.assertEqual(result[0]["pay_rate"], 0)


class AppHtmlRegressionTests(unittest.TestCase):
    def test_generate_html_renders_trends_and_resolves_product_compare_names(self):
        html = generate_html(
            today_rows=[app_row()],
            prev_rows=[app_row(amt=90000, pay_num=90, active_members=900, zhenxin_member=70000)],
            trend_rows_raw=[
                {
                    "ftime": "20260226",
                    "amt": 50000,
                    "pay_num": 50,
                    "active_members": 1000,
                    "refund_money": 100,
                    "retain_1d": 300,
                },
                {
                    "ftime": "20260227",
                    "amt": 100000,
                    "pay_num": 100,
                    "active_members": 1000,
                    "refund_money": 1000,
                    "retain_1d": 400,
                },
            ],
            date_display="2026-02-27",
        )

        self.assertIn("10日营收趋势", html)
        self.assertIn("width:100%;background:#0f172a", html)
        self.assertNotIn("{tn}", html)
        self.assertNotIn("{bn}", html)


if __name__ == "__main__":
    unittest.main()
