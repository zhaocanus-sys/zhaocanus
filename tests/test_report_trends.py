import unittest

from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from app_report_html import kpi_cards_html
from generate_app_full_report import build_trend_data


class SparklineSvgTests(unittest.TestCase):
    def test_returns_empty_for_insufficient_data(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([None, 42]), "")

    def test_flat_series_renders_without_division_by_zero(self):
        svg = sparkline_svg([5, 5, 5], width=30, height=12, fill=True)

        self.assertIn('<svg width="30" height="12"', svg)
        self.assertIn("<polygon", svg)
        self.assertIn("<polyline", svg)
        self.assertIn('<circle cx="29.0" cy="11.0" r="2" fill="#16a34a"', svg)

    def test_downward_last_point_uses_red_dot(self):
        svg = sparkline_svg([10, 7], fill=False)

        self.assertNotIn("<polygon", svg)
        self.assertIn('fill="#dc2626"', svg)
        self.assertIn('stroke="#3b82f6"', svg)


class ExtractTrendValuesTests(unittest.TestCase):
    def test_history_is_returned_chronologically_and_missing_values_are_zero(self):
        history = [
            {"date": "2026-02-27", "metrics": {"revenue": 300}},
            {"date": "2026-02-26", "metrics": {"revenue": None}},
            {"date": "2026-02-25", "metrics": {"other": 100}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=400),
            [0.0, 0.0, 300.0, 400.0],
        )

    def test_previous_value_provides_baseline_when_history_is_empty(self):
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=12, prev_val=10),
            [10.0, 12.0],
        )


class AppTrendDataTests(unittest.TestCase):
    def test_build_trend_data_groups_rows_by_day_and_computes_rates(self):
        rows = [
            {
                "ftime": "20260227090000",
                "amt": "100",
                "pay_num": "2",
                "active_members": "20",
                "refund_money": "5",
                "retain_1d": "4",
            },
            {
                "ftime": "20260227120000",
                "amt": "50",
                "pay_num": "1",
                "active_members": "10",
                "refund_money": "2",
                "retain_1d": "1",
            },
            {
                "ftime": "20260226090000",
                "amt": "80",
                "pay_num": "0",
                "active_members": "0",
                "refund_money": "0",
                "retain_1d": "0",
            },
        ]

        trends = build_trend_data(rows)

        self.assertEqual([row["dt"] for row in trends], ["2026-02-26", "2026-02-27"])
        self.assertEqual(trends[0]["arpu"], 0)
        self.assertEqual(trends[0]["pay_rate"], 0)
        self.assertEqual(trends[1]["amt"], 150.0)
        self.assertEqual(trends[1]["pay_num"], 3.0)
        self.assertEqual(trends[1]["active_members"], 30.0)
        self.assertEqual(trends[1]["refund_money"], 7.0)
        self.assertEqual(trends[1]["retain_1d"], 5.0)
        self.assertEqual(trends[1]["arpu"], 50.0)
        self.assertEqual(trends[1]["pay_rate"], 10.0)


class KpiCardsHtmlTrendTests(unittest.TestCase):
    def _metrics(self):
        return {
            "active": 200000,
            "retain_rate_1d": 40.0,
            "retain_rate_7d": 25.0,
            "pay_rate": 4.0,
            "pay_num": 8000,
            "arpu": 25.0,
            "total_rev": 200000.0,
            "fugou_amt": 50000.0,
            "fugou_pct": 25.0,
            "refund_rate": 1.5,
            "order_conv": 60.0,
            "order_fail": 40,
            "zhenxin_pct": 70.0,
            "amt_m": 1000000.0,
            "pay_m": 30000,
        }

    def test_kpi_cards_render_sparklines_when_trend_has_at_least_two_days(self):
        trends = [
            {
                "active_members": 180000,
                "pay_rate": 3.5,
                "arpu": 22,
                "amt": 180000,
                "fugou_amt": 45000,
                "refund_money": 2000,
                "order_conv": 55,
                "retain_1d": 35,
            },
            {
                "active_members": 200000,
                "pay_rate": 4.0,
                "arpu": 25,
                "amt": 200000,
                "fugou_amt": 50000,
                "refund_money": 3000,
                "order_conv": 60,
                "retain_1d": 40,
            },
        ]

        html = kpi_cards_html(self._metrics(), {}, trends=trends)

        self.assertGreaterEqual(html.count("<svg"), 8)
        self.assertIn("DAU", html)
        self.assertIn("订单成功率60.0%", html)

    def test_kpi_cards_skip_sparklines_for_single_day_trend(self):
        html = kpi_cards_html(
            self._metrics(),
            {},
            trends=[{"active_members": 200000, "amt": 200000}],
        )

        self.assertNotIn("<svg", html)


if __name__ == "__main__":
    unittest.main()
