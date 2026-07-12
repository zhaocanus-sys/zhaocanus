# -*- coding: utf-8 -*-
import unittest

from agent_system.actions import api_client


class ApiClientUtilityTest(unittest.TestCase):
    def test_safe_number_parsing_handles_report_formats(self):
        self.assertEqual(api_client.safe_float(None), 0.0)
        self.assertEqual(api_client.safe_float(" 1,234.50% "), 1234.5)
        self.assertEqual(api_client.safe_float("not-a-number", d=7.5), 7.5)
        self.assertEqual(api_client.safe_int("42.9"), 42)

    def test_parallel_fetch_empty_call_list_is_noop(self):
        self.assertEqual(api_client.parallel_fetch([]), [])

    def test_parallel_fetch_preserves_order_and_isolates_errors(self):
        def bad_call():
            raise RuntimeError("boom")

        results = api_client.parallel_fetch([
            lambda: {"name": "first"},
            bad_call,
            lambda: {"name": "third"},
        ])

        self.assertEqual(results[0], {"name": "first"})
        self.assertEqual(results[2], {"name": "third"})
        self.assertIn("boom", results[1]["error"])
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)


if __name__ == "__main__":
    unittest.main()
