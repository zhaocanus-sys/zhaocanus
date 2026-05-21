import time
import unittest

from agent_system.actions.api_client import parallel_fetch, safe_float, safe_int


class ApiClientHelperTests(unittest.TestCase):
    def test_safe_numeric_parsing_handles_report_field_formats(self):
        self.assertEqual(safe_float("1,234.50"), 1234.5)
        self.assertEqual(safe_float("12.5%"), 12.5)
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float("not-a-number", d=7.5), 7.5)
        self.assertEqual(safe_int("1,234.9"), 1234)

    def test_parallel_fetch_preserves_input_order_when_calls_finish_out_of_order(self):
        calls = [
            lambda: (time.sleep(0.02), {"rows": ["slow"]})[1],
            lambda: {"rows": ["fast"]},
            lambda: {"rows": ["last"]},
        ]

        self.assertEqual(
            parallel_fetch(calls),
            [{"rows": ["slow"]}, {"rows": ["fast"]}, {"rows": ["last"]}],
        )

    def test_parallel_fetch_isolates_single_call_failure(self):
        def broken():
            raise RuntimeError("boom")

        results = parallel_fetch([
            lambda: {"rows": [1]},
            broken,
            lambda: {"rows": [3]},
        ])

        self.assertEqual(results[0], {"rows": [1]})
        self.assertEqual(results[2], {"rows": [3]})
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertIn("boom", results[1]["error"])

    def test_parallel_fetch_handles_empty_call_list(self):
        self.assertEqual(parallel_fetch([]), [])


if __name__ == "__main__":
    unittest.main()
