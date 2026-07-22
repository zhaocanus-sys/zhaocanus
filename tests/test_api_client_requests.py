import unittest
from unittest.mock import Mock, patch

from agent_system.actions import api_client


class ApiClientRequestTests(unittest.TestCase):
    @patch("agent_system.actions.api_client.api_config")
    @patch("agent_system.actions.api_client.requests.request")
    def test_daily_sends_auth_and_pagination_contract(self, request, api_config):
        api_config.return_value = {"api_key": "test-api-key"}
        response = Mock()
        response.json.return_value = {"rows": [{"amt": 100}], "row_count": 1}
        request.return_value = response

        result = api_client.daily("shop", "20260722", page=3, size=40)

        request.assert_called_once_with(
            "GET",
            f"{api_client.BASE_URL}/api/v1/team/shop/daily",
            headers={"X-API-Key": "test-api-key"},
            params={"page": 3, "page_size": 40, "date": "20260722"},
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result, {"rows": [{"amt": 100}], "row_count": 1})

    @patch("agent_system.actions.api_client.api_config")
    @patch("agent_system.actions.api_client.requests.request")
    def test_query_preserves_role_date_and_default_pagination(self, request, api_config):
        api_config.return_value = {"api_key": "test-api-key"}
        response = Mock()
        response.json.return_value = {"rows": []}
        request.return_value = response

        api_client.query("hongniang", "hourly", "20260201")

        request.assert_called_once_with(
            "GET",
            f"{api_client.BASE_URL}/api/v1/team/hongniang/query",
            headers={"X-API-Key": "test-api-key"},
            params={
                "page": 1,
                "page_size": 500,
                "table_role": "hourly",
                "date": "20260201",
            },
            timeout=30,
        )

    @patch("agent_system.actions.api_client.requests.request")
    def test_transport_http_and_json_failures_return_stable_empty_payload(self, request):
        transport_error = RuntimeError("connection reset")
        http_response = Mock()
        http_response.raise_for_status.side_effect = RuntimeError("503 unavailable")
        json_response = Mock()
        json_response.json.side_effect = ValueError("invalid json")

        scenarios = (
            (transport_error, "connection reset"),
            (http_response, "503 unavailable"),
            (json_response, "invalid json"),
        )
        for outcome, expected_error in scenarios:
            with self.subTest(expected_error=expected_error):
                request.reset_mock()
                if isinstance(outcome, Exception):
                    request.side_effect = outcome
                    request.return_value = None
                else:
                    request.side_effect = None
                    request.return_value = outcome

                result = api_client.health("app")

                self.assertEqual(
                    result,
                    {
                        "error": expected_error,
                        "rows": [],
                        "row_count": 0,
                        "columns": [],
                    },
                )


if __name__ == "__main__":
    unittest.main()
