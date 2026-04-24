import unittest

from agent_system.actions.api_client import parallel_fetch


class ParallelFetchTests(unittest.TestCase):
    def test_preserves_input_order_even_when_completion_order_differs(self):
        calls = [
            lambda: "first",
            lambda: "second",
            lambda: "third",
        ]

        result = parallel_fetch(calls)

        self.assertEqual(result, ["first", "second", "third"])

    def test_wraps_exceptions_into_error_payload(self):
        def bad_call():
            raise RuntimeError("boom")

        calls = [
            lambda: {"ok": True},
            bad_call,
        ]

        result = parallel_fetch(calls)

        self.assertEqual(result[0], {"ok": True})
        self.assertIsInstance(result[1], dict)
        self.assertIn("error", result[1])
        self.assertIn("boom", result[1]["error"])
        self.assertEqual(result[1]["rows"], [])
        self.assertEqual(result[1]["row_count"], 0)
        self.assertEqual(result[1]["columns"], [])


if __name__ == "__main__":
    unittest.main()
