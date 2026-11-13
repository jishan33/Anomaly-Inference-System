import json
import httpx2
import unittest

from app.api.transaction import generate_risk_evaluated_transaction
from app.inference.clients import vllm_client
from openai import APITimeoutError
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

VLLM_URL = "https://vllm.example.test"
API_KEY = "test-key"
MODEL = "transaction-explainer"

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
        self.client = MagicMock()
        self.client.post = AsyncMock()
        self.transactions = [
            generate_risk_evaluated_transaction(),
            generate_risk_evaluated_transaction(),
        ]

    async def test_sends_one_conversation_per_transaction(self):
        self.client.post.return_value = {
            "choices": [
                {"index": 1, "message": {"content": "VIP explanation"}},
                {"index": 0, "message": {"content": "FREE explanation"}},
            ]
        }

        responses = await vllm_client.transactions_explainer(
            self.client, self.transactions
        )

        self.client.post.assert_awaited_once()
        call = self.client.post.await_args
        self.assertEqual(call.args, ("/chat/completions/batch",))
        self.assertIs(call.kwargs["cast_to"], dict)

        body = call.kwargs["body"]
        self.assertEqual(body["model"], MODEL)
        self.assertIs(body["stream"], False)

        conversations = body["messages"]
        self.assertEqual(len(conversations), len(self.transactions))

        for index, (conversation, transaction) in enumerate(
                zip(conversations, self.transactions)
        ):
            with self.subTest(transaction_index=index):
                system_message, user_message = conversation
                self.assertEqual(system_message["role"], "system")
                self.assertEqual(user_message["role"], "user")
                self.assertEqual(json.loads(user_message["content"]), transaction.model_dump(mode="json"))

        self.assertEqual(
            [(response.index, response.content) for response in responses],
            [(1, "VIP explanation"), (0, "FREE explanation")],
        )

    async def test_propagates_timeout_to_caller(self):
        timeout = APITimeoutError(
            request=httpx2.Request(
                "POST", f"{VLLM_URL}/v1/chat/completions/batch"
            )
        )
        self.client.post.side_effect = timeout

        with self.assertRaises(APITimeoutError) as raised:
            await vllm_client.transactions_explainer(
                self.client, self.transactions
            )

        self.assertIs(raised.exception, timeout)