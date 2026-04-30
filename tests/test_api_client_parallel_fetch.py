import unittest

from agent_system.actions.api_client import parallel_fetch


class ParallelFetchTests(unittest.TestCase):
    def test_preserves_input_order_and_isolates_failures(self):
        def first():
            return {"rows": [{"id": 1}]}

        def boom():
            raise RuntimeError("broken source")

        def third():
            return {"rows": [{"id": 3}]}

        results = parallel_fetch([first, boom, third])

        self.assertEqual(results[0], {"rows": [{"id": 1}]})
        self.assertEqual(results[2], {"rows": [{"id": 3}]})
        self.assertIn("broken source", results[1]["error"])
        self.assertEqual(results[1]["rows"], [])
        self.assertEqual(results[1]["row_count"], 0)
        self.assertEqual(results[1]["columns"], [])


if __name__ == "__main__":
    unittest.main()
