import json
import httpx2
import unittest

from app.api.transaction import generate_risk_evaluated_transaction
from app.inference.clients import vllm_client
from openai import APITimeoutError, APIConnectionError, APIStatusError
from unittest.mock import AsyncMock, MagicMock, patch

from app.inference.models.risk_summary_model import to_risk_summary_requests

VLLM_URL = "https://vllm.example.test"
API_KEY = "test-key"
MODEL = "request-explainer"

class TestHealthCheck(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(
            patch.multiple(vllm_client, URL=VLLM_URL, API_KEY=API_KEY)
        )
        self.client_factory = self.enterContext(
            patch.object(vllm_client.httpx2, "AsyncClient")
        )
        http_client = self.client_factory.return_value.__aenter__.return_value
        self.get = http_client.get = AsyncMock()
        self.request = httpx2.Request("GET", f"{VLLM_URL}/health")

    async def test_returns_200_when_healthy(self):
        self.get.return_value = httpx2.Response(200, request=self.request)

        status = await vllm_client.health_check()

        self.assertEqual(status, 200)
        self.client_factory.assert_called_once_with(timeout=3.0)
        self.get.assert_awaited_once_with(
            str(self.request.url),
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

    async def test_wraps_503_as_runtime_error(self):
        self.get.return_value = httpx2.Response(503, request=self.request)

        with self.assertRaisesRegex(RuntimeError, "service is unavailable") as raised:
            await vllm_client.health_check()

        cause = raised.exception.__cause__
        self.assertIsInstance(cause, httpx2.HTTPStatusError)
        self.assertEqual(cause.response.status_code, 503)

    async def test_wraps_read_timeout_as_runtime_error(self):
        timeout = httpx2.ReadTimeout("Read timed out", request=self.request)
        self.get.side_effect = timeout

        with self.assertRaisesRegex(RuntimeError, "service is unavailable") as raised:
            await vllm_client.health_check()

        self.assertIs(raised.exception.__cause__, timeout)


class TestTransactionsExplainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        transaction_1 = generate_risk_evaluated_transaction()
        transaction_2 = generate_risk_evaluated_transaction()

        self.client = MagicMock()
        self.client.post = AsyncMock()
        self.transactions_with_ids = [
            (transaction_1, "job_id_1"),
            (transaction_2, "job_id_2")
        ]
        self.requests = to_risk_summary_requests(self.transactions_with_ids)
        self.request_counter = self.enterContext(
            patch.object(vllm_client, "VLLM_CLIENT_REQUESTS")
        )
        self.error_counter = self.enterContext(
            patch.object(vllm_client, "VLLM_CLIENT_ERRORS")
        )

    async def test_sends_one_conversation_per_transaction(self):
        self.client.post.return_value = {
            "choices": [
                {"index": 0, "message": {"content": "VIP explanation"}},
                {"index": 1, "message": {"content": "FREE explanation"}},
            ]
        }

        responses = await vllm_client.generate_risk_summaries(
            self.client, self.transactions_with_ids
        )

        self.client.post.assert_awaited_once()
        call = self.client.post.await_args
        self.assertEqual(call.args, ("/chat/completions/batch",))
        self.assertIs(call.kwargs["cast_to"], dict)

        body = call.kwargs["body"]
        self.assertEqual(body["model"], MODEL)
        self.assertIs(body["stream"], False)

        conversations = body["messages"]
        self.assertEqual(len(conversations), len(self.transactions_with_ids))

        for index, (conversation, requests) in enumerate(
                zip(conversations, self.requests)
        ):
            with self.subTest(transaction_index=index):
                system_message, user_message = conversation
                self.assertEqual(system_message["role"], "system")
                self.assertEqual(user_message["role"], "user")
                self.assertEqual(json.loads(user_message["content"]), requests.model_dump(mode="json"))

        self.assertEqual(
            [(response.index, response.content) for response in responses],
            [(0, "VIP explanation"), (1, "FREE explanation")],
        )

    async def test_propagates_timeout_to_caller(self):
        timeout = APITimeoutError(
            request=httpx2.Request(
                "POST", f"{VLLM_URL}/v1/chat/completions/batch"
            )
        )
        self.client.post.side_effect = timeout

        with self.assertRaises(APITimeoutError) as raised:
            await vllm_client.generate_risk_summaries(
                self.client, self.transactions_with_ids
            )

        self.assertIs(raised.exception, timeout)


    async def test_returns_empty_without_calling_vllm(self):
        responses = await vllm_client.generate_risk_summaries(
            self.client, []
        )

        self.assertEqual(responses, [])
        self.client.post.assert_not_awaited()
        self.request_counter.inc.assert_not_called()
        self.error_counter.labels.assert_not_called()

    async def test_records_and_propagates_transport_errors(self):
        request = httpx2.Request(
            "POST", f"{VLLM_URL}/v1/chat/completions/batch"
        )
        cases = [
            ("timeout", APITimeoutError(request=request)),
            (
                "connection",
                APIConnectionError(
                    message="Connection failed",
                    request=request,
                ),
            ),
        ]

        for error_type, error in cases:
            with self.subTest(error_type=error_type):
                self.request_counter.reset_mock()
                self.error_counter.reset_mock()
                self.client.post.reset_mock()
                self.client.post.side_effect = error

                with self.assertRaises(type(error)) as raised:
                    await vllm_client.generate_risk_summaries(
                        self.client, self.transactions_with_ids
                    )

                self.assertIs(raised.exception, error)
                self.request_counter.inc.assert_called_once_with()
                self.error_counter.labels.assert_called_once_with(
                    error_type, "none"
                )
                self.error_counter.labels.return_value.inc.assert_called_once_with()

    async def test_records_and_propagates_http_errors(self):
        request = httpx2.Request(
            "POST", f"{VLLM_URL}/v1/chat/completions/batch"
        )

        for status_code in (400, 401, 429, 500, 503):
            with self.subTest(status_code=status_code):
                self.request_counter.reset_mock()
                self.error_counter.reset_mock()

                error = APIStatusError(
                    "vLLM request failed",
                    response=httpx2.Response(
                        status_code, request=request
                    ),
                    body=None,
                )
                self.client.post.side_effect = error

                with self.assertRaises(APIStatusError) as raised:
                    await vllm_client.generate_risk_summaries(
                        self.client, self.transactions_with_ids
                    )

                self.assertIs(raised.exception, error)
                self.request_counter.inc.assert_called_once_with()
                self.error_counter.labels.assert_called_once_with(
                    "http", str(status_code)
                )
                self.error_counter.labels.return_value.inc.assert_called_once_with()

    async def test_rejects_invalid_responses(self):
        def choice(index, content="Risk summary"):
            return {
                "index": index,
                "message": {"content": content},
            }

        cases = {
            "missing_choices": {},
            "choices_not_list": {"choices": None},
            "missing_message": {
                "choices": [{"index": 0}, choice(1)]
            },
            "missing_content": {
                "choices": [
                    {"index": 0, "message": {}},
                    choice(1),
                ]
            },
            "invalid_content": {
                "choices": [choice(0, {}), choice(1)]
            },
            "empty_choices": {"choices": []},
            "missing_result": {"choices": [choice(0)]},
            "duplicate_indices": {
                "choices": [choice(0), choice(0)]
            },
            "unexpected_index": {
                "choices": [choice(0), choice(2)]
            },
            "extra_result": {
                "choices": [choice(0), choice(1), choice(2)]
            },
        }

        for case_name, payload in cases.items():
            with self.subTest(case=case_name):
                self.request_counter.reset_mock()
                self.error_counter.reset_mock()
                self.client.post.return_value = payload

                with self.assertRaisesRegex(
                        ValueError, "Invalid vLLM batch response"
                ) as raised:
                    await vllm_client.generate_risk_summaries(
                        self.client, self.transactions_with_ids
                    )

                self.assertIsNotNone(raised.exception.__cause__)
                self.request_counter.inc.assert_called_once_with()
                self.error_counter.labels.assert_called_once_with(
                    "invalid_response", "none"
                )
                self.error_counter.labels.return_value.inc.assert_called_once_with()