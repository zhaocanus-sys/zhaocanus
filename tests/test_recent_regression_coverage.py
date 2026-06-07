import time
import unittest

from agent_system.actions.api_client import parallel_fetch, safe_float, safe_int
from agent_system.actions.report_sparkline import extract_trend_values, sparkline_svg
from generate_hongniang_full_report import agg_hongniang
from generate_telesale_full_report import agg_telesale, dept_rows


class ReportSparklineTests(unittest.TestCase):
    def test_sparkline_renders_trend_direction_and_ignores_missing_values(self):
        rising = sparkline_svg([None, 10, 15, 20])
        falling = sparkline_svg([20, 15, 10])

        self.assertIn("<svg", rising)
        self.assertIn("<polyline", rising)
        self.assertIn('fill="#16a34a"', rising)
        self.assertIn('fill="#dc2626"', falling)

    def test_sparkline_handles_empty_single_and_flat_series(self):
        self.assertEqual(sparkline_svg([]), "")
        self.assertEqual(sparkline_svg([3]), "")

        flat = sparkline_svg([3, 3, 3])
        self.assertIn("<svg", flat)
        self.assertIn("<polygon", flat)
        self.assertIn('fill="#16a34a"', flat)

    def test_extract_trend_values_returns_chronological_series_with_fallbacks(self):
        history = [
            {"date": "2026-03-02", "metrics": {"revenue": 120}},
            {"date": "2026-03-01", "metrics": {"revenue": 100}},
        ]

        self.assertEqual(
            extract_trend_values(history, "revenue", today_val=130),
            [100.0, 120.0, 130.0],
        )
        self.assertEqual(
            extract_trend_values([], "revenue", today_val=130, prev_val=90),
            [90.0, 130.0],
        )


class ApiClientHelperTests(unittest.TestCase):
    def test_safe_numeric_parsing_handles_common_api_formats(self):
        self.assertEqual(safe_float("1,234.50"), 1234.5)
        self.assertEqual(safe_float("12.5%"), 12.5)
        self.assertEqual(safe_float(None, d=7.5), 7.5)
        self.assertEqual(safe_float("not-a-number", d=2.0), 2.0)
        self.assertEqual(safe_int("1,234.9"), 1234)

    def test_parallel_fetch_handles_empty_calls(self):
        self.assertEqual(parallel_fetch([]), [])

    def test_parallel_fetch_preserves_input_order_even_when_completion_order_differs(self):
        def slow_first():
            time.sleep(0.03)
            return "first"

        def fast_second():
            return "second"

        def medium_third():
            time.sleep(0.01)
            return "third"

        self.assertEqual(
            parallel_fetch([slow_first, fast_second, medium_third]),
            ["first", "second", "third"],
        )

    def test_parallel_fetch_isolates_exceptions_to_the_failing_slot(self):
        def ok():
            return {"rows": [1]}

        def boom():
            raise RuntimeError("upstream timeout")

        results = parallel_fetch([ok, boom, ok])

        self.assertEqual(results[0], {"rows": [1]})
        self.assertEqual(results[2], {"rows": [1]})
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("upstream timeout", results[1]["error"])


class BusinessAggregationTests(unittest.TestCase):
    def test_telesale_aggregation_computes_core_rates_and_ignores_zero_ai_scores(self):
        rows = [
            {
                "dept_name": "电销一部",
                "pay_1d_amt": "1,000",
                "worker_nums": "2",
                "callout_1d_num": "100",
                "link_1d_num": "25",
                "linkmems_deeptalk_10_1d_num": "10",
                "pay_1d_num": "2",
                "pay_1m_amt": "9,000",
                "new_worker_num": "1",
                "ai_score": "80",
            },
            {
                "dept_name": "电销二部",
                "pay_1d_amt": "500",
                "worker_nums": "1",
                "callout_1d_num": "0",
                "link_1d_num": "5",
                "linkmems_deeptalk_10_1d_num": "1",
                "pay_1d_num": "1",
                "pay_1m_amt": "1,000",
                "new_worker_num": "0",
                "ai_score": "0",
            },
        ]

        agg = agg_telesale(rows)

        self.assertEqual(agg["total_rev"], 1500)
        self.assertEqual(agg["workers"], 3)
        self.assertEqual(agg["calls"], 100)
        self.assertEqual(agg["links"], 30)
        self.assertEqual(agg["deep"], 11)
        self.assertAlmostEqual(agg["connect_rate"], 30.0)
        self.assertAlmostEqual(agg["deep_rate"], 36.6666666667)
        self.assertAlmostEqual(agg["conv_rate"], 27.2727272727)
        self.assertAlmostEqual(agg["per_capita"], 500.0)
        self.assertEqual(agg["avg_ai"], 80)

    def test_telesale_department_rows_are_sorted_and_safe_on_zero_denominators(self):
        rows = [
            {
                "dept_name": "低营收部",
                "pay_1d_amt": "0",
                "worker_nums": "0",
                "callout_1d_num": "0",
                "link_1d_num": "0",
                "linkmems_deeptalk_10_1d_num": "0",
                "pay_1d_num": "0",
            },
            {
                "dept_name": "高营收部",
                "pay_1d_amt": "200",
                "worker_nums": "2",
                "callout_1d_num": "20",
                "link_1d_num": "10",
                "linkmems_deeptalk_10_1d_num": "5",
                "pay_1d_num": "1",
            },
        ]

        depts = dept_rows(rows)

        self.assertEqual([d["dept_name"] for d in depts], ["高营收部", "低营收部"])
        self.assertEqual(depts[1]["per_capita"], 0)
        self.assertEqual(depts[1]["connect_rate"], 0)
        self.assertEqual(depts[1]["deep_rate"], 0)

    def test_hongniang_aggregation_sums_refund_channels_and_zero_denominators(self):
        rows = [
            {
                "pay_1d_amt": "1,000",
                "pay_1m_amt": "5,000",
                "staff_new": "2",
                "jm_n": "6",
                "link_time_count": "20",
                "deep_count": "5",
                "zhenai_back": "10",
                "zhenaigd_back": "20",
                "zhenai_hz_back": "30",
                "zhenai_xfh_back": "40",
                "zhenai_md_back": "50",
            },
            {
                "pay_1d_amt": "0",
                "pay_1m_amt": "1,000",
                "staff_new": "0",
                "jm_n": "0",
                "link_time_count": "0",
                "deep_count": "0",
            },
        ]

        agg = agg_hongniang(rows)

        self.assertEqual(agg["total_refund"], 150)
        self.assertEqual(agg["pay_m"], 6000)
        self.assertEqual(agg["jm_rate"], 3)
        self.assertEqual(agg["per_rev"], 500)
        self.assertAlmostEqual(agg["refund_rate"], 15.0)
        self.assertAlmostEqual(agg["deep_rate"], 25.0)


if __name__ == "__main__":
    unittest.main()
