import unittest

from app_report_data import build_trend_data
from app_report_html import kpi_cards_html


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_groups_by_day_and_sorts(self):
        rows = [
            {
                "ftime": "20260227010101",
                "amt": "100",
                "pay_num": "2",
                "active_members": "10",
                "refund_money": "5",
                "retain_1d": "3",
                "order_cnt": "4",
                "order_pay": "2",
                "anchmems": "1",
                "giftmems": "2",
                "fugou_amt": "10",
            },
            {
                "ftime": "20260226010101",
                "amt": "50",
                "pay_num": "1",
                "active_members": "8",
                "refund_money": "1",
                "retain_1d": "2",
                "order_cnt": "2",
                "order_pay": "1",
                "anchmems": "1",
                "giftmems": "1",
                "fugou_amt": "6",
            },
            {
                "ftime": "20260227125959",
                "amt": "200",
                "pay_num": "3",
                "active_members": "20",
                "refund_money": "10",
                "retain_1d": "7",
                "order_cnt": "5",
                "order_pay": "4",
                "anchmems": "3",
                "giftmems": "5",
                "fugou_amt": "12",
            },
        ]

        result = build_trend_data(rows)
        self.assertEqual([x["dt"] for x in result], ["2026-02-26", "2026-02-27"])

        day_26 = result[0]
        self.assertEqual(day_26["amt"], 50.0)
        self.assertEqual(day_26["pay_num"], 1.0)
        self.assertEqual(day_26["active_members"], 8.0)
        self.assertAlmostEqual(day_26["arpu"], 50.0)
        self.assertAlmostEqual(day_26["pay_rate"], 12.5)
        self.assertAlmostEqual(day_26["order_conv"], 50.0)

        day_27 = result[1]
        self.assertEqual(day_27["amt"], 300.0)
        self.assertEqual(day_27["pay_num"], 5.0)
        self.assertEqual(day_27["active_members"], 30.0)
        self.assertEqual(day_27["refund_money"], 15.0)
        self.assertEqual(day_27["order_cnt"], 9.0)
        self.assertEqual(day_27["order_pay"], 6.0)
        self.assertAlmostEqual(day_27["arpu"], 60.0)
        self.assertAlmostEqual(day_27["pay_rate"], 16.6666666667)
        self.assertAlmostEqual(day_27["order_conv"], 66.6666666667)

    def test_build_trend_data_handles_zero_denominators(self):
        result = build_trend_data(
            [
                {
                    "ftime": "20260228000000",
                    "amt": "0",
                    "pay_num": "0",
                    "active_members": "0",
                    "order_cnt": "0",
                    "order_pay": "0",
                }
            ]
        )

        self.assertEqual(len(result), 1)
        day = result[0]
        self.assertEqual(day["dt"], "2026-02-28")
        self.assertEqual(day["arpu"], 0)
        self.assertEqual(day["pay_rate"], 0)
        self.assertEqual(day["order_conv"], 0)


class KpiCardsHtmlTests(unittest.TestCase):
    def _sample_metrics(self):
        return {
            "active": 1000,
            "retain_rate_1d": 45.0,
            "retain_rate_7d": 20.0,
            "pay_rate": 5.5,
            "pay_num": 55,
            "arpu": 32.0,
            "total_rev": 176000.0,
            "fugou_amt": 20000.0,
            "fugou_pct": 11.4,
            "refund_rate": 1.5,
            "order_conv": 70.0,
            "order_fail": 10,
            "zhenxin_pct": 60.0,
            "amt_m": 600000.0,
            "pay_m": 500,
        }

    def test_kpi_cards_contains_sparkline_when_trend_data_available(self):
        t = self._sample_metrics()
        p = {"active": 900, "total_rev": 150000.0}
        trends = [
            {
                "active_members": 900,
                "pay_rate": 4.2,
                "arpu": 30.0,
                "amt": 120000.0,
                "fugou_amt": 15000.0,
                "refund_money": 800.0,
                "order_conv": 60.0,
                "retain_1d": 350,
            },
            {
                "active_members": 1000,
                "pay_rate": 5.5,
                "arpu": 32.0,
                "amt": 176000.0,
                "fugou_amt": 20000.0,
                "refund_money": 900.0,
                "order_conv": 70.0,
                "retain_1d": 450,
            },
        ]

        html = kpi_cards_html(t, p, trends)
        self.assertIn("<svg", html)
        self.assertIn("流转: DAU1,000", html)

    def test_kpi_cards_omits_sparkline_for_missing_or_zero_trends(self):
        t = self._sample_metrics()
        p = {"active": 900, "total_rev": 150000.0}

        html_no_trend = kpi_cards_html(t, p, trends=[])
        self.assertNotIn("<svg", html_no_trend)

        html_zero_trend = kpi_cards_html(
            t,
            p,
            trends=[
                {
                    "active_members": 0,
                    "pay_rate": 0,
                    "arpu": 0,
                    "amt": 0,
                    "fugou_amt": 0,
                    "refund_money": 0,
                    "order_conv": 0,
                    "retain_1d": 0,
                },
                {
                    "active_members": 0,
                    "pay_rate": 0,
                    "arpu": 0,
                    "amt": 0,
                    "fugou_amt": 0,
                    "refund_money": 0,
                    "order_conv": 0,
                    "retain_1d": 0,
                },
            ],
        )
        self.assertNotIn("<svg", html_zero_trend)


if __name__ == "__main__":
    unittest.main()
